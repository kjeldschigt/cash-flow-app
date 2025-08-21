from typing import List, Dict, Optional
from datetime import date
import uuid

from src.container import get_container
from src.repositories.base import DatabaseConnection
from src.services.error_handler import get_error_handler

# Import models for type hints only (avoid runtime dependency cycles)
try:
    from src.services.airtable_import_service import LeadModel, BookingModel
except Exception:
    LeadModel = object  # type: ignore
    BookingModel = object  # type: ignore


class IngestRepository:
    """
    Repository for ingesting imported (Airtable) data into local DB with idempotent upserts.

    Schema:
      - leads(lead_id PK, email, created_at, mql_yes, sql_yes, utm_source, utm_medium, utm_campaign, raw_source, unique_key UNIQUE)
      - bookings(booking_id PK, booking_date, arrival_date, departure_date, guests, amount, email, raw_source)
    """

    def __init__(self, db: Optional[DatabaseConnection] = None) -> None:
        self.db = db or get_container().get_db_connection()
        self.error_handler = get_error_handler()

    def create_tables_if_missing(self) -> None:
        """Create required tables if they do not already exist."""
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            # Leads table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS leads (
                    lead_id TEXT PRIMARY KEY,
                    email TEXT,
                    created_at DATE,
                    mql_yes BOOLEAN,
                    sql_yes BOOLEAN,
                    utm_source TEXT,
                    utm_medium TEXT,
                    utm_campaign TEXT,
                    raw_source TEXT,
                    unique_key TEXT UNIQUE
                )
                """
            )
            # Bookings table
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bookings (
                    booking_id TEXT PRIMARY KEY,
                    booking_date DATE,
                    arrival_date DATE,
                    departure_date DATE,
                    guests INTEGER,
                    amount REAL,
                    email TEXT,
                    raw_source TEXT
                )
                """
            )
            # Ensure required columns exist (idempotent)
            self.ensure_columns(conn)

    def column_exists(self, conn, table: str, column: str) -> bool:
        """Return True if a column exists on a table using PRAGMA table_info.
        Uses tuple indexing (row[1] is the column name) to avoid KeyError.
        """
        try:
            cur = conn.cursor()
            cur.execute(f"PRAGMA table_info({table})")
            cols = [row[1] for row in cur.fetchall()]
            return column in cols
        except Exception:
            # If PRAGMA fails for any reason, be conservative and return False
            return False

    def ensure_columns(self, conn) -> None:
        """Ensure schema columns exist; add bookings.email if missing.
        This is safe and idempotent; logs errors without crashing.
        """
        try:
            if not self.column_exists(conn, "bookings", "email"):
                cur = conn.cursor()
                cur.execute("ALTER TABLE bookings ADD COLUMN email TEXT")
        except Exception as e:
            # Non-fatal: log database error but do not raise
            self.error_handler.handle_database_error(
                e,
                operation="alter_table_add_email",
                affected_table="bookings",
            )

    @staticmethod
    def _to_iso(d: Optional[date]) -> Optional[str]:
        return d.isoformat() if d else None

    def upsert_leads(self, records: List["LeadModel"], raw_source: str = "airtable:Main") -> Dict[str, int]:
        """
        Idempotent upsert for leads.
        unique_key = f"{email}|{created_at}"
        If exists -> update MQL/SQL/UTM fields. Else insert new row with UUID4 lead_id.
        """
        inserted = 0
        updated = 0
        self.create_tables_if_missing()
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            for r in records:
                try:
                    email = (getattr(r, "email", None) or "").strip().lower()
                    created_at = self._to_iso(getattr(r, "created_date", None))
                    if not created_at:
                        # Skip if no created date (shouldn't happen due to model)
                        continue
                    unique_key = f"{email}|{created_at}"

                    cur.execute("SELECT lead_id FROM leads WHERE unique_key = ?", (unique_key,))
                    row = cur.fetchone()
                    if row:
                        # Update existing
                        cur.execute(
                            """
                            UPDATE leads
                               SET email = ?,
                                   mql_yes = ?,
                                   sql_yes = ?,
                                   utm_source = ?,
                                   utm_medium = ?,
                                   utm_campaign = ?,
                                   raw_source = ?
                             WHERE unique_key = ?
                            """,
                            (
                                email,
                                bool(getattr(r, "is_mql", False)),
                                bool(getattr(r, "is_sql", False)),
                                getattr(r, "utm_source", None),
                                getattr(r, "utm_medium", None),
                                getattr(r, "utm_campaign", None),
                                raw_source,
                                unique_key,
                            ),
                        )
                        updated += 1
                    else:
                        lead_id = str(uuid.uuid4())
                        cur.execute(
                            """
                            INSERT INTO leads (
                                lead_id, email, created_at, mql_yes, sql_yes,
                                utm_source, utm_medium, utm_campaign, raw_source, unique_key
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                lead_id,
                                email,
                                created_at,
                                bool(getattr(r, "is_mql", False)),
                                bool(getattr(r, "is_sql", False)),
                                getattr(r, "utm_source", None),
                                getattr(r, "utm_medium", None),
                                getattr(r, "utm_campaign", None),
                                raw_source,
                                unique_key,
                            ),
                        )
                        inserted += 1
                except Exception as e:
                    # Log but continue processing
                    self.error_handler.handle_database_error(e, operation="upsert_leads", affected_table="leads")
                    continue
        return {"inserted": inserted, "updated": updated}

    def upsert_bookings(self, records: List["BookingModel"], raw_source: str = "airtable:Bookings<>Able") -> Dict[str, int]:
        """
        Idempotent upsert for bookings by booking_id.
        If booking_id exists -> update numeric/date fields; else insert.
        """
        inserted = 0
        updated = 0
        self.create_tables_if_missing()
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            for r in records:
                try:
                    booking_id = getattr(r, "booking_id", None)
                    if not booking_id:
                        continue

                    cur.execute("SELECT booking_id FROM bookings WHERE booking_id = ?", (booking_id,))
                    row = cur.fetchone()
                    if row:
                        cur.execute(
                            """
                            UPDATE bookings
                               SET booking_date = ?,
                                   arrival_date = ?,
                                   departure_date = ?,
                                   guests = ?,
                                   amount = ?,
                                   email = ?,
                                   raw_source = ?
                             WHERE booking_id = ?
                            """,
                            (
                                self._to_iso(getattr(r, "booking_date", None)),
                                self._to_iso(getattr(r, "arrival_date", None)),
                                self._to_iso(getattr(r, "departure_date", None)),
                                int(getattr(r, "guests", 0) or 0),
                                float(getattr(r, "amount", 0.0) or 0.0),
                                (getattr(r, "email", None) or None),
                                raw_source,
                                booking_id,
                            ),
                        )
                        updated += 1
                    else:
                        cur.execute(
                            """
                            INSERT INTO bookings (
                                booking_id, booking_date, arrival_date, departure_date, guests, amount, email, raw_source
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                booking_id,
                                self._to_iso(getattr(r, "booking_date", None)),
                                self._to_iso(getattr(r, "arrival_date", None)),
                                self._to_iso(getattr(r, "departure_date", None)),
                                int(getattr(r, "guests", 0) or 0),
                                float(getattr(r, "amount", 0.0) or 0.0),
                                (getattr(r, "email", None) or None),
                                raw_source,
                            ),
                        )
                        inserted += 1
                except Exception as e:
                    self.error_handler.handle_database_error(e, operation="upsert_bookings", affected_table="bookings")
                    continue
        return {"inserted": inserted, "updated": updated}


# Module-level singleton accessor
_ingest_repo: Optional[IngestRepository] = None


def get_ingest_repository() -> IngestRepository:
    global _ingest_repo
    if _ingest_repo is None:
        _ingest_repo = IngestRepository()
    return _ingest_repo
