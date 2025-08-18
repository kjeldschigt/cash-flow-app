"""
Enhanced authentication UI components with Redis session management.
Replaces Streamlit session state with proper server-side sessions.
"""

import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime

from ..middleware.session_middleware import get_session_middleware
from ..services.user_service import UserService
from ..repositories.base import DatabaseConnection
from ..models.user import User, UserRole
from ..security.pii_protection import get_structured_logger

logger = get_structured_logger().get_logger(__name__)


class EnhancedAuthComponents:
    """Enhanced authentication components with Redis session backend"""
    
    def __init__(self):
        self.session_middleware = get_session_middleware()
        self.db_connection = DatabaseConnection()
        self.user_service = UserService(self.db_connection)
        
    def show_login_form(self) -> bool:
        """
        Show login form with Redis session management
        
        Returns:
            True if login successful
        """
        st.subheader("🔐 Login")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            remember_me = st.checkbox("Remember me for 30 days")
            
            submitted = st.form_submit_button("Login", use_container_width=True)
            
            if submitted:
                if not email or not password:
                    st.error("❌ Please enter both email and password")
                    return False
                
                # Authenticate user
                user = self.user_service.authenticate_with_identifier(email, password)
                if not user:
                    st.error("❌ Invalid email or password")
                    logger.warning("Failed login attempt", 
                                 email=email,
                                 operation="show_login_form")
                    return False
                
                # Get client info for session
                client_info = self._get_client_info()
                
                # Login user with session management
                success = self.session_middleware.login_user(
                    user,
                    client_info['ip_address'],
                    client_info['user_agent']
                )
                
                if success:
                    st.success("✅ Login successful! Redirecting...")
                    st.rerun()
                    return True
                else:
                    st.error("❌ Login failed. Please try again.")
                    return False
        
        return False
    
    def show_register_form(self) -> bool:
        """
        Show registration form with session management
        
        Returns:
            True if registration successful
        """
        st.subheader("📝 Create Account")
        
        with st.form("register_form"):
            email = st.text_input("Email", placeholder="Enter your email")
            password = st.text_input("Password", type="password", placeholder="Create a password")
            confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
            
            # Role selection (admin can create other roles)
            current_user = self.session_middleware.get_current_user()
            if current_user and current_user.role == UserRole.ADMIN:
                role_options = [role.value for role in UserRole]
                selected_role = st.selectbox("Role", role_options, index=2)  # Default to USER
                role = UserRole(selected_role)
            else:
                role = UserRole.USER
                st.info("New accounts are created with USER role by default")
            
            submitted = st.form_submit_button("Create Account", use_container_width=True)
            
            if submitted:
                # Validation
                if not email or not password or not confirm_password:
                    st.error("❌ Please fill in all fields")
                    return False
                
                if password != confirm_password:
                    st.error("❌ Passwords do not match")
                    return False
                
                if len(password) < 8:
                    st.error("❌ Password must be at least 8 characters long")
                    return False
                
                try:
                    # Register user
                    user = self.user_service.register_user(email, password, role)
                    
                    # Auto-login after registration
                    client_info = self._get_client_info()
                    success = self.session_middleware.login_user(
                        user,
                        client_info['ip_address'],
                        client_info['user_agent']
                    )
                    
                    if success:
                        st.success("✅ Account created successfully! You are now logged in.")
                        st.rerun()
                        return True
                    else:
                        st.success("✅ Account created successfully! Please log in.")
                        return True
                        
                except ValueError as e:
                    st.error(f"❌ {str(e)}")
                    return False
                except Exception as e:
                    st.error("❌ Registration failed. Please try again.")
                    logger.error("Registration failed",
                               email=email,
                               error_type=type(e).__name__,
                               operation="show_register_form")
                    return False
        
        return False
    
    def show_logout_button(self) -> bool:
        """
        Show logout button with session cleanup
        
        Returns:
            True if logout successful
        """
        if st.button("🚪 Logout", use_container_width=True):
            success = self.session_middleware.logout_user()
            if success:
                st.success("✅ Logged out successfully!")
                st.rerun()
                return True
            else:
                st.error("❌ Logout failed")
                return False
        return False
    
    def show_user_info(self):
        """Show current user information"""
        user = self.session_middleware.get_current_user()
        if not user:
            st.warning("No user information available")
            return
        
        session_info = self.session_middleware.get_session_info()
        
        st.subheader("👤 User Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.write(f"**Email:** {user.email}")
            st.write(f"**Role:** {user.role.value.title()}")
            st.write(f"**User ID:** {user.id}")
        
        with col2:
            if session_info.get('created_at'):
                created_at = datetime.fromisoformat(session_info['created_at'])
                st.write(f"**Session Started:** {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if session_info.get('last_accessed'):
                last_accessed = datetime.fromisoformat(session_info['last_accessed'])
                st.write(f"**Last Active:** {last_accessed.strftime('%Y-%m-%d %H:%M:%S')}")
            
            if session_info.get('ip_address'):
                st.write(f"**IP Address:** {session_info['ip_address']}")
    
    def show_session_management(self):
        """Show session management interface for admins"""
        current_user = self.session_middleware.get_current_user()
        if not current_user or current_user.role != UserRole.ADMIN:
            st.error("❌ Admin access required")
            return
        
        st.subheader("🔧 Session Management")
        
        # Current session info
        session_info = self.session_middleware.get_session_info()
        st.json(session_info)
        
        # User session management
        st.subheader("User Sessions")
        
        user_id = st.text_input("User ID", placeholder="Enter user ID to manage sessions")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("Get Session Info"):
                if user_id:
                    info = self.session_middleware.session_manager.get_session_info(user_id)
                    st.json(info)
        
        with col2:
            if st.button("Invalidate All Sessions"):
                if user_id:
                    count = self.session_middleware.session_manager.invalidate_all_user_sessions(user_id)
                    st.success(f"✅ Invalidated {count} sessions")
        
        with col3:
            if st.button("Check Rate Limits"):
                if user_id and self.session_middleware.rate_limiter:
                    status = self.session_middleware.rate_limiter.get_rate_limit_status(user_id, 'auth_login')
                    st.json(status)
    
    def require_authentication(self, min_role: UserRole = UserRole.USER) -> bool:
        """
        Require authentication for current page
        
        Args:
            min_role: Minimum required role
            
        Returns:
            True if authenticated with sufficient role
        """
        # Validate session
        session_data = self.session_middleware.validate_session(require_auth=True)
        if not session_data:
            self._show_authentication_required()
            return False
        
        # Check role permissions
        user_role = UserRole(session_data.role)
        if user_role.value < min_role.value:
            st.error(f"❌ {min_role.value.title()} role required. You have {user_role.value} role.")
            st.stop()
            return False
        
        return True
    
    def require_exact_role(self, required_role: UserRole) -> bool:
        """
        Require exact role match
        
        Args:
            required_role: Exact role required
            
        Returns:
            True if user has exact role
        """
        session_data = self.session_middleware.validate_session(require_auth=True)
        if not session_data:
            self._show_authentication_required()
            return False
        
        user_role = UserRole(session_data.role)
        if user_role != required_role:
            st.error(f"❌ {required_role.value.title()} role required. You have {user_role.value} role.")
            st.stop()
            return False
        
        return True
    
    def _show_authentication_required(self):
        """Show authentication required message"""
        st.warning("🔐 Authentication required")
        
        tab1, tab2 = st.tabs(["Login", "Register"])
        
        with tab1:
            self.show_login_form()
        
        with tab2:
            self.show_register_form()
        
        st.stop()
    
    def _get_client_info(self) -> Dict[str, str]:
        """Get client information from request"""
        try:
            # Try to get from Streamlit context
            if hasattr(st, 'context') and hasattr(st.context, 'headers'):
                headers = st.context.headers
                ip_address = (
                    headers.get('X-Forwarded-For', '').split(',')[0].strip() or
                    headers.get('X-Real-IP', '') or
                    headers.get('Remote-Addr', 'unknown')
                )
                user_agent = headers.get('User-Agent', 'unknown')
            else:
                ip_address = 'unknown'
                user_agent = 'unknown'
            
            return {
                'ip_address': ip_address,
                'user_agent': user_agent
            }
            
        except Exception as e:
            logger.debug("Could not get client info",
                        error_type=type(e).__name__,
                        operation="_get_client_info")
            return {'ip_address': 'unknown', 'user_agent': 'unknown'}
    
    def show_csrf_token_field(self) -> str:
        """Show CSRF token as hidden field for forms"""
        session_data = self.session_middleware.validate_session()
        if session_data:
            csrf_token = session_data.csrf_token
            st.markdown(f'<input type="hidden" name="csrf_token" value="{csrf_token}">', 
                       unsafe_allow_html=True)
            return csrf_token
        return ""
    
    def validate_csrf_token(self, form_data: Dict[str, Any]) -> bool:
        """Validate CSRF token from form submission"""
        return self.session_middleware.check_csrf_protection(form_data)


# Global instance
_enhanced_auth = None

def get_enhanced_auth() -> EnhancedAuthComponents:
    """Get global enhanced auth instance"""
    global _enhanced_auth
    if _enhanced_auth is None:
        _enhanced_auth = EnhancedAuthComponents()
    return _enhanced_auth


# Convenience functions
def require_auth(min_role: UserRole = UserRole.USER) -> bool:
    """Convenience function to require authentication"""
    return get_enhanced_auth().require_authentication(min_role)


def require_admin() -> bool:
    """Convenience function to require admin role"""
    return get_enhanced_auth().require_authentication(UserRole.ADMIN)


def require_manager() -> bool:
    """Convenience function to require manager role"""
    return get_enhanced_auth().require_authentication(UserRole.MANAGER)


def show_login() -> bool:
    """Convenience function to show login form"""
    return get_enhanced_auth().show_login_form()


def show_logout() -> bool:
    """Convenience function to show logout button"""
    return get_enhanced_auth().show_logout_button()


def get_current_user() -> Optional[User]:
    """Convenience function to get current user"""
    return get_enhanced_auth().session_middleware.get_current_user()


def is_authenticated() -> bool:
    """Convenience function to check authentication"""
    return get_enhanced_auth().session_middleware.is_authenticated()
