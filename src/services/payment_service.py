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
from typing import Dict, Any, Optional
import stripe
import logging
from datetime import datetime
from enum import Enum


class StripeService:
    """Service for handling Stripe payment processing."""

    class PaymentStatus(str, Enum):
        SUCCEEDED = "succeeded"
        PROCESSING = "processing"
        REQUIRES_ACTION = "requires_action"
        FAILED = "failed"
        CANCELED = "canceled"

    def __init__(self, api_key: Optional[str] = None):
        """Initialize Stripe service with API key.
        
        Args:
            api_key: Stripe API secret key. If not provided, uses STRIPE_API_KEY from environment.
        """
        self.api_key = api_key or os.getenv("STRIPE_API_KEY")
        if not self.api_key:
            raise ValueError("Stripe API key is required. Set STRIPE_API_KEY environment variable.")
        
        stripe.api_key = self.api_key
        self.logger = logging.getLogger(__name__)

    def create_payment_intent(
        self,
        amount: int,
        currency: str = "usd",
        payment_method_types: Optional[list] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Create a payment intent with Stripe.
        
        Args:
            amount: Amount in smallest currency unit (e.g., cents for USD)
            currency: 3-letter ISO currency code (default: 'usd')
            payment_method_types: List of payment method types (e.g., ['card'])
            **kwargs: Additional parameters for Stripe API
            
        Returns:
            Dict containing payment intent details
        """
        if payment_method_types is None:
            payment_method_types = ['card']
            
        try:
            intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency.lower(),
                payment_method_types=payment_method_types,
                **kwargs
            )
            return {
                "id": intent.id,
                "client_secret": intent.client_secret,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency.upper(),
                "created": datetime.fromtimestamp(intent.created)
            }
        except stripe.error.StripeError as e:
            self.logger.error(f"Stripe payment intent creation failed: {str(e)}")
            raise

    def get_payment_status(self, payment_intent_id: str) -> Dict[str, Any]:
        """Get the status of a payment intent.
        
        Args:
            payment_intent_id: Stripe payment intent ID
            
        Returns:
            Dict containing payment status and details
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                "id": intent.id,
                "status": intent.status,
                "amount": intent.amount,
                "currency": intent.currency.upper(),
                "created": datetime.fromtimestamp(intent.created),
                "payment_method": intent.payment_method,
                "receipt_email": intent.receipt_email,
                "charges": [{
                    "id": charge.id,
                    "amount": charge.amount,
                    "currency": charge.currency.upper(),
                    "status": charge.status,
                    "paid": charge.paid,
                    "refunded": charge.refunded,
                    "receipt_url": charge.receipt_url,
                } for charge in getattr(intent, 'charges', {}).get('data', [])]
            }
        except stripe.error.StripeError as e:
            self.logger.error(f"Failed to retrieve payment intent {payment_intent_id}: {str(e)}")
            raise

    def refund_payment(
        self,
        payment_intent_id: str,
        amount: Optional[int] = None,
        reason: str = "requested_by_customer"
    ) -> Dict[str, Any]:
        """Refund a payment.
        
        Args:
            payment_intent_id: Stripe payment intent ID
            amount: Amount to refund in smallest currency unit (None for full refund)
            reason: Reason for the refund
            
        Returns:
            Dict containing refund details
        """
        try:
            refund = stripe.Refund.create(
                payment_intent=payment_intent_id,
                amount=amount,
                reason=reason
            )
            return {
                "id": refund.id,
                "status": refund.status,
                "amount": refund.amount,
                "currency": refund.currency.upper(),
                "reason": refund.reason,
                "created": datetime.fromtimestamp(refund.created)
            }
        except stripe.error.StripeError as e:
            self.logger.error(f"Failed to process refund for {payment_intent_id}: {str(e)}")
            raise


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

    def get_revenue_breakdown(self, start_date=None, end_date=None):
        """Development fallback for revenue breakdown."""
        return []

    def get_cost_breakdown(self, start_date=None, end_date=None):
        """Development fallback for cost breakdown."""
        return []


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
        recurrence_pattern: RecurrenceType,
        due_date: date,
        comment: Optional[str] = None,
    ) -> PaymentSchedule:
        """Create a new payment schedule."""
        schedule = PaymentSchedule.create(
            name=name,
            category=category,
            currency=currency,
            amount_expected=amount_expected,
            recurrence_pattern=recurrence_pattern,
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

    def get_revenue_breakdown(self, start_date=None, end_date=None):
        """Development fallback for revenue breakdown."""
        return []

    def get_cost_breakdown(self, start_date=None, end_date=None):
        """Development fallback for cost breakdown."""
        return []
