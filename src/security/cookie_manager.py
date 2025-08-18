"""
Secure HTTP-only cookie management with CSRF protection for Streamlit applications.
Handles session tokens and CSRF tokens with proper security headers.
"""

import os
import secrets
import hashlib
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
from urllib.parse import quote, unquote

import streamlit as st
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from .pii_protection import get_structured_logger

logger = get_structured_logger().get_logger(__name__)


class SecureCookieManager:
    """Secure cookie manager for Streamlit with HTTP-only cookies and CSRF protection"""

    def __init__(self, secret_key: str = None, domain: str = None, secure: bool = None):
        self.secret_key = (
            secret_key
            or os.getenv("COOKIE_SECRET_KEY")
            or os.getenv("SESSION_SECRET_KEY")
        )
        if not self.secret_key:
            raise ValueError(
                "COOKIE_SECRET_KEY or SESSION_SECRET_KEY environment variable is required"
            )

        self.domain = domain or os.getenv("COOKIE_DOMAIN")
        self.secure = (
            secure
            if secure is not None
            else (os.getenv("ENVIRONMENT", "development") == "production")
        )

        # Cookie configuration
        self.session_cookie_name = "session_token"
        self.csrf_cookie_name = "csrf_token"
        self.cookie_max_age = 3600  # 1 hour

        # Serializers for secure cookie signing
        self.cookie_serializer = URLSafeTimedSerializer(self.secret_key)

        logger.info(
            "Secure cookie manager initialized",
            secure=self.secure,
            domain=self.domain or "default",
        )

    def set_session_cookie(self, session_token: str, max_age: int = None) -> str:
        """
        Set secure HTTP-only session cookie

        Args:
            session_token: The session token to store
            max_age: Cookie expiration in seconds

        Returns:
            JavaScript code to set the cookie
        """
        try:
            max_age = max_age or self.cookie_max_age
            expires = datetime.utcnow() + timedelta(seconds=max_age)

            # Sign the token for integrity
            signed_token = self.cookie_serializer.dumps(session_token)

            # Build cookie attributes
            cookie_attrs = [
                f"{self.session_cookie_name}={quote(signed_token)}",
                f"Max-Age={max_age}",
                f"Expires={expires.strftime('%a, %d %b %Y %H:%M:%S GMT')}",
                "Path=/",
                "HttpOnly",
                "SameSite=Strict",
            ]

            if self.secure:
                cookie_attrs.append("Secure")

            if self.domain:
                cookie_attrs.append(f"Domain={self.domain}")

            cookie_string = "; ".join(cookie_attrs)

            # JavaScript to set cookie (workaround for Streamlit limitations)
            js_code = f"""
            <script>
                document.cookie = "{cookie_string}";
                console.log("Session cookie set");
            </script>
            """

            logger.debug(
                "Session cookie set",
                max_age=max_age,
                secure=self.secure,
                operation="set_session_cookie",
            )

            return js_code

        except Exception as e:
            logger.error(
                "Failed to set session cookie",
                error_type=type(e).__name__,
                operation="set_session_cookie",
            )
            return ""

    def set_csrf_cookie(self, csrf_token: str, max_age: int = None) -> str:
        """
        Set CSRF token cookie (readable by JavaScript for form submissions)

        Args:
            csrf_token: The CSRF token to store
            max_age: Cookie expiration in seconds

        Returns:
            JavaScript code to set the cookie
        """
        try:
            max_age = max_age or self.cookie_max_age
            expires = datetime.utcnow() + timedelta(seconds=max_age)

            # Build cookie attributes (not HttpOnly so JS can read it)
            cookie_attrs = [
                f"{self.csrf_cookie_name}={quote(csrf_token)}",
                f"Max-Age={max_age}",
                f"Expires={expires.strftime('%a, %d %b %Y %H:%M:%S GMT')}",
                "Path=/",
                "SameSite=Strict",
            ]

            if self.secure:
                cookie_attrs.append("Secure")

            if self.domain:
                cookie_attrs.append(f"Domain={self.domain}")

            cookie_string = "; ".join(cookie_attrs)

            # JavaScript to set cookie
            js_code = f"""
            <script>
                document.cookie = "{cookie_string}";
                console.log("CSRF cookie set");
            </script>
            """

            logger.debug(
                "CSRF cookie set", max_age=max_age, operation="set_csrf_cookie"
            )

            return js_code

        except Exception as e:
            logger.error(
                "Failed to set CSRF cookie",
                error_type=type(e).__name__,
                operation="set_csrf_cookie",
            )
            return ""

    def get_session_token(self) -> Optional[str]:
        """
        Get session token from cookie

        Returns:
            Session token if valid, None otherwise
        """
        try:
            # Get cookies from Streamlit request
            cookies = self._get_cookies_from_request()
            if not cookies:
                return None

            signed_token = cookies.get(self.session_cookie_name)
            if not signed_token:
                return None

            # Verify signature and extract token
            session_token = self.cookie_serializer.loads(
                unquote(signed_token), max_age=self.cookie_max_age
            )

            return session_token

        except (BadSignature, SignatureExpired) as e:
            logger.warning(
                "Invalid or expired session cookie",
                error_type=type(e).__name__,
                operation="get_session_token",
            )
            return None
        except Exception as e:
            logger.error(
                "Failed to get session token",
                error_type=type(e).__name__,
                operation="get_session_token",
            )
            return None

    def get_csrf_token(self) -> Optional[str]:
        """
        Get CSRF token from cookie

        Returns:
            CSRF token if present, None otherwise
        """
        try:
            cookies = self._get_cookies_from_request()
            if not cookies:
                return None

            csrf_token = cookies.get(self.csrf_cookie_name)
            return unquote(csrf_token) if csrf_token else None

        except Exception as e:
            logger.error(
                "Failed to get CSRF token",
                error_type=type(e).__name__,
                operation="get_csrf_token",
            )
            return None

    def clear_session_cookies(self) -> str:
        """
        Clear session and CSRF cookies

        Returns:
            JavaScript code to clear cookies
        """
        try:
            # JavaScript to clear cookies by setting them to expire
            js_code = f"""
            <script>
                document.cookie = "{self.session_cookie_name}=; Max-Age=0; Path=/; HttpOnly; SameSite=Strict{'; Secure' if self.secure else ''}{f'; Domain={self.domain}' if self.domain else ''}";
                document.cookie = "{self.csrf_cookie_name}=; Max-Age=0; Path=/; SameSite=Strict{'; Secure' if self.secure else ''}{f'; Domain={self.domain}' if self.domain else ''}";
                console.log("Session cookies cleared");
            </script>
            """

            logger.info("Session cookies cleared", operation="clear_session_cookies")
            return js_code

        except Exception as e:
            logger.error(
                "Failed to clear session cookies",
                error_type=type(e).__name__,
                operation="clear_session_cookies",
            )
            return ""

    def _get_cookies_from_request(self) -> Dict[str, str]:
        """
        Extract cookies from Streamlit request headers

        Returns:
            Dictionary of cookie name-value pairs
        """
        try:
            # Try to get cookies from Streamlit context
            if hasattr(st, "context") and hasattr(st.context, "headers"):
                cookie_header = st.context.headers.get("Cookie", "")
            else:
                # Fallback: try to get from session state if stored there
                cookie_header = st.session_state.get("_cookies", "")

            if not cookie_header:
                return {}

            # Parse cookie header
            cookies = {}
            for cookie in cookie_header.split(";"):
                cookie = cookie.strip()
                if "=" in cookie:
                    name, value = cookie.split("=", 1)
                    cookies[name.strip()] = value.strip()

            return cookies

        except Exception as e:
            logger.debug(
                "Could not extract cookies from request",
                error_type=type(e).__name__,
                operation="_get_cookies_from_request",
            )
            return {}

    def inject_cookie_reader(self) -> str:
        """
        Inject JavaScript to read cookies and store in Streamlit session state

        Returns:
            JavaScript code to read cookies
        """
        js_code = f"""
        <script>
            function getCookies() {{
                const cookies = {{}};
                document.cookie.split(';').forEach(cookie => {{
                    const [name, value] = cookie.trim().split('=');
                    if (name && value) {{
                        cookies[name] = decodeURIComponent(value);
                    }}
                }});
                return cookies;
            }}
            
            function updateStreamlitCookies() {{
                const cookies = getCookies();
                const cookieString = document.cookie;
                
                // Store in session state via Streamlit's JavaScript bridge
                if (window.parent && window.parent.streamlitBridge) {{
                    window.parent.streamlitBridge.setCookies(cookies);
                }}
                
                // Also try direct session state update
                if (window.streamlit) {{
                    window.streamlit.setComponentValue({{
                        cookies: cookies,
                        cookieString: cookieString
                    }});
                }}
            }}
            
            // Update cookies on page load
            updateStreamlitCookies();
            
            // Monitor cookie changes
            let lastCookieString = document.cookie;
            setInterval(() => {{
                if (document.cookie !== lastCookieString) {{
                    lastCookieString = document.cookie;
                    updateStreamlitCookies();
                }}
            }}, 1000);
        </script>
        """

        return js_code

    def create_csrf_form_field(self, csrf_token: str) -> str:
        """
        Create hidden form field for CSRF token

        Args:
            csrf_token: CSRF token value

        Returns:
            HTML for hidden form field
        """
        return f'<input type="hidden" name="csrf_token" value="{csrf_token}">'

    def validate_csrf_from_form(
        self, form_data: Dict[str, Any], session_csrf_token: str
    ) -> bool:
        """
        Validate CSRF token from form submission

        Args:
            form_data: Form data containing csrf_token
            session_csrf_token: Expected CSRF token from session

        Returns:
            True if CSRF token is valid
        """
        try:
            form_csrf_token = form_data.get("csrf_token")
            if not form_csrf_token or not session_csrf_token:
                return False

            return secrets.compare_digest(form_csrf_token, session_csrf_token)

        except Exception as e:
            logger.error(
                "CSRF validation failed",
                error_type=type(e).__name__,
                operation="validate_csrf_from_form",
            )
            return False

    def generate_secure_headers(self) -> Dict[str, str]:
        """
        Generate security headers for HTTP responses

        Returns:
            Dictionary of security headers
        """
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": (
                "max-age=31536000; includeSubDomains" if self.secure else ""
            ),
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
        }

    def get_cookie_info(self) -> Dict[str, Any]:
        """Get cookie configuration information"""
        return {
            "session_cookie_name": self.session_cookie_name,
            "csrf_cookie_name": self.csrf_cookie_name,
            "max_age": self.cookie_max_age,
            "secure": self.secure,
            "domain": self.domain,
            "same_site": "Strict",
            "http_only": True,  # For session cookie
        }


# Global cookie manager instance
_cookie_manager = None


def get_cookie_manager() -> SecureCookieManager:
    """Get global cookie manager instance"""
    global _cookie_manager
    if _cookie_manager is None:
        _cookie_manager = SecureCookieManager()
    return _cookie_manager
