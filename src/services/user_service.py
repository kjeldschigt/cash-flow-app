"""
User service for authentication and user management.
"""

import logging
from typing import Optional
from ..models.user import User, UserRole
from ..repositories.user_repository import UserRepository
from ..repositories.base import DatabaseConnection
from ..security.encryption import SecureStorage

try:
    from ..security.pii_protection import get_structured_logger

    logger = get_structured_logger().get_logger(__name__)
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


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

    def register_user(
        self, email: str, password: str, role: UserRole = UserRole.USER
    ) -> User:
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
        """Get user by email with proper error handling."""
        try:
            return self.user_repository.find_by_email(email)
        except Exception as e:
            logger.error(
                "Error retrieving user by email",
                operation="get_user_by_email",
                error_type=type(e).__name__,
            )
            return None

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username with proper error handling."""
        try:
            return self.user_repository.find_by_username(username)
        except Exception as e:
            logger.error(
                "Error retrieving user by username",
                operation="get_user_by_username",
                error_type=type(e).__name__,
            )
            return None

    def authenticate(self, identifier: str, password: str) -> Optional[User]:
        """Authenticate user with email or username and password."""
        return self.authenticate_with_identifier(identifier, password)

    def authenticate_with_identifier(
        self, identifier: str, password: str
    ) -> Optional[User]:
        """Authenticate user with email or username and password.

        Args:
            identifier: Email address or username
            password: User password

        Returns:
            User object if authentication successful, None otherwise
        """
        try:
            # First try to authenticate with email
            user = self.get_user_by_email(identifier)

            # If not found by email, try username
            if not user:
                user = self.get_user_by_username(identifier)

            # Verify password if user found
            if user and user.verify_password(password):
                user.update_last_login()
                self.user_repository.update_last_login(user.id)
                return user

            return None

        except Exception as e:
            logger.error(
                "Authentication error",
                operation="authenticate",
                error_type=type(e).__name__,
            )
            return None

    def get_all_active_users(self) -> list[User]:
        """Get all active users."""
        return self.user_repository.find_active_users()

    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        return self.user_repository.deactivate_user(user_id)

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
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

    def create_user(self, user: User, password: str) -> User:
        """Create a new user with password."""
        # Set the password hash
        user.set_password(password)
        return self.user_repository.save(user)

    def count(self) -> int:
        """Count total number of users."""
        return self.user_repository.count()

    def has_permission(self, user_id: str, required_role: UserRole) -> bool:
        """Check if user has required permission level."""
        user = self.user_repository.find_by_id(user_id)
        return user.has_permission(required_role) if user else False
