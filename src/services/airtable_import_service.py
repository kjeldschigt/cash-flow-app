import os
import csv
import io
from typing import List, Dict, Tuple, Optional
from datetime import datetime, date

from pydantic import BaseModel
from dateutil import parser as date_parser

# Optional import for Airtable SDK; allows this module to be imported even if pyairtable is not installed,
# as long as Airtable functions are not invoked.
try:
    from pyairtable import Table as _AirtableTable
except Exception:
    _AirtableTable = None  # type: ignore


class LeadModel(BaseModel):
    email: str
    created_date: date
    utm_source: str
    utm_medium: str
    utm_campaign: str
    is_mql: bool
    is_sql: bool


class BookingModel(BaseModel):
    booking_id: str
    booking_date: Optional[date]
    arrival_date: Optional[date]
    departure_date: Optional[date]
    guests: int
    amount: float
    email: Optional[str] = None


def _get_table(table_name: str):
    if _AirtableTable is None:
        raise RuntimeError("pyairtable is not installed. Please install requirements or avoid Airtable imports.")
    api_key = os.getenv("AIRTABLE_API_KEY")
    base_id = os.getenv("AIRTABLE_BASE_ID")
    if not api_key or not base_id:
        raise RuntimeError("AIRTABLE_API_KEY and AIRTABLE_BASE_ID must be set in environment variables")
    return _AirtableTable(api_key, base_id, table_name)


def _parse_date(value) -> date:
    if value is None:
        raise ValueError("Missing date value")
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        # Try strict ISO first
        try:
            return datetime.fromisoformat(value).date()
        except Exception:
            # Try common YYYY-MM-DD fallback
            try:
                return datetime.strptime(value, "%Y-%m-%d").date()
            except Exception as e:
                raise ValueError(f"Invalid date string: {value}") from e
    raise ValueError(f"Unsupported date type: {type(value)}")


def _get_field_ci(fields: Dict, key: str):
    """Get a field value by case-insensitive key lookup, returning None if not found."""
    if key in fields:
        return fields[key]
    for k in fields.keys():
        if isinstance(k, str) and k.lower() == key.lower():
            return fields[k]
    return None


def _norm_lower_strip(value: str, default: str = "unknown") -> str:
    if value is None:
        return default
    s = str(value).strip().lower()
    return s if s else default


def _to_bool(value) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    s = str(value).strip().lower()
    return s in {"yes", "true", "1", "y", "t"}


def _parse_date_flexible(value) -> Optional[date]:
    """Parse various date inputs using dateutil; return None for blanks."""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    s = str(value).strip()
    if not s:
        return None
    try:
        return date_parser.parse(s).date()
    except Exception:
        return None


def _get_ci(row: Dict[str, str], *names: str) -> Optional[str]:
    """Case-insensitive getter supporting aliases; returns the first match."""
    if not row:
        return None
    lower = {k.lower(): v for k, v in row.items()}
    for name in names:
        if name is None:
            continue
        key = name.lower()
        if key in lower:
            return lower[key]
    return None


def to_bool(v) -> bool:
    """Strict CSV boolean parsing: only explicit true values evaluate True."""
    try:
        s = str(v).strip().lower()
    except Exception:
        return False
    return s in {"true", "t", "yes", "y", "1", "✓", "✅"}


def parse_csv_leads(file_obj) -> List["LeadModel"]:
    """Backward-compatible wrapper: returns only records.
    See parse_csv_leads_with_diagnostics for full diagnostics.
    """
    records, _diag = parse_csv_leads_with_diagnostics(file_obj)
    return records


def _read_csv_text_and_detect_delimiter(file_obj) -> Tuple[str, str, List[str]]:
    """Read uploaded file as UTF-8 with BOM handling and detect delimiter.
    Returns (text, delimiter, headers_from_first_line)
    """
    if hasattr(file_obj, "getvalue"):
        raw = file_obj.getvalue()
    else:
        raw = file_obj.read()
    if isinstance(raw, bytes):
        text = raw.decode("utf-8-sig")  # strip BOM if present
    else:
        text = str(raw)

    first_line = text.splitlines()[0] if text.splitlines() else ""
    headers_guess: List[str] = []
    if first_line:
        for d in [",", ";", "\t", "|"]:
            if d in first_line:
                headers_guess = [h.strip() for h in first_line.split(d)]
                break

    # Try csv.Sniffer
    delimiter = ","
    try:
        sample = text[:4096]
        sniff = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        if sniff and sniff.delimiter in {",", ";", "\t", "|"}:
            delimiter = sniff.delimiter
    except Exception:
        # Fallback: choose the delimiter with most separators in first line
        counts = {d: first_line.count(d) for d in [",", ";", "\t", "|"]}
        delimiter = max(counts, key=counts.get) if counts else ","

    return text, delimiter, headers_guess


