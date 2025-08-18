"""
Cost domain models and related entities with Pydantic v2.
"""

from datetime import datetime, date, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional, List, Dict, Any, Annotated
from pydantic import Field, field_validator, model_validator

from .base import BaseModel, FieldConfig, PositiveDecimal, CurrencyCode
from .payment import RecurrenceType

# Type aliases
Amount = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
PositiveAmount = Annotated[Decimal, Field(gt=0, max_digits=12, decimal_places=2)]


class CostCategory(str, Enum):
    """Cost category enumeration with color coding for UI."""

    MARKETING = "Marketing"
    OPERATIONS = "Operations"
    TECHNOLOGY = "Technology"
    LEGAL = "Legal"
    FINANCE = "Finance"
    HUMAN_RESOURCES = "Human Resources"
    OFFICE = "Office"
    TRAVEL = "Travel"
    EQUIPMENT = "Equipment"
    OTHER = "Other"
    
    @classmethod
    def get_color(cls, category: 'CostCategory') -> str:
        """Get a consistent color for each category."""
        colors = {
            cls.MARKETING: "#4e79a7",
            cls.OPERATIONS: "#f28e2b",
            cls.TECHNOLOGY: "#e15759",
            cls.LEGAL: "#76b7b2",
            cls.FINANCE: "#59a14f",
            cls.HUMAN_RESOURCES: "#edc948",
            cls.OFFICE: "#b07aa1",
            cls.TRAVEL: "#ff9da7",
            cls.EQUIPMENT: "#9c755f",
            cls.OTHER: "#bab0ac"
        }
        return colors.get(category, "#999999")


