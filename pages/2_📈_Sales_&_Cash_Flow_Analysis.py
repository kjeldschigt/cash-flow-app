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
    # Sidebar filters
    with st.sidebar:
        st.header("Analysis Filters")

        # Date range selector
        date_range = st.selectbox(
            "Date Range",
            [
                "Last 7 Days",
                "Last 30 Days",
                "Last 90 Days",
                "Last 6 Months",
                "YTD",
                "Last 12 Months",
            ],
            index=1,
        )

        # Currency filter
        currency_filter = st.selectbox("Currency", ["All", "USD", "CRC"])

        # Analysis type
        analysis_type = st.selectbox(
            "Analysis Type",
            ["Overview", "Detailed Breakdown", "Trends", "Comparisons"],
            index=0,
        )

    # Convert date range to actual dates
    today = datetime.now().date()
    if date_range == "Last 7 Days":
        start_date = today - timedelta(days=7)
    elif date_range == "Last 30 Days":
        start_date = today - timedelta(days=30)
    elif date_range == "Last 90 Days":
        start_date = today - timedelta(days=90)
    elif date_range == "Last 6 Months":
        start_date = today - timedelta(days=180)
    elif date_range == "YTD":
        start_date = datetime(today.year, 1, 1).date()
    elif date_range == "Last 12 Months":
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)

    # Key Performance Metrics
    UIComponents.section_header(
        "Key Performance Metrics", "Overview of sales and cash flow performance"
    )

    # Get cash flow metrics using service
    cash_flow_metrics = analytics_service.get_cash_flow_metrics(
        start_date=start_date, end_date=today
    )

    if cash_flow_metrics:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            UIComponents.currency_metric(
                "Total Revenue",
                cash_flow_metrics.total_sales_usd,
                "USD",
                delta=getattr(cash_flow_metrics, "revenue_growth", 0),
            )

        with col2:
            UIComponents.currency_metric(
                "Total Costs",
                cash_flow_metrics.total_costs_usd,
                "USD",
                delta=getattr(cash_flow_metrics, "cost_growth", 0),
            )

        with col3:
            UIComponents.currency_metric(
                "Net Cash Flow",
                cash_flow_metrics.net_cash_flow,
                "USD",
                delta=getattr(cash_flow_metrics, "net_growth", 0),
            )

        with col4:
            UIComponents.metric_card(
                "Profit Margin", f"{cash_flow_metrics.profit_margin:.1f}%", "margin"
            )

        st.divider()

        # Analysis Type Specific Content
        if analysis_type == "Overview":
            # Daily Trends Chart
            UIComponents.section_header("Daily Trends", "Recent daily performance")

            daily_trends = analytics_service.get_daily_trends(
                start_date=start_date, end_date=today
            )

            if daily_trends:
                ChartComponents.cash_flow_chart(
                    daily_trends, title="Daily Cash Flow Trend"
                )

        elif analysis_type == "Detailed Breakdown":
            # Revenue and Cost Breakdown
            UIComponents.section_header(
                "Revenue & Cost Breakdown", "Detailed financial analysis"
            )

            col1, col2 = st.columns(2)

            with col1:
                # Revenue breakdown by source
                revenue_breakdown = payment_service.get_revenue_breakdown(
                    start_date=start_date, end_date=today
                )

                if revenue_breakdown:
                    ChartComponents.pie_chart(
                        revenue_breakdown, title="Revenue by Source"
                    )

            with col2:
                # Cost breakdown by category
                cost_breakdown = analytics_service.get_cost_breakdown(
                    start_date=start_date, end_date=today
                )

                if cost_breakdown:
                    ChartComponents.category_breakdown_chart(
                        cost_breakdown, title="Costs by Category"
                    )

        elif analysis_type == "Trends":
            # Monthly Trends
            UIComponents.section_header(
                "Monthly Trends", "Long-term performance analysis"
            )

            monthly_summary = analytics_service.get_monthly_summary(
                start_date.year,
                start_date.month
            )

            if monthly_summary:
                ChartComponents.monthly_trend_chart(
                    monthly_summary, title="Monthly Revenue vs Costs Trend"
                )

        elif analysis_type == "Comparisons":
            # Year-over-Year Comparisons
            UIComponents.section_header(
                "Performance Comparisons", "Period-over-period analysis"
            )

            yoy_comparison = analytics_service.get_yoy_comparison(
                start_date=start_date, end_date=today
            )

            if yoy_comparison:
                col1, col2, col3 = st.columns(3)

                with col1:
                    UIComponents.currency_metric(
                        "Revenue Growth",
                        yoy_comparison.current_revenue,
                        "USD",
                        delta=getattr(yoy_comparison, "revenue_growth_pct", 0),
                    )

                with col2:
                    UIComponents.currency_metric(
                        "Cost Change",
                        yoy_comparison.current_costs,
                        "USD",
                        delta=getattr(yoy_comparison, "cost_growth_pct", 0),
                    )

                with col3:
                    UIComponents.currency_metric(
                        "Net Change",
                        yoy_comparison.current_net,
                        "USD",
                        delta=getattr(yoy_comparison, "net_growth_pct", 0),
                    )

    else:
        UIComponents.empty_state(
            "No Financial Data",
            f"No sales or cash flow data available for {date_range.lower()}. Add some transactions to see analytics.",
        )

except Exception:
    st.error(traceback.format_exc())
