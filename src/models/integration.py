"""
Integration domain models and related entities.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any, List


class IntegrationType(Enum):
    """Integration type enumeration."""
    STRIPE = "stripe"
    AIRTABLE = "airtable"
    WEBHOOK = "webhook"
    GOOGLE_ADS = "google_ads"
    ABLE_CDP = "able_cdp"
    CUSTOM = "custom"


class IntegrationStatus(Enum):
    """Integration status enumeration."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    PENDING = "pending"
    CONFIGURED = "configured"


@dataclass
class Integration:
    """Integration configuration entity."""
    id: Optional[str]
    name: str
    type: IntegrationType
    is_enabled: bool
    config: Dict[str, Any]
    events: List[str]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    last_sync: Optional[datetime]

    @classmethod
    def create(
        cls,
        name: str,
        integration_type: IntegrationType,
        config: Dict[str, Any],
        events: Optional[List[str]] = None
    ) -> 'Integration':
        """Create a new integration."""
        return cls(
            id=None,
            name=name,
            type=integration_type,
            is_enabled=True,
            config=config,
            events=events or [],
            created_at=datetime.now(),
            updated_at=datetime.now(),
            last_sync=None
        )

    def enable(self) -> None:
        """Enable the integration."""
        self.is_enabled = True
        self.updated_at = datetime.now()

    def disable(self) -> None:
        """Disable the integration."""
        self.is_enabled = False
        self.updated_at = datetime.now()

    def update_config(self, config: Dict[str, Any]) -> None:
        """Update integration configuration."""
        self.config.update(config)
        self.updated_at = datetime.now()

    def record_sync(self) -> None:
        """Record successful sync timestamp."""
        self.last_sync = datetime.now()

    def get_api_key(self) -> Optional[str]:
        """Get API key from config if available."""
        return self.config.get('api_key')

    def get_webhook_url(self) -> Optional[str]:
        """Get webhook URL from config if available."""
        return self.config.get('webhook_url')

    def is_configured(self) -> bool:
        """Check if integration is properly configured."""
        if self.type in [IntegrationType.STRIPE, IntegrationType.AIRTABLE, IntegrationType.GOOGLE_ADS]:
            return bool(self.get_api_key())
        elif self.type == IntegrationType.WEBHOOK:
            return bool(self.get_webhook_url())
        elif self.type == IntegrationType.AIRTABLE:
            return bool(
                self.get_api_key() and 
                self.config.get('base_id') and 
                self.config.get('table_name')
            )
        return bool(self.config)
