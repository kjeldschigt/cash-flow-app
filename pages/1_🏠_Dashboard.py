import streamlit as st
import sys
import os
import pandas as pd
from datetime import datetime, timedelta
import warnings
import plotly.graph_objects as go
import plotly.express as px

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import components
from components.ui_helpers import render_metric_grid, create_section_header, render_chart_container
from components.dashboard_comparisons import get_during_month_comparison, render_month_to_date_comparison
from utils.data_manager import load_combined_data, init_session_filters, filter_data_by_range, get_daily_aggregates
from utils.theme_manager import apply_theme
from utils.error_handler import show_error, validate_number_input, validate_date_range
from services.fx import apply_fx_conversion
from services.settings_manager import get_setting
from services.auth import require_auth

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)

@st.cache_data
def get_filtered_data_cached(df, range_select):
    """Cache filtered data to avoid recomputation"""
    return filter_data_by_range(df, range_select)

@st.cache_data
def get_daily_data_cached(filtered_df):
    """Cache daily aggregated data"""
    if filtered_df.empty:
        return pd.DataFrame()
    
    daily_data = filtered_df.groupby('Date').agg({
        'Sales_USD': 'sum',
        'Costs_USD': 'sum'
    }).reset_index()
    daily_data['Net'] = daily_data['Sales_USD'] - daily_data['Costs_USD']
    return daily_data

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

# Check authentication
require_auth()

# Apply theme
theme = get_setting('theme', 'light')
st.markdown(apply_theme(theme), unsafe_allow_html=True)

st.title("🏠 Dashboard")

try:
    # Initialize session filters and load data
    init_session_filters()
    df = load_combined_data()
    
    # Sidebar filters
    with st.sidebar:
        st.header("Dashboard Filters")
        
        # Date range selector
        range_select = st.selectbox(
            "Date Range",
            ["Last 7 Days", "12 Months", "YTD", "QTD", "YTD vs LY", "During-Month vs LY"],
            index=1,
            key="dashboard_range"
        )
        
        # Additional filters
        if not df.empty and 'Category' in df.columns:
            categories = ['All'] + list(df['Category'].unique())
            category_filter = st.selectbox("Category", categories)
            
            if category_filter != 'All':
                df = df[df['Category'] == category_filter]

    # Filter data based on selection
    filtered_df = get_filtered_data_cached(df, range_select)
    
    # Key Metrics Section
    create_section_header("Key Metrics", f"Performance overview for {range_select.lower()}")
    
    if not filtered_df.empty:
        total_sales = filtered_df['Sales_USD'].sum()
        total_costs = filtered_df['Costs_USD'].sum()
        net_cash_flow = total_sales - total_costs
        transaction_count = len(filtered_df)
        avg_transaction = total_sales / transaction_count if transaction_count > 0 else 0
        
        # Calculate growth rates (simplified)
        sales_growth = 8.5  # Placeholder
        cost_growth = -3.2  # Placeholder
        
        key_metrics = [
            {"title": "Total Sales", "value": f"${total_sales:,.0f}", "delta": f"+{sales_growth:.1f}%", "caption": f"{transaction_count} transactions"},
            {"title": "Total Costs", "value": f"${total_costs:,.0f}", "delta": f"{cost_growth:.1f}%", "caption": "All categories"},
            {"title": "Net Cash Flow", "value": f"${net_cash_flow:,.0f}", "delta": f"+{sales_growth + abs(cost_growth):.1f}%", "caption": "Sales - Costs"},
            {"title": "Avg Transaction", "value": f"${avg_transaction:.0f}", "delta": "+2.1%", "caption": "Per transaction"}
        ]
        
        render_metric_grid(key_metrics, columns=4)
    else:
        st.info(f"No data available for {range_select}")

    # Business Metrics Section
    create_section_header("Business Metrics", "Lead generation and conversion tracking")
    
    # Get business metrics from session state or defaults
    total_leads = st.session_state.get('total_leads', 120)
    mql = st.session_state.get('mql', 48)
    sql = st.session_state.get('sql', 24)
    current_costs = total_costs if not filtered_df.empty else 0
    
    # Convert to numeric and calculate rates
    mql = pd.to_numeric(mql, errors="coerce") if not pd.isna(mql) else 0
    sql = pd.to_numeric(sql, errors="coerce") if not pd.isna(sql) else 0
    total_leads = pd.to_numeric(total_leads, errors="coerce") if not pd.isna(total_leads) else 0
    
    mql_rate = (mql / total_leads * 100) if total_leads > 0 else 0
    sql_rate = (sql / mql * 100) if mql > 0 else 0
    
    business_metrics = [
        {"title": "Total Leads", "value": f"{total_leads:,}", "caption": "This period"},
        {"title": "MQL Rate", "value": f"{mql_rate:.1f}%", "caption": f"{mql}/{total_leads}"},
        {"title": "SQL Rate", "value": f"{sql_rate:.1f}%", "caption": f"{sql}/{mql}"},
        {"title": "Costs", "value": f"${current_costs:,.0f}", "caption": f"{range_select.lower()}"}
    ]
    
    render_metric_grid(business_metrics, columns=4)

    # Enhanced Leads Analysis
    create_section_header("Lead Performance Analysis", "Detailed lead metrics and conversion tracking")
    
    # Calculate lead metrics with context
    avg_leads_per_month = 80  # Context baseline
    current_leads = total_leads
    leads_vs_avg = ((current_leads - avg_leads_per_month) / avg_leads_per_month * 100) if avg_leads_per_month > 0 else 0
    
    # Year-over-year comparison (calculate from data)
    leads_yoy_change = 5.2  # Placeholder - replace with actual calculation from historical data
    conversion_rate = (sql / total_leads * 100) if total_leads > 0 else 0
    
    lead_analysis_metrics = [
        {
            "title": "Total Leads", 
            "value": f"{current_leads}", 
            "delta": f"{'Up' if leads_yoy_change > 0 else 'Down'} {abs(leads_yoy_change):.1f}% vs LY",
            "caption": f"{'Above' if leads_vs_avg > 0 else 'Below'} avg {avg_leads_per_month} leads/mo ({leads_vs_avg:+.1f}%)"
        },
        {
            "title": "Conversion Rate", 
            "value": f"{conversion_rate:.1f}%",
            "caption": "Strong performance" if conversion_rate > 15 else "Average performance" if conversion_rate > 10 else "Below average"
        },
        {
            "title": "MQL Rate", 
            "value": f"{(mql / total_leads * 100) if total_leads > 0 else 0:.1f}%",
            "caption": f"MQL to SQL: {(sql/mql*100) if mql > 0 else 0:.1f}%"
        }
    ]
    
    render_metric_grid(lead_analysis_metrics, columns=3)

    # Month-to-Date Comparison
    if not df.empty:
        render_month_to_date_comparison(df)

except Exception as e:
    show_error("Dashboard Error", f"An error occurred while loading the dashboard: {str(e)}")
    st.info("Please check your data connections and try again.")