def parse_csv_leads_with_diagnostics(file_obj) -> Tuple[List["LeadModel"], Dict]:
    """Parse Leads CSV with robust delimiter detection, alias mapping, strict booleans, dedupe, and diagnostics.

    Diagnostics include:
      - total_rows
      - delimiter
      - headers (as read)
      - dropped: missing_email, invalid_date, header_not_found
      - groups_after_dedupe, mql_true_after_dedupe, sql_true_after_dedupe
    """
    text, delimiter, _headers_guess = _read_csv_text_and_detect_delimiter(file_obj)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = reader.fieldnames or []

    # Critical headers presence (by alias)
    def has_any(names: List[str]) -> bool:
        lower = [h.lower().strip() for h in headers]
        return any(n.lower() in lower for n in names)

    email_aliases = ["email", "e-mail", "guest email", "customer email"]
    created_aliases = [
        "created_at",
        "created date",
        "date",
        "date added",
        "submission date",
        "submitted at",
        "added at",
    ]
    mql_aliases = ["mql_yes", "mql", "is_mql", "marketing qualified lead"]
    sql_aliases = ["sql_yes", "sql", "is_sql", "sales qualified lead"]
    utm_source_aliases = ["utm_source", "utm source", "source"]
    utm_medium_aliases = ["utm_medium", "utm medium", "medium"]
    utm_campaign_aliases = ["utm_campaign", "utm campaign", "campaign"]

    diagnostics: Dict[str, any] = {
        "total_rows": 0,
        "delimiter": delimiter,
        "headers": headers,
        "dropped": {"missing_email": 0, "invalid_date": 0, "header_not_found": 0},
        "groups_after_dedupe": 0,
        "mql_true_after_dedupe": 0,
        "sql_true_after_dedupe": 0,
    }

    # If critical headers missing, count rows and abort parsing
    critical_missing = []
    if not has_any(email_aliases):
        critical_missing.append("email")
    if not has_any(created_aliases):
        critical_missing.append("created_at")
    if critical_missing:
        # Count data rows for diagnostics
        for _ in reader:
            diagnostics["total_rows"] += 1
        diagnostics["dropped"]["header_not_found"] = diagnostics["total_rows"]
        diagnostics["missing_headers"] = critical_missing
        return [], diagnostics

    # Parse rows
    by_key: Dict[str, Tuple[int, datetime, LeadModel]] = {}
    row_index = 0
    for row in reader:
        row_index += 1
        diagnostics["total_rows"] += 1
        try:
            email_val = None
            for a in email_aliases:
                email_val = _get_ci(row, a)
                if email_val is not None:
                    break
            email = (str(email_val).strip().lower() if email_val is not None else "")
            if not email:
                diagnostics["dropped"]["missing_email"] += 1
                continue

            created_raw = None
            for a in created_aliases:
                v = _get_ci(row, a)
                if v is not None:
                    created_raw = v
                    break
            created_dt_full: Optional[datetime]
            try:
                created_dt_full = date_parser.parse(str(created_raw)) if created_raw is not None else None
            except Exception:
                created_dt_full = None
            if not created_dt_full:
                diagnostics["dropped"]["invalid_date"] += 1
                continue
            created_date = created_dt_full.date()

            # Booleans
            mql_raw = None
            for a in mql_aliases:
                v = _get_ci(row, a)
                if v is not None:
                    mql_raw = v
                    break
            sql_raw = None
            for a in sql_aliases:
                v = _get_ci(row, a)
                if v is not None:
                    sql_raw = v
                    break
            is_mql = to_bool(mql_raw)
            is_sql = to_bool(sql_raw)

            # Negative flags force false
            neg_flag = _get_ci(row, "false_mql", "mql_false", "not_mql")
            if to_bool(neg_flag):
                is_mql = False
                is_sql = False

            utm_source = (next(((_get_ci(row, a) or "") for a in utm_source_aliases if _get_ci(row, a) is not None), "").strip().lower())
            utm_medium = (next(((_get_ci(row, a) or "") for a in utm_medium_aliases if _get_ci(row, a) is not None), "").strip().lower())
            utm_campaign = (next(((_get_ci(row, a) or "") for a in utm_campaign_aliases if _get_ci(row, a) is not None), "").strip().lower())

            key = f"{email}|{created_date.isoformat()}"
            lead = LeadModel(
                email=email,
                created_date=created_date,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                is_mql=is_mql,
                is_sql=is_sql,
            )
            if key not in by_key:
                by_key[key] = (row_index, created_dt_full, lead)
            else:
                prev_idx, prev_dt, _prev_lead = by_key[key]
                # Latest wins by datetime; if tie, later row index wins
                if created_dt_full > prev_dt or (
                    created_dt_full == prev_dt and row_index > prev_idx
                ):
                    by_key[key] = (row_index, created_dt_full, lead)
        except Exception:
            # Skip malformed rows silently but counted only in total_rows
            continue

    records = [t[2] for t in by_key.values()]
    diagnostics["groups_after_dedupe"] = len(records)
    diagnostics["mql_true_after_dedupe"] = sum(1 for r in records if r.is_mql)
    diagnostics["sql_true_after_dedupe"] = sum(1 for r in records if r.is_sql)

    return records, diagnostics


