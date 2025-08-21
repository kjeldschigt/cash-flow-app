#!/usr/bin/env python3
"""
One-off merge utility to copy missing rows from the legacy 'cash_flow.db'
into the canonical database defined by Settings().database.path ('cashflow.db').

- Non-destructive and idempotent
- Inserts only rows that are missing in destination
- Tables covered:
  * leads (unique logic: unique_key)
  * bookings (unique logic: booking_id)
  * costs (optional if table exists; unique logic: (name, amount, currency, cost_date))

Usage:
  python3 -u scripts/merge_db_once.py
"""
import os
import sys
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

# Compute project root and import settings
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.config.settings import Settings  # noqa: E402


def table_exists(conn: sqlite3.Connection, table: str) -> bool:
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
    return cur.fetchone() is not None


def ensure_table_leads(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
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
    conn.commit()


def ensure_table_bookings(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            booking_id TEXT PRIMARY KEY,
            booking_date DATE,
            arrival_date DATE,
            departure_date DATE,
            guests INTEGER,
            amount REAL,
            raw_source TEXT
        )
        """
    )
    conn.commit()


def ensure_table_costs(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS costs (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            cost_date DATE,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()


def _row_get(row: sqlite3.Row, key: str, default=None):
    # sqlite3.Row supports mapping-like access
    try:
        return row[key]
    except (KeyError, IndexError, TypeError):
        return default


def merge_leads(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    if not table_exists(src, "leads"):
        return 0
    ensure_table_leads(dst)

    src.row_factory = sqlite3.Row
    dst.row_factory = sqlite3.Row
    s_cur = src.cursor()
    d_cur = dst.cursor()

    inserted = 0
    s_cur.execute("SELECT * FROM leads")
    rows = s_cur.fetchall()

    for row in rows:
        # Determine unique key, compute if missing
        email = (_row_get(row, "email", "") or "").strip().lower()
        created_at = _row_get(row, "created_at")
        unique_key = _row_get(row, "unique_key")
        if not unique_key:
            if not created_at:
                # Cannot dedupe without created_at; skip
                continue
            unique_key = f"{email}|{created_at}"

        d_cur.execute("SELECT 1 FROM leads WHERE unique_key = ?", (unique_key,))
        if d_cur.fetchone():
            continue

        lead_id = _row_get(row, "lead_id") or str(uuid.uuid4())
        mql_yes = 1 if bool(_row_get(row, "mql_yes", False)) else 0
        sql_yes = 1 if bool(_row_get(row, "sql_yes", False)) else 0
        utm_source = _row_get(row, "utm_source")
        utm_medium = _row_get(row, "utm_medium")
        utm_campaign = _row_get(row, "utm_campaign")
        raw_source = _row_get(row, "raw_source") or "merge:legacy"

        d_cur.execute(
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
                mql_yes,
                sql_yes,
                utm_source,
                utm_medium,
                utm_campaign,
                raw_source,
                unique_key,
            ),
        )
        inserted += 1

    dst.commit()
    return inserted


def merge_bookings(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    if not table_exists(src, "bookings"):
        return 0
    ensure_table_bookings(dst)

    src.row_factory = sqlite3.Row
    dst.row_factory = sqlite3.Row
    s_cur = src.cursor()
    d_cur = dst.cursor()

    inserted = 0
    s_cur.execute("SELECT * FROM bookings")
    rows = s_cur.fetchall()

    for row in rows:
        booking_id = _row_get(row, "booking_id")
        if not booking_id:
            continue

        d_cur.execute("SELECT 1 FROM bookings WHERE booking_id = ?", (booking_id,))
        if d_cur.fetchone():
            continue

        booking_date = _row_get(row, "booking_date")
        arrival_date = _row_get(row, "arrival_date")
        departure_date = _row_get(row, "departure_date")
        guests = int(_row_get(row, "guests", 0) or 0)
        amount = float(_row_get(row, "amount", 0.0) or 0.0)
        raw_source = _row_get(row, "raw_source") or "merge:legacy"

        d_cur.execute(
            """
            INSERT INTO bookings (
                booking_id, booking_date, arrival_date, departure_date, guests, amount, raw_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                booking_id,
                booking_date,
                arrival_date,
                departure_date,
                guests,
                amount,
                raw_source,
            ),
        )
        inserted += 1

    dst.commit()
    return inserted


def merge_costs(src: sqlite3.Connection, dst: sqlite3.Connection) -> int:
    if not table_exists(src, "costs"):
        return 0
    ensure_table_costs(dst)

    src.row_factory = sqlite3.Row
    dst.row_factory = sqlite3.Row
    s_cur = src.cursor()
    d_cur = dst.cursor()

    inserted = 0
    s_cur.execute("SELECT * FROM costs")
    rows = s_cur.fetchall()

    now_ts = datetime.utcnow().isoformat(timespec="seconds")

    for row in rows:
        name = _row_get(row, "name")
        amount = _row_get(row, "amount")
        currency = _row_get(row, "currency")
        cost_date = _row_get(row, "cost_date")
        if name is None or amount is None:
            continue  # insufficient to dedupe

        # Existence check on composite key (name, amount, currency, cost_date)
        d_cur.execute(
            """
            SELECT 1 FROM costs
             WHERE name = ? AND amount = ?
               AND ((currency IS NULL AND ? IS NULL) OR currency = ?)
               AND ((cost_date IS NULL AND ? IS NULL) OR cost_date = ?)
            """,
            (name, amount, currency, currency, cost_date, cost_date),
        )
        if d_cur.fetchone():
            continue

        row_id = _row_get(row, "id") or str(uuid.uuid4())
        category = _row_get(row, "category")
        description = _row_get(row, "description")
        created_at = _row_get(row, "created_at") or now_ts
        updated_at = _row_get(row, "updated_at") or now_ts

        d_cur.execute(
            """
            INSERT INTO costs (
                id, name, category, amount, currency, cost_date, description, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row_id,
                name,
                category,
                amount,
                currency,
                cost_date,
                description,
                created_at,
                updated_at,
            ),
        )
        inserted += 1

    dst.commit()
    return inserted


def main() -> int:
    settings = Settings()
    dst_db = settings.database.path
    src_db = os.path.join(PROJECT_ROOT, "cash_flow.db")

    if not os.path.exists(src_db):
        print("No source DB found, nothing to merge.")
        return 0

    print(f"Using src_db: {src_db}")
    print(f"Using dst_db: {dst_db}")

    src_conn = sqlite3.connect(src_db)
    dst_conn = sqlite3.connect(dst_db)

    try:
        leads_inserted = merge_leads(src_conn, dst_conn)
        bookings_inserted = merge_bookings(src_conn, dst_conn)
        costs_inserted = merge_costs(src_conn, dst_conn)

        print(
            "Inserted per table: leads=%d, bookings=%d, costs=%d"
            % (leads_inserted, bookings_inserted, costs_inserted)
        )
    finally:
        try:
            src_conn.close()
        except Exception:
            pass
        try:
            dst_conn.close()
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
