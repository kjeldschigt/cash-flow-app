"""
Environment management and validation.
"""

import os
from enum import Enum
from typing import Dict, Any, Optional


class Environment(Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class EnvironmentManager:
    """Manages environment variables and validation."""

    def __init__(self):
        self.env = self._detect_environment()
        self._required_vars = self._get_required_variables()
        self._validate_environment()

    def _detect_environment(self) -> Environment:
        """Detect current environment from ENV variable."""
        env_str = os.getenv("ENV", "development").lower()
        try:
            return Environment(env_str)
        except ValueError:
            return Environment.DEVELOPMENT

    def _get_required_variables(self) -> Dict[Environment, list]:
        """Get required environment variables by environment."""
        return {
            Environment.DEVELOPMENT: [],
            Environment.STAGING: ["SECRET_KEY"],
            Environment.PRODUCTION: [
                "SECRET_KEY",
                "STRIPE_API_KEY",
                "AIRTABLE_API_KEY",
                "AIRTABLE_BASE_ID",
            ],
            Environment.TESTING: [],
        }

    def _validate_environment(self) -> None:
        """Validate that required environment variables are set."""
        required = self._required_vars.get(self.env, [])
        missing = []

        for var in required:
            if not os.getenv(var):
                missing.append(var)

        if missing:
            raise EnvironmentError(
                f"Missing required environment variables for {self.env.value}: {', '.join(missing)}"
            )

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.env == Environment.DEVELOPMENT

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.env == Environment.PRODUCTION

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.env == Environment.TESTING

    def get_database_url(self) -> str:
        """Get database URL based on environment."""
        if self.is_testing():
            return ":memory:"
        elif self.is_production():
            return os.getenv("DATABASE_URL", "cashflow_prod.db")
        else:
            return os.getenv("DATABASE_URL", "cashflow.db")

    def get_log_level(self) -> str:
        """Get appropriate log level for environment."""
        level_map = {
            Environment.DEVELOPMENT: "DEBUG",
            Environment.STAGING: "INFO",
            Environment.PRODUCTION: "WARNING",
            Environment.TESTING: "ERROR",
        }
        return os.getenv("LOG_LEVEL", level_map[self.env])

    def get_debug_mode(self) -> bool:
        """Get debug mode setting."""
        if self.is_production():
            return False
        return os.getenv("DEBUG", "true").lower() == "true"
