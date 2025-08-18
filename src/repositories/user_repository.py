"""
User repository for database operations.
"""

import sqlite3
from datetime import datetime
from typing import Optional, List, Type
from ..models.user import User, UserRole
from .base import BaseRepository, DatabaseConnection


class UserRepository(BaseRepository[User]):
    """Repository for User entities."""
    
    def _get_table_name(self) -> str:
        return "users"
    
    def _get_model_class(self) -> Type[User]:
        return User
    
    def _row_to_model(self, row: sqlite3.Row) -> User:
        """Convert database row to User model."""
        return User(
            id=str(row['id']),
            email=row['email'],
            password_hash=row['password_hash'],
            role=UserRole(row.get('role', 'user')),
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            last_login=datetime.fromisoformat(row['last_login']) if row['last_login'] else None,
            is_active=bool(row.get('is_active', True)),
            username=row.get('username')
        )
    
    def _model_to_dict(self, model: User) -> dict:
        """Convert User model to dictionary."""
        return {
            'id': model.id,
            'email': model.email,
            'password_hash': model.password_hash,
            'role': model.role.value,
            'created_at': model.created_at.isoformat() if model.created_at else None,
            'last_login': model.last_login.isoformat() if model.last_login else None,
            'is_active': model.is_active,
            'username': model.username
        }
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email address."""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT * FROM {self._table_name} WHERE email = ? AND is_active = 1",
                    (email.lower().strip(),)
                )
                row = cursor.fetchone()
                return self._row_to_model(row) if row else None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Database error finding user by email {email}: {str(e)}")
            return None
    
    def find_by_username(self, username: str) -> Optional[User]:
        """Find user by username.
        
        Args:
            username: The username to search for
            
        Returns:
            User object if found, None otherwise
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f"SELECT * FROM {self._table_name} WHERE username = ? AND is_active = 1",
                    (username.strip(),)
                )
                row = cursor.fetchone()
                return self._row_to_model(row) if row else None
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Database error finding user by username {username}: {str(e)}")
            return None
    
    def find_active_users(self) -> List[User]:
        """Find all active users."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT * FROM {self._table_name} WHERE is_active = 1")
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {self._table_name} SET last_login = ? WHERE id = ?",
                (datetime.now().isoformat(), user_id)
            )
            return cursor.rowcount > 0
    
    def deactivate_user(self, user_id: str) -> bool:
        """Deactivate a user account."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"UPDATE {self._table_name} SET is_active = 0 WHERE id = ?",
                (user_id,)
            )
            return cursor.rowcount > 0
