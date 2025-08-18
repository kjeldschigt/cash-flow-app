"""
User domain model and related entities.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional
import bcrypt


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
            UserRole.ADMIN: 3
        }
        return hierarchy.get(self, 0)


@dataclass
class User:
    """User domain entity."""
    id: Optional[str]
    email: str
    password_hash: Optional[bytes]
    role: UserRole
    created_at: Optional[datetime]
    last_login: Optional[datetime]
    is_active: bool = True
    username: Optional[str] = None  # Allow NULL for migration compatibility

    @classmethod
    def create(cls, email: str, password: str, role: UserRole = UserRole.USER, username: Optional[str] = None) -> 'User':
        """Create a new user with hashed password."""
        password_bytes = password.encode('utf-8')
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password_bytes, salt)
        
        # Generate username from email if not provided
        if not username:
            username = email.split('@')[0]
        
        return cls(
            id=None,
            email=email.lower().strip(),
            password_hash=password_hash,
            role=role,
            created_at=datetime.now(),
            last_login=None,
            is_active=True,
            username=username
        )

    def verify_password(self, password: str) -> bool:
        """Verify the provided password against the stored hash."""
        if not self.password_hash:
            return False
        
        password_bytes = password.encode('utf-8')
        # Handle both string and bytes stored hashes
        if isinstance(self.password_hash, str):
            hash_bytes = self.password_hash.encode('utf-8')
        else:
            hash_bytes = self.password_hash
        
        return bcrypt.checkpw(password_bytes, hash_bytes)

    def update_last_login(self) -> None:
        """Update the last login timestamp."""
        self.last_login = datetime.now()

    def has_permission(self, required_role: UserRole) -> bool:
        """Check if user has required permission level using role hierarchy."""
        return self.role.level >= required_role.level
    
    def can_access_role(self, target_role: UserRole) -> bool:
        """Check if user can access features for a specific role."""
        return self.has_permission(target_role)
    
    def get_permission_level(self) -> int:
        """Get user's numeric permission level."""
        return self.role.level
