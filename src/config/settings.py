"""
Application settings and configuration management using Pydantic BaseSettings.
"""

import os
from typing import Optional, Dict, Any, List
from pathlib import Path
from pydantic import Field, validator
from pydantic_settings import BaseSettings
from enum import Enum

class Environment(str, Enum):
    """Environment enumeration"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class DatabaseConfig(BaseSettings):
    """Database configuration settings."""
    path: str = Field(default="cashflow.db", env="DATABASE_PATH")
    users_db_path: str = Field(default="users.db", env="USERS_DATABASE_PATH")
    connection_timeout: float = Field(default=30.0, env="DATABASE_TIMEOUT")
    enable_foreign_keys: bool = Field(default=True, env="DATABASE_FOREIGN_KEYS")
    
    @property
    def absolute_path(self) -> str:
        """Get absolute path to main database."""
        return str(Path(self.path).resolve())
    
    @property
    def users_absolute_path(self) -> str:
        """Get absolute path to users database."""
        return str(Path(self.users_db_path).resolve())
    
    class Config:
        env_prefix = "DB_"


class SecurityConfig(BaseSettings):
    """Security configuration settings."""
    secret_key: str = Field(default="dev-secret-key-change-in-production", env="SECRET_KEY")
    session_timeout_minutes: int = Field(default=480, env="SESSION_TIMEOUT_MINUTES")
    bcrypt_rounds: int = Field(default=12, ge=10, le=15, env="BCRYPT_ROUNDS")
    require_https: bool = Field(default=False, env="REQUIRE_HTTPS")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=30, env="LOCKOUT_DURATION_MINUTES")
    
    @validator('secret_key')
    def validate_secret_key(cls, v):
        if not v:
            import secrets
            return secrets.token_urlsafe(32)
        if len(v) < 32:
            raise ValueError('Secret key must be at least 32 characters long')
        return v
    
    class Config:
        env_prefix = "SECURITY_"


class RateLimitConfig(BaseSettings):
    """Rate limiting configuration."""
    enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    requests_per_minute: int = Field(default=60, env="RATE_LIMIT_RPM")
    requests_per_hour: int = Field(default=1000, env="RATE_LIMIT_RPH")
    burst_limit: int = Field(default=10, env="RATE_LIMIT_BURST")
    
    class Config:
        env_prefix = "RATE_LIMIT_"

class FeatureFlags(BaseSettings):
    """Feature flags for gradual rollouts."""
    advanced_analytics: bool = Field(default=True, env="FEATURE_ADVANCED_ANALYTICS")
    monte_carlo_forecasting: bool = Field(default=False, env="FEATURE_MONTE_CARLO")
    real_time_notifications: bool = Field(default=False, env="FEATURE_NOTIFICATIONS")
    audit_logging: bool = Field(default=True, env="FEATURE_AUDIT_LOGGING")
    data_encryption: bool = Field(default=True, env="FEATURE_DATA_ENCRYPTION")
    
    class Config:
        env_prefix = "FEATURE_"

class IntegrationConfig(BaseSettings):
    """External integration configuration."""
    stripe_api_key: Optional[str] = Field(default=None, env="STRIPE_API_KEY")
    airtable_api_key: Optional[str] = Field(default=None, env="AIRTABLE_API_KEY")
    airtable_base_id: Optional[str] = Field(default=None, env="AIRTABLE_BASE_ID")
    airtable_table_name: Optional[str] = Field(default=None, env="AIRTABLE_TABLE_NAME")
    webhook_secret: Optional[str] = Field(default=None, env="WEBHOOK_SECRET")
    google_ads_api_key: Optional[str] = Field(default=None, env="GOOGLE_ADS_API_KEY")
    hk_start_usd: Optional[str] = Field(default=None, env="HK_START_USD")
    
    def get_stripe_config(self) -> Dict[str, Any]:
        """Get Stripe configuration."""
        return {
            'api_key': self.stripe_api_key,
            'enabled': bool(self.stripe_api_key)
        }
    
    def get_airtable_config(self) -> Dict[str, Any]:
        """Get Airtable configuration."""
        return {
            'api_key': self.airtable_api_key,
            'base_id': self.airtable_base_id,
            'enabled': bool(self.airtable_api_key and self.airtable_base_id)
        }
    
    class Config:
        env_prefix = "INTEGRATION_"


class AppConfig(BaseSettings):
    """Application configuration settings."""
    environment: Environment = Field(default=Environment.DEVELOPMENT, env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    theme: str = Field(default="light", env="THEME")
    page_title: str = Field(default="Cash Flow Dashboard", env="PAGE_TITLE")
    page_icon: str = Field(default="💰", env="PAGE_ICON")
    
    @validator('log_level')
    def validate_log_level(cls, v):
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        if v.upper() not in valid_levels:
            raise ValueError(f'Log level must be one of: {valid_levels}')
        return v.upper()
    
    @property
    def is_production(self) -> bool:
        return self.environment == Environment.PRODUCTION
    
    @property
    def is_development(self) -> bool:
        return self.environment == Environment.DEVELOPMENT
    
    class Config:
        env_prefix = "APP_"


class Settings(BaseSettings):
    """Centralized application settings manager using Pydantic BaseSettings."""
    
    # Define fields as class attributes
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    integrations: IntegrationConfig = Field(default_factory=IntegrationConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    
    def __init__(self, **kwargs):
        self._load_env_file()
        super().__init__(**kwargs)
    
    def _load_env_file(self) -> None:
        """Load environment variables from .env file."""
        env_file = Path('.env')
        if env_file.exists():
            from dotenv import load_dotenv
            load_dotenv(env_file)
    
    def update_database_path(self, path: str) -> None:
        """Update database path."""
        self.database.path = path
    
    def is_integration_enabled(self, integration_name: str) -> bool:
        """Check if specific integration is enabled."""
        config_map = {
            'stripe': self.integrations.get_stripe_config(),
            'airtable': self.integrations.get_airtable_config()
        }
        
        config = config_map.get(integration_name.lower())
        return config.get('enabled', False) if config else False
    
    def get_integration_config(self, integration_name: str) -> Dict[str, Any]:
        """Get configuration for specific integration."""
        config_map = {
            'stripe': self.integrations.get_stripe_config(),
            'airtable': self.integrations.get_airtable_config()
        }
        
        return config_map.get(integration_name.lower(), {})
    
    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature flag is enabled."""
        return getattr(self.features, feature_name, False)
    
    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore'  # Allow extra fields to be ignored
