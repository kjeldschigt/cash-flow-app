import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta, date
import sqlite3
import numpy as np
from decimal import Decimal
import sys
import os
import warnings
import traceback

# Add the src directory to the Python path
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import services and utilities
from src.services.storage_service import StorageService
from src.security.auth import AuthManager
from src.utils.data_manager import calculate_metrics, get_date_range_data
from src.services.error_handler import handle_error
from src.utils.theme_manager import apply_theme
from components.ui_helpers import (
    render_metric_grid,
    create_section_header,
    render_chart_container,
)

# New clean architecture imports
from src.container import get_container
from src.container import get_bank_service
from src.ui.auth import AuthComponents
from src.ui.components.components import UIComponents
from src.ui.forms import FormComponents
from src.ui.components.charts import ChartComponents
from src.services.error_handler import ErrorHandler
from src.utils.date_ranges import (
    comparison_options,
)
from src.ui.state.date_controls import (
    range_selector,
    compare_selector,
    get_dates_from_state,
)
from src.analytics.compare_utils import align_for_overlay

# Configure page
st.set_page_config(page_title="Dashboard", page_icon="🏠", layout="wide")

# Filter warnings
warnings.filterwarnings("ignore", category=UserWarning)


def _get_date_range_from_selection(range_select):
    """Convert range selection to start/end dates"""
    today = datetime.now().date()

    if range_select == "Last 7 Days":
        start_date = today - timedelta(days=7)
    elif range_select == "Last 30 Days":
        start_date = today - timedelta(days=30)
    elif range_select == "Last 3 Months":
        start_date = today - timedelta(days=90)
    elif range_select == "Last 6 Months":
        start_date = today - timedelta(days=180)
    elif range_select == "Last 12 Months":
        start_date = today - timedelta(days=365)
    elif range_select == "YTD":
        start_date = datetime(today.year, 1, 1).date()
    else:
        start_date = today - timedelta(days=30)

    return {"start": start_date, "end": today}


def generate_pdf(df, title):
    """Generate PDF report from dataframe"""
    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", "B", 16)
        pdf.cell(0, 10, title, 0, 1, "C")
        return pdf.output(dest="S").encode("latin-1")
    except ImportError:
        return None


