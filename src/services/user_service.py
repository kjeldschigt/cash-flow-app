"""
User service for authentication and user management.
"""

from typing import Optional
from ..models.user import User, UserRole
from ..repositories.user_repository import UserRepository
from ..repositories.base import DatabaseConnection


class UserService:
    """Service for user authentication and management operations."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.user_repository = UserRepository(db_connection)
    
    def authenticate(self, email: str, password: str) -> Optional[User]:
        """Authenticate user with email and password."""
        user = self.user_repository.find_by_email(email)
        if user and user.verify_password(password):
            user.update_last_login()
            self.user_repository.update_last_login(user.id)
            return user
        return None
    
    def register_user(self, email: str, password: str, role: UserRole = UserRole.USER) -> User:
        """Register a new user."""
        # Check if user already exists
        existing_user = self.user_repository.find_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")
        
        # Create new user
        user = User.create(email, password, role)
        return self.user_repository.save(user)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.user_repository.find_by_id(user_id)
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        return self.user_repository.find_by_email(email)
    
    def get_all_active_users(self) -> list[User]:
        """Get all active users."""
        return self.user_repository.find_active_users()
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        return self.user_repository.deactivate_user(user_id)
    
    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        """Change user password."""
        user = self.user_repository.find_by_id(user_id)
        if not user or not user.verify_password(old_password):
            return False
        
        # Create new user instance with updated password
        updated_user = User.create(user.email, new_password, user.role)
        updated_user.id = user.id
        updated_user.created_at = user.created_at
        updated_user.last_login = user.last_login
        
        self.user_repository.save(updated_user)
        return True
    
    def has_permission(self, user_id: str, required_role: UserRole) -> bool:
        """Check if user has required permission level."""
        user = self.user_repository.find_by_id(user_id)
        return user.has_permission(required_role) if user else False
