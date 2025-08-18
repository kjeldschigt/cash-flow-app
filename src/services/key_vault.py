"""
Secure API Key Vault Service with encryption, caching, and audit logging
"""

import os
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any
from contextlib import contextmanager
from dataclasses import dataclass
import logging

from src.security.api_key_encryption import APIKeyEncryption
from src.services.api_key_test_service import APIKeyTestService

logger = logging.getLogger(__name__)


@dataclass
class APIKeyInfo:
    """Information about an API key"""

    id: int
    key_name: str
    masked_value: str
    service_type: str
    added_by_user: int
    created_at: datetime
    last_modified: datetime
    is_active: bool
    description: Optional[str] = None


@dataclass
class AuditLogEntry:
    """Audit log entry for key operations"""

    operation: str
    key_name: str
    user_id: int
    timestamp: datetime
    success: bool
    error_message: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


@dataclass
class CachedAPIKey:
    """Cached API key with metadata"""

    key_name: str
    key_value: str
    service_type: str
    cached_at: datetime
    access_count: int = 0
    last_accessed: Optional[datetime] = None


class APIKeyContext:
    """Context manager for secure API key access"""

    def __init__(self, key_name: str, key_value: str, service_type: str):
        self.key_name = key_name
        self.key_value = key_value
        self.service_type = service_type

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Securely clear the key from memory
        if hasattr(self, "key_value") and self.key_value:
            # Overwrite the string in memory (Python limitation - best effort)
            self.key_value = "0" * len(self.key_value)
            logger.info(f"API key '{self.key_name}' cleared from context memory")


