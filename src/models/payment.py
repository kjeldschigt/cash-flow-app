"""
Payment domain models and related entities.
"""

from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Annotated
from pydantic import Field, field_validator, model_validator

from .base import BaseModel, FieldConfig

# Custom types for better validation
PositiveDecimal = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]
CurrencyCode = Annotated[str, Field(pattern=r'^[A-Z]{3}$', description="3-letter ISO currency code")]


class PaymentStatus(str, Enum):
    """Payment status enumeration."""

    SCHEDULED = "scheduled"
    PAID = "paid"
    SKIPPED = "skipped"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    
    @classmethod
    def get_status_style(cls, status: 'PaymentStatus') -> str:
        """Get CSS class for status display."""
        styles = {
            cls.SCHEDULED: "badge bg-info",
            cls.PAID: "badge bg-success",
            cls.SKIPPED: "badge bg-warning text-dark",
            cls.OVERDUE: "badge bg-danger",
            cls.CANCELLED: "badge bg-secondary"
        }
        return styles.get(status, "badge bg-secondary")


class RecurrenceType(str, Enum):
    """Payment recurrence types with interval in days."""
    
    WEEKLY = "weekly"
    BIWEEKLY = "bi-weekly"
    MONTHLY = "monthly"
    BIMONTHLY = "bimonthly"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    YEARLY = "yearly"
    
    @property
    def days_interval(self) -> int:
        """Get the number of days between occurrences."""
        intervals = {
            self.WEEKLY: 7,
            self.BIWEEKLY: 14,
            self.MONTHLY: 30,  # Approximation
            self.BIMONTHLY: 60,  # Approximation
            self.QUARTERLY: 90,  # Approximation
            self.SEMIANNUAL: 180,  # Approximation
            self.YEARLY: 365  # Approximation
        }
        return intervals.get(self, 30)
    
    @classmethod
    def get_next_date(cls, current_date: date, recurrence_pattern: 'RecurrenceType') -> date:
        """Calculate next occurrence date based on recurrence.
        
        Args:
            current_date: The reference date to calculate from
            recurrence_pattern: The recurrence pattern to use for calculation
            
        Returns:
            date: The next occurrence date
        """
        from dateutil.relativedelta import relativedelta
        
        delta_map = {
            cls.WEEKLY: relativedelta(weeks=1),
            cls.BIWEEKLY: relativedelta(weeks=2),
            cls.MONTHLY: relativedelta(months=1),
            cls.BIMONTHLY: relativedelta(months=2),
            cls.QUARTERLY: relativedelta(months=3),
            cls.SEMIANNUAL: relativedelta(months=6),
            cls.YEARLY: relativedelta(years=1)
        }
        
        return current_date + delta_map.get(recurrence_pattern, relativedelta(months=1))


class Payment(BaseModel):
    """Individual payment entity with validation and business logic."""
    
    model_config = BaseModel.model_config.copy()
    model_config.update(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439012",
                "amount": "99.99",
                "currency": "USD",
                "status": "paid",
                "payment_date": "2023-01-15",
                "description": "Monthly subscription",
                "external_id": "pi_3Nk2XqLzdXvBQ5Yb1X2X3X4X",
                "metadata": {"invoice_id": "INV-2023-001"},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-15T14:30:00Z"
            }
        }
    )
    
    amount: PositiveDecimal = Field(..., description="Payment amount")
    currency: CurrencyCode = Field(..., description="3-letter ISO currency code")
    status: PaymentStatus = Field(default=PaymentStatus.SCHEDULED, description="Payment status")
    payment_date: Optional[date] = Field(
        default=None,
        description="Date when payment was processed"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Description or notes about the payment"
    )
    external_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="External payment reference (e.g., Stripe payment ID)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the payment"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when payment was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when payment was last updated"
    )
    
    @field_validator('amount')
    @classmethod
    def validate_amount(cls, v: Decimal) -> Decimal:
        """Ensure amount is positive and has no more than 2 decimal places."""
        if v <= 0:
            raise ValueError("Amount must be positive")
        if v.as_tuple().exponent < -2:  # More than 2 decimal places
            v = v.quantize(Decimal('0.01'))
        return v
    
    def mark_as_paid(self, payment_date: Optional[date] = None) -> None:
        """Mark payment as paid and update timestamps."""
        self.status = PaymentStatus.PAID
        self.payment_date = payment_date or date.today()
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_overdue(self) -> None:
        """Mark payment as overdue if it's still scheduled."""
        if self.status == PaymentStatus.SCHEDULED:
            self.status = PaymentStatus.OVERDUE
            self.updated_at = datetime.now(timezone.utc)
    
    def is_overdue(self, due_date: Optional[date] = None) -> bool:
        """Check if payment is overdue."""
        if self.status != PaymentStatus.SCHEDULED:
            return False
        due_date = due_date or (self.payment_date if self.payment_date else date.today())
        return due_date < date.today()
    
    def get_status_style(self) -> str:
        """Get CSS class for status display."""
        return PaymentStatus.get_status_style(self.status)


