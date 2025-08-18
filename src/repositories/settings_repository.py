"""
Settings Repository
Handles application settings persistence
"""

from typing import Dict, Any, Optional
from .base import BaseRepository
from ..models.setting import Setting


class SettingsRepository(BaseRepository):
    """Repository for application settings"""

    def _get_model_class(self):
        """Return the model class for this repository"""
        return Setting

    def _get_table_name(self) -> str:
        """Return the table name for this repository"""
        return "settings"

    def _model_to_dict(self, model: Setting) -> Dict[str, Any]:
        """Convert model to dictionary for database storage"""
        return {
            "key": model.key,
            "value": model.value,
            "description": model.description,
            "created_at": model.created_at,
            "updated_at": model.updated_at,
        }

    def _row_to_model(self, row: Dict[str, Any]) -> Setting:
        """Convert database row to model"""
        return Setting(
            key=row["key"],
            value=row["value"],
            description=row.get("description"),
            created_at=row.get("created_at"),
            updated_at=row.get("updated_at"),
        )

    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key"""
        try:
            cursor = self.db_connection.get_cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()

            if result:
                return result[0]
            return default

        except Exception as e:
            self.logger.error(f"Error getting setting {key}: {str(e)}")
            return default

    def set_setting(self, key: str, value: Any) -> bool:
        """Set a setting value"""
        try:
            cursor = self.db_connection.get_cursor()

            # Use UPSERT (INSERT OR REPLACE)
            cursor.execute(
                """
                INSERT OR REPLACE INTO settings (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
                (key, str(value)),
            )

            self.db_connection.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error setting {key}: {str(e)}")
            return False

    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary"""
        try:
            cursor = self.db_connection.get_cursor()
            cursor.execute("SELECT key, value FROM settings")

            return {row[0]: row[1] for row in cursor.fetchall()}

        except Exception as e:
            self.logger.error(f"Error getting all settings: {str(e)}")
            return {}

    def delete_setting(self, key: str) -> bool:
        """Delete a setting"""
        try:
            cursor = self.db_connection.get_cursor()
            cursor.execute("DELETE FROM settings WHERE key = ?", (key,))

            self.db_connection.commit()
            return True

        except Exception as e:
            self.logger.error(f"Error deleting setting {key}: {str(e)}")
            return False

    def get_settings_by_prefix(self, prefix: str) -> Dict[str, Any]:
        """Get all settings with a specific prefix"""
        try:
            cursor = self.db_connection.get_cursor()
            cursor.execute(
                "SELECT key, value FROM settings WHERE key LIKE ?", (f"{prefix}%",)
            )

            return {row[0]: row[1] for row in cursor.fetchall()}

        except Exception as e:
            self.logger.error(f"Error getting settings with prefix {prefix}: {str(e)}")
            return {}