class KeyVaultService:
    """Secure API key management service with caching and audit logging"""

    def __init__(self, session_id: str, user_id: int):
        """Initialize KeyVaultService for a session"""
        self.session_id = session_id
        self.user_id = user_id
        self._cache: Dict[str, CachedAPIKey] = {}
        self._cache_timeout = timedelta(minutes=30)  # 30-minute cache timeout
        self._lock = threading.RLock()

        # Initialize encryption service
        self.encryption = APIKeyEncryption()

        # Initialize API key test service
        self.test_service = APIKeyTestService()

        # Database connection
        self.db_path = os.getenv("DATABASE_URL", "cash_flow_app.db").replace(
            "sqlite:///", ""
        )

        logger.info(
            f"KeyVaultService initialized for session {session_id[:8]}... user {user_id}"
        )

    def _get_db_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        return sqlite3.connect(self.db_path)

    def _log_audit_event(
        self,
        operation: str,
        key_name: str,
        success: bool = True,
        error_message: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log audit event for key operation"""
        audit_entry = AuditLogEntry(
            operation=operation,
            key_name=key_name,
            user_id=self.user_id,
            timestamp=datetime.utcnow(),
            success=success,
            error_message=error_message,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO audit_logs 
                    (operation, key_name, user_id, timestamp, success, error_message, ip_address, user_agent)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        audit_entry.operation,
                        audit_entry.key_name,
                        audit_entry.user_id,
                        audit_entry.timestamp.isoformat(),
                        audit_entry.success,
                        audit_entry.error_message,
                        audit_entry.ip_address,
                        audit_entry.user_agent,
                    ),
                )
                conn.commit()
        except Exception as e:
            logger.error(f"Failed to log audit event: {e}")

    def store_api_key(
        self,
        key_name: str,
        api_key: str,
        service_type: str,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Store API key in vault with encryption

        Args:
            key_name: Unique name for the API key
            api_key: The actual API key value
            service_type: Type of service (stripe, openai, etc.)
            description: Optional description
            ip_address: Client IP for audit
            user_agent: Client user agent for audit

        Returns:
            Tuple of (success, message)
        """
        try:
            # Encrypt the API key
            encrypted_key = self.encryption.encrypt_api_key(api_key)

            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO api_keys 
                    (key_name, encrypted_value, service_type, added_by_user, description)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    (key_name, encrypted_key, service_type, self.user_id, description),
                )
                conn.commit()

            # Clear from cache if exists
            with self._lock:
                if key_name in self._cache:
                    del self._cache[key_name]

            self._log_audit_event(
                "store_api_key", key_name, True, None, ip_address, user_agent
            )
            logger.info(f"API key '{key_name}' stored successfully in vault")

            return True, f"API key '{key_name}' stored successfully in vault"

        except sqlite3.IntegrityError:
            error_msg = f"API key '{key_name}' already exists"
            self._log_audit_event(
                "store_api_key", key_name, False, error_msg, ip_address, user_agent
            )
            return False, error_msg
        except Exception as e:
            error_msg = f"Failed to store API key: {str(e)}"
            self._log_audit_event(
                "store_api_key", key_name, False, error_msg, ip_address, user_agent
            )
            logger.error(error_msg)
            return False, error_msg

    @contextmanager
    def retrieve_api_key(
        self,
        key_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """
        Retrieve API key using context manager for secure access

        Args:
            key_name: Name of the API key to retrieve
            ip_address: Client IP for audit
            user_agent: Client user agent for audit

        Yields:
            APIKeyContext with decrypted key or None if not found
        """
        try:
            # Check cache first
            with self._lock:
                if key_name in self._cache:
                    cached = self._cache[key_name]
                    # Check if cache is still valid
                    if datetime.utcnow() - cached.cached_at < self._cache_timeout:
                        cached.access_count += 1
                        cached.last_accessed = datetime.utcnow()

                        self._log_audit_event(
                            "retrieve_key_cached",
                            key_name,
                            True,
                            None,
                            ip_address,
                            user_agent,
                        )
                        yield APIKeyContext(
                            key_name, cached.key_value, cached.service_type
                        )
                        return
                    else:
                        # Cache expired, remove it
                        del self._cache[key_name]

            # Retrieve from database
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT encrypted_value, service_type FROM api_keys 
                    WHERE key_name = ? AND is_active = 1
                """,
                    (key_name,),
                )
                result = cursor.fetchone()

            if not result:
                self._log_audit_event(
                    "retrieve_key",
                    key_name,
                    False,
                    "Key not found",
                    ip_address,
                    user_agent,
                )
                yield None
                return

            encrypted_value, service_type = result

            # Decrypt the key
            decrypted_key = self.encryption.decrypt_api_key(encrypted_value)

            # Cache the decrypted key
            with self._lock:
                self._cache[key_name] = CachedAPIKey(
                    key_name=key_name,
                    key_value=decrypted_key,
                    service_type=service_type,
                    cached_at=datetime.utcnow(),
                    access_count=1,
                    last_accessed=datetime.utcnow(),
                )

            self._log_audit_event(
                "retrieve_key", key_name, True, None, ip_address, user_agent
            )
            yield APIKeyContext(key_name, decrypted_key, service_type)

        except Exception as e:
            error_msg = f"Failed to retrieve API key: {str(e)}"
            self._log_audit_event(
                "retrieve_key", key_name, False, error_msg, ip_address, user_agent
            )
            logger.error(error_msg)
            yield None

    def update_api_key(
        self,
        key_name: str,
        new_api_key: str,
        description: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Update API key in vault

        Args:
            key_name: Name of the API key to update
            new_api_key: New API key value
            description: Updated description
            ip_address: Client IP for audit
            user_agent: Client user agent for audit

        Returns:
            Tuple of (success, message)
        """
        try:
            # Encrypt the new API key
            encrypted_key = self.encryption.encrypt_api_key(new_api_key)

            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE api_keys 
                    SET encrypted_value = ?, description = ?, last_modified = CURRENT_TIMESTAMP
                    WHERE key_name = ? AND is_active = 1
                """,
                    (encrypted_key, description, key_name),
                )

                if cursor.rowcount == 0:
                    error_msg = f"API key '{key_name}' not found or inactive"
                    self._log_audit_event(
                        "update_key", key_name, False, error_msg, ip_address, user_agent
                    )
                    return False, error_msg

                conn.commit()

            # Clear from cache
            with self._lock:
                if key_name in self._cache:
                    del self._cache[key_name]

            self._log_audit_event(
                "update_key", key_name, True, None, ip_address, user_agent
            )
            logger.info(f"API key '{key_name}' updated successfully in vault")

            return True, f"API key '{key_name}' updated successfully in vault"

        except Exception as e:
            error_msg = f"Failed to update API key: {str(e)}"
            self._log_audit_event(
                "update_key", key_name, False, error_msg, ip_address, user_agent
            )
            logger.error(error_msg)
            return False, error_msg

    def delete_api_key(
        self,
        key_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Delete API key from vault (soft delete)

        Args:
            key_name: Name of the API key to delete
            ip_address: Client IP for audit
            user_agent: Client user agent for audit

        Returns:
            Tuple of (success, message)
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE api_keys 
                    SET is_active = 0, last_modified = CURRENT_TIMESTAMP
                    WHERE key_name = ? AND is_active = 1
                """,
                    (key_name,),
                )

                if cursor.rowcount == 0:
                    error_msg = f"API key '{key_name}' not found or already inactive"
                    self._log_audit_event(
                        "delete_key", key_name, False, error_msg, ip_address, user_agent
                    )
                    return False, error_msg

                conn.commit()

            # Clear from cache
            with self._lock:
                if key_name in self._cache:
                    del self._cache[key_name]

            self._log_audit_event(
                "delete_key", key_name, True, None, ip_address, user_agent
            )
            logger.info(f"API key '{key_name}' deleted successfully from vault")

            return True, f"API key '{key_name}' deleted successfully from vault"

        except Exception as e:
            error_msg = f"Failed to delete API key: {str(e)}"
            self._log_audit_event(
                "delete_key", key_name, False, error_msg, ip_address, user_agent
            )
            logger.error(error_msg)
            return False, error_msg

    def list_api_keys(
        self, service_type: Optional[str] = None, include_inactive: bool = False
    ) -> List[APIKeyInfo]:
        """
        List API keys in vault

        Args:
            service_type: Filter by service type
            include_inactive: Include inactive keys

        Returns:
            List of APIKeyInfo objects
        """
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()

                query = """
                    SELECT id, key_name, encrypted_value, service_type, added_by_user, 
                           created_at, last_modified, is_active, description
                    FROM api_keys
                    WHERE 1=1
                """
                params = []

                if not include_inactive:
                    query += " AND is_active = 1"

                if service_type:
                    query += " AND service_type = ?"
                    params.append(service_type)

                query += " ORDER BY created_at DESC"

                cursor.execute(query, params)
                results = cursor.fetchall()

            api_keys = []
            for row in results:
                # Decrypt and mask the key for display
                try:
                    decrypted_key = self.encryption.decrypt_api_key(row[2])
                    masked_value = self.encryption.mask_api_key(decrypted_key, row[3])
                except Exception:
                    masked_value = "****ERROR****"

                api_keys.append(
                    APIKeyInfo(
                        id=row[0],
                        key_name=row[1],
                        masked_value=masked_value,
                        service_type=row[3],
                        added_by_user=row[4],
                        created_at=(
                            datetime.fromisoformat(row[5])
                            if row[5]
                            else datetime.utcnow()
                        ),
                        last_modified=(
                            datetime.fromisoformat(row[6])
                            if row[6]
                            else datetime.utcnow()
                        ),
                        is_active=bool(row[7]),
                        description=row[8],
                    )
                )

            return api_keys

        except Exception as e:
            logger.error(f"Failed to list API keys: {str(e)}")
            return []

    def test_api_key(
        self,
        key_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Test API key connection

        Args:
            key_name: Name of the API key to test
            ip_address: Client IP for audit
            user_agent: Client user agent for audit

        Returns:
            Tuple of (success, message, details)
        """
        try:
            with self.retrieve_api_key(key_name, ip_address, user_agent) as key_context:
                if not key_context:
                    error_msg = f"API key '{key_name}' not found"
                    self._log_audit_event(
                        "test_key", key_name, False, error_msg, ip_address, user_agent
                    )
                    return False, error_msg, {}

                # Test the API key
                success, message, details = self.test_service.test_api_key(
                    key_context.key_value, key_context.service_type
                )

                self._log_audit_event(
                    "test_key",
                    key_name,
                    success,
                    None if success else message,
                    ip_address,
                    user_agent,
                )

                return success, message, details

        except Exception as e:
            error_msg = f"Failed to test API key: {str(e)}"
            self._log_audit_event(
                "test_key", key_name, False, error_msg, ip_address, user_agent
            )
            logger.error(error_msg)
            return False, error_msg, {}

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            cache_info = {}
            for key_name, cached in self._cache.items():
                age_minutes = (
                    datetime.utcnow() - cached.cached_at
                ).total_seconds() / 60
                cache_info[key_name] = {
                    "cached_at": cached.cached_at.isoformat(),
                    "age_minutes": age_minutes,
                    "access_count": cached.access_count,
                    "last_accessed": (
                        cached.last_accessed.isoformat()
                        if cached.last_accessed
                        else None
                    ),
                }

            return {
                "session_id": self.session_id,
                "cached_keys": len(self._cache),
                "cache_timeout_minutes": self._cache_timeout.total_seconds() / 60,
                "keys": cache_info,
            }

    def clear_cache(self):
        """Clear all cached keys"""
        with self._lock:
            # Securely clear key values
            for cached in self._cache.values():
                if hasattr(cached, "key_value") and cached.key_value:
                    cached.key_value = "0" * len(cached.key_value)

            self._cache.clear()
            logger.info(f"Cache cleared for session {self.session_id}")

    def cleanup_expired_cache(self):
        """Remove expired entries from cache"""
        with self._lock:
            expired_keys = []
            for key_name, cached in self._cache.items():
                if datetime.utcnow() - cached.cached_at > self._cache_timeout:
                    expired_keys.append(key_name)

            for key_name in expired_keys:
                self._remove_from_cache(key_name)

            if expired_keys:
                logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def _remove_from_cache(self, key_name: str):
        """Securely remove key from cache"""
        if key_name in self._cache:
            cached = self._cache[key_name]
            if hasattr(cached, "key_value") and cached.key_value:
                cached.key_value = "0" * len(cached.key_value)
            del self._cache[key_name]

    def get_audit_logs(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get audit logs for this session/user"""
        try:
            with self._get_db_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT operation, key_name, user_id, timestamp, success, 
                           error_message, ip_address, user_agent
                    FROM audit_logs
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                """,
                    (self.user_id, limit),
                )

                results = cursor.fetchall()

                logs = []
                for row in results:
                    logs.append(
                        {
                            "operation": row[0],
                            "key_name": row[1],
                            "user_id": row[2],
                            "timestamp": row[3],
                            "success": bool(row[4]),
                            "error_message": row[5],
                            "ip_address": row[6],
                            "user_agent": row[7],
                        }
                    )

                return logs

        except Exception as e:
            logger.error(f"Failed to get audit logs: {str(e)}")
            return []


# Global instances per session
_key_vault_instances: Dict[str, KeyVaultService] = {}
_vault_lock = threading.RLock()


def get_key_vault_service(session_id: str, user_id: int) -> KeyVaultService:
    """Get KeyVaultService instance for session"""
    global _key_vault_instances

    if session_id not in _key_vault_instances:
        _key_vault_instances[session_id] = KeyVaultService(session_id, user_id)

    return _key_vault_instances[session_id]


def clear_session_vault(session_id: str):
    """Clear vault cache for specific session (called on logout)"""
    global _key_vault_instances

    if session_id in _key_vault_instances:
        try:
            _key_vault_instances[session_id].clear_cache()
            del _key_vault_instances[session_id]
            logger.info(f"Cleared vault cache for session: {session_id[:8]}...")
        except Exception as e:
            logger.error(
                f"Error clearing vault cache for session {session_id[:8]}...: {e}"
            )
