"""
Payment and payment schedule repositories.
"""

import sqlite3
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Type
from ..models.payment import Payment, PaymentSchedule, PaymentStatus, RecurrenceType
from .base import BaseRepository, DatabaseConnection


class PaymentRepository(BaseRepository[Payment]):
    """Repository for Payment entities."""
    
    def _get_table_name(self) -> str:
        return "payments"
    
    def _get_model_class(self) -> Type[Payment]:
        return Payment
    
    def _row_to_model(self, row: sqlite3.Row) -> Payment:
        """Convert database row to Payment model."""
        return Payment(
            id=str(row['id']),
            amount=Decimal(str(row['amount'])),
            currency=row['currency'],
            status=PaymentStatus(row['status']),
            payment_date=date.fromisoformat(row['payment_date']) if row['payment_date'] else None,
            description=row['description'],
            external_id=row['external_id'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
        )
    
    def _model_to_dict(self, model: Payment) -> dict:
        """Convert Payment model to dictionary."""
        return {
            'id': model.id,
            'amount': float(model.amount),
            'currency': model.currency,
            'status': model.status.value,
            'payment_date': model.payment_date.isoformat() if model.payment_date else None,
            'description': model.description,
            'external_id': model.external_id,
            'created_at': model.created_at.isoformat() if model.created_at else None,
            'updated_at': model.updated_at.isoformat() if model.updated_at else None
        }


class PaymentScheduleRepository(BaseRepository[PaymentSchedule]):
    """Repository for PaymentSchedule entities."""
    
    def _get_table_name(self) -> str:
        return "payment_schedule"
    
    def _get_model_class(self) -> Type[PaymentSchedule]:
        return PaymentSchedule
    
    def _row_to_model(self, row: sqlite3.Row) -> PaymentSchedule:
        """Convert database row to PaymentSchedule model."""
        return PaymentSchedule(
            id=str(row['id']),
            name=row['name'],
            category=row['category'],
            currency=row['currency'],
            amount_expected=Decimal(str(row['amount_expected'])),
            amount_actual=Decimal(str(row['amount_actual'])) if row['amount_actual'] else None,
            comment=row['comment'],
            recurrence=RecurrenceType(row['recurrence']),
            due_date=date.fromisoformat(row['due_date']),
            status=PaymentStatus(row['status']),
            created_at=datetime.fromisoformat(row['created_at']) if row.get('created_at') else None,
            updated_at=datetime.fromisoformat(row['updated_at']) if row.get('updated_at') else None
        )
    
    def _model_to_dict(self, model: PaymentSchedule) -> dict:
        """Convert PaymentSchedule model to dictionary."""
        return {
            'id': model.id,
            'name': model.name,
            'category': model.category,
            'currency': model.currency,
            'amount_expected': float(model.amount_expected),
            'amount_actual': float(model.amount_actual) if model.amount_actual else None,
            'comment': model.comment,
            'recurrence': model.recurrence.value,
            'due_date': model.due_date.isoformat(),
            'status': model.status.value,
            'created_at': model.created_at.isoformat() if model.created_at else None,
            'updated_at': model.updated_at.isoformat() if model.updated_at else None
        }
    
    def find_scheduled_payments(self) -> List[PaymentSchedule]:
        """Find all scheduled payments."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE status = ? ORDER BY due_date ASC",
                (PaymentStatus.SCHEDULED.value,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def find_overdue_payments(self) -> List[PaymentSchedule]:
        """Find overdue scheduled payments."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE status = ? AND due_date < ? ORDER BY due_date ASC",
                (PaymentStatus.SCHEDULED.value, date.today().isoformat())
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
    
    def find_by_category(self, category: str) -> List[PaymentSchedule]:
        """Find payment schedules by category."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE category = ? ORDER BY due_date ASC",
                (category,)
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
