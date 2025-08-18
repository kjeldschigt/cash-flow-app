"""
Cost domain models and related entities.
"""

from dataclasses import dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional


class CostCategory(Enum):
    """Cost category enumeration."""
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


@dataclass
class Cost:
    """Individual cost entry entity."""
    id: Optional[str]
    date: date
    category: CostCategory
    amount_usd: Decimal
    amount_crc: Optional[Decimal]
    description: Optional[str]
    is_paid: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def create(
        cls,
        date: date,
        category: CostCategory,
        amount_usd: Decimal,
        amount_crc: Optional[Decimal] = None,
        description: Optional[str] = None,
        is_paid: bool = False
    ) -> 'Cost':
        """Create a new cost entry."""
        return cls(
            id=None,
            date=date,
            category=category,
            amount_usd=amount_usd,
            amount_crc=amount_crc,
            description=description,
            is_paid=is_paid,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def mark_as_paid(self) -> None:
        """Mark cost as paid."""
        self.is_paid = True
        self.updated_at = datetime.now()

    def update_amount(self, amount_usd: Decimal, amount_crc: Optional[Decimal] = None) -> None:
        """Update cost amounts."""
        self.amount_usd = amount_usd
        self.amount_crc = amount_crc
        self.updated_at = datetime.now()


@dataclass
class RecurringCost:
    """Recurring cost template entity."""
    id: Optional[str]
    name: str
    category: CostCategory
    currency: str
    amount_expected: Decimal
    comment: Optional[str]
    recurrence: str  # weekly, monthly, quarterly, yearly
    next_due_date: date
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    @classmethod
    def create(
        cls,
        name: str,
        category: CostCategory,
        currency: str,
        amount_expected: Decimal,
        recurrence: str,
        next_due_date: date,
        comment: Optional[str] = None
    ) -> 'RecurringCost':
        """Create a new recurring cost."""
        return cls(
            id=None,
            name=name,
            category=category,
            currency=currency,
            amount_expected=amount_expected,
            comment=comment,
            recurrence=recurrence,
            next_due_date=next_due_date,
            is_active=True,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

    def deactivate(self) -> None:
        """Deactivate recurring cost."""
        self.is_active = False
        self.updated_at = datetime.now()

    def update_next_due_date(self, next_date: date) -> None:
        """Update next due date."""
        self.next_due_date = next_date
        self.updated_at = datetime.now()


# Alias for backward compatibility
CostModel = Cost
RecurringCostModel = RecurringCost
