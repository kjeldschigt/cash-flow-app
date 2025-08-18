"""
Session validation middleware for Streamlit applications.
Validates sessions on each request and handles authentication flow.
"""

import os
import time
from typing import Dict, Any, Optional, Callable
from functools import wraps
from datetime import datetime

import streamlit as st

from ..security.session_manager import get_session_manager, SessionData
from ..security.cookie_manager import get_cookie_manager
from ..security.rate_limiter import create_rate_limiter, RateLimitRule
from ..security.pii_protection import get_structured_logger
from ..models.user import User, UserRole

logger = get_structured_logger().get_logger(__name__)


class SessionMiddleware:
    """Session validation middleware for Streamlit"""

    def __init__(self):
        self.session_manager = get_session_manager()
        self.cookie_manager = get_cookie_manager()

        # Initialize rate limiter if Redis is available
        try:
            with self.session_manager.get_redis_connection() as redis_client:
                self.rate_limiter = create_rate_limiter(redis_client)
        except Exception as e:
            logger.warning("Rate limiter not available", error_type=type(e).__name__)
            self.rate_limiter = None

        # Middleware configuration
        self.exempt_paths = {"/login", "/register", "/health", "/favicon.ico"}

        self.public_pages = {"Login", "Register", "Health Check"}

        logger.info("Session middleware initialized")

    def validate_session(self, require_auth: bool = True) -> Optional[SessionData]:
        """
        Validate current session

        Args:
            require_auth: Whether authentication is required

        Returns:
            SessionData if valid session, None otherwise
        """
        try:
            # Get session token from cookie
            session_token = self.cookie_manager.get_session_token()
            if not session_token:
                if require_auth:
                    logger.debug("No session token found", operation="validate_session")
                return None

            # Validate session with Redis backend
            session_data = self.session_manager.get_session(session_token)
            if not session_data:
                if require_auth:
                    logger.debug("Invalid session token", operation="validate_session")
                return None

            # Check session age and refresh if needed
            age = datetime.utcnow() - session_data.created_at
            if age.total_seconds() > self.session_manager.session_timeout / 2:
                # Refresh session
                new_token = self.session_manager.refresh_session(session_token)
                if new_token:
                    # Update cookie with new token
                    cookie_js = self.cookie_manager.set_session_cookie(new_token)
                    st.components.v1.html(cookie_js, height=0)
                    logger.info(
                        "Session refreshed",
                        user_id=session_data.user_id,
                        operation="validate_session",
                    )

            # Store session data in Streamlit session state for easy access
            st.session_state["_session_data"] = session_data
            st.session_state["_authenticated"] = True
            st.session_state["_user_id"] = session_data.user_id
            st.session_state["_user_email"] = session_data.email
            st.session_state["_user_role"] = session_data.role

            return session_data

        except Exception as e:
            logger.error(
                "Session validation failed",
                error_type=type(e).__name__,
                operation="validate_session",
            )
            return None

    def require_authentication(self, min_role: UserRole = UserRole.USER) -> Callable:
        """
        Decorator to require authentication for Streamlit pages

        Args:
            min_role: Minimum required user role

        Returns:
            Decorator function
        """

        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Check if current page is public
                page_title = st.get_option("page_title") or "Unknown"
                if page_title in self.public_pages:
                    return func(*args, **kwargs)

                # Validate session
                session_data = self.validate_session(require_auth=True)
                if not session_data:
                    self._redirect_to_login("Authentication required")
                    return

                # Check role permissions
                user_role = UserRole(session_data.role)
                if user_role.value < min_role.value:
                    st.error("❌ Insufficient permissions")
                    st.stop()

                # Check rate limiting for authenticated actions
                if self.rate_limiter:
                    rate_result = self.rate_limiter.check_rate_limit(
                        session_data.user_id, "api_call"
                    )
                    if not rate_result.allowed:
                        st.error(
                            f"❌ Rate limit exceeded. Try again in {rate_result.retry_after} seconds."
                        )
                        st.stop()

                return func(*args, **kwargs)

            return wrapper

        return decorator

    def check_csrf_protection(self, form_data: Dict[str, Any] = None) -> bool:
        """
        Check CSRF protection for form submissions

        Args:
            form_data: Form data containing CSRF token

        Returns:
            True if CSRF check passes
        """
        try:
            session_data = st.session_state.get("_session_data")
            if not session_data:
                return False

            # Get CSRF token from cookie or form
            if form_data:
                # Form submission - validate against session
                return self.cookie_manager.validate_csrf_from_form(
                    form_data, session_data.csrf_token
                )
            else:
                # Regular page load - just check if CSRF token exists
                csrf_token = self.cookie_manager.get_csrf_token()
                return csrf_token == session_data.csrf_token

        except Exception as e:
            logger.error(
                "CSRF check failed",
                error_type=type(e).__name__,
                operation="check_csrf_protection",
            )
            return False

    def login_user(
        self, user: User, ip_address: str = None, user_agent: str = None
    ) -> bool:
        """
        Login user and create session

        Args:
            user: User object
            ip_address: Client IP address
            user_agent: Client user agent

        Returns:
            True if login successful
        """
        try:
            # Check rate limiting for login attempts
            if self.rate_limiter:
                identifier = ip_address or user.email
                rate_result = self.rate_limiter.check_rate_limit(
                    identifier, "auth_login"
                )
                if not rate_result.allowed:
                    st.error(
                        f"❌ Too many login attempts. Try again in {rate_result.retry_after} seconds."
                    )
                    return False

            # Create session
            session_token, csrf_token = self.session_manager.create_session(
                user, ip_address, user_agent
            )

            # Set secure cookies
            session_cookie_js = self.cookie_manager.set_session_cookie(session_token)
            csrf_cookie_js = self.cookie_manager.set_csrf_cookie(csrf_token)

            # Inject cookies using Streamlit components
            cookie_html = f"""
            {session_cookie_js}
            {csrf_cookie_js}
            {self.cookie_manager.inject_cookie_reader()}
            """
            st.components.v1.html(cookie_html, height=0)

            # Update session state
            st.session_state["_authenticated"] = True
            st.session_state["_user_id"] = user.id
            st.session_state["_user_email"] = user.email
            st.session_state["_user_role"] = user.role.value
            st.session_state["_session_token"] = session_token
            st.session_state["_csrf_token"] = csrf_token

            logger.info(
                "User logged in successfully", user_id=user.id, operation="login_user"
            )

            return True

        except Exception as e:
            logger.error(
                "Login failed",
                user_id=user.id,
                error_type=type(e).__name__,
                operation="login_user",
            )
            return False

    def logout_user(self) -> bool:
        """Logout current user and invalidate session"""
        try:
            if not self.is_authenticated():
                return True

            session_token = self.cookie_manager.get_session_cookie()
            session_id = None

            if session_token:
                # Get session ID before invalidation
                session_data = self.session_manager.get_session(session_token)
                if session_data:
                    session_id = session_token

                # Invalidate session in Redis
                self.session_manager.invalidate_session(session_token)

                # Clear cookies
                self.cookie_manager.clear_session_cookie()
                self.cookie_manager.clear_csrf_cookie()

            # Clear KeyVault cache for this session
            try:
                from src.services.key_vault import clear_session_vault

                clear_session_vault(session_id)
                logger.info(
                    "KeyVaultService cache cleared on logout",
                    session_id=session_id,
                )
            except Exception as e:
                logger.warning(f"Failed to clear KeyVaultService cache: {e}")

            # Clear API Key Resolver cache on logout
            try:
                from src.services.api_key_resolver import clear_resolver_cache

                clear_resolver_cache(
                    session_id, session_data.get("user_id") if session_data else None
                )
                logger.info(
                    "API Key Resolver cache cleared on logout",
                    session_id=session_id,
                )
            except Exception as e:
                logger.warning(f"Failed to clear API Key Resolver cache: {e}")

            # Clear Streamlit session state
            for key in list(st.session_state.keys()):
                if key.startswith(("user_", "auth_", "session_")):
                    del st.session_state[key]

            st.session_state.authenticated = False
            st.session_state.user_info = None

            logger.info(
                "User logged out successfully",
                operation="logout_user",
                session_cleared=session_id is not None,
            )

            return True

        except Exception as e:
            logger.error("Failed to logout user", error=str(e), operation="logout_user")
            return False

    def get_current_user(self) -> Optional[User]:
        """
        Get current authenticated user

        Returns:
            User object if authenticated, None otherwise
        """
        try:
            session_data = st.session_state.get("_session_data")
            if not session_data:
                return None

            return User(
                id=session_data.user_id,
                email=session_data.email,
                role=UserRole(session_data.role),
            )

        except Exception as e:
            logger.error(
                "Failed to get current user",
                error_type=type(e).__name__,
                operation="get_current_user",
            )
            return None

    def is_authenticated(self) -> bool:
        """Check if current user is authenticated"""
        return bool(st.session_state.get("_authenticated", False))

    def has_role(self, required_role: UserRole) -> bool:
        """Check if current user has required role"""
        try:
            current_role = st.session_state.get("_user_role")
            if not current_role:
                return False

            user_role = UserRole(current_role)
            return user_role.value >= required_role.value

        except Exception:
            return False

    def _redirect_to_login(self, message: str = "Please log in"):
        """Redirect to login page"""
        st.warning(f"🔐 {message}")

        # Show login form or redirect
        if st.button("Go to Login"):
            st.switch_page("pages/Login.py")

        st.stop()

    def _get_client_info(self) -> Dict[str, str]:
        """Get client IP and user agent from request"""
        try:
            # Try to get from Streamlit context
            if hasattr(st, "context") and hasattr(st.context, "headers"):
                headers = st.context.headers
                ip_address = (
                    headers.get("X-Forwarded-For", "").split(",")[0].strip()
                    or headers.get("X-Real-IP", "")
                    or headers.get("Remote-Addr", "unknown")
                )
                user_agent = headers.get("User-Agent", "unknown")
            else:
                ip_address = "unknown"
                user_agent = "unknown"

            return {"ip_address": ip_address, "user_agent": user_agent}

        except Exception as e:
            logger.debug(
                "Could not get client info",
                error_type=type(e).__name__,
                operation="_get_client_info",
            )
            return {"ip_address": "unknown", "user_agent": "unknown"}

    def inject_security_headers(self) -> str:
        """Inject security headers via JavaScript"""
        headers = self.cookie_manager.generate_secure_headers()

        js_code = """
        <script>
            // Note: These headers should ideally be set by the web server
            // This is a fallback for development/testing
            console.log("Security headers should be configured at web server level");
        </script>
        """

        return js_code

    def get_session_info(self) -> Dict[str, Any]:
        """Get current session information"""
        try:
            session_data = st.session_state.get("_session_data")
            if not session_data:
                return {"authenticated": False}

            return {
                "authenticated": True,
                "user_id": session_data.user_id,
                "email": session_data.email,
                "role": session_data.role,
                "created_at": session_data.created_at.isoformat(),
                "last_accessed": session_data.last_accessed.isoformat(),
                "ip_address": session_data.ip_address,
                "csrf_token_present": bool(session_data.csrf_token),
            }

        except Exception as e:
            logger.error(
                "Failed to get session info",
                error_type=type(e).__name__,
                operation="get_session_info",
            )
            return {"authenticated": False, "error": str(e)}


# Global middleware instance
_session_middleware = None


def get_session_middleware() -> SessionMiddleware:
    """Get global session middleware instance"""
    global _session_middleware
    if _session_middleware is None:
        _session_middleware = SessionMiddleware()
    return _session_middleware


# Convenience decorators
def require_auth(min_role: UserRole = UserRole.USER):
    """Convenience decorator for requiring authentication"""
    return get_session_middleware().require_authentication(min_role)


def require_admin():
    """Convenience decorator for requiring admin role"""
    return require_auth(UserRole.ADMIN)


def require_manager():
    """Convenience decorator for requiring manager role"""
    return require_auth(UserRole.MANAGER)
