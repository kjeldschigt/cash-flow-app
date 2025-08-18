"""
Enhanced Authentication and Role-Based Access Control (RBAC)
"""

import logging
import streamlit as st
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from enum import Enum
from ..models.user import User, UserRole
from ..services.user_service import UserService
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class Permission(str, Enum):
    """System permissions"""
    VIEW_DASHBOARD = "view_dashboard"
    VIEW_ANALYTICS = "view_analytics"
    MANAGE_COSTS = "manage_costs"
    MANAGE_PAYMENTS = "manage_payments"
    MANAGE_INTEGRATIONS = "manage_integrations"
    MANAGE_USERS = "manage_users"
    EXPORT_DATA = "export_data"
    VIEW_AUDIT_LOGS = "view_audit_logs"

class RoleBasedAccessControl:
    """Role-Based Access Control system"""
    
    # Define role permissions
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: {
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_ANALYTICS,
            Permission.MANAGE_COSTS,
            Permission.MANAGE_PAYMENTS,
            Permission.MANAGE_INTEGRATIONS,
            Permission.MANAGE_USERS,
            Permission.EXPORT_DATA,
            Permission.VIEW_AUDIT_LOGS
        },
        UserRole.MANAGER: {
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_ANALYTICS,
            Permission.MANAGE_COSTS,
            Permission.MANAGE_PAYMENTS,
            Permission.EXPORT_DATA
        },
        UserRole.VIEWER: {
            Permission.VIEW_DASHBOARD,
            Permission.VIEW_ANALYTICS
        }
    }
    
    @classmethod
    def has_permission(cls, user_role: UserRole, permission: Permission) -> bool:
        """Check if role has specific permission"""
        role_permissions = cls.ROLE_PERMISSIONS.get(user_role, set())
        return permission in role_permissions
    
    @classmethod
    def get_user_permissions(cls, user_role: UserRole) -> Set[Permission]:
        """Get all permissions for a user role"""
        return cls.ROLE_PERMISSIONS.get(user_role, set())
    
    @classmethod
    def require_permission(cls, permission: Permission):
        """Decorator to require specific permission"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                if 'user' not in st.session_state:
                    st.error("Authentication required")
                    st.stop()
                
                user = st.session_state.user
                if not cls.has_permission(user.role, permission):
                    st.error(f"Access denied. Required permission: {permission.value}")
                    st.stop()
                
                return func(*args, **kwargs)
            return wrapper
        return decorator

class AuthManager:
    """Enhanced authentication manager with session security"""
    
    def __init__(self, user_service: UserService, settings: Settings):
        self.user_service = user_service
        self.settings = settings
        self.failed_attempts = {}  # Track failed login attempts
    
    def authenticate_user(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with enhanced security"""
        try:
            # Check for account lockout
            if self._is_account_locked(email):
                logger.warning(f"Login attempt on locked account: {email}")
                return None
            
            # Attempt authentication
            user = self.user_service.authenticate_user(email, password)
            
            if user:
                # Reset failed attempts on successful login
                self.failed_attempts.pop(email, None)
                self._create_secure_session(user)
                logger.info(f"Successful login: {email}")
                return user
            else:
                # Track failed attempt
                self._record_failed_attempt(email)
                logger.warning(f"Failed login attempt: {email}")
                return None
                
        except Exception as e:
            logger.error(f"Authentication error for {email}: {str(e)}")
            return None
    
    def _create_secure_session(self, user: User) -> None:
        """Create secure session with timeout"""
        session_data = {
            'user': user,
            'login_time': datetime.now(),
            'last_activity': datetime.now(),
            'session_id': self._generate_session_id(),
            'ip_address': self._get_client_ip()
        }
        
        # Store in Streamlit session state
        for key, value in session_data.items():
            st.session_state[key] = value
    
    def validate_session(self) -> bool:
        """Validate current session"""
        if 'user' not in st.session_state:
            return False
        
        # Check session timeout
        if self._is_session_expired():
            self.logout_user()
            return False
        
        # Update last activity
        st.session_state.last_activity = datetime.now()
        return True
    
    def _is_session_expired(self) -> bool:
        """Check if session has expired"""
        if 'last_activity' not in st.session_state:
            return True
        
        last_activity = st.session_state.last_activity
        timeout_minutes = self.settings.security.session_timeout_minutes
        
        return datetime.now() - last_activity > timedelta(minutes=timeout_minutes)
    
    def _is_account_locked(self, email: str) -> bool:
        """Check if account is locked due to failed attempts"""
        if email not in self.failed_attempts:
            return False
        
        attempt_data = self.failed_attempts[email]
        max_attempts = self.settings.security.max_login_attempts
        lockout_duration = self.settings.security.lockout_duration_minutes
        
        if attempt_data['count'] >= max_attempts:
            time_since_last = datetime.now() - attempt_data['last_attempt']
            return time_since_last < timedelta(minutes=lockout_duration)
        
        return False
    
    def _record_failed_attempt(self, email: str) -> None:
        """Record failed login attempt"""
        if email not in self.failed_attempts:
            self.failed_attempts[email] = {'count': 0, 'last_attempt': datetime.now()}
        
        self.failed_attempts[email]['count'] += 1
        self.failed_attempts[email]['last_attempt'] = datetime.now()
    
    def _generate_session_id(self) -> str:
        """Generate secure session ID"""
        import secrets
        return secrets.token_urlsafe(32)
    
    def _get_client_ip(self) -> str:
        """Get client IP address (simplified for Streamlit)"""
        # In production, you'd extract this from request headers
        return "127.0.0.1"
    
    def logout_user(self) -> None:
        """Securely logout user"""
        if 'user' in st.session_state:
            user = st.session_state.user
            logger.info(f"User logout: {user.email}")
        
        # Clear all session data
        session_keys = ['user', 'login_time', 'last_activity', 'session_id', 'ip_address']
        for key in session_keys:
            st.session_state.pop(key, None)
    
    def get_current_user(self) -> Optional[User]:
        """Get current authenticated user"""
        if self.validate_session():
            return st.session_state.get('user')
        return None
    
    def require_authentication(self) -> bool:
        """Require user authentication"""
        if not self.validate_session():
            st.error("Please log in to access this page")
            return False
        return True
    
    def require_role(self, required_role: UserRole) -> bool:
        """Require specific user role"""
        user = self.get_current_user()
        if not user:
            st.error("Authentication required")
            return False
        
        if user.role != required_role and user.role != UserRole.ADMIN:
            st.error(f"Access denied. Required role: {required_role.value}")
            return False
        
        return True
