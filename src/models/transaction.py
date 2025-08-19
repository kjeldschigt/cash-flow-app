"""
Transaction and Revenue Domain Models
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer, model_validator
from pydantic_core.core_schema import FieldValidationInfo
from typing import Optional, Dict, Any


class TransactionType(Enum):
    """Transaction type enumeration"""

    INCOME = "income"
    EXPENSE = "expense"
    TRANSFER = "transfer"


class TransactionStatus(Enum):
    """Transaction status enumeration"""

    PENDING = "pending"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TransactionModel(BaseModel):
    """Transaction model with comprehensive validation"""

    id: Optional[str] = None
    transaction_type: TransactionType
    amount: Decimal = Field(
        ..., gt=0, description="Transaction amount must be positive"
    )
    currency: str = Field(
        ..., min_length=3, max_length=3, description="ISO currency code"
    )
    description: str = Field(..., min_length=1, max_length=500)
    category: str = Field(..., min_length=1, max_length=100)
    transaction_date: date = Field(default_factory=date.today)
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    reference_id: Optional[str] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code"""
        valid_currencies = ["USD", "CRC", "EUR", "GBP", "CAD"]
        if v.upper() not in valid_currencies:
            raise ValueError(f"Currency must be one of: {valid_currencies}")
        return v.upper()

    @field_validator("transaction_date")
    @classmethod
    def validate_date(cls, v: date) -> date:
        """Validate transaction date is not in future"""
        if v > date.today():
            raise ValueError("Transaction date cannot be in the future")
        return v

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }
    )


class RevenueModel(BaseModel):
    """Revenue model with business validation"""

    id: Optional[str] = None
    source: str = Field(..., min_length=1, max_length=200)
    amount: Decimal = Field(..., gt=0, description="Revenue amount must be positive")
    currency: str = Field(..., min_length=3, max_length=3)
    revenue_date: date = Field(default_factory=date.today)
    customer_id: Optional[str] = None
    product_category: Optional[str] = None
    recurring: bool = Field(default=False)
    tax_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    net_amount: Optional[Decimal] = None
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code"""
        valid_currencies = ["USD", "CRC", "EUR", "GBP", "CAD"]
        if v.upper() not in valid_currencies:
            raise ValueError(f"Currency must be one of: {valid_currencies}")
        return v.upper()

    @model_validator(mode='before')
    @classmethod
    def calculate_net_amount(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate net amount after tax"""
        if "amount" in values and "tax_rate" in values and "net_amount" not in values:
            amount = values["amount"]
            tax_rate = values.get("tax_rate", Decimal("0.0"))
            tax = amount * (tax_rate / 100)
            values["net_amount"] = amount + tax
        return values

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }
    )
