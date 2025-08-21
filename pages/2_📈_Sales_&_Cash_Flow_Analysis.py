import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, date, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# New clean architecture imports
from src.container import get_container
from src.ui.auth import AuthComponents
from src.ui.components.components import UIComponents
from src.ui.forms import FormComponents
from src.ui.components.charts import ChartComponents
from src.security import AuditLogger, AuditAction
from src.utils.date_utils import DateUtils
from src.utils.date_ranges import (
    comparison_options,
)
from src.ui.state.date_controls import (
    range_selector,
    compare_selector,
    get_dates_from_state,
)
from src.analytics.compare_utils import align_for_overlay

# Legacy imports for backward compatibility
from src.utils.theme_manager import apply_theme
from src.services.settings_service import get_setting
from src.services.error_handler import handle_error

# Legacy imports for theme
from src.utils.theme_manager import apply_current_theme
import traceback

try:
    # Check authentication using new auth system
    if not AuthComponents.require_authentication():
        st.stop()

    # Apply theme
    apply_current_theme()

    # Get services from container
    container = get_container()
    analytics_service = container.get_analytics_service()
    payment_service = container.get_payment_service()
    from src.services.error_handler import get_error_handler

    error_handler = get_error_handler()

    st.title("📈 Sales & Cash Flow Analysis")
    # Date control state handled via centralized helpers

    # Sidebar filters
    with st.sidebar:
        st.header("Analysis Filters")
        range_selector("Date Range", key_prefix="sales")
        compare_selector("Compare to", key_prefix="sales")
        # Currency filter (reserved for future use)
        currency_filter = st.selectbox("Currency", ["All", "USD", "CRC"])

    # Compute windows
    base_start, base_end, compare_mode, c_start, c_end = get_dates_from_state("sales")
    comp_range = (c_start, c_end) if c_start and c_end else None

    # Tabs: Sales (Bookings) and Cash Flow
    tab_sales, tab_cash = st.tabs(["Sales (Bookings)", "Cash Flow"])

    # --- Sales (Bookings) Tab ---
    with tab_sales:
        UIComponents.section_header("Sales (Bookings)", "Bookings revenue and activity")

        # Bookings summary metrics with comparison deltas
        try:
            bsum = analytics_service.bookings_summary(start_date=base_start, end_date=base_end)
        except Exception as e:
            error_handler.handle_error(e, user_message="Unable to load bookings summary")
            bsum = {"total_amount": 0.0, "bookings_count": 0, "avg_booking_amount": 0.0}

        c_bsum = None
        if comp_range:
            try:
                c_bsum = analytics_service.bookings_summary(start_date=comp_range[0], end_date=comp_range[1])
            except Exception as e:
                error_handler.handle_error(e, user_message="Unable to load comparison bookings summary")
                c_bsum = None

        c1, c2, c3 = st.columns(3)
        with c1:
            total_amt = float(bsum.get("total_amount", 0.0) or 0.0)
            delta_amt = None
            help_txt = None
            if c_bsum:
                comp_amt = float(c_bsum.get("total_amount", 0.0) or 0.0)
                delta_amt = total_amt - comp_amt
                pct = ((total_amt - comp_amt) / comp_amt * 100.0) if comp_amt else None
                mode_label = comparison_options().get(compare_mode, "comparison").lower()
                help_txt = (f"Δ {pct:.1f}% vs {mode_label}" if pct is not None else "Δ n/a")
            UIComponents.currency_metric("Total Bookings Revenue", total_amt, "USD", delta_amount=delta_amt, help_text=help_txt)
        with c2:
            count = int(bsum.get("bookings_count", 0) or 0)
            delta = None
            if c_bsum is not None:
                c_count = int(c_bsum.get("bookings_count", 0) or 0)
                pct = ((count - c_count) / c_count * 100.0) if c_count else None
                delta = f"{count - c_count:+d}" + (f" ({pct:.1f}%)" if pct is not None else "")
            UIComponents.metric_card("Bookings", f"{count}", delta)
        with c3:
            avg_amt = float(bsum.get("avg_booking_amount", 0.0) or 0.0)
            delta_avg = None
            help_txt2 = None
            if c_bsum is not None:
                c_avg = float(c_bsum.get("avg_booking_amount", 0.0) or 0.0)
                delta_avg = avg_amt - c_avg
                pct2 = ((avg_amt - c_avg) / c_avg * 100.0) if c_avg else None
                mode_label = comparison_options().get(st.session_state["sales_compare_mode"], "comparison").lower()
                help_txt2 = (f"Δ {pct2:.1f}% vs {mode_label}" if pct2 is not None else "Δ n/a")
            UIComponents.currency_metric("Avg Booking Amount", avg_amt, "USD", delta_amount=delta_avg, help_text=help_txt2)

        # Daily bookings sales chart with comparison overlay
        try:
            bookings_df = analytics_service.bookings_by_date_daily(start_date=base_start, end_date=base_end)
        except Exception as e:
            error_handler.handle_error(e, user_message="Unable to load bookings by date")
            bookings_df = pd.DataFrame(columns=["date", "total_amount", "total_guests", "bookings_count"])

        if bookings_df is not None and not bookings_df.empty:
            comp_df = None
            comp_label = comparison_options().get(compare_mode, "Comparison")
            if comp_range:
                try:
                    comp_daily = analytics_service.bookings_by_date_daily(start_date=comp_range[0], end_date=comp_range[1])
                    # Align comparison onto current window for overlay
                    comp_df = align_for_overlay(
                        comp_daily,
                        current_start=base_start,
                        current_end=base_end,
                        comp_start=comp_range[0],
                        value_cols=["total_amount", "total_guests", "bookings_count"],
                    )
                except Exception as e:
                    error_handler.handle_error(e, user_message="Unable to load comparison bookings by date")
                    comp_df = None

            ChartComponents.sales_line_chart(
                bookings_df,
                title="Daily Bookings Revenue",
                date_column="date",
                value_column="total_amount",
                comp_df=comp_df,
                comp_date_column="date",
                comp_value_column="total_amount",
                comp_label=f"{comp_label} (aligned)",
            )

            # Export comparison CSV when active
            if comp_range:
                try:
                    # Prepare both actual and aligned for export
                    actual_df = analytics_service.bookings_by_date_daily(start_date=comp_range[0], end_date=comp_range[1])

                    export_mode = st.radio(
                        "Export comparison data",
                        options=["Aligned", "Actual"],
                        horizontal=True,
                        key="sales_export_mode",
                    )

                    cur = bookings_df[["date", "total_amount"]].rename(columns={"total_amount": "current_amount"}).copy()
                    if export_mode == "Aligned" and comp_df is not None and not comp_df.empty:
                        cmp = comp_df[["date", "total_amount"]].rename(columns={"total_amount": "comparison_amount"}).copy()
                        suffix = "aligned"
                    else:
                        cmp = actual_df[["date", "total_amount"]].rename(columns={"total_amount": "comparison_amount"}).copy()
                        suffix = "actual"

                    cur["date"] = pd.to_datetime(cur["date"]).dt.date
                    cmp["date"] = pd.to_datetime(cmp["date"]).dt.date
                    merged = pd.merge(cur, cmp, on="date", how="outer").sort_values("date")
                    merged["date"] = merged["date"].apply(lambda d: d.isoformat() if pd.notnull(d) else "")
                    csv_bytes = merged.to_csv(index=False).encode("utf-8")
                    fname = f"sales_comparison_{base_start.isoformat()}_{base_end.isoformat()}_{suffix}.csv"
                    st.download_button("⬇️ Export Comparison CSV", data=csv_bytes, file_name=fname, mime="text/csv")
                except Exception as e:
                    error_handler.handle_error(e, user_message="Unable to export comparison CSV")
        else:
            UIComponents.info_message("No bookings data yet — import and save from Settings first")

        # Lead → Booking Lag analytics
        with st.expander("Lead → Booking Lag", expanded=False):
            try:
                start_iso = base_start.isoformat()
                end_iso = base_end.isoformat()
                result = analytics_service.lead_to_booking_lag(start_iso, end_iso)

                summary = result.get("summary", {})
                matched = int(summary.get("matched_bookings", 0))
                unmatched = int(summary.get("unmatched_bookings", 0))
                total = matched + unmatched

                if total == 0:
                    UIComponents.info_message("No bookings in this range.")
                elif matched == 0:
                    UIComponents.info_message(
                        "No matched lead→booking pairs in this range. Try widening the dates or import more data."
                    )
                else:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        UIComponents.metric_card("Matched Bookings", f"{matched}")
                    with c2:
                        UIComponents.metric_card("Avg Lag (days)", f"{summary.get('avg_days', 0.0):.1f}")
                    with c3:
                        UIComponents.metric_card(
                            "Median (p50) / P90 (days)",
                            f"{summary.get('median_days', 0.0):.1f} / {summary.get('p90_days', 0.0):.1f}"
                        )

                    lag_table = result.get("lag_table", [])
                    if lag_table:
                        df = pd.DataFrame(lag_table)
                        cols = [
                            "booking_date", "booking_id", "amount", "guests",
                            "lead_created_at", "lag_days",
                            "utm_source", "utm_medium", "utm_campaign", "email",
                        ]
                        df = df[[c for c in cols if c in df.columns]]
                        UIComponents.data_table(df)

                    with st.expander("UTM Breakdown", expanded=False):
                        utm = result.get("utm_breakdown", {})
                        by_src = pd.DataFrame(utm.get("by_source", []))
                        by_cmp = pd.DataFrame(utm.get("by_campaign", []))
                        colA, colB = st.columns(2)
                        with colA:
                            if not by_src.empty:
                                UIComponents.data_table(by_src)
                            else:
                                UIComponents.info_message("No source data")
                        with colB:
                            if not by_cmp.empty:
                                UIComponents.data_table(by_cmp)
                            else:
                                UIComponents.info_message("No campaign data")

                    cohorts = pd.DataFrame(result.get("monthly_cohorts", []))
                    if not cohorts.empty:
                        UIComponents.data_table(cohorts)
            except Exception as e:
                error_handler.handle_error(e, user_message="Unable to compute lead → booking lag")

    # --- Cash Flow Tab ---
    with tab_cash:
        UIComponents.section_header("Cash Flow", "True cash inflows and outflows from ledger")

        try:
            csum = analytics_service.cash_ledger_summary(start_date=base_start, end_date=base_end)
        except Exception as e:
            error_handler.handle_error(e, user_message="Unable to load cash ledger summary")
            csum = {"inflow": 0.0, "outflow": 0.0, "net": 0.0, "entries": 0}

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            UIComponents.currency_metric("Cash Inflow", csum.get("inflow", 0.0), "USD")
        with c2:
            UIComponents.currency_metric("Cash Outflow", csum.get("outflow", 0.0), "USD")
        with c3:
            UIComponents.currency_metric("Net Cash Flow", csum.get("net", 0.0), "USD")
        with c4:
            UIComponents.metric_card("Entries", f"{csum.get('entries', 0)}")

        # Daily cash flow chart
        try:
            cash_df = analytics_service.cash_ledger_by_date(start_date=base_start, end_date=base_end)
        except Exception as e:
            error_handler.handle_error(e, user_message="Unable to load cash ledger by date")
            cash_df = pd.DataFrame(columns=["date", "inflow", "outflow"])

        if cash_df is not None and not cash_df.empty:
            ChartComponents.cash_flow_chart(cash_df[["date", "inflow", "outflow"]], title="Daily Cash Flow")
        else:
            UIComponents.info_message("No cash ledger data yet — add entries in Cash Ledger page or Settings")

except Exception:
    st.error(traceback.format_exc())
