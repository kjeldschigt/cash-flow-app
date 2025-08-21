"""
Utilities for aligning comparison period data onto the current period for overlay charts,
and for generating continuous daily indices with zero-filled values.
"""
from __future__ import annotations

from datetime import date
from typing import List, Optional

import pandas as pd


def _detect_value_cols(df: pd.DataFrame, fallback: Optional[List[str]] = None) -> List[str]:
    """
    Detect numeric value columns to zero-fill. Falls back to provided list if given.
    """
    if fallback:
        return [c for c in fallback if c in df.columns]
    # Default heuristic: numeric columns except the date
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    return [c for c in numeric_cols if c.lower() != "date"]


def make_daily_index(
    df: pd.DataFrame,
    start: date,
    end: date,
    value_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Reindex DataFrame to a continuous daily date range [start, end] inclusive.
    Missing dates are added with zeros for specified value columns.

    Args:
        df: Input DataFrame expected to have a 'date' column (string/date-like)
        start: Start date (inclusive)
        end: End date (inclusive)
        value_cols: Optional list of columns to zero-fill. If None, will detect
                    numeric columns to fill.

    Returns:
        DataFrame with columns preserved, continuous 'date' column, and zeros
        filled for value columns on missing days.
    """
    # Build full date range
    full_range = pd.date_range(pd.to_datetime(start), pd.to_datetime(end), freq="D")

    if df is None or df.empty:
        # Construct new DF of zeros
        cols = value_cols or ["total_amount", "total_guests", "bookings_count"]
        base = pd.DataFrame({"date": full_range})
        for c in cols:
            base[c] = 0.0 if c.endswith("amount") else 0
        return base

    data = df.copy()
    if "date" not in data.columns:
        raise ValueError("make_daily_index expects a 'date' column in the DataFrame")

    data["date"] = pd.to_datetime(data["date"]).dt.normalize()
    # Ensure aggregation per day (in case duplicates exist)
    # Sum numeric columns
    data = (
        data.groupby("date", as_index=False).sum(numeric_only=True).merge(
            data.drop(columns=data.select_dtypes(include=["number"]).columns),
            on="date",
            how="left",
        )
    )

    data = data.set_index("date")
    reindexed = data.reindex(full_range)

    # Determine which columns to fill with zero
    to_fill = _detect_value_cols(data.reset_index(), value_cols)
    reindexed[to_fill] = reindexed[to_fill].fillna(0)

    # Reset index back to column
    reindexed = reindexed.reset_index().rename(columns={"index": "date"})
    return reindexed


def align_for_overlay(
    df_compare: pd.DataFrame,
    current_start: date,
    current_end: date,
    comp_start: date,
    value_cols: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Shift comparison DataFrame dates so that comp_start aligns to current_start.
    Then reindex to current [current_start, current_end] with zero fill.

    Args:
        df_compare: Comparison period daily DataFrame with a 'date' column.
        current_start: Current period start date.
        current_end: Current period end date.
        comp_start: Original comparison period start date.
        value_cols: Optional columns to zero-fill during reindex.

    Returns:
        DataFrame aligned to current period dates with shifted 'date' and zero-filled gaps.
    """
    if df_compare is None:
        return pd.DataFrame(columns=["date"])  # safe fallback

    comp = df_compare.copy()
    if "date" not in comp.columns:
        raise ValueError("align_for_overlay expects a 'date' column in df_compare")

    # Compute shift delta
    cur_start_ts = pd.to_datetime(current_start)
    comp_start_ts = pd.to_datetime(comp_start)
    delta = cur_start_ts - comp_start_ts

    comp["date"] = pd.to_datetime(comp["date"]) + delta

    # Reindex to the current range to trim/zero-fill
    aligned = make_daily_index(comp, current_start, current_end, value_cols=value_cols)
    return aligned