try:
    # Check authentication using new auth system
    if not AuthComponents.require_authentication():
        st.stop()

    # Apply theme
    apply_theme("light")

    # Get services from container
    container = get_container()
    analytics_service = container.get_analytics_service()
    bank_service = get_bank_service()
    from src.services.error_handler import get_error_handler

    error_handler = get_error_handler()

    st.title("🏠 Dashboard")

    # Sidebar filters
    with st.sidebar:
        st.header("Dashboard Filters")
        range_selector("Date Range", key_prefix="dashboard")
        compare_selector("Compare to", key_prefix="dashboard")
        # Currency filter (placeholder for future use)
        currency_filter = st.selectbox("Currency", ["All", "USD", "CRC"])

    # Compute current and comparison ranges from centralized state
    base_start, base_end, compare_mode, c_start, c_end = get_dates_from_state("dashboard")
    comp_range = (c_start, c_end) if c_start and c_end else None

    # Key Metrics Section
    UIComponents.section_header(
        "Key Metrics", f"Performance overview for {base_start.isoformat()} → {base_end.isoformat()}"
    )

    # Bookings summary (Sales)
    try:
        bsum = analytics_service.bookings_summary(
            start_date=base_start, end_date=base_end
        )
    except Exception as e:
        error_handler.handle_error(e, user_message="Unable to load bookings summary")
        bsum = {"total_amount": 0.0, "bookings_count": 0, "avg_booking_amount": 0.0}

    # Comparison bookings summary
    c_bsum = None
    if comp_range:
        try:
            c_bsum = analytics_service.bookings_summary(start_date=comp_range[0], end_date=comp_range[1])
        except Exception as e:
            error_handler.handle_error(e, user_message="Unable to load comparison bookings summary")
            c_bsum = None

    # Cash ledger summary (true cash flow)
    try:
        csum = analytics_service.cash_ledger_summary(
            start_date=base_start, end_date=base_end
        )
    except Exception as e:
        error_handler.handle_error(e, user_message="Unable to load cash ledger summary")
        csum = {"inflow": 0.0, "outflow": 0.0, "net": 0.0, "entries": 0}

    # Comparison cash ledger summary
    c_csum = None
    if comp_range:
        try:
            c_csum = analytics_service.cash_ledger_summary(start_date=comp_range[0], end_date=comp_range[1])
        except Exception as e:
            error_handler.handle_error(e, user_message="Unable to load comparison cash ledger summary")
            c_csum = None

    # Display metrics: bookings totals/count/avg, and net cash flow if entries exist
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        total_amt = float(bsum.get("total_amount", 0.0) or 0.0)
        delta_amt = None
        pct_help = None
        if c_bsum:
            comp_amt = float(c_bsum.get("total_amount", 0.0) or 0.0)
            delta_amt = total_amt - comp_amt
            pct = ((total_amt - comp_amt) / comp_amt * 100.0) if comp_amt else None
            pct_help = (f"Δ {pct:.1f}% vs {comparison_options().get(compare_mode, '').lower()}" if pct is not None else "Δ n/a")
        UIComponents.currency_metric("Total Bookings Revenue", total_amt, "USD", delta_amount=delta_amt, help_text=pct_help)

    with col2:
        bcnt = int(bsum.get("bookings_count", 0) or 0)
        delta = None
        if c_bsum is not None:
            comp_bcnt = int(c_bsum.get("bookings_count", 0) or 0)
            pct = ((bcnt - comp_bcnt) / comp_bcnt * 100.0) if comp_bcnt else None
            delta = f"{bcnt - comp_bcnt:+d}" + (f" ({pct:.1f}%)" if pct is not None else "")
        UIComponents.metric_card("Bookings", str(bcnt), delta)

    with col3:
        avg_amt = float(bsum.get("avg_booking_amount", 0.0) or 0.0)
        delta_avg = None
        pct_help2 = None
        if c_bsum is not None:
            comp_avg = float(c_bsum.get("avg_booking_amount", 0.0) or 0.0)
            delta_avg = avg_amt - comp_avg
            pct2 = ((avg_amt - comp_avg) / comp_avg * 100.0) if comp_avg else None
            pct_help2 = (f"Δ {pct2:.1f}% vs {comparison_options().get(compare_mode, '').lower()}" if pct2 is not None else "Δ n/a")
        UIComponents.currency_metric("Avg Booking Amount", avg_amt, "USD", delta_amount=delta_avg, help_text=pct_help2)

    with col4:
        if int(csum.get("entries", 0)) > 0:
            net = float(csum.get("net", 0.0) or 0.0)
            delta_net = None
            pct_help3 = None
            if c_csum is not None and int(c_csum.get("entries", 0)) > 0:
                comp_net = float(c_csum.get("net", 0.0) or 0.0)
                delta_net = net - comp_net
                pct3 = ((net - comp_net) / comp_net * 100.0) if comp_net else None
                pct_help3 = (f"Δ {pct3:.1f}% vs {comparison_options().get(compare_mode, '').lower()}" if pct3 is not None else "Δ n/a")
            UIComponents.currency_metric("Net Cash Flow", net, "USD", delta_amount=delta_net, help_text=pct_help3)
        else:
            UIComponents.metric_card("Net Cash Flow", "—", "no ledger data")

    # Bank Account Balances section
    UIComponents.section_header("Bank Account Balances", "Current balances across active accounts")
    try:
        balances = bank_service.balance_for_all_accounts(date.today())
        if balances:
            display_rows = [
                {
                    "Account": f"{b.get('name')} ({b.get('currency')})",
                    "Balance": f"{b.get('current_balance', 0.0):,.2f} {b.get('currency')}",
                }
                for b in balances
            ]
            st.table(display_rows)
        else:
            UIComponents.info_message("No bank accounts configured.")
    except Exception as e:
        error_handler.handle_error(e, user_message="Unable to load bank balances")

    st.divider()

    # Business Metrics Section (Leads & Conversions)
    UIComponents.section_header(
        "Business Metrics", "Lead generation and conversion tracking"
    )

    try:
        leads = analytics_service.leads_summary(
            start_date=base_start, end_date=base_end
        )
    except Exception as e:
        error_handler.handle_error(e, user_message="Unable to load leads summary")
        leads = {"total_leads": 0, "mql_count": 0, "sql_count": 0}

    comp_leads = None
    if comp_range:
        try:
            comp_leads = analytics_service.leads_summary(start_date=comp_range[0], end_date=comp_range[1])
        except Exception as e:
            error_handler.handle_error(e, user_message="Unable to load comparison leads summary")
            comp_leads = None

    total_leads = int(leads.get("total_leads", 0) or 0)
    mql_count = int(leads.get("mql_count", 0) or 0)
    sql_count = int(leads.get("sql_count", 0) or 0)
    mql_rate = (mql_count / total_leads * 100) if total_leads > 0 else 0.0
    sql_rate = (sql_count / max(mql_count, 1) * 100) if mql_count > 0 else 0.0

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        delta = None
        if comp_leads is not None:
            c_total = int(comp_leads.get("total_leads", 0) or 0)
            pct = ((total_leads - c_total) / c_total * 100.0) if c_total else None
            delta = f"{total_leads - c_total:+d}" + (f" ({pct:.1f}%)" if pct is not None else "")
        UIComponents.metric_card("Total Leads", str(total_leads), delta)

    with col2:
        delta = None
        help_txt = f"{mql_rate:.1f}% of leads"
        if comp_leads is not None:
            c_mql = int(comp_leads.get("mql_count", 0) or 0)
            pct = ((mql_count - c_mql) / c_mql * 100.0) if c_mql else None
            delta = f"{mql_count - c_mql:+d}" + (f" ({pct:.1f}%)" if pct is not None else "")
        UIComponents.metric_card("MQL", str(mql_count), delta, help_text=help_txt)

    with col3:
        delta = None
        help_txt = f"{sql_rate:.1f}% of MQLs"
        if comp_leads is not None:
            c_sql = int(comp_leads.get("sql_count", 0) or 0)
            pct = ((sql_count - c_sql) / c_sql * 100.0) if c_sql else None
            delta = f"{sql_count - c_sql:+d}" + (f" ({pct:.1f}%)" if pct is not None else "")
        UIComponents.metric_card("SQL", str(sql_count), delta, help_text=help_txt)

    with col4:
        # Conversion rate delta vs comparison
        delta_txt = None
        if comp_leads is not None:
            c_total = int(comp_leads.get("total_leads", 0) or 0)
            c_mql = int(comp_leads.get("mql_count", 0) or 0)
            c_rate = (c_mql / c_total * 100.0) if c_total > 0 else 0.0
            d = mql_rate - c_rate
            delta_txt = f"{d:+.1f}%"
        UIComponents.metric_card(
            "Conversion Rate", f"{mql_rate:.1f}%", delta_txt, help_text=f"{mql_count}/{total_leads}"
        )

    # UTM Breakdown
    try:
        utm = analytics_service.leads_by_utm(
            start_date=base_start, end_date=base_end
        )
    except Exception as e:
        error_handler.handle_error(e, user_message="Unable to load UTM breakdown")
        utm = {"by_source": [], "by_campaign": []}

    with st.expander("Lead UTM Breakdown", expanded=False):
        col_a, col_b = st.columns(2)
        with col_a:
            st.caption("By Source")
            if utm.get("by_source"):
                UIComponents.data_table(utm["by_source"])
            else:
                UIComponents.info_message("No UTM source data in this range.")
        with col_b:
            st.caption("By Campaign")
            if utm.get("by_campaign"):
                UIComponents.data_table(utm["by_campaign"])
            else:
                UIComponents.info_message("No UTM campaign data in this range.")

    st.divider()

    # Charts Section
    UIComponents.section_header(
        "Analytics Charts", "Sales (Bookings) vs. true Cash Flow"
    )

    # Daily Bookings Sales chart
    try:
        bookings_df = analytics_service.bookings_by_date_daily(
            start_date=base_start, end_date=base_end
        )
    except Exception as e:
        error_handler.handle_error(e, user_message="Unable to load bookings by date")
        bookings_df = pd.DataFrame(columns=["date", "total_amount", "total_guests", "bookings_count"])

    if bookings_df is not None and not bookings_df.empty:
        comp_df = None
        comp_label = comparison_options().get(compare_mode, "Comparison")
        if comp_range:
            try:
                comp_daily = analytics_service.bookings_by_date_daily(start_date=comp_range[0], end_date=comp_range[1])
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
        # Export comparison CSV with toggle for aligned vs actual
        if comp_range:
            try:
                actual_df = analytics_service.bookings_by_date_daily(start_date=comp_range[0], end_date=comp_range[1])

                export_mode = st.radio(
                    "Export comparison data",
                    options=["Aligned", "Actual"],
                    horizontal=True,
                    key="dashboard_export_mode",
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
        UIComponents.info_message("No bookings data yet — import in Settings → CSV Uploads or Airtable Backfill")

    # Daily Cash Flow chart (true ledger)
    try:
        cash_df = analytics_service.cash_ledger_by_date(
            start_date=base_start, end_date=base_end
        )
    except Exception as e:
        error_handler.handle_error(e, user_message="Unable to load cash ledger by date")
        cash_df = pd.DataFrame(columns=["date", "inflow", "outflow"])

    if cash_df is not None and not cash_df.empty:
        ChartComponents.cash_flow_chart(
            cash_df[["date", "inflow", "outflow"]], title="Daily Cash Flow"
        )
    else:
        UIComponents.info_message("No cash ledger data yet — add entries in Cash Ledger or import via Settings")

    # Note: We no longer rely on aggregated cash_flow_metrics. Sales and cash flow are sourced separately.

except Exception:
    st.error(traceback.format_exc())
