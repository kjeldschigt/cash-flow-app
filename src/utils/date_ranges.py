"""
Date range presets and comparison window utilities.
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Tuple, Optional, Dict


# Preset keys
PRESETS = {
    "TODAY": "Today",
    "YESTERDAY": "Yesterday",
    "LAST_7": "Last 7 Days",
    "LAST_30": "Last 30 Days",
    "LAST_90": "Last 90 Days",
    "THIS_MONTH": "This Month",
    "LAST_MONTH": "Last Month",
    "YTD": "Year to Date",
    "LAST_12M": "Last 12 Months",
    "CUSTOM": "Custom",
}


def _safe_replace_year(d: date, new_year: int) -> date:
    """Replace year, clamping Feb 29 to Feb 28 when needed."""
    try:
        return d.replace(year=new_year)
    except ValueError:
        # Handle Feb 29 -> Feb 28
        if d.month == 2 and d.day == 29:
            return date(new_year, 2, 28)
        raise


def resolve_range(
    range_key: str,
    today: Optional[date] = None,
    custom_start: Optional[date] = None,
    custom_end: Optional[date] = None,
) -> Tuple[date, date]:
    """
    Resolve a preset key to an inclusive [start, end] date range.

    All dates are timezone-agnostic dates (YYYY-MM-DD when isoformatted).
    """
    if today is None:
        today = date.today()

    key = (range_key or "").upper()
    if key == "TODAY":
        return today, today
    if key == "YESTERDAY":
        y = today - timedelta(days=1)
        return y, y
    if key == "LAST_7":
        return today - timedelta(days=6), today
    if key == "LAST_30":
        return today - timedelta(days=29), today
    if key == "LAST_90":
        return today - timedelta(days=89), today
    if key == "THIS_MONTH":
        start = today.replace(day=1)
        return start, today
    if key == "LAST_MONTH":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        start_prev = last_prev.replace(day=1)
        return start_prev, last_prev
    if key == "YTD":
        return date(today.year, 1, 1), today
    if key == "LAST_12M":
        return today - timedelta(days=365 - 1), today
    if key == "CUSTOM":
        if not custom_start or not custom_end:
            # Default to last 30 days if not provided
            return today - timedelta(days=29), today
        if custom_start > custom_end:
            # Swap if user input reversed
            custom_start, custom_end = custom_end, custom_start
        return custom_start, custom_end

    # Fallback (treat as LAST_30)
    return today - timedelta(days=29), today


def get_comparison_window(
    start_date: date,
    end_date: date,
    mode: str,
) -> Optional[Tuple[date, date]]:
    """
    Compute the comparison window for a given base range and mode.

    Modes:
    - NONE: no comparison (returns None)
    - PREVIOUS_PERIOD: immediately preceding period of same length
    - SAME_PERIOD_LAST_YEAR: same calendar range 1 year earlier
    """
    m = (mode or "NONE").upper()
    if m in ("NONE", "OFF"):
        return None

    days = (end_date - start_date).days + 1  # inclusive length

    if m == "PREVIOUS_PERIOD":
        comp_end = start_date - timedelta(days=1)
        comp_start = comp_end - timedelta(days=days - 1)
        return comp_start, comp_end

    if m == "SAME_PERIOD_LAST_YEAR":
        comp_start = _safe_replace_year(start_date, start_date.year - 1)
        comp_end = _safe_replace_year(end_date, end_date.year - 1)
        return comp_start, comp_end

    return None


def preset_options() -> Dict[str, str]:
    """Return mapping of preset key -> human label."""
    return PRESETS.copy()


def comparison_options() -> Dict[str, str]:
    """Return mapping of comparison key -> human label."""
    return {
        "NONE": "Do not compare",
        "PREVIOUS_PERIOD": "Previous period",
        "SAME_PERIOD_LAST_YEAR": "Same period last year",
    }