class Cost(BaseModel):
    """Individual cost entry with validation and business logic."""
    
    model_config = BaseModel.model_config.copy()
    model_config.update(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439014",
                "cost_date": "2023-06-15",
                "category": "TECHNOLOGY",
                "amount_usd": "99.99",
                "amount_crc": "53450.25",
                "description": "Monthly SaaS subscription",
                "is_paid": False,
                "metadata": {"invoice_number": "INV-2023-001"},
                "created_at": "2023-06-10T10:30:00Z",
                "updated_at": "2023-06-10T10:30:00Z"
            }
        }
    )
    
    cost_date: date = Field(..., description="Date when the cost was incurred")
    category: CostCategory = Field(..., description="Category of the cost")
    amount_usd: PositiveAmount = Field(..., description="Amount in USD")
    amount_crc: Optional[Amount] = Field(
        default=None,
        description="Amount in local currency (CRC) if applicable"
    )
    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Description or notes about the cost"
    )
    is_paid: bool = Field(
        default=False,
        description="Whether the cost has been paid"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the cost"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the record was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp when the record was last updated"
    )
    
    @field_validator('cost_date')
    @classmethod
    def validate_date_not_in_future(cls, v: date) -> date:
        """Ensure the cost date is not in the future."""
        if v > date.today():
            raise ValueError("Cost date cannot be in the future")
        return v
    
    @field_validator('amount_crc')
    @classmethod
    def validate_amount_crc_positive(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Ensure CRC amount is positive if provided."""
        if v is not None and v < 0:
            raise ValueError("CRC amount cannot be negative")
        return v
    
    def mark_as_paid(self) -> None:
        """Mark the cost as paid and update timestamps."""
        self.is_paid = True
        self.updated_at = datetime.now(timezone.utc)
    
    def update_amounts(
        self, 
        amount_usd: Optional[Decimal] = None, 
        amount_crc: Optional[Decimal] = None
    ) -> None:
        """Update cost amounts with validation.
        
        Args:
            amount_usd: New USD amount (optional)
            amount_crc: New CRC amount (optional, can be None to clear)
        """
        if amount_usd is not None:
            if amount_usd <= 0:
                raise ValueError("USD amount must be positive")
            self.amount_usd = amount_usd
            
        if amount_crc is not None:
            if amount_crc < 0:
                raise ValueError("CRC amount cannot be negative")
            self.amount_crc = amount_crc if amount_crc > 0 else None
            
        self.updated_at = datetime.now(timezone.utc)
    
    def get_category_color(self) -> str:
        """Get the color associated with this cost's category."""
        return CostCategory.get_color(self.category)
    
    def to_dict(self, include_metadata: bool = False) -> Dict[str, Any]:
        """Convert to dictionary with options to include/exclude fields."""
        data = self.model_dump(exclude_none=True)
        if not include_metadata:
            data.pop('metadata', None)
        return data


class RecurringCost(BaseModel):
    """Template for recurring costs with scheduling and tracking."""
    
    model_config = BaseModel.model_config.copy()
    model_config.update(
        json_schema_extra={
            "example": {
                "id": "507f1f77bcf86cd799439015",
                "name": "AWS Monthly Bill",
                "category": "TECHNOLOGY",
                "currency": "USD",
                "amount_expected": "150.00",
                "comment": "Monthly cloud services",
                "recurrence_type": "MONTHLY",
                "next_due_date": "2023-07-01",
                "is_active": True,
                "metadata": {"account_id": "aws-12345"},
                "created_at": "2023-01-01T12:00:00Z",
                "updated_at": "2023-06-01T12:00:00Z"
            }
        }
    )
    
    name: str = Field(..., max_length=100, description="Name of the recurring cost")
    category: CostCategory = Field(..., description="Category of the cost")
    currency: CurrencyCode = Field(..., description="Currency code (e.g., USD, CRC)")
    amount_expected: PositiveAmount = Field(..., description="Expected amount per occurrence")
    comment: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Additional notes about this recurring cost"
    )
    recurrence_type: RecurrenceType = Field(
        default=RecurrenceType.MONTHLY,
        description="How often this cost recurs",
        alias="recurrence"
    )
    next_due_date: date = Field(..., description="Next due date for this cost")
    is_active: bool = Field(
        default=True,
        description="Whether this recurring cost is currently active"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata about the recurring cost"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this record was created"
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this record was last updated"
    )
    
    @classmethod
    def create(
        cls,
        name: str,
        category: CostCategory,
        currency: str,
        amount_expected: Decimal,
        recurrence_type: RecurrenceType,
        next_due_date: date,
        comment: Optional[str] = None,
        is_active: bool = True,
        **kwargs
    ) -> "RecurringCost":
        """Create a new recurring cost with validation.
        
        Args:
            name: Name of the recurring cost
            category: Category of the cost
            currency: 3-letter ISO currency code (e.g., 'USD', 'CRC')
            amount_expected: Expected amount per occurrence
            recurrence_type: How often this cost recurs
            next_due_date: Next due date for this cost
            comment: Optional notes about this cost
            is_active: Whether this cost is currently active
            **kwargs: Additional fields to set on the model
            
        Returns:
            A new RecurringCost instance
        """
        return cls(
            name=name,
            category=category,
            currency=currency.upper(),
            amount_expected=amount_expected,
            recurrence_type=recurrence_type,
            next_due_date=next_due_date,
            comment=comment,
            is_active=is_active,
            **kwargs
        )
    
    @field_validator('currency')
    @classmethod
    def validate_currency_code(cls, v: str) -> str:
        """Ensure currency code is valid and uppercase."""
        if len(v) != 3 or not v.isalpha():
            raise ValueError("Currency code must be a 3-letter ISO code")
        return v.upper()
    
    @field_validator('next_due_date')
    @classmethod
    def validate_future_date(cls, v: date) -> date:
        """Ensure next due date is in the future."""
        if v < date.today():
            raise ValueError("Next due date must be today or in the future")
        return v
    
    def update_next_due_date(self) -> None:
        """Update the next due date based on the recurrence pattern."""
        from dateutil.relativedelta import relativedelta
        
        today = date.today()
        next_date = self.next_due_date
        
        # Skip if the next due date is already in the future
        if next_date > today:
            return
            
        # Use the RecurrenceType enum to get the appropriate time delta
        if self.recurrence_type == RecurrenceType.WEEKLY:
            delta = relativedelta(weeks=1)
        elif self.recurrence_type == RecurrenceType.BIWEEKLY:
            delta = relativedelta(weeks=2)
        elif self.recurrence_type == RecurrenceType.MONTHLY:
            delta = relativedelta(months=1)
        elif self.recurrence_type == RecurrenceType.QUARTERLY:
            delta = relativedelta(months=3)
        elif self.recurrence_type == RecurrenceType.SEMIANNUAL:
            delta = relativedelta(months=6)
        elif self.recurrence_type == RecurrenceType.YEARLY:
            delta = relativedelta(years=1)
        else:
            raise ValueError(f"Unsupported recurrence type: {self.recurrence_type}")
        
        # Calculate next date after today
        while next_date <= today:
            next_date += delta
            
        self.next_due_date = next_date
        self.updated_at = datetime.now(timezone.utc)
    
    def generate_occurrences(self, start_date: date, end_date: date) -> List[date]:
        """Generate all occurrence dates within the given date range.
        
        Args:
            start_date: The start date of the range (inclusive)
            end_date: The end date of the range (inclusive)
            
        Returns:
            A list of dates when the recurring cost occurs within the range
            
        Raises:
            ValueError: If start_date is after end_date
        """
        from dateutil.rrule import rrule, WEEKLY, MONTHLY, YEARLY, DAILY
        from dateutil.relativedelta import relativedelta
        
        if start_date > end_date:
            raise ValueError("Start date must be before end date")
            
        if self.next_due_date > end_date:
            return []
            
        # Map RecurrenceType to dateutil's frequency and interval
        freq_map = {
            RecurrenceType.WEEKLY: (WEEKLY, 1),
            RecurrenceType.BIWEEKLY: (WEEKLY, 2),
            RecurrenceType.MONTHLY: (MONTHLY, 1),
            RecurrenceType.QUARTERLY: (MONTHLY, 3),
            RecurrenceType.SEMIANNUAL: (MONTHLY, 6),
            RecurrenceType.YEARLY: (YEARLY, 1)
        }
        
        # Get the frequency and interval from our mapping
        freq, interval = freq_map.get(self.recurrence_type, (None, None))
        if freq is None:
            raise ValueError(f"Unsupported recurrence type: {self.recurrence_type}")
        
        # Set up the rule
        rule = rrule(
            freq=freq,
            interval=interval,
            dtstart=datetime.combine(self.next_due_date, datetime.min.time()),
            until=datetime.combine(end_date, datetime.max.time())
        )
        
        # Generate all occurrences and filter by date range
        occurrences = [
            d.date() 
            for d in rule.between(
                datetime.combine(start_date, datetime.min.time()),
                datetime.combine(end_date, datetime.max.time()),
                inc=True
            )
            if start_date <= d.date() <= end_date
        ]
        
        return occurrences
    
    def to_cost(self, occurrence_date: Optional[date] = None) -> 'Cost':
        """Convert this recurring cost to a concrete Cost instance."""
        from .cost import Cost
        
        if occurrence_date is None:
            occurrence_date = self.next_due_date
            
        return Cost(
            cost_date=occurrence_date,
            category=self.category,
            amount_usd=self.amount_expected if self.currency == 'USD' else None,
            amount_crc=self.amount_expected if self.currency != 'USD' else None,
            description=f"{self.name} (Recurring: {self.recurrence_type.value})",
            is_paid=False,
            metadata={
                "recurring_cost_id": str(getattr(self, 'id', '')),
                "recurrence_type": self.recurrence_type.value,
                "original_currency": self.currency,
                **self.metadata
            }
        )


# Alias for backward compatibility
CostModel = Cost
RecurringCostModel = RecurringCost