def parse_csv_bookings(file_obj) -> List["BookingModel"]:
    """Backward-compatible wrapper: returns only records.
    See parse_csv_bookings_with_diagnostics for full diagnostics.
    """
    records, _diag = parse_csv_bookings_with_diagnostics(file_obj)
    return records


def parse_csv_bookings_with_diagnostics(file_obj) -> Tuple[List["BookingModel"], Dict]:
    """Parse Bookings CSV with delimiter detection, sanity checks, dedupe, and diagnostics.

    Drops rows with invalid non-empty booking_date. Warns on duplicate booking_id within file.
    """
    text, delimiter, _headers_guess = _read_csv_text_and_detect_delimiter(file_obj)
    reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
    headers = reader.fieldnames or []

    diagnostics: Dict[str, any] = {
        "total_rows": 0,
        "delimiter": delimiter,
        "headers": headers,
        "dropped": {"missing_id": 0, "invalid_booking_date": 0},
        "duplicates_in_file": 0,
    }

    by_id: Dict[str, BookingModel] = {}
    seen_ids_count: Dict[str, int] = {}
    for row in reader:
        diagnostics["total_rows"] += 1
        try:
            booking_id_raw = _get_ci(row, "booking_id")
            booking_id = str(booking_id_raw).strip() if booking_id_raw is not None else ""
            if not booking_id:
                diagnostics["dropped"]["missing_id"] += 1
                continue
            seen_ids_count[booking_id] = seen_ids_count.get(booking_id, 0) + 1

            booking_date_val = _get_ci(row, "booking_date", "date", "created_at")
            booking_date = _parse_date_flexible(booking_date_val)
            # Drop only if original value is non-empty but unparseable
            if (booking_date is None) and (str(booking_date_val or "").strip() != ""):
                diagnostics["dropped"]["invalid_booking_date"] += 1
                continue

            arrival_date = _parse_date_flexible(_get_ci(row, "arrival_date", "arrival"))
            departure_date = _parse_date_flexible(_get_ci(row, "departure_date", "departure"))

            guests_raw = _get_ci(row, "guests")
            try:
                guests = int(float(guests_raw)) if guests_raw not in (None, "") else 0
            except Exception:
                guests = 0

            amount_raw = _get_ci(row, "amount")
            try:
                amount = float(amount_raw) if amount_raw not in (None, "") else 0.0
            except Exception:
                amount = 0.0

            email_raw = _get_ci(row, "email")
            email = (str(email_raw).strip().lower() or None) if email_raw is not None else None

            booking = BookingModel(
                booking_id=booking_id,
                booking_date=booking_date,
                arrival_date=arrival_date,
                departure_date=departure_date,
                guests=guests,
                amount=amount,
                email=email,
            )
            by_id[booking_id] = booking
        except Exception:
            continue

    diagnostics["duplicates_in_file"] = sum(1 for cnt in seen_ids_count.values() if cnt > 1)
    return list(by_id.values()), diagnostics


def summarize_leads(records: List[LeadModel]) -> Dict:
    utm_counts: Dict[str, int] = {}
    for r in records:
        src = r.utm_source or "unknown"
        utm_counts[src] = utm_counts.get(src, 0) + 1
    return {
        "deduped": len(records),
        "utm_sources": utm_counts,
    }


