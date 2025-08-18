"""
Redis-based session management with secure HTTP-only cookies and CSRF protection.
Replaces Streamlit session state with proper server-side session storage.
"""

import os
import secrets
import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from contextlib import contextmanager

import redis
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from cryptography.fernet import Fernet

from .pii_protection import get_structured_logger
from ..models.user import User, UserRole

logger = get_structured_logger().get_logger(__name__)


@dataclass
class SessionData:
    """Session data structure"""

    user_id: str
    email: str
    role: str
    created_at: datetime
    last_accessed: datetime
    csrf_token: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        data["last_accessed"] = self.last_accessed.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionData":
        """Create from dictionary"""
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        return cls(**data)


class RedisSessionManager:
    """Redis-based session manager with security features"""

    def __init__(
        self,
        redis_url: str = None,
        secret_key: str = None,
        session_timeout: int = 3600,  # 1 hour
        csrf_timeout: int = 1800,  # 30 minutes
        max_sessions_per_user: int = 5,
    ):

        # Redis connection
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)

        # Security configuration
        self.secret_key = secret_key or os.getenv("SESSION_SECRET_KEY")
        if not self.secret_key:
            raise ValueError("SESSION_SECRET_KEY environment variable is required")

        # Session configuration
        self.session_timeout = session_timeout
        self.csrf_timeout = csrf_timeout
        self.max_sessions_per_user = max_sessions_per_user

        # Serializers for secure token generation
        self.session_serializer = URLSafeTimedSerializer(self.secret_key)
        self.csrf_serializer = URLSafeTimedSerializer(self.secret_key + "_csrf")

        # Encryption for session data
        self.fernet = Fernet(self._derive_encryption_key())

        # Redis key prefixes
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.csrf_prefix = "csrf:"

        logger.info(
            "Redis session manager initialized",
            redis_url=self.redis_url.split("@")[-1],  # Hide credentials
            session_timeout=session_timeout,
        )

    def _derive_encryption_key(self) -> bytes:
        """Derive encryption key from secret key"""
        key_material = hashlib.pbkdf2_hmac(
            "sha256",
            self.secret_key.encode(),
            b"session_encryption_salt",
            100000,
            32,  # Ensure exactly 32 bytes
        )
        # Convert to URL-safe base64 for Fernet
        import base64

        return base64.urlsafe_b64encode(key_material)

    def _generate_session_id(self) -> str:
        """Generate cryptographically secure session ID"""
        return secrets.token_urlsafe(32)

    def _generate_csrf_token(self) -> str:
        """Generate CSRF token"""
        return secrets.token_urlsafe(32)

    def _encrypt_session_data(self, data: Dict[str, Any]) -> str:
        """Encrypt session data"""
        json_data = json.dumps(data, default=str)
        encrypted_data = self.fernet.encrypt(json_data.encode())
        return encrypted_data.decode()

    def _decrypt_session_data(self, encrypted_data: str) -> Dict[str, Any]:
        """Decrypt session data"""
        try:
            decrypted_data = self.fernet.decrypt(encrypted_data.encode())
            return json.loads(decrypted_data.decode())
        except Exception as e:
            logger.warning(
                "Failed to decrypt session data", error_type=type(e).__name__
            )
            return {}

    def create_session(
        self, user: User, ip_address: str = None, user_agent: str = None
    ) -> Tuple[str, str]:
        """
        Create new session for user

        Returns:
            Tuple of (session_token, csrf_token)
        """
        try:
            # Generate session ID and CSRF token
            session_id = self._generate_session_id()
            csrf_token = self._generate_csrf_token()

            # Create session data
            now = datetime.utcnow()
            session_data = SessionData(
                user_id=user.id,
                email=user.email,
                role=user.role,
                created_at=now,
                last_accessed=now,
                csrf_token=csrf_token,
                ip_address=ip_address,
                user_agent=user_agent,
            )

            # Encrypt and store session data
            encrypted_data = self._encrypt_session_data(session_data.to_dict())
            session_key = f"{self.session_prefix}{session_id}"

            # Store session with expiration
            self.redis_client.setex(session_key, self.session_timeout, encrypted_data)

            # Track user sessions for cleanup
            user_sessions_key = f"{self.user_sessions_prefix}{user.id}"
            self.redis_client.sadd(user_sessions_key, session_id)
            self.redis_client.expire(user_sessions_key, self.session_timeout)

            # Limit concurrent sessions per user
            self._cleanup_user_sessions(user.id)

            # Create signed session token
            session_token = self.session_serializer.dumps(session_id)

            logger.info(
                "Session created",
                user_id=user.id,
                session_id=session_id[:8] + "...",
                operation="create_session",
            )

            return session_token, csrf_token

        except Exception as e:
            logger.error(
                "Failed to create session",
                user_id=user.id,
                error_type=type(e).__name__,
                operation="create_session",
            )
            raise

    def get_session(self, session_token: str) -> Optional[SessionData]:
        """Get session data from token"""
        try:
            # Verify and extract session ID
            session_id = self.session_serializer.loads(
                session_token, max_age=self.session_timeout
            )

            # Retrieve session data
            session_key = f"{self.session_prefix}{session_id}"
            encrypted_data = self.redis_client.get(session_key)

            if not encrypted_data:
                logger.debug("Session not found", session_id=session_id[:8] + "...")
                return None

            # Decrypt and deserialize session data
            session_dict = self._decrypt_session_data(encrypted_data)
            if not session_dict:
                return None

            session_data = SessionData.from_dict(session_dict)

            # Update last accessed time
            session_data.last_accessed = datetime.utcnow()
            updated_data = self._encrypt_session_data(session_data.to_dict())

            # Extend session expiration
            self.redis_client.setex(session_key, self.session_timeout, updated_data)

            return session_data

        except (BadSignature, SignatureExpired) as e:
            logger.warning(
                "Invalid or expired session token",
                error_type=type(e).__name__,
                operation="get_session",
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get session",
                error_type=type(e).__name__,
                operation="get_session",
            )
            return None

    def validate_csrf_token(self, session_data: SessionData, csrf_token: str) -> bool:
        """Validate CSRF token against session"""
        try:
            return secrets.compare_digest(session_data.csrf_token, csrf_token)
        except Exception:
            return False

    def refresh_session(self, session_token: str) -> Optional[str]:
        """Refresh session and return new token"""
        try:
            session_data = self.get_session(session_token)
            if not session_data:
                return None

            # Check if session needs refresh (older than half timeout)
            age = datetime.utcnow() - session_data.created_at
            if age.total_seconds() < self.session_timeout / 2:
                return session_token  # No refresh needed

            # Create user object for new session
            user = User.create(
                email=session_data.email,
                password="temp-password",
                role=UserRole(session_data.role),
            )
            user.id = session_data.user_id

            # Invalidate old session
            self.invalidate_session(session_token)

            # Create new session
            new_token, _ = self.create_session(
                user, session_data.ip_address, session_data.user_agent
            )

            logger.info(
                "Session refreshed",
                user_id=session_data.user_id,
                operation="refresh_session",
            )

            return new_token

        except Exception as e:
            logger.error(
                "Failed to refresh session",
                error_type=type(e).__name__,
                operation="refresh_session",
            )
            return None

    def invalidate_session(self, session_token: str) -> bool:
        """Invalidate specific session"""
        try:
            session_id = self.session_serializer.loads(
                session_token, max_age=self.session_timeout
            )

            session_key = f"{self.session_prefix}{session_id}"

            # Get session data to find user ID
            encrypted_data = self.redis_client.get(session_key)
            if encrypted_data:
                session_dict = self._decrypt_session_data(encrypted_data)
                if session_dict:
                    user_id = session_dict.get("user_id")
                    if user_id:
                        # Remove from user sessions set
                        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
                        self.redis_client.srem(user_sessions_key, session_id)

            # Delete session
            result = self.redis_client.delete(session_key)

            logger.info(
                "Session invalidated",
                session_id=session_id[:8] + "...",
                operation="invalidate_session",
            )

            return bool(result)

        except Exception as e:
            logger.error(
                "Failed to invalidate session",
                error_type=type(e).__name__,
                operation="invalidate_session",
            )
            return False

    def invalidate_all_user_sessions(self, user_id: str) -> int:
        """Invalidate all sessions for a user"""
        try:
            user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
            session_ids = self.redis_client.smembers(user_sessions_key)

            count = 0
            for session_id in session_ids:
                session_key = f"{self.session_prefix}{session_id}"
                if self.redis_client.delete(session_key):
                    count += 1

            # Clear user sessions set
            self.redis_client.delete(user_sessions_key)

            logger.info(
                "All user sessions invalidated",
                user_id=user_id,
                count=count,
                operation="invalidate_all_user_sessions",
            )

            return count

        except Exception as e:
            logger.error(
                "Failed to invalidate user sessions",
                user_id=user_id,
                error_type=type(e).__name__,
                operation="invalidate_all_user_sessions",
            )
            return 0

    def _cleanup_user_sessions(self, user_id: str):
        """Cleanup old sessions if user has too many"""
        try:
            user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
            session_ids = list(self.redis_client.smembers(user_sessions_key))

            if len(session_ids) <= self.max_sessions_per_user:
                return

            # Get session creation times
            sessions_with_time = []
            for session_id in session_ids:
                session_key = f"{self.session_prefix}{session_id}"
                encrypted_data = self.redis_client.get(session_key)
                if encrypted_data:
                    session_dict = self._decrypt_session_data(encrypted_data)
                    if session_dict:
                        created_at = datetime.fromisoformat(session_dict["created_at"])
                        sessions_with_time.append((session_id, created_at))

            # Sort by creation time and remove oldest
            sessions_with_time.sort(key=lambda x: x[1])
            sessions_to_remove = sessions_with_time[: -self.max_sessions_per_user]

            for session_id, _ in sessions_to_remove:
                session_key = f"{self.session_prefix}{session_id}"
                self.redis_client.delete(session_key)
                self.redis_client.srem(user_sessions_key, session_id)

            if sessions_to_remove:
                logger.info(
                    "Cleaned up old sessions",
                    user_id=user_id,
                    removed_count=len(sessions_to_remove),
                    operation="cleanup_user_sessions",
                )

        except Exception as e:
            logger.error(
                "Failed to cleanup user sessions",
                user_id=user_id,
                error_type=type(e).__name__,
                operation="cleanup_user_sessions",
            )

    def get_session_info(self, user_id: str) -> Dict[str, Any]:
        """Get session information for user"""
        try:
            user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
            session_ids = self.redis_client.smembers(user_sessions_key)

            sessions = []
            for session_id in session_ids:
                session_key = f"{self.session_prefix}{session_id}"
                encrypted_data = self.redis_client.get(session_key)
                if encrypted_data:
                    session_dict = self._decrypt_session_data(encrypted_data)
                    if session_dict:
                        sessions.append(
                            {
                                "session_id": session_id[:8] + "...",
                                "created_at": session_dict["created_at"],
                                "last_accessed": session_dict["last_accessed"],
                                "ip_address": session_dict.get("ip_address"),
                                "user_agent": (
                                    session_dict.get("user_agent", "")[:50] + "..."
                                    if session_dict.get("user_agent")
                                    else None
                                ),
                            }
                        )

            return {
                "user_id": user_id,
                "active_sessions": len(sessions),
                "sessions": sessions,
            }

        except Exception as e:
            logger.error(
                "Failed to get session info",
                user_id=user_id,
                error_type=type(e).__name__,
                operation="get_session_info",
            )
            return {"user_id": user_id, "active_sessions": 0, "sessions": []}

    @contextmanager
    def get_redis_connection(self):
        """Context manager for Redis connection"""
        try:
            yield self.redis_client
        except Exception as e:
            logger.error(
                "Redis connection error",
                error_type=type(e).__name__,
                operation="get_redis_connection",
            )
            raise

    def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            self.redis_client.ping()
            return True
        except Exception as e:
            logger.error(
                "Redis health check failed",
                error_type=type(e).__name__,
                operation="health_check",
            )
            return False


# Global session manager instance
_session_manager = None


def get_session_manager() -> RedisSessionManager:
    """Get global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = RedisSessionManager()
    return _session_manager
