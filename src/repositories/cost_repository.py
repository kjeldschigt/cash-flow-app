"""
Cost and recurring cost repositories.
"""

import sqlite3
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List, Type
from ..models.cost import Cost, RecurringCost, CostCategory
from .base import BaseRepository, DatabaseConnection


class CostRepository(BaseRepository[Cost]):
    """Repository for Cost entities."""

    def _get_table_name(self) -> str:
        return "costs"

    def _get_model_class(self) -> Type[Cost]:
        return Cost

    def _row_to_model(self, row: dict) -> Cost:
        """
        Convert a raw database row to a Cost instance.
        Adds fallbacks for missing fields (useful in dev mode with empty DB).
        """
        # --- Fallbacks to avoid Pydantic validation errors ---
        # ID as string
        cost_id = str(row.get("id",""))

        # cost_date fallback: use cost_date -> date -> today
        cost_date = row.get("cost_date") or row.get("date") or date.today()

        # category fallback: use valid category or default to "Other"
        category = row.get("category") or "Other"

        # amount fallback (for older DBs)
        amount = row.get("amount_usd") or row.get("amount") or 0

        # created_at / updated_at fallbacks
        created_at = row.get("created_at") or datetime.now()
        updated_at = row.get("updated_at") or datetime.now()

        # description fallback
        description = row.get("description") or ""

        # Build and return Cost
        return Cost(
            id=cost_id,
            cost_date=cost_date,
            category=category,
            amount_usd=amount,
            created_at=created_at,
            updated_at=updated_at,
            description=description,
        )

    def _model_to_dict(self, model: Cost) -> dict:
        """Convert Cost model to dictionary."""
        return {
            "id": model.id,
            "date": model.date.isoformat(),
            "category": model.category.value,
            "amount_usd": float(model.amount_usd),
            "amount_crc": float(model.amount_crc) if model.amount_crc else None,
            "description": model.description,
            "is_paid": model.is_paid,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        }

    def find_by_date_range(self, start_date: date, end_date: date) -> List[Cost]:
        """Find costs within date range."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE date BETWEEN ? AND ? ORDER BY date DESC",
                (start_date.isoformat(), end_date.isoformat()),
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def find_by_category(self, category: CostCategory) -> List[Cost]:
        """Find costs by category."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE category = ? ORDER BY date DESC",
                (category.value,),
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def find_unpaid_costs(self) -> List[Cost]:
        """Find all unpaid costs."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE is_paid = 0 ORDER BY date ASC"
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def get_total_by_month(self, year: int, month: int) -> Decimal:
        """Get total costs for a specific month."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT SUM(amount_usd) FROM {self._table_name} WHERE strftime('%Y', date) = ? AND strftime('%m', date) = ?",
                (str(year), f"{month:02d}"),
            )
            result = cursor.fetchone()[0]
            return Decimal(str(result)) if result else Decimal("0")


class RecurringCostRepository(BaseRepository[RecurringCost]):
    """Repository for RecurringCost entities."""

    def _get_table_name(self) -> str:
        return "recurring_costs"

    def _get_model_class(self) -> Type[RecurringCost]:
        return RecurringCost

    def _row_to_model(self, row: sqlite3.Row) -> RecurringCost:
        """Convert database row to RecurringCost model."""
        # Convert category with fallback
        try:
            category = CostCategory(row.get("category", "Unknown"))
        except Exception:
            # Fallback for invalid or unknown values (development data)
            category = CostCategory.OTHER
        
        return RecurringCost(
            id=str(row["id"]),
            name=row["name"],
            category=category,
            currency=row["currency"],
            amount_expected=Decimal(str(row["amount_expected"])),
            comment=row["comment"],
            recurrence_pattern=row["recurrence"],  # Alias will handle the mapping
            next_due_date=date.fromisoformat(row["next_due_date"]),
            is_active=bool(row.get("is_active", True)),
            created_at=(
                datetime.fromisoformat(row["created_at"])
                if row.get("created_at")
                else None
            ),
            updated_at=(
                datetime.fromisoformat(row["updated_at"])
                if row.get("updated_at")
                else None
            ),
        )

    def _model_to_dict(self, model: RecurringCost) -> dict:
        """Convert RecurringCost model to dictionary."""
        return {
            "id": model.id,
            "name": model.name,
            "category": model.category.value,
            "currency": model.currency,
            "amount_expected": float(model.amount_expected),
            "comment": model.comment,
            "recurrence": model.recurrence_pattern,  # Keep using alias for backward compatibility
            "next_due_date": model.next_due_date.isoformat(),
            "is_active": model.is_active,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        }

    def find_active_costs(self) -> List[RecurringCost]:
        """Find all active recurring costs."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE is_active = 1 ORDER BY next_due_date ASC"
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]

    def find_due_costs(self, due_date: date) -> List[RecurringCost]:
        """Find recurring costs due on or before specified date."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM {self._table_name} WHERE is_active = 1 AND next_due_date <= ? ORDER BY next_due_date ASC",
                (due_date.isoformat(),),
            )
            rows = cursor.fetchall()
            return [self._row_to_model(row) for row in rows]
