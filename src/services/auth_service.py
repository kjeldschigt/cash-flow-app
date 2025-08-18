"""
Authentication service that provides a clean interface for authentication operations.
This acts as a facade to the AuthManager and RBAC functionality.
"""

from typing import Optional
from ..security.auth import AuthManager, RoleBasedAccessControl, Permission
from ..models.user import User, UserRole
from ..services.user_service import UserService
from ..config.settings import Settings

class AuthService:
    """Service layer for authentication and authorization."""
    
    def __init__(self):
        self.settings = Settings()
        self.user_service = UserService()
        self.rbac = RoleBasedAccessControl()
        self.auth_manager = AuthManager(self.user_service, self.settings)
    
    def authenticate(self, login_identifier: str, password: str) -> Optional[User]:
        """Authenticate a user with email/username and password."""
        return self.auth_manager.authenticate_user(login_identifier, password)
    
    def logout(self) -> None:
        """Log out the current user."""
        self.auth_manager.logout()
    
    def get_current_user(self) -> Optional[User]:
        """Get the currently authenticated user."""
        return self.auth_manager.get_current_user()
    
    def has_permission(self, permission: Permission) -> bool:
        """Check if current user has the specified permission."""
        user = self.get_current_user()
        if not user:
            return False
        return self.rbac.has_permission(user.role, permission)
    
    def require_authentication(self) -> bool:
        """Require user to be authenticated."""
        return self.auth_manager.require_authentication()
    
    def require_role(self, required_role: UserRole) -> bool:
        """Require user to have at least the specified role."""
        return self.auth_manager.require_role(required_role)
    
    def require_exact_role(self, required_role: UserRole) -> bool:
        """Require user to have exactly the specified role."""
        return self.auth_manager.require_exact_role(required_role)
    
    def validate_session(self) -> bool:
        """Validate the current session."""
        return self.auth_manager.validate_session()
