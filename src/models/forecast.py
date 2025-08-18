"""
Forecast and Loan Domain Models
"""

from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict, field_serializer
from pydantic_core.core_schema import FieldValidationInfo


class ForecastType(Enum):
    """Forecast type enumeration"""

    REVENUE = "revenue"
    EXPENSE = "expense"
    CASH_FLOW = "cash_flow"


class ForecastPeriod(Enum):
    """Forecast period enumeration"""

    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class ForecastModel(BaseModel):
    """Financial forecast model with validation"""

    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=200)
    forecast_type: ForecastType
    period: ForecastPeriod
    start_date: date
    end_date: date
    projected_amount: Decimal = Field(..., description="Projected amount")
    currency: str = Field(..., min_length=3, max_length=3)
    confidence_level: Decimal = Field(default=Decimal("0.8"), ge=0, le=1)
    assumptions: Optional[str] = Field(None, max_length=1000)
    created_at: Optional[datetime] = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = Field(default_factory=datetime.now)

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, v: date, info: FieldValidationInfo) -> date:
        """Validate end date is after start date"""
        data = info.data
        if "start_date" in data and v <= data["start_date"]:
            raise ValueError("End date must be after start date")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """Validate currency code"""
        valid_currencies = ["USD", "CRC", "EUR", "GBP", "CAD"]
        if v.upper() not in valid_currencies:
            raise ValueError(f"Currency must be one of: {valid_currencies}")
        return v.upper()

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }
    )


class LoanType(Enum):
    """Loan type enumeration"""

    TERM_LOAN = "term_loan"
    LINE_OF_CREDIT = "line_of_credit"
    MORTGAGE = "mortgage"
    PERSONAL = "personal"
    BUSINESS = "business"


class LoanStatus(Enum):
    """Loan status enumeration"""

    ACTIVE = "active"
    PAID_OFF = "paid_off"
    DEFAULTED = "defaulted"
    REFINANCED = "refinanced"


class LoanModel(BaseModel):
    """Loan model with comprehensive validation"""

    id: Optional[str] = None
    loan_name: str = Field(..., min_length=1, max_length=200)
    loan_type: LoanType
    principal_amount: Decimal = Field(
        ..., gt=0, description="Principal amount must be positive"
    )
    interest_rate: Decimal = Field(
        ..., ge=0, le=1, description="Interest rate as decimal (0.05 = 5%)"
    )
    term_months: int = Field(..., gt=0, le=600, description="Loan term in months")
    currency: str = Field(..., min_length=3, max_length=3)
    start_date: date
    monthly_payment: Optional[Decimal] = None
    remaining_balance: Optional[Decimal] = None
    status: LoanStatus = Field(default=LoanStatus.ACTIVE)
    lender: Optional[str] = Field(None, max_length=200)
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

    @model_validator(mode='after')
    def calculate_monthly_payment(self) -> 'LoanModel':
        """Calculate monthly payment if not provided"""
        if self.monthly_payment is None and all(
            hasattr(self, field)
            for field in ["principal_amount", "interest_rate", "term_months"]
        ):
            principal = self.principal_amount
            rate = self.interest_rate / 12  # Monthly rate
            months = self.term_months

            if rate > 0:
                # Amortization formula
                monthly_payment = (
                    principal
                    * (rate * (1 + rate) ** months)
                    / ((1 + rate) ** months - 1)
                )
                self.monthly_payment = monthly_payment
            else:
                # No interest, simple division
                self.monthly_payment = principal / months
        return self

    @field_validator("remaining_balance", mode='before')
    @classmethod
    def set_initial_balance(
        cls, 
        v: Optional[Decimal], 
        info: FieldValidationInfo
    ) -> Decimal:
        """Set initial remaining balance to principal amount"""
        data = info.data
        if v is None and "principal_amount" in data:
            return data["principal_amount"]
        return v or Decimal("0.0")

    def calculate_amortization_schedule(self) -> List[dict]:
        """Calculate loan amortization schedule"""
        schedule = []
        balance = self.remaining_balance or self.principal_amount
        monthly_rate = self.interest_rate / 12

        for month in range(1, self.term_months + 1):
            if balance <= 0:
                break

            interest_payment = balance * monthly_rate
            principal_payment = self.monthly_payment - interest_payment

            if principal_payment > balance:
                principal_payment = balance

            balance -= principal_payment

            schedule.append(
                {
                    "month": month,
                    "payment": float(self.monthly_payment),
                    "principal": float(principal_payment),
                    "interest": float(interest_payment),
                    "balance": float(balance),
                }
            )

        return schedule

    model_config = ConfigDict(
        from_attributes=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            date: lambda v: v.isoformat(),
            Decimal: lambda v: float(v),
        }
    )
