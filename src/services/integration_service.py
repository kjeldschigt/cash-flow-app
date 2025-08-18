"""
Integration service for external API management with circuit breaker and retry logic.
"""

import json
import requests
import time
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Callable
from functools import wraps
from ..models.integration import Integration, IntegrationType
from ..repositories.integration_repository import IntegrationRepository
from ..repositories.settings_repository import SettingsRepository
from ..repositories.base import DatabaseConnection
from ..config.settings import Settings

logger = logging.getLogger(__name__)

class CircuitBreakerError(Exception):
    """Circuit breaker is open"""
    pass

class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
    
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == 'OPEN':
            if datetime.now() - self.last_failure_time > timedelta(seconds=self.timeout):
                self.state = 'HALF_OPEN'
            else:
                raise CircuitBreakerError("Circuit breaker is OPEN")
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as e:
            self._on_failure()
            raise e
    
    def _on_success(self):
        """Reset circuit breaker on success"""
        self.failure_count = 0
        self.state = 'CLOSED'
    
    def _on_failure(self):
        """Handle failure in circuit breaker"""
        self.failure_count += 1
        self.last_failure_time = datetime.now()
        
        if self.failure_count >= self.failure_threshold:
            self.state = 'OPEN'

def retry_with_backoff(max_retries: int = 3, backoff_factor: float = 1.0):
    """Decorator for retry logic with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    
                    wait_time = backoff_factor * (2 ** attempt)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {wait_time}s: {str(e)}")
                    time.sleep(wait_time)
            
            return None
        return wrapper
    return decorator

class IntegrationService:
    """Service for managing external integrations with resilience patterns."""
    
    def __init__(self, db_connection: DatabaseConnection, settings: Settings):
        self.integration_repository = IntegrationRepository(db_connection)
        self.settings_repository = SettingsRepository(db_connection)
        self.settings = settings
        self.circuit_breakers = {}  # Per-integration circuit breakers
    
    def create_integration(
        self,
        name: str,
        integration_type: IntegrationType,
        config: Dict[str, Any],
        events: Optional[List[str]] = None
    ) -> Integration:
        """Create a new integration."""
        integration = Integration.create(
            name=name,
            integration_type=integration_type,
            config=config,
            events=events or []
        )
        return self.integration_repository.save(integration)
    
    def get_all_integrations(self) -> List[Integration]:
        """Get all integrations."""
        return self.integration_repository.find_all()
    
    def get_enabled_integrations(self) -> List[Integration]:
        """Get all enabled integrations."""
        return self.integration_repository.find_enabled_integrations()
    
    def get_integrations_by_type(self, integration_type: IntegrationType) -> List[Integration]:
        """Get integrations by type."""
        return self.integration_repository.find_by_type(integration_type)
    
    def enable_integration(self, integration_id: str) -> bool:
        """Enable an integration."""
        integration = self.integration_repository.find_by_id(integration_id)
        if not integration:
            return False
        
        integration.enable()
        self.integration_repository.save(integration)
        return True
    
    def disable_integration(self, integration_id: str) -> bool:
        """Disable an integration."""
        integration = self.integration_repository.find_by_id(integration_id)
        if not integration:
            return False
        
        integration.disable()
        self.integration_repository.save(integration)
        return True
    
    def update_integration_config(
        self,
        integration_id: str,
        config_updates: Dict[str, Any]
    ) -> Optional[Integration]:
        """Update integration configuration."""
        integration = self.integration_repository.find_by_id(integration_id)
        if not integration:
            return None
        
        integration.update_config(config_updates)
        return self.integration_repository.save(integration)
    
    def test_integration(self, integration_id: str) -> Dict[str, Any]:
        """Test integration connectivity."""
        integration = self.integration_repository.find_by_id(integration_id)
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        if not integration.is_enabled:
            return {"success": False, "error": "Integration is disabled"}
        
        try:
            if integration.type == IntegrationType.STRIPE:
                return self._test_stripe_integration(integration)
            elif integration.type == IntegrationType.AIRTABLE:
                return self._test_airtable_integration(integration)
            elif integration.type == IntegrationType.WEBHOOK:
                return self._test_webhook_integration(integration)
            else:
                return {"success": False, "error": "Integration type not supported for testing"}
        
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _test_stripe_integration(self, integration: Integration) -> Dict[str, Any]:
        """Test Stripe integration."""
        api_key = integration.get_api_key()
        if not api_key:
            return {"success": False, "error": "API key not configured"}
        
        try:
            import stripe
            stripe.api_key = api_key
            
            # Test by retrieving account info
            account = stripe.Account.retrieve()
            integration.record_sync()
            self.integration_repository.save(integration)
            
            return {
                "success": True,
                "message": f"Connected to Stripe account: {account.get('display_name', account.get('id'))}"
            }
        except Exception as e:
            return {"success": False, "error": f"Stripe connection failed: {str(e)}"}
    
    def _test_airtable_integration(self, integration: Integration) -> Dict[str, Any]:
        """Test Airtable integration."""
        api_key = integration.get_api_key()
        base_id = integration.config.get('base_id')
        
        if not api_key or not base_id:
            return {"success": False, "error": "API key or base ID not configured"}
        
        try:
            from pyairtable import Api
            api = Api(api_key)
            base = api.base(base_id)
            
            # Test by listing tables
            tables = base.schema().tables
            integration.record_sync()
            self.integration_repository.save(integration)
            
            return {
                "success": True,
                "message": f"Connected to Airtable base with {len(tables)} tables"
            }
        except Exception as e:
            return {"success": False, "error": f"Airtable connection failed: {str(e)}"}
    
    def _test_webhook_integration(self, integration: Integration) -> Dict[str, Any]:
        """Test webhook integration."""
        webhook_url = integration.get_webhook_url()
        if not webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        try:
            test_payload = {
                "test": True,
                "timestamp": datetime.now().isoformat(),
                "message": "Test webhook from Cash Flow Dashboard"
            }
            
            response = requests.post(
                webhook_url,
                json=test_payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                integration.record_sync()
                self.integration_repository.save(integration)
                return {"success": True, "message": "Webhook test successful"}
            else:
                return {
                    "success": False,
                    "error": f"Webhook returned status {response.status_code}"
                }
        
        except requests.exceptions.Timeout:
            return {"success": False, "error": "Webhook request timed out"}
        except Exception as e:
            return {"success": False, "error": f"Webhook test failed: {str(e)}"}
    
    def send_webhook_payload(self, integration_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Send custom payload to webhook."""
        integration = self.integration_repository.find_by_id(integration_id)
        if not integration or integration.type != IntegrationType.WEBHOOK:
            return {"success": False, "error": "Webhook integration not found"}
        
        webhook_url = integration.get_webhook_url()
        if not webhook_url:
            return {"success": False, "error": "Webhook URL not configured"}
        
        try:
            response = requests.post(
                webhook_url,
                json=payload,
                timeout=10,
                headers={"Content-Type": "application/json"}
            )
            
            return {
                "success": True,
                "status_code": response.status_code,
                "response": response.text[:500]  # Limit response size
            }
        
        except Exception as e:
            return {"success": False, "error": str(e)}
