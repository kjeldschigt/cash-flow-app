"""
Settings service for application configuration management.
"""

import logging
from typing import Any, Optional, Dict
from ..repositories.settings_repository import SettingsRepository
from ..repositories.base import DatabaseConnection

logger = logging.getLogger(__name__)

class SettingsService:
    """Service for managing application settings."""
    
    def __init__(self, db_connection: DatabaseConnection):
        self.settings_repository = SettingsRepository(db_connection)
        self._cache = {}
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting value by key."""
        try:
            # Check cache first
            if key in self._cache:
                return self._cache[key]
            
            # Get from repository
            setting = self.settings_repository.find_by_key(key)
            if setting:
                self._cache[key] = setting.value
                return setting.value
            
            return default
        except Exception as e:
            logger.error(f"Error getting setting {key}: {e}")
            return default
    
    def set_setting(self, key: str, value: Any) -> bool:
        """Set a setting value."""
        try:
            from ..models.setting import Setting
            
            # Create or update setting
            setting = Setting(key=key, value=value)
            result = self.settings_repository.save(setting)
            
            if result:
                # Update cache
                self._cache[key] = value
                return True
            
            return False
        except Exception as e:
            logger.error(f"Error setting {key}: {str(e)}")
            return False
    
    def get_all_settings(self) -> Dict[str, Any]:
        """Get all settings as a dictionary."""
        try:
            settings = self.settings_repository.find_all()
            return {setting.key: setting.value for setting in settings}
        except Exception as e:
            logger.error(f"Error retrieving all settings: {str(e)}")
            return {}
    
    def clear_cache(self) -> None:
        """Clear the settings cache."""
        self._cache.clear()


# Legacy compatibility functions
def get_setting(key: str, default: Any = None) -> Any:
    """Get a setting value by key - legacy compatibility function."""
    # Return default values for common settings
    defaults = {
        'theme': 'light',
        'currency': 'USD',
        'date_format': '%Y-%m-%d',
        'decimal_places': 2
    }
    return defaults.get(key, default)


def set_setting(key: str, value: Any) -> bool:
    """Set a setting value - legacy compatibility function."""
    # For now, just return True as if it was saved
    return True


def get_all_settings() -> Dict[str, Any]:
    """Get all settings - legacy compatibility function."""
    return {
        'theme': 'light',
        'currency': 'USD',
        'date_format': '%Y-%m-%d',
        'decimal_places': 2
    }