class PaymentSchedule(BaseModel):
    """Payment schedule entity for recurring payments with validation and business logic."""
    
    model_config = BaseModel.model_config.copy()
    model_config.update(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439013",
                "name": "Netflix Subscription",
                "category": "Entertainment",
                "currency": "USD",
                "amount_expected": "15.99",
                "amount_actual": "15.99",
                "comment": "Monthly streaming service",
                "recurrence_pattern": "monthly",
                "due_date": "2023-02-01",
                "status": "scheduled",
                "metadata": {"account_id": "netflix123"},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-01-01T12:00:00Z"
            }
        }
    )
    
    name: str = Field(..., max_length=100, description="Name or description of the payment")
    category: str = Field(..., max_length=50, description="Category for grouping payments")
    currency: CurrencyCode = Field(..., description="3-letter ISO currency code")
    amount_expected: PositiveDecimal = Field(..., description="Expected payment amount")
    amount_actual: Optional[PositiveDecimal] = Field(
        default=None,
        description="Actual amount paid (may differ from expected)"
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Additional notes or comments about the payment"
    )
    recurrence_pattern: RecurrenceType = Field(
            default=RecurrenceType.MONTHLY,
            description="How often this payment recurs",
            alias="recurrence"
        )
    due_date: date = Field(..., description="Next due date for the payment")
    status: PaymentStatus = Field(
        default=PaymentStatus.SCHEDULED,
        description="Current status of the payment schedule"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the payment schedule"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when schedule was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when schedule was last updated"
    )
    
    @classmethod
    def create(
        cls,
        name: str,
        category: str,
        currency: str,
        amount_expected: Decimal,
        recurrence_pattern: RecurrenceType,
        due_date: date,
        **kwargs
    ) -> 'PaymentSchedule':
        """Create a new payment schedule with proper defaults."""
        return cls(
            name=name,
            category=category,
            currency=currency.upper(),
            amount_expected=amount_expected,
            recurrence_pattern=recurrence_pattern,
            due_date=due_date,
            **kwargs
        )
    
    @model_validator(mode='after')
    def validate_dates(self) -> 'PaymentSchedule':
        """Ensure dates are valid and consistent."""
        if hasattr(self, 'created_at') and hasattr(self, 'updated_at'):
            if self.updated_at < self.created_at:
                raise ValueError("Updated date cannot be before created date")
        return self
    
    def update_status(self, new_status: PaymentStatus) -> None:
        """Update the payment schedule status and timestamps."""
        self.status = new_status
        self.updated_at = datetime.now(timezone.utc)
    
    def mark_as_paid(self, amount: Optional[Decimal] = None) -> None:
        """Mark the scheduled payment as paid."""
        self.status = PaymentStatus.PAID
        self.amount_actual = amount or self.amount_expected
        self.updated_at = datetime.now(timezone.utc)
    
    def calculate_next_payment_date(self, current_date: Optional[date] = None) -> date:
        """Calculate the next payment date based on recurrence.
        
        Args:
            current_date: Optional reference date (defaults to today)
            
        Returns:
            date: Next payment due date
        """
        current_date = current_date or date.today()
        next_date = self.due_date
        
        # If the due date is in the future, return it
        if next_date > current_date:
            return next_date
            
        # Otherwise, calculate the next occurrence using the recurrence pattern
        return RecurrenceType.get_next_date(current_date, self.recurrence_pattern)
    
    def get_status_style(self) -> str:
        """Get CSS class for status display."""
        return PaymentStatus.get_status_style(self.status)
    
    def to_payment(self) -> 'Payment':
        """Convert schedule to a Payment instance."""
        return Payment(
            amount=self.amount_expected,
            currency=self.currency,
            status=self.status,
            payment_date=self.due_date if self.status == PaymentStatus.PAID else None,
            description=f"{self.name} - {self.comment}" if self.comment else self.name,
            metadata={
                "schedule_id": str(self.id),
                "category": self.category,
                **self.metadata
            }
        )
