from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from typing import List, Dict, Any, Optional

import stripe  # Requires stripe package in requirements

from src.services.error_handler import ErrorHandler
from src.repositories.base import DatabaseConnection
from src.config.settings import Settings
from src.services.cash_ledger_service import CashLedgerService
from src.models.cash_ledger import CashLedgerEntry, Account


class StripeService:
    """
    Service for interacting with Stripe to import payouts into the cash ledger.
    """

    def __init__(self, db_connection: DatabaseConnection | None = None, error_handler: Optional[ErrorHandler] = None):
        self.db = db_connection or DatabaseConnection(Settings().database.path)
        self.ledger = CashLedgerService(self.db)
        self.error_handler = error_handler or ErrorHandler()

    def _get_api_key(self) -> str:
        api_key = os.environ.get("STRIPE_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("Stripe API key not found. Set STRIPE_API_KEY in environment.")
        return api_key

    def _init_client(self) -> None:
        # Stripe v10+ uses global api_key configuration
        stripe.api_key = self._get_api_key()

    def fetch_payouts(self, start_date: date, end_date: date, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Fetch payouts from Stripe within the date range.
        Returns list of dicts: {payout_id, date, amount, currency, status}
        """
        try:
            self._init_client()
            created_filter = {
                "gte": int(datetime.combine(start_date, datetime.min.time()).timestamp()),
                "lte": int(datetime.combine(end_date, datetime.max.time()).timestamp()),
            }
            payouts = stripe.Payout.list(created=created_filter, limit=min(limit, 100))
            results: List[Dict[str, Any]] = []
            for p in getattr(payouts, "data", []) or []:
                # Stripe payout amount is in the smallest currency unit (e.g., cents)
                amount = float(p.get("amount", 0) or 0) / 100.0
                cur = (p.get("currency") or "").upper()
                status = p.get("status") or "unknown"
                pid = p.get("id")
                # Prefer arrival_date if present, otherwise created
                ts = p.get("arrival_date") or p.get("created")
                d = date.fromtimestamp(ts) if isinstance(ts, int) and ts > 0 else date.today()
                results.append(
                    {
                        "payout_id": pid,
                        "date": d,
                        "amount": amount,
                        "currency": cur,
                        "status": status,
                    }
                )
            return results
        except Exception as e:
            self.error_handler.handle_error(e, user_message="Unable to fetch Stripe payouts")
            return []

    def import_payouts_to_ledger(
        self,
        bank_account_id: Optional[str] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        only_status: str = "paid",
    ) -> Dict[str, int]:
        """
        Import Stripe payouts as cash inflow ledger entries.
        Deduplicates by external_id (unique index on cash_ledger.external_id).
        """
        start_date = start_date or (date.today() - timedelta(days=365))
        end_date = end_date or date.today()

        payouts = self.fetch_payouts(start_date, end_date, limit=100)
        created, skipped = 0, 0
        for p in payouts:
            try:
                if only_status and p.get("status") != only_status:
                    skipped += 1
                    continue
                # Build ledger entry
                entry = CashLedgerEntry(
                    entry_date=p["date"],
                    description=f"Stripe Payout {p['payout_id']}",
                    amount=p["amount"],  # positive inflow
                    currency=p["currency"],
                    # Account is optional for balance math; default to a placeholder
                    account=Account.OCBC_USD,
                    category="Stripe Payout",
                    source="stripe_payout",
                    external_id=p["payout_id"],
                    bank_account_id=bank_account_id,
                )
                # Attempt insert; rely on unique index to prevent duplicates
                self.ledger.create_entry(entry)
                created += 1
            except Exception as e:
                # If unique constraint failure, treat as skipped; else report
                msg = str(e).lower()
                if "unique" in msg and "external_id" in msg:
                    skipped += 1
                    continue
                self.error_handler.handle_error(e, user_message="Failed to import a Stripe payout")
                skipped += 1
        return {"created": created, "skipped": skipped}
