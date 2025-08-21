"""
Smoke test for ingest repository upserts without Airtable.
Creates sample LeadModel and BookingModel records, runs upserts twice,
prints inserted/updated counts to verify idempotency, and shows table row counts.
"""
from datetime import date
import sqlite3
import os
import sys

# Allow running this script directly without setting PYTHONPATH
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.settings import Settings
from src.services.airtable_import_service import (
    LeadModel,
    BookingModel,
    save_leads_to_db,
    save_bookings_to_db,
)


def show_counts(conn):
    cur = conn.cursor()
    for tbl in ("leads", "bookings"):
        try:
            cur.execute(f"SELECT COUNT(*) FROM {tbl}")
            n = cur.fetchone()[0]
        except Exception:
            n = 0
        print(f"{tbl}: {n} rows")


def main():
    settings = Settings()
    db_path = settings.database.path

    leads = [
        LeadModel(
            email="test@example.com",
            created_date=date(2025, 1, 1),
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="winter",
            is_mql=True,
            is_sql=False,
        ),
        LeadModel(
            email="Test@Example.com",  # same logical lead different casing
            created_date=date(2025, 1, 1),
            utm_source="google",
            utm_medium="cpc",
            utm_campaign="winter",
            is_mql=True,
            is_sql=True,
        ),
    ]

    bookings = [
        BookingModel(
            booking_id="BK-001",
            booking_date=date(2025, 2, 1),
            arrival_date=date(2025, 3, 1),
            departure_date=date(2025, 3, 5),
            guests=2,
            amount=500.0,
        ),
        BookingModel(
            booking_id="BK-002",
            booking_date=date(2025, 2, 2),
            arrival_date=date(2025, 4, 1),
            departure_date=date(2025, 4, 4),
            guests=3,
            amount=750.0,
        ),
    ]

    print("First upsert run (should insert)")
    print("Leads:", save_leads_to_db(leads))
    print("Bookings:", save_bookings_to_db(bookings))

    print("\nSecond upsert run (should update, not insert)")
    print("Leads:", save_leads_to_db(leads))
    # Change amount to trigger an update on BK-001
    bookings[0].amount = 600.0
    print("Bookings:", save_bookings_to_db(bookings))

    # Show table counts
    print(f"\nUsing DB: {db_path}")
    conn = sqlite3.connect(db_path)
    try:
        print("\nTable row counts:")
        show_counts(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
