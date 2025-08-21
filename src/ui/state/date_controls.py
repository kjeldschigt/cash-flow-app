from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

import streamlit as st

from src.utils.date_ranges import (
    resolve_range,
    get_comparison_window,
    preset_options,
    comparison_options,
)


def ensure_state_default(key: str, value):
    """
    Ensure a session_state key exists without reassigning on reruns.
    Uses setdefault to avoid Streamlit warnings about conflicting defaults.
    """
    if key not in st.session_state:
        st.session_state.setdefault(key, value)


def range_selector(label: str, key_prefix: str) -> None:
    """
    Render a date preset selector plus optional custom date inputs.
    Keys used:
      {key_prefix}_range_key, {key_prefix}_custom_start, {key_prefix}_custom_end
    Rules:
    - Initialize defaults via session_state.setdefault
    - Do NOT pass index/defaults; rely on session state binding only
    """
    presets = preset_options()

    rk = f"{key_prefix}_range_key"
    cs = f"{key_prefix}_custom_start"
    ce = f"{key_prefix}_custom_end"

    ensure_state_default(rk, "LAST_30")
    # For custom dates, default to today; only shown when CUSTOM selected
    ensure_state_default(cs, date.today())
    ensure_state_default(ce, date.today())

    # Selectbox bound to session state; no index passed
    st.selectbox(
        label,
        options=list(presets.keys()),
        key=rk,
        format_func=lambda k: presets[k],
    )

    # Show custom date inputs when CUSTOM
    if st.session_state.get(rk) == "CUSTOM":
        col1, col2 = st.columns(2)
        with col1:
            st.date_input("Start", key=cs)
        with col2:
            st.date_input("End", key=ce)


def compare_selector(label: str, key_prefix: str) -> None:
    """
    Render a comparison mode selector.
    Key used: {key_prefix}_compare_mode
    """
    comps = comparison_options()
    ck = f"{key_prefix}_compare_mode"
    ensure_state_default(ck, "NONE")

    # Selectbox bound to session state; no index passed
    st.selectbox(
        label,
        options=list(comps.keys()),
        key=ck,
        format_func=lambda k: comps[k],
    )


def get_dates_from_state(key_prefix: str) -> Tuple[date, date, str, Optional[date], Optional[date]]:
    """
    Compute current and comparison date windows from session state.

    Returns: (start_date, end_date, compare_mode, comp_start, comp_end)
    """
    rk = f"{key_prefix}_range_key"
    cs = f"{key_prefix}_custom_start"
    ce = f"{key_prefix}_custom_end"
    ck = f"{key_prefix}_compare_mode"

    range_key = st.session_state.get(rk, "LAST_30")
    custom_start = st.session_state.get(cs)
    custom_end = st.session_state.get(ce)

    start_date, end_date = resolve_range(range_key, custom_start=custom_start, custom_end=custom_end)

    compare_mode = st.session_state.get(ck, "NONE")
    comp_window = get_comparison_window(start_date, end_date, compare_mode)
    if comp_window:
        c_start, c_end = comp_window
    else:
        c_start, c_end = None, None

    return start_date, end_date, compare_mode, c_start, c_end
