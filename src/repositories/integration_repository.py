"""
Integration repository for database operations.
"""

import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Type, Dict, Any
from ..models.integration import Integration, IntegrationType
from .base import BaseRepository, DatabaseConnection


class IntegrationRepository(BaseRepository[Integration]):
    """Repository for Integration entities."""
    
    def _get_table_name(self) -> str:
        return "integrations"
    
    def _get_model_class(self) -> Type[Integration]:
        return Integration
    
    def _row_to_model(self, row: sqlite3.Row) -> Integration:
        """Convert database row to Integration model."""
        return Integration(
            id=str(row['id']),
            name=row['name'],
            type=IntegrationType(row['type']),
            is_enabled=bool(row['is_enabled']),
            config=json.loads(row['config']) if row['config'] else {},
            events=json.loads(row['events']) if row['events'] else [],
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None,
            last_sync=datetime.fromisoformat(row['last_sync']) if row.get('last_sync') else None
        )
    
    def _model_to_dict(self, model: Integration) -> dict:
        """Convert Integration model to dictionary."""
        return {
            'id': model.id,
            'name': model.name,
            'type': model.type.value,
            'is_enabled': model.is_enabled,
            'config': json.dumps(model.config),
            'events': json.dumps(model.events),
            'created_at': model.created_at.isoformat() if model.created_at else None,
            'updated_at': model.updated_at.isoformat() if model.updated_at else None,
            'last_sync': model.last_sync.isoformat() if model.last_sync else None
        }
    
    def find_by_type(self, integration_type: IntegrationType) -> List[Integration]:
        """Find integrations by type."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE type = ? ORDER BY name",
                (integration_type.value,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def find_enabled_integrations(self) -> List[Integration]:
        """Find all enabled integrations."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE is_enabled = 1 ORDER BY name"
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def find_by_name(self, name: str) -> Optional[Integration]:
        """Find integration by name."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE name = ?",
                (name,)
            )
            row = cursor.fetchone()
            return self._row_to_model(row) if row else None


class SettingsRepository:
    """Repository for application settings stored as key-value pairs."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.db = db_connection
        self._table_name = "settings"
    
    def get_setting(self, key: str) -> Optional[str]:
        """Get setting value by key."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT value FROM {self._table_name} WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row['value'] if row else None
    
    def set_setting(self, key: str, value: str) -> None:
        """Set setting value."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"INSERT OR REPLACE INTO {self._table_name} (key, value) VALUES (?, ?)",
                (key, value)
            )
    
    def get_json_setting(self, key: str) -> Optional[Dict[str, Any]]:
        """Get JSON setting value by key."""
        value = self.get_setting(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None
    
    def set_json_setting(self, key: str, value: Dict[str, Any]) -> None:
        """Set JSON setting value."""
        self.set_setting(key, json.dumps(value))
    
    def delete_setting(self, key: str) -> bool:
        """Delete setting by key."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"DELETE FROM {self._table_name} WHERE key = ?",
                (key,)
            )
            return cursor.rowcount > 0
    
    def get_all_settings(self) -> Dict[str, str]:
        """Get all settings as dictionary."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"SELECT key, value FROM {self._table_name}")
            rows = cursor.fetchall()
            return {row['key']: row['value'] for row in rows}
