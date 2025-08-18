"""
Payment service for payment and payment schedule management.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from ..models.payment import Payment, PaymentSchedule, PaymentStatus, RecurrenceType
from ..models.cost import Cost, CostCategory
from ..repositories.payment_repository import (
    PaymentRepository,
    PaymentScheduleRepository,
)
from ..repositories.cost_repository import CostRepository
from ..repositories.base import DatabaseConnection
from ..utils.date_utils import DateUtils


class PaymentService:
    """Service for payment operations."""

    def __init__(self, db_connection: DatabaseConnection):
        self.payment_repository = PaymentRepository(db_connection)
        self.payment_schedule_repository = PaymentScheduleRepository(db_connection)
        self.cost_repository = CostRepository(db_connection)

    def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> Payment:
        """Create a new payment."""
        payment = Payment(
            id=None,
            amount=amount,
            currency=currency,
            status=PaymentStatus.SCHEDULED,
            payment_date=None,
            description=description,
            external_id=external_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        return self.payment_repository.save(payment)

    def mark_payment_as_paid(
        self, payment_id: str, payment_date: Optional[date] = None
    ) -> bool:
        """Mark payment as paid."""
        payment = self.payment_repository.find_by_id(payment_id)
        if not payment:
            return False

        payment.mark_as_paid(payment_date)
        self.payment_repository.save(payment)
        return True


class PaymentScheduleService:
    """Service for payment schedule operations."""

    def __init__(self, db_connection: DatabaseConnection):
        self.payment_schedule_repository = PaymentScheduleRepository(db_connection)
        self.cost_repository = CostRepository(db_connection)

    def create_payment_schedule(
        self,
        name: str,
        category: str,
        currency: str,
        amount_expected: Decimal,
        recurrence: RecurrenceType,
        due_date: date,
        comment: Optional[str] = None,
    ) -> PaymentSchedule:
        """Create a new payment schedule."""
        schedule = PaymentSchedule.create(
            name=name,
            category=category,
            currency=currency,
            amount_expected=amount_expected,
            recurrence=recurrence,
            due_date=due_date,
            comment=comment,
        )
        return self.payment_schedule_repository.save(schedule)

    def get_scheduled_payments(self) -> List[PaymentSchedule]:
        """Get all scheduled payments."""
        return self.payment_schedule_repository.find_scheduled_payments()

    def get_overdue_payments(self) -> List[PaymentSchedule]:
        """Get overdue scheduled payments."""
        return self.payment_schedule_repository.find_overdue_payments()

    def mark_payment_as_paid(
        self, schedule_id: str, actual_amount: Decimal, create_cost_entry: bool = True
    ) -> bool:
        """Mark scheduled payment as paid and optionally create cost entry."""
        schedule = self.payment_schedule_repository.find_by_id(schedule_id)
        if not schedule or schedule.status != PaymentStatus.SCHEDULED:
            return False

        # Mark as paid
        schedule.mark_as_paid(actual_amount)
        self.payment_schedule_repository.save(schedule)

        # Create cost entry if requested
        if create_cost_entry:
            cost = Cost.create(
                date=date.today(),
                category=CostCategory(schedule.category),
                amount_usd=(
                    actual_amount if schedule.currency == "USD" else Decimal("0")
                ),
                amount_crc=actual_amount if schedule.currency == "CRC" else None,
                description=f"Payment: {schedule.name}",
                is_paid=True,
            )
            self.cost_repository.save(cost)

        return True

    def skip_payment(self, schedule_id: str) -> bool:
        """Skip a scheduled payment."""
        schedule = self.payment_schedule_repository.find_by_id(schedule_id)
        if not schedule or schedule.status != PaymentStatus.SCHEDULED:
            return False

        schedule.skip()
        self.payment_schedule_repository.save(schedule)
        return True

    def get_payments_by_category(self, category: str) -> List[PaymentSchedule]:
        """Get payment schedules by category."""
        return self.payment_schedule_repository.find_by_category(category)

    def update_payment_schedule(
        self, schedule_id: str, **updates
    ) -> Optional[PaymentSchedule]:
        """Update payment schedule fields."""
        schedule = self.payment_schedule_repository.find_by_id(schedule_id)
        if not schedule:
            return None

        # Update allowed fields
        allowed_fields = ["name", "category", "amount_expected", "comment", "due_date"]
        for field, value in updates.items():
            if field in allowed_fields and hasattr(schedule, field):
                setattr(schedule, field, value)

        schedule.updated_at = datetime.now()
        return self.payment_schedule_repository.save(schedule)
