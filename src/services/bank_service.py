from __future__ import annotations
from typing import Optional, Dict, Any, List
from datetime import date

from src.repositories.base import DatabaseConnection
from src.repositories.bank_repository import BankRepository
from src.services.error_handler import get_error_handler
from src.config.settings import Settings


class BankService:
    """Service layer for bank accounts, opening balances, and adjustments."""

    def __init__(self, db_connection: Optional[DatabaseConnection] = None) -> None:
        db = db_connection or DatabaseConnection(Settings().database.path)
        self.repo = BankRepository(db)
        self.error_handler = get_error_handler()

    # Accounts
    def upsert_account(self, data: Dict[str, Any]) -> str:
        if not data or not (data.get("name") or "").strip():
            raise ValueError("Account name is required")
        if data.get("currency"):
            data["currency"] = str(data["currency"]).upper().strip() or "USD"
        return self.repo.upsert_bank_account(data)

    def list_accounts(self, active_only: bool = False) -> List[Dict[str, Any]]:
        return self.repo.list_accounts(active_only=active_only)

    # Opening balances
    def set_opening_balance(self, bank_account_id: str, as_of_date: date | str, opening_balance: float) -> None:
        if not bank_account_id:
            raise ValueError("bank_account_id is required")
        self.repo.set_opening_balance(bank_account_id, as_of_date, float(opening_balance))

    # Adjustments
    def add_adjustment(self, data: Dict[str, Any]) -> str:
        if "amount" not in data:
            raise ValueError("amount is required")
        if not data.get("reason"):
            raise ValueError("reason is required")
        return self.repo.add_adjustment(data)

    # Balances
    def balance_for_all_accounts(self, as_of_date: Optional[date | str] = None) -> List[Dict[str, Any]]:
        return self.repo.get_account_balances(as_of_date)
