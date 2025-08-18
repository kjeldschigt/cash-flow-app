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

# Add the src directory to the Python path
src_path = os.path.join(os.path.dirname(__file__), '..', 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import services and utilities
from src.services.storage_service import StorageService
from src.security.auth import AuthManager
from src.utils.data_manager import calculate_metrics, get_date_range_data
from src.services.error_handler import handle_error
from src.utils.theme_manager import apply_theme
from components.ui_helpers import render_metric_grid, create_section_header, render_chart_container

# New clean architecture imports
from src.container import get_container
from src.ui.auth import AuthComponents
from src.ui.components import UIComponents
from src.services.error_handler import ErrorHandler

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
        pdf.set_font('Arial', 'B', 16)
        pdf.cell(0, 10, title, 0, 1, 'C')
        return pdf.output(dest='S').encode('latin-1')
    except ImportError:
        return None

# Check authentication using new auth system
if not AuthComponents.require_authentication():
    st.stop()

# Apply theme
apply_theme('light')

# Get services from container
container = get_container()
analytics_service = container.get_analytics_service()
error_handler = get_error_handler()

st.title("🏠 Dashboard")

try:
    # Sidebar filters
    with st.sidebar:
        st.header("Dashboard Filters")
        
        # Date range selector
        range_select = st.selectbox(
            "Date Range",
            ["Last 7 Days", "Last 30 Days", "Last 3 Months", "Last 6 Months", "Last 12 Months", "YTD"],
            index=4,
            key="dashboard_range"
        )
        
        # Currency filter
        currency_filter = st.selectbox("Currency", ["All", "USD", "CRC"])
    
    # Key Metrics Section
    UIComponents.section_header("Key Metrics", f"Performance overview for {range_select.lower()}")
    
    # Get analytics data using service
    date_range = _get_date_range_from_selection(range_select)
    cash_flow_metrics = analytics_service.get_cash_flow_metrics(
        start_date=date_range['start'],
        end_date=date_range['end']
    )
    
    if cash_flow_metrics:
        # Display metrics using new UI components
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            UIComponents.currency_metric(
                "Total Revenue", 
                cash_flow_metrics.total_revenue, 
                "USD"
            )
        
        with col2:
            UIComponents.currency_metric(
                "Total Costs", 
                cash_flow_metrics.total_costs, 
                "USD"
            )
        
        with col3:
            UIComponents.currency_metric(
                "Net Cash Flow", 
                cash_flow_metrics.net_cash_flow, 
                "USD",
                delta=cash_flow_metrics.net_cash_flow
            )
        
        with col4:
            UIComponents.metric_card(
                "Transactions", 
                str(cash_flow_metrics.transaction_count),
                "total"
            )
        
        st.divider()
        
        # Business Metrics Section
        UIComponents.section_header("Business Metrics", "Lead generation and conversion tracking")
        
        # Get business metrics using service
        business_metrics = analytics_service.get_business_metrics(
            start_date=date_range['start'],
            end_date=date_range['end']
        )
        
        if business_metrics:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                UIComponents.metric_card(
                    "Total Leads", 
                    str(business_metrics.total_leads),
                    "this period"
                )
            
            with col2:
                UIComponents.metric_card(
                    "MQL Rate", 
                    f"{business_metrics.mql_rate:.1f}%",
                    f"{business_metrics.mql}/{business_metrics.total_leads}"
                )
            
            with col3:
                UIComponents.metric_card(
                    "SQL Rate", 
                    f"{business_metrics.sql_rate:.1f}%",
                    f"{business_metrics.sql}/{business_metrics.mql}"
                )
            
            with col4:
                UIComponents.currency_metric(
                    "Total Costs", 
                    business_metrics.total_costs, 
                    "USD"
                )
        
        st.divider()
        
        # Charts Section
        UIComponents.section_header("Analytics Charts", "Visual insights into cash flow trends")
        
        # Cash Flow Trend Chart
        daily_trends = analytics_service.get_daily_trends(
            start_date=date_range['start'],
            end_date=date_range['end']
        )
        
        if daily_trends:
            ChartComponents.cash_flow_chart(
                daily_trends,
                title="Daily Cash Flow Trend"
            )
        
        # Monthly Summary Chart
        monthly_summary = analytics_service.get_monthly_summary(
            start_date=date_range['start'],
            end_date=date_range['end']
        )
        
        if monthly_summary:
            col1, col2 = st.columns(2)
            
            with col1:
                ChartComponents.monthly_trend_chart(
                    monthly_summary,
                    title="Monthly Revenue vs Costs"
                )
            
            with col2:
                ChartComponents.category_breakdown_chart(
                    monthly_summary,
                    title="Cost Breakdown by Category"
                )
    
    else:
        UIComponents.empty_state(
            "No Data Available",
            f"No financial data found for {range_select.lower()}. Add some transactions to see insights."
        )

except Exception as e:
    error_result = error_handler.handle_exception(e, "dashboard_load")
    UIComponents.error_message(error_result['message'])
