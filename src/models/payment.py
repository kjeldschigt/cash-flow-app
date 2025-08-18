"""
Payment domain models and related entities.
"""

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional


class PaymentStatus(Enum):
    """Payment status enumeration."""

    SCHEDULED = "scheduled"
    PAID = "paid"
    SKIPPED = "skipped"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"


class RecurrenceType(Enum):
    """Payment recurrence types."""

    WEEKLY = "weekly"
    BIWEEKLY = "bi-weekly"
    MONTHLY = "monthly"
    BIMONTHLY = "every 2 months"
    QUARTERLY = "quarterly"
    SEMIANNUAL = "semiannual"
    YEARLY = "yearly"


@dataclass
class Payment:
    """Individual payment entity."""

    id: Optional[str]
    amount: Decimal
    currency: str
    status: PaymentStatus
    payment_date: Optional[date]
    description: Optional[str]
    external_id: Optional[str]  # Stripe payment ID, etc.
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    def mark_as_paid(self, payment_date: Optional[date] = None) -> None:
        """Mark payment as paid."""
        self.status = PaymentStatus.PAID
        self.payment_date = payment_date or date.today()
        self.updated_at = datetime.now()

    def is_overdue(self, due_date: date) -> bool:
        """Check if payment is overdue."""
        return self.status == PaymentStatus.SCHEDULED and due_date < date.today()


@dataclass
class PaymentSchedule:
    """Payment schedule entity for recurring payments."""

    id: Optional[str]
    name: str
    category: str
    currency: str
    amount_expected: Decimal
    amount_actual: Optional[Decimal]
    comment: Optional[str]
    recurrence: RecurrenceType
    due_date: date
    status: PaymentStatus
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def create(
        cls,
        name: str,
        category: str,
        currency: str,
        amount_expected: Decimal,
        recurrence: RecurrenceType,
        due_date: date,
        comment: Optional[str] = None,
    ) -> "PaymentSchedule":
        """Create a new payment schedule."""
        return cls(
            id=None,
            name=name,
            category=category,
            currency=currency,
            amount_expected=amount_expected,
            amount_actual=None,
            comment=comment,
            recurrence=recurrence,
            due_date=due_date,
            status=PaymentStatus.SCHEDULED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    def mark_as_paid(self, actual_amount: Decimal) -> None:
        """Mark scheduled payment as paid."""
        self.status = PaymentStatus.PAID
        self.amount_actual = actual_amount
        self.updated_at = datetime.now()

    def skip(self) -> None:
        """Mark scheduled payment as skipped."""
        self.status = PaymentStatus.SKIPPED
        self.updated_at = datetime.now()

    def is_overdue(self) -> bool:
        """Check if scheduled payment is overdue."""
        return self.status == PaymentStatus.SCHEDULED and self.due_date < date.today()
