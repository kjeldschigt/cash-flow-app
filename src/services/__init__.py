"""
Services package initialization.

This module provides access to all service classes used in the application.
"""

import logging
from typing import Optional, Type, TypeVar, Any

# Type variable for service classes
T = TypeVar('T')

def _import_service(module_name: str, class_name: str) -> Optional[Type[Any]]:
    """Safely import a service class with error handling."""
    try:
        # Try direct import first
        module = __import__(f"src.services.{module_name}", fromlist=[class_name])
        return getattr(module, class_name)
    except (ImportError, AttributeError):
        try:
            # Fall back to relative import
            module = __import__(f".{module_name}", fromlist=[class_name], level=1)
            return getattr(module, class_name)
        except (ImportError, AttributeError) as e:
            logging.warning(
                "Could not import %s from %s: %s",
                class_name,
                module_name,
                str(e),
                exc_info=True
            )
            return None

# Import core services
from .auth_service import AuthService
from .storage_service import StorageService
from .payment_service import PaymentService as StripeService
from .integration_service import IntegrationService as AirtableService
from .financial_calculator import FinancialCalculator

# Export all services
__all__ = [
    "AuthService",
    "StorageService",
    "StripeService",
    "AirtableService",
    "FinancialCalculator"
]
