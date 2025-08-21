from __future__ import annotations
from typing import Optional, List, Dict, Any
from datetime import date
import uuid

from src.repositories.base import DatabaseConnection
from src.services.error_handler import get_error_handler


class BankRepository:
    """
    Repository for bank accounts, opening balances, and adjustments.

    Tables:
      - bank_accounts(id TEXT PK, name TEXT NOT NULL, currency TEXT DEFAULT 'USD', bank_name TEXT, last4 TEXT, is_active BOOLEAN DEFAULT 1)
      - bank_opening_balances(bank_account_id TEXT UNIQUE, as_of_date DATE NOT NULL, opening_balance REAL NOT NULL)
      - bank_adjustments(id TEXT PK, bank_account_id TEXT NOT NULL, date DATE NOT NULL, amount REAL NOT NULL, category TEXT NOT NULL, reason TEXT NOT NULL, memo TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)

    Also ensures optional nullable column bank_account_id exists on cash_ledger.
    """

    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        from src.container import get_container
        self.db = db or get_container().get_db_connection()
        self.error_handler = get_error_handler()
        self.create_tables_if_missing()

    def create_tables_if_missing(self) -> None:
        """Create bank-related tables and ensure schema columns idempotently."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            # bank_accounts
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bank_accounts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    currency TEXT DEFAULT 'USD',
                    bank_name TEXT,
                    last4 TEXT,
                    is_active BOOLEAN DEFAULT 1
                )
                """
            )
            # bank_opening_balances
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bank_opening_balances (
                    bank_account_id TEXT UNIQUE,
                    as_of_date DATE NOT NULL,
                    opening_balance REAL NOT NULL,
                    FOREIGN KEY(bank_account_id) REFERENCES bank_accounts(id)
                )
                """
            )
            # bank_adjustments
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bank_adjustments (
                    id TEXT PRIMARY KEY,
                    bank_account_id TEXT NOT NULL,
                    date DATE NOT NULL,
                    amount REAL NOT NULL,
                    category TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    memo TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(bank_account_id) REFERENCES bank_accounts(id)
                )
                """
            )
            # Ensure optional column on cash_ledger
            try:
                cur.execute("PRAGMA table_info(cash_ledger)")
                cols = [row[1] for row in cur.fetchall()]
                if "bank_account_id" not in cols:
                    cur.execute("ALTER TABLE cash_ledger ADD COLUMN bank_account_id TEXT NULL")
            except Exception as e:
                # Log but don't raise
                self.error_handler.handle_database_error(
                    e,
                    operation="alter_table_add_bank_account_id",
                    affected_table="cash_ledger",
                )

    @staticmethod
    def _iso(d: Optional[date | str]) -> Optional[str]:
        if d is None:
            return None
        if isinstance(d, date):
            return d.isoformat()
        return str(d)

    def upsert_bank_account(self, data: Dict[str, Any]) -> str:
        """Create or update a bank account. Returns account id.
        Strategy (portable):
          - If id provided and exists -> UPDATE
          - Else if id provided and not exists -> INSERT with that id
          - Else try find by (name, last4) to avoid duplicates; if found -> UPDATE
          - Else INSERT with new uuid4 id
        """
        name = (data.get("name") or "").strip()
        if not name:
            raise ValueError("name is required")
        currency = (data.get("currency") or "USD").upper().strip()
        bank_name = (data.get("bank_name") or None)
        last4 = (data.get("last4") or None)
        is_active = 1 if data.get("is_active", True) else 0
        acct_id = (data.get("id") or None)

        with self.db.get_connection() as conn:
            cur = conn.cursor()
            existing_id: Optional[str] = None

            try:
                if acct_id:
                    cur.execute("SELECT id FROM bank_accounts WHERE id = ?", (acct_id,))
                    row = cur.fetchone()
                    existing_id = row.get("id") if row else None
                if not existing_id:
                    cur.execute(
                        "SELECT id FROM bank_accounts WHERE name = ? AND IFNULL(last4,'') = IFNULL(?, '')",
                        (name, last4),
                    )
                    row = cur.fetchone()
                    existing_id = row.get("id") if row else None

                if existing_id:
                    cur.execute(
                        """
                        UPDATE bank_accounts
                           SET name = ?, currency = ?, bank_name = ?, last4 = ?, is_active = ?
                         WHERE id = ?
                        """,
                        (name, currency, bank_name, last4, is_active, existing_id),
                    )
                    return existing_id
                else:
                    new_id = acct_id or str(uuid.uuid4())
                    cur.execute(
                        """
                        INSERT INTO bank_accounts (id, name, currency, bank_name, last4, is_active)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """,
                        (new_id, name, currency, bank_name, last4, is_active),
                    )
                    return new_id
            except Exception as e:
                self.error_handler.handle_database_error(
                    e, operation="upsert_bank_account", affected_table="bank_accounts"
                )
                raise

    def list_accounts(self, active_only: bool = False) -> List[Dict[str, Any]]:
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            if active_only:
                cur.execute("SELECT * FROM bank_accounts WHERE is_active = 1 ORDER BY name")
            else:
                cur.execute("SELECT * FROM bank_accounts ORDER BY is_active DESC, name")
            return cur.fetchall()

    def set_opening_balance(self, bank_account_id: str, as_of_date: date | str, opening_balance: float) -> None:
        as_of = self._iso(as_of_date)
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT bank_account_id FROM bank_opening_balances WHERE bank_account_id = ?",
                    (bank_account_id,),
                )
                row = cur.fetchone()
                if row:
                    cur.execute(
                        "UPDATE bank_opening_balances SET as_of_date = ?, opening_balance = ? WHERE bank_account_id = ?",
                        (as_of, float(opening_balance), bank_account_id),
                    )
                else:
                    cur.execute(
                        "INSERT INTO bank_opening_balances (bank_account_id, as_of_date, opening_balance) VALUES (?, ?, ?)",
                        (bank_account_id, as_of, float(opening_balance)),
                    )
            except Exception as e:
                self.error_handler.handle_database_error(
                    e,
                    operation="set_opening_balance",
                    affected_table="bank_opening_balances",
                )
                raise

    def add_adjustment(self, data: Dict[str, Any]) -> str:
        acct_id = data.get("bank_account_id")
        if not acct_id:
            raise ValueError("bank_account_id is required")
        adj_id = data.get("id") or str(uuid.uuid4())
        dt = self._iso(data.get("date"))
        amount = float(data.get("amount") or 0.0)
        category = (data.get("category") or "other").strip()
        reason = (data.get("reason") or "").strip()
        memo = data.get("memo")
        if not dt:
            raise ValueError("date is required")
        if not reason:
            raise ValueError("reason is required")
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            try:
                cur.execute(
                    """
                    INSERT INTO bank_adjustments (id, bank_account_id, date, amount, category, reason, memo)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (adj_id, acct_id, dt, amount, category, reason, memo),
                )
                return adj_id
            except Exception as e:
                self.error_handler.handle_database_error(
                    e, operation="add_adjustment", affected_table="bank_adjustments"
                )
                raise

    def get_account_balances(self, as_of_date: Optional[date | str] = None) -> List[Dict[str, Any]]:
        as_of = self._iso(as_of_date) if as_of_date else None
        with self.db.get_connection() as conn:
            cur = conn.cursor()

            # Load accounts
            cur.execute("SELECT * FROM bank_accounts WHERE is_active = 1 ORDER BY name")
            accounts = cur.fetchall()
            results: List[Dict[str, Any]] = []

            for a in accounts:
                account_id = a.get("id")
                # Opening balance
                cur.execute(
                    "SELECT opening_balance, as_of_date FROM bank_opening_balances WHERE bank_account_id = ?",
                    (account_id,),
                )
                ob_row = cur.fetchone() or {}
                opening_balance = float(ob_row.get("opening_balance", 0.0) or 0.0)

                # Ledger sums (net, inflows, outflows)
                if as_of:
                    cur.execute(
                        "SELECT COALESCE(SUM(amount),0) as net, COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END),0) as inflows, COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END),0) as outflows FROM cash_ledger WHERE bank_account_id = ? AND entry_date <= ?",
                        (account_id, as_of),
                    )
                else:
                    cur.execute(
                        "SELECT COALESCE(SUM(amount),0) as net, COALESCE(SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END),0) as inflows, COALESCE(SUM(CASE WHEN amount < 0 THEN -amount ELSE 0 END),0) as outflows FROM cash_ledger WHERE bank_account_id = ?",
                        (account_id,),
                    )
                ledger_row = cur.fetchone() or {"net": 0.0, "inflows": 0.0, "outflows": 0.0}
                net_ledger = float(ledger_row.get("net", 0.0) or 0.0)
                inflows = float(ledger_row.get("inflows", 0.0) or 0.0)
                outflows = float(ledger_row.get("outflows", 0.0) or 0.0)

                # Adjustments
                if as_of:
                    cur.execute(
                        "SELECT COALESCE(SUM(amount),0) AS total FROM bank_adjustments WHERE bank_account_id = ? AND date <= ?",
                        (account_id, as_of),
                    )
                else:
                    cur.execute(
                        "SELECT COALESCE(SUM(amount),0) AS total FROM bank_adjustments WHERE bank_account_id = ?",
                        (account_id,),
                    )
                adj_total_row = cur.fetchone() or {"total": 0.0}
                adjustments_total = float(adj_total_row.get("total", 0.0) or 0.0)

                current_balance = opening_balance + net_ledger + adjustments_total

                results.append(
                    {
                        "account_id": account_id,
                        "name": a.get("name"),
                        "currency": a.get("currency", "USD"),
                        "opening_balance": opening_balance,
                        "inflows": inflows,
                        "outflows": outflows,
                        "adjustments_total": adjustments_total,
                        "current_balance": current_balance,
                    }
                )

            return results
