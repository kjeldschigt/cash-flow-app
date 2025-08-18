"""
User domain model and related entities.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, ClassVar, Dict, Any
import bcrypt

from .base import BaseModel, Field, FieldConfig, PyObjectId, EmailStr, constr




class UserRole(str, Enum):
    """User role enumeration with numeric hierarchy"""

    ADMIN = "admin"
    MANAGER = "manager"
    USER = "user"
    VIEWER = "viewer"

    @property
    def level(self) -> int:
        """Get numeric permission level for role hierarchy"""
        hierarchy = {
            UserRole.VIEWER: 0,
            UserRole.USER: 1,
            UserRole.MANAGER: 2,
            UserRole.ADMIN: 3,
        }
        return hierarchy.get(self, 0)


class User(BaseModel):
    """User domain entity with authentication and authorization.
    
    Attributes:
        id: Unique identifier (MongoDB ObjectId as string)
        email: User's email address (unique)
        password_hash: Hashed password (bcrypt)
        role: User's role (from UserRole enum)
        created_at: Timestamp when user was created
        last_login: Timestamp of last successful login
        is_active: Whether the user account is active
        username: Optional username (defaults to email prefix)
    """
    
    # Pydantic v2 model configuration
    model_config = BaseModel.model_config.copy()
    model_config.update(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439011",
                "email": "user@example.com",
                "role": "user",
                "is_active": True,
                "username": "user",
                "created_at": "2023-01-01T00:00:00",
                "last_login": "2023-01-01T00:00:00"
            }
        }
    )
    
    email: str = FieldConfig.email()
    password_hash: Optional[bytes] = Field(
        default=None,
        exclude=True,
        description="Hashed password (bcrypt)",
        json_schema_extra={"example": "$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW"}
    )
    role: UserRole = Field(
        default=UserRole.USER,
        description="User's role with access level"
    )
    is_active: bool = Field(
        default=True,
        description="Whether the user account is active"
    )
    username: Optional[str] = Field(
        default=None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+$",
        description="Unique username (alphanumeric + underscore)",
        json_schema_extra={"example": "johndoe"}
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when user was created"
    )
    last_login: Optional[datetime] = Field(
        default=None,
        description="Timestamp of last successful login"
    )
    
    # Class-level configuration
    _bcrypt_rounds: ClassVar[int] = 12  # Configurable bcrypt work factor

    @classmethod
    def create(
        cls,
        email: str,
        password: str,
        role: UserRole = UserRole.USER,
        username: Optional[str] = None,
        **kwargs
    ) -> "User":
        """Create a new user with hashed password.
        
        Args:
            email: User's email address
            password: Plain text password (will be hashed)
            role: User role (default: UserRole.USER)
            username: Optional username (defaults to email prefix)
            **kwargs: Additional user attributes
            
        Returns:
            New User instance with hashed password
        """
        # Generate username from email if not provided
        if not username:
            username = email.split("@")[0]
            
        # Create password hash
        password_bytes = password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=cls._bcrypt_rounds)
        password_hash = bcrypt.hashpw(password_bytes, salt)
        
        # Create and return user
        return cls(
            email=email.lower().strip(),
            password_hash=password_hash,
            role=role,
            username=username,
            **kwargs
        )

    def verify_password(self, password: str) -> bool:
        """Verify the provided password against the stored hash.
        
        Args:
            password: Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
            
        Raises:
            ValueError: If password_hash is not set
        """
        if not self.password_hash:
            raise ValueError("No password hash set for user")
            
        password_bytes = password.encode("utf-8")
        
        # Handle both string and bytes stored hashes
        if isinstance(self.password_hash, str):
            hash_bytes = self.password_hash.encode("utf-8")
        else:
            hash_bytes = self.password_hash
            
        try:
            return bcrypt.checkpw(password_bytes, hash_bytes)
        except (ValueError, TypeError) as e:
            # Handle invalid hash formats
            return False

    def update_last_login(self) -> None:
        """Update the last login timestamp to current UTC time."""
        self.last_login = datetime.utcnow()

    def has_permission(self, required_role: UserRole) -> bool:
        """Check if user has required permission level using role hierarchy.
        
        Args:
            required_role: Minimum role level required
            
        Returns:
            bool: True if user has sufficient permissions, False otherwise
        """
        return self.role.level >= required_role.level

    def can_access_role(self, target_role: UserRole) -> bool:
        """Check if user can access features for a specific role.
        
        Args:
            target_role: Role to check access for
            
        Returns:
            bool: True if user can access the role's features
        """
        return self.has_permission(target_role)
        
    def set_password(self, new_password: str) -> None:
        """Update the user's password with a new hashed value.
        
        Args:
            new_password: New plain text password
        """
        password_bytes = new_password.encode("utf-8")
        salt = bcrypt.gensalt(rounds=self._bcrypt_rounds)
        self.password_hash = bcrypt.hashpw(password_bytes, salt)
        
    def to_public_dict(self) -> Dict[str, Any]:
        """Convert user to public dictionary, excluding sensitive fields."""
        return self.model_dump(
            exclude={"password_hash"},
            exclude_none=True
        )
        
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == UserRole.ADMIN
        
    @property
    def is_manager_or_above(self) -> bool:
        """Check if user has manager or admin role."""
        return self.role in {UserRole.MANAGER, UserRole.ADMIN}

    def get_permission_level(self) -> int:
        """Get user's numeric permission level."""
        return self.role.level


class UserCreate(BaseModel):
    """Model for creating a new user."""
    email: str = Field(..., description="User's email address")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+",
        description="Username (alphanumeric + underscore, optional)"
    )
    role: UserRole = Field(default=UserRole.USER, description="User's role")
    is_active: bool = Field(default=True, description="Whether the user account is active")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "user@example.com",
                "password": "SecurePassword123!",
                "username": "johndoe",
                "role": "user",
                "is_active": True
            }
        }
    }


class UserUpdate(BaseModel):
    """Model for updating an existing user."""
    email: Optional[str] = Field(None, description="User's email address")
    password: Optional[str] = Field(None, min_length=8, description="New password (min 8 characters)")
    username: Optional[str] = Field(
        None,
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9_]+",
        description="Username (alphanumeric + underscore)"
    )
    role: Optional[UserRole] = Field(None, description="User's role")
    is_active: Optional[bool] = Field(None, description="Whether the user account is active")

    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "updated@example.com",
                "password": "NewSecurePassword123!",
                "username": "updateduser",
                "role": "manager",
                "is_active": True
            }
        }
    }


class UserInDB(User):
    """Database model for user with sensitive data."""
    # This model is used internally and includes sensitive fields
    # that should not be exposed in API responses
    pass


# Export all models for easier imports
__all__ = [
    "UserRole",
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB"
]
