"""
Domain Models

This module contains the core domain entities and value objects
for the cash flow dashboard application.
"""

# Base models
from .base import BaseModel, FieldConfig, PositiveDecimal, CurrencyCode, Amount, PositiveAmount

# Core domain models
from .user import User, UserRole, UserCreate, UserUpdate, UserInDB
from .payment import Payment, PaymentStatus, PaymentSchedule, RecurrenceType
from .cost import Cost, CostCategory, RecurringCost, CostModel, RecurringCostModel
from .integration import Integration, IntegrationType, IntegrationStatus
from .analytics import CashFlowMetrics, BusinessMetrics, FinancialHealthScore

# Re-export all models for easier imports
__all__ = [
    # Base models
    "BaseModel",
    "FieldConfig",
    "PositiveDecimal",
    "CurrencyCode",
    "Amount",
    "PositiveAmount",
    
    # User models
    "User",
    "UserRole",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    
    # Payment models
    "Payment",
    "PaymentStatus",
    "PaymentSchedule",
    "RecurrenceType",
    
    # Cost models
    "Cost",
    "CostModel",  # Legacy alias
    "CostCategory",
    "RecurringCost",
    "RecurringCostModel",  # Legacy alias
    
    # Integration models
    "Integration",
    "IntegrationType",
    "IntegrationStatus",
    
    # Analytics models
    "CashFlowMetrics",
    "BusinessMetrics",
    "FinancialHealthScore",
]

# Legacy exports for backward compatibility
# These will be deprecated in a future version
PaymentModel = Payment
IntegrationModel = Integration
AnalyticsModel = CashFlowMetrics