def import_leads() -> Tuple[List[LeadModel], Dict]:
    """Import leads from Airtable table 'Main'.

    Rules:
    - Drop records where mql_false is true.
    - Only include records where at least one of mql_yes/sql_yes is true.
    - Map fields to LeadModel.
    """
    table = _get_table("Main")
    records_raw = table.all()

    total_raw = len(records_raw)
    leads_filtered: List[LeadModel] = []
    # For dedupe key tracking
    seen_keys = set()
    after_filter_before_dedupe = 0

    for idx, rec in enumerate(records_raw):
        fields = rec.get("fields", {})
        try:
            # Normalize booleans
            mql_yes = _to_bool(_get_field_ci(fields, "mql_yes") if _get_field_ci(fields, "mql_yes") is not None else _get_field_ci(fields, "mql"))
            sql_yes = _to_bool(_get_field_ci(fields, "sql_yes") if _get_field_ci(fields, "sql_yes") is not None else _get_field_ci(fields, "sql"))
            mql_false = _to_bool(_get_field_ci(fields, "mql_false"))

            # Filter rules
            if mql_false:
                continue
            if not (mql_yes or sql_yes):
                continue

            created = _parse_date(_get_field_ci(fields, "created_date"))
            # Normalize text fields
            utm_source = _norm_lower_strip(_get_field_ci(fields, "utm_source"))
            utm_medium = _norm_lower_strip(_get_field_ci(fields, "utm_medium"))
            utm_campaign = _norm_lower_strip(_get_field_ci(fields, "utm_campaign"))

            # Email normalization for dedupe key
            email_raw = _get_field_ci(fields, "email")
            email_norm = _norm_lower_strip(email_raw, default="")
            if not email_norm:
                row_id = rec.get("id") or f"row-{idx}"
                email_norm = f"unknown-{row_id}"

            # Count after filters but before dedupe
            after_filter_before_dedupe += 1

            dedupe_key = (email_norm, created)
            if dedupe_key in seen_keys:
                continue
            seen_keys.add(dedupe_key)

            lead = LeadModel(
                email=email_norm,
                created_date=created,
                utm_source=utm_source,
                utm_medium=utm_medium,
                utm_campaign=utm_campaign,
                is_mql=mql_yes,
                is_sql=sql_yes,
            )
            leads_filtered.append(lead)
        except Exception:
            # Skip malformed records silently per minimal implementation
            continue

    # Build summary counts
    # Build summary
    base_summary = summarize_leads(leads_filtered)
    summary: Dict = {
        "total_raw": total_raw,
        "after_mql_sql_filter": after_filter_before_dedupe,
        **base_summary,
    }

    return leads_filtered, summary


def summarize_bookings(records: List[BookingModel]) -> Dict:
    total_amount = sum((r.amount or 0.0) for r in records)
    guests_total = sum((r.guests or 0) for r in records)
    return {
        "deduped": len(records),
        "total_amount": float(total_amount),
        "guests_total": int(guests_total),
    }


def import_bookings() -> Tuple[List[BookingModel], Dict]:
    """Import bookings from Airtable table 'Bookings<>Able'."""
    table = _get_table("Bookings<>Able")
    records_raw = table.all()

    total_raw = len(records_raw)
    bookings: List[BookingModel] = []
    seen_ids = set()

    for rec in records_raw:
        fields = rec.get("fields", {})
        try:
            booking_id_raw = _get_field_ci(fields, "booking_id")
            booking_id = str(booking_id_raw).strip() if booking_id_raw is not None else (rec.get("id") or "")
            if not booking_id:
                # If still empty, skip as we cannot dedupe reliably
                continue
            if booking_id in seen_ids:
                continue
            seen_ids.add(booking_id)

            booking_date = _parse_date(_get_field_ci(fields, "booking_date"))
            arrival_date = _parse_date(_get_field_ci(fields, "arrival_date"))
            departure_date = _parse_date(_get_field_ci(fields, "departure_date"))

            guests_raw = _get_field_ci(fields, "guests")
            amount_raw = _get_field_ci(fields, "amount")

            # Normalize email if present
            email_raw = _get_field_ci(fields, "email")
            email_norm = _norm_lower_strip(email_raw, default="")
            email_val: Optional[str] = email_norm if email_norm else None

            guests = int(guests_raw) if guests_raw is not None else 0
            amount = float(amount_raw) if amount_raw is not None else 0.0

            booking = BookingModel(
                booking_id=booking_id,
                booking_date=booking_date,
                arrival_date=arrival_date,
                departure_date=departure_date,
                guests=guests,
                amount=amount,
                email=email_val,
            )
            bookings.append(booking)
        except Exception:
            # Skip malformed records silently per minimal implementation
            continue

    base_summary = summarize_bookings(bookings)
    summary: Dict = {
        "total_raw": total_raw,
        **base_summary,
    }

    return bookings, summary


def fetch_all_leads() -> List[LeadModel]:
    """
    Fetch all historical leads from Airtable 'Main' and return normalized LeadModel list.
    Applies the same filtering and deduplication rules as import_leads().
    """
    records, _ = import_leads()
    return records


def fetch_all_bookings() -> List[BookingModel]:
    """
    Fetch all historical bookings from Airtable 'Bookings<>Able' and return normalized BookingModel list.
    Applies the same deduplication rules as import_bookings().
    """
    records, _ = import_bookings()
    return records


def save_leads_to_db(records: List[LeadModel]) -> Dict:
    """Persist leads to DB using ingest repository upsert."""
    from src.repositories.ingest_repository import get_ingest_repository

    repo = get_ingest_repository()
    return repo.upsert_leads(records)


def save_bookings_to_db(records: List[BookingModel]) -> Dict:
    """Persist bookings to DB using ingest repository upsert."""
    from src.repositories.ingest_repository import get_ingest_repository

    repo = get_ingest_repository()
    return repo.upsert_bookings(records)
