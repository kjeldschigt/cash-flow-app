"""
Repository Layer

This module provides data access abstractions and database operations
following the Repository pattern for clean separation of concerns.
"""

from .base import BaseRepository, DatabaseConnection
from .user_repository import UserRepository
from .payment_repository import PaymentRepository, PaymentScheduleRepository
from .cost_repository import CostRepository, RecurringCostRepository
from .integration_repository import IntegrationRepository
from .settings_repository import SettingsRepository

__all__ = [
    "BaseRepository",
    "DatabaseConnection",
    "UserRepository",
    "PaymentRepository",
    "PaymentScheduleRepository",
    "CostRepository",
    "RecurringCostRepository",
    "IntegrationRepository",
    "SettingsRepository"
]
