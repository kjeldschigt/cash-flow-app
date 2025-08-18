"""
Cost service for cost and recurring cost management.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional, Dict, Any
from ..models.cost import Cost, RecurringCost, CostCategory
from ..repositories.cost_repository import CostRepository, RecurringCostRepository
from ..repositories.base import DatabaseConnection
from ..utils.date_utils import DateUtils
from ..utils.currency_utils import CurrencyUtils


class CostService:
    """Service for cost management operations."""

    def __init__(self, db_connection: DatabaseConnection):
        self.cost_repository = CostRepository(db_connection)
        self.recurring_cost_repository = RecurringCostRepository(db_connection)

    def create_cost(
        self,
        date: date,
        category: CostCategory,
        amount_usd: Decimal,
        amount_crc: Optional[Decimal] = None,
        description: Optional[str] = None,
        is_paid: bool = False,
    ) -> Cost:
        """Create a new cost entry."""
        cost = Cost.create(
            date=date,
            category=category,
            amount_usd=amount_usd,
            amount_crc=amount_crc,
            description=description,
            is_paid=is_paid,
        )
        return self.cost_repository.save(cost)

    def get_costs_by_date_range(self, start_date: date, end_date: date) -> List[Cost]:
        """Get costs within date range."""
        return self.cost_repository.find_by_date_range(start_date, end_date)

    def get_costs_by_category(self, category: CostCategory) -> List[Cost]:
        """Get costs by category."""
        return self.cost_repository.find_by_category(category)

    def get_unpaid_costs(self) -> List[Cost]:
        """Get unpaid costs."""
        return self.cost_repository.find_unpaid()

    def mark_cost_paid(self, cost_id: str) -> bool:
        """Mark cost as paid."""
        cost = self.cost_repository.find_by_id(cost_id)
        if cost:
            cost.mark_as_paid()
            self.cost_repository.save(cost)
            return True
        return False

    def get_recurring_costs(self) -> List[Dict[str, Any]]:
        """Get recurring costs - compatibility method."""
        import pandas as pd

        # Return empty DataFrame for now
        return pd.DataFrame()

    def get_monthly_cost_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get monthly cost summary."""
        total_amount = self.cost_repository.get_total_by_month(year, month)
        start_date, end_date = DateUtils.get_month_range(year, month)
        costs = self.get_costs_by_date_range(start_date, end_date)

        # Group by category
        category_totals = {}
        for cost in costs:
            category = cost.category.value
            if category not in category_totals:
                category_totals[category] = Decimal("0")
            category_totals[category] += cost.amount_usd

        return {
            "total_amount": total_amount,
            "cost_count": len(costs),
            "category_breakdown": category_totals,
            "period": f"{year}-{month:02d}",
        }

    def update_cost(
        self,
        cost_id: str,
        amount_usd: Optional[Decimal] = None,
        amount_crc: Optional[Decimal] = None,
        description: Optional[str] = None,
        category: Optional[CostCategory] = None,
    ) -> Optional[Cost]:
        """Update cost entry."""
        cost = self.cost_repository.find_by_id(cost_id)
        if not cost:
            return None

        if amount_usd is not None:
            cost.update_amount(amount_usd, amount_crc)
        if description is not None:
            cost.description = description
        if category is not None:
            cost.category = category

        cost.updated_at = datetime.now()
        return self.cost_repository.save(cost)


class RecurringCostService:
    """Service for recurring cost management."""

    def __init__(self, db_connection: DatabaseConnection):
        self.recurring_cost_repository = RecurringCostRepository(db_connection)
        self.cost_repository = CostRepository(db_connection)

    def create_recurring_cost(
        self,
        name: str,
        category: CostCategory,
        currency: str,
        amount_expected: Decimal,
        recurrence_pattern: str,
        next_due_date: date,
        comment: Optional[str] = None,
    ) -> RecurringCost:
        """Create a new recurring cost."""
        recurring_cost = RecurringCost.create(
            name=name,
            category=category,
            currency=currency,
            amount_expected=amount_expected,
            recurrence_pattern=recurrence_pattern,
            next_due_date=next_due_date,
            comment=comment,
        )
        return self.recurring_cost_repository.save(recurring_cost)

    def get_active_recurring_costs(self) -> List[RecurringCost]:
        """Get all active recurring costs."""
        return self.recurring_cost_repository.find_active_costs()

    def get_due_recurring_costs(
        self, due_date: Optional[date] = None
    ) -> List[RecurringCost]:
        """Get recurring costs due on or before specified date."""
        if due_date is None:
            due_date = date.today()
        return self.recurring_cost_repository.find_due_costs(due_date)

    def process_due_recurring_costs(self) -> List[Cost]:
        """Process due recurring costs and create cost entries."""
        due_costs = self.get_due_recurring_costs()
        created_costs = []

        for recurring_cost in due_costs:
            # Create cost entry
            cost = Cost.create(
                date=date.today(),
                category=recurring_cost.category,
                amount_usd=(
                    recurring_cost.amount_expected
                    if recurring_cost.currency == "USD"
                    else Decimal("0")
                ),
                amount_crc=(
                    recurring_cost.amount_expected
                    if recurring_cost.currency == "CRC"
                    else None
                ),
                description=f"Recurring: {recurring_cost.name}",
                is_paid=False,
            )
            created_cost = self.cost_repository.save(cost)
            created_costs.append(created_cost)

            # Update next due date
            next_due = DateUtils.get_next_recurrence_date(
                recurring_cost.next_due_date, recurring_cost.recurrence_pattern
            )
            recurring_cost.update_next_due_date(next_due)
            self.recurring_cost_repository.save(recurring_cost)

        return created_costs

    def deactivate_recurring_cost(self, recurring_cost_id: str) -> bool:
        """Deactivate a recurring cost."""
        recurring_cost = self.recurring_cost_repository.find_by_id(recurring_cost_id)
        if not recurring_cost:
            return False

        recurring_cost.deactivate()
        self.recurring_cost_repository.save(recurring_cost)
        return True
