from src.models.cash_ledger import CashLedgerEntry
from src.models.cash_ledger import Account
from src.repositories.base import DatabaseConnection
from src.config.settings import Settings

class CashLedgerService:
    def __init__(self, db_connection: DatabaseConnection | None = None):
        # Use injected DatabaseConnection or default singleton
        self.db = db_connection or DatabaseConnection(Settings().database.path)
        self._create_table()

    def _create_table(self):
        with self.db.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cash_ledger (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_date TEXT,
                    description TEXT,
                    amount REAL,
                    currency TEXT,
                    account TEXT,
                    category TEXT
                )
                """
            )
            # Ensure optional columns exist (SQLite-safe migrations)
            cur = conn.execute("PRAGMA table_info(cash_ledger)")
            cols = {row[1] for row in cur.fetchall()}
            if "source" not in cols:
                conn.execute("ALTER TABLE cash_ledger ADD COLUMN source TEXT")
            if "external_id" not in cols:
                conn.execute("ALTER TABLE cash_ledger ADD COLUMN external_id TEXT")
            if "bank_account_id" not in cols:
                conn.execute("ALTER TABLE cash_ledger ADD COLUMN bank_account_id TEXT")

            # Create unique index on external_id (allows multiple NULLs in SQLite)
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_cash_ledger_external_id ON cash_ledger(external_id)"
            )

    def get_all_entries(self):
        with self.db.get_connection() as conn:
            cur = conn.execute("SELECT * FROM cash_ledger ORDER BY entry_date DESC")
            rows = cur.fetchall()
            return [
                CashLedgerEntry(
                    id=row.get("id"),
                    entry_date=row.get("entry_date"),
                    description=row.get("description"),
                    amount=row.get("amount"),
                    currency=row.get("currency"),
                    account=Account(row.get("account")) if row.get("account") else Account.OCBC_USD,
                    category=row.get("category", "General"),
                    source=row.get("source"),
                    external_id=row.get("external_id"),
                    bank_account_id=row.get("bank_account_id"),
                )
                for row in rows
            ]

    def create_entry(self, entry: CashLedgerEntry):
        with self.db.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO cash_ledger (
                    entry_date, description, amount, currency, account, category,
                    source, external_id, bank_account_id
                ) VALUES (?,?,?,?,?,?,?,?,?)
                """,
                (
                    entry.entry_date,
                    entry.description,
                    entry.amount,
                    entry.currency,
                    entry.account.value if entry.account else None,
                    entry.category,
                    entry.source,
                    entry.external_id,
                    entry.bank_account_id,
                ),
            )
