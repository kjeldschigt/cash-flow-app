"""
Dependency Injection Container

This module provides a centralized container for managing dependencies
and service instantiation throughout the application.
"""

from typing import Dict, Any, Optional, TypeVar, Type
from .config.settings import Settings
from .repositories.base import DatabaseConnection
from .repositories.user_repository import UserRepository
from .repositories.payment_repository import PaymentRepository, PaymentScheduleRepository
from .repositories.cost_repository import CostRepository, RecurringCostRepository
from .repositories.integration_repository import IntegrationRepository, SettingsRepository
from .services.user_service import UserService
from .services.payment_service import PaymentService, PaymentScheduleService
from .services.cost_service import CostService, RecurringCostService
from .services.integration_service import IntegrationService
from .services.analytics_service import AnalyticsService

T = TypeVar('T')


class Container:
    """Dependency injection container for managing application services."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._singletons: Dict[str, Any] = {}
        self._settings: Optional[Settings] = None
        self._db_connection: Optional[DatabaseConnection] = None
    
    def configure(self, settings: Optional[Settings] = None) -> None:
        """Configure the container with settings."""
        self._settings = settings or Settings()
        self._db_connection = DatabaseConnection(self._settings.database.path)
        
        # Register core services
        self._register_repositories()
        self._register_services()
    
    def get_settings(self) -> Settings:
        """Get application settings."""
        if not self._settings:
            self._settings = Settings()
        return self._settings
    
    def get_db_connection(self) -> DatabaseConnection:
        """Get database connection."""
        if not self._db_connection:
            settings = self.get_settings()
            self._db_connection = DatabaseConnection(settings.database.path)
        return self._db_connection
    
    def _register_repositories(self) -> None:
        """Register repository instances."""
        db = self.get_db_connection()
        
        self._singletons['user_repository'] = UserRepository(db)
        self._singletons['payment_repository'] = PaymentRepository(db)
        self._singletons['payment_schedule_repository'] = PaymentScheduleRepository(db)
        self._singletons['cost_repository'] = CostRepository(db)
        self._singletons['recurring_cost_repository'] = RecurringCostRepository(db)
        self._singletons['integration_repository'] = IntegrationRepository(db)
        self._singletons['settings_repository'] = SettingsRepository(db)
    
    def _register_services(self) -> None:
        """Register service instances."""
        db = self.get_db_connection()
        settings = self.get_settings()
        
        self._singletons['user_service'] = UserService(db)
        self._singletons['payment_service'] = PaymentService(db)
        self._singletons['payment_schedule_service'] = PaymentScheduleService(db)
        self._singletons['cost_service'] = CostService(db)
        self._singletons['recurring_cost_service'] = RecurringCostService(db)
        self._singletons['integration_service'] = IntegrationService(db, settings)
        self._singletons['analytics_service'] = AnalyticsService(db)
    
    def get_user_service(self) -> UserService:
        """Get user service instance."""
        return self._singletons['user_service']
    
    def get_payment_service(self) -> PaymentService:
        """Get payment service instance."""
        return self._singletons['payment_service']
    
    def get_payment_schedule_service(self) -> PaymentScheduleService:
        """Get payment schedule service instance."""
        return self._singletons['payment_schedule_service']
    
    def get_cost_service(self) -> CostService:
        """Get cost service instance."""
        return self._singletons['cost_service']
    
    def get_recurring_cost_service(self) -> RecurringCostService:
        """Get recurring cost service instance."""
        return self._singletons['recurring_cost_service']
    
    def get_integration_service(self) -> IntegrationService:
        """Get integration service instance."""
        return self._singletons['integration_service']
    
    def get_analytics_service(self) -> AnalyticsService:
        """Get analytics service instance."""
        return self._singletons['analytics_service']
    
    def get_user_repository(self) -> UserRepository:
        """Get user repository instance."""
        return self._singletons['user_repository']
    
    def get_payment_repository(self) -> PaymentRepository:
        """Get payment repository instance."""
        return self._singletons['payment_repository']
    
    def get_payment_schedule_repository(self) -> PaymentScheduleRepository:
        """Get payment schedule repository instance."""
        return self._singletons['payment_schedule_repository']
    
    def get_cost_repository(self) -> CostRepository:
        """Get cost repository instance."""
        return self._singletons['cost_repository']
    
    def get_recurring_cost_repository(self) -> RecurringCostRepository:
        """Get recurring cost repository instance."""
        return self._singletons['recurring_cost_repository']
    
    def get_integration_repository(self) -> IntegrationRepository:
        """Get integration repository instance."""
        return self._singletons['integration_repository']
    
    def get_settings_repository(self) -> SettingsRepository:
        """Get settings repository instance."""
        return self._singletons['settings_repository']
    
    def register_singleton(self, name: str, instance: Any) -> None:
        """Register a singleton instance."""
        self._singletons[name] = instance
    
    def get_singleton(self, name: str) -> Any:
        """Get a singleton instance by name."""
        return self._singletons.get(name)
    
    def cleanup(self) -> None:
        """Cleanup container resources."""
        if self._db_connection:
            self._db_connection.close_all_connections()
        self._services.clear()
        self._singletons.clear()


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """Get the global container instance."""
    global _container
    if _container is None:
        _container = Container()
        _container.configure()
    return _container


def configure_container(settings: Optional[Settings] = None) -> Container:
    """Configure and return the global container."""
    global _container
    _container = Container()
    _container.configure(settings)
    return _container


def cleanup_container() -> None:
    """Cleanup the global container."""
    global _container
    if _container:
        _container.cleanup()
        _container = None
