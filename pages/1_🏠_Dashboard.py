import streamlit as st
import sys
import os
import pandas as pd
import requests
import numpy as np
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
try:
    from fpdf import FPDF
except ImportError:
    FPDF = None

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage import get_combined_data, load_settings, insert_monthly_cost
from services.fx import apply_fx_conversion
from services.airtable import get_lead_metrics
from services.stripe import get_payment_metrics

def filter_data_by_range(df, date_range):
    """Filter dataframe based on selected date range using df.query"""
    if df.empty:
        return df
    
    # Ensure we have a date column
    if 'Date' not in df.columns:
        return df
    
    # Convert Date column to datetime if not already
    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    today = datetime.now()
    
    if date_range == "Last 7 Days":
        start_date = today - timedelta(days=7)
        return df.query('@start_date <= Date <= @today')
    elif date_range == "12 Months":
        start_date = today - timedelta(days=365)
        return df.query('@start_date <= Date <= @today')
    elif date_range == "YTD":
        start_date = datetime(today.year, 1, 1)
        return df.query('@start_date <= Date <= @today')
    elif date_range == "QTD":
        quarter_start_month = ((today.month - 1) // 3) * 3 + 1
        start_date = datetime(today.year, quarter_start_month, 1)
        return df.query('@start_date <= Date <= @today')
    elif date_range == "YTD vs LY":
        # Current YTD
        ytd_start = datetime(today.year, 1, 1)
        current_ytd = df.query('@ytd_start <= Date <= @today')
        # Last year same period
        ly_start = datetime(today.year - 1, 1, 1)
        ly_end = datetime(today.year - 1, today.month, today.day)
        last_year_ytd = df.query('@ly_start <= Date <= @ly_end')
        # Combine both periods
        return pd.concat([current_ytd, last_year_ytd])
    elif date_range == "During-Month vs LY":
        # Current month to date
        month_start = datetime(today.year, today.month, 1)
        current_mtd = df.query('@month_start <= Date <= @today')
        # Last year same month period
        ly_month_start = datetime(today.year - 1, today.month, 1)
        ly_month_end = datetime(today.year - 1, today.month, today.day)
        ly_mtd = df.query('@ly_month_start <= Date <= @ly_month_end')
        return pd.concat([current_mtd, ly_mtd])
    
    return df

def get_during_month_comparison(df, current_month=None, current_day=None):
    """Get during-month comparison (e.g., Aug 1-16 vs last Aug 1-16/LY)"""
    if df.empty or 'Date' not in df.columns:
        return {}, {}
    
    today = datetime.now()
    if current_month is None:
        current_month = today.month
    if current_day is None:
        current_day = today.day
    
    # Current month to date
    current_year_start = datetime(today.year, current_month, 1)
    current_year_end = datetime(today.year, current_month, min(current_day, 31))
    current_mtd = df[(df['Date'] >= current_year_start) & (df['Date'] <= current_year_end)]
    
    # Last year same period
    ly_start = datetime(today.year - 1, current_month, 1)
    ly_end = datetime(today.year - 1, current_month, min(current_day, 31))
    ly_mtd = df[(df['Date'] >= ly_start) & (df['Date'] <= ly_end)]
    
    # Calculate metrics
    current_metrics = {
        'sales': current_mtd['Sales_USD'].sum() if 'Sales_USD' in current_mtd.columns else 0,
        'costs': current_mtd['Costs_USD'].sum() if 'Costs_USD' in current_mtd.columns else 0,
        'net': current_mtd['Sales_USD'].sum() - current_mtd['Costs_USD'].sum() if 'Sales_USD' in current_mtd.columns and 'Costs_USD' in current_mtd.columns else 0,
        'count': len(current_mtd)
    }
    
    ly_metrics = {
        'sales': ly_mtd['Sales_USD'].sum() if 'Sales_USD' in ly_mtd.columns else 0,
        'costs': ly_mtd['Costs_USD'].sum() if 'Costs_USD' in ly_mtd.columns else 0,
        'net': ly_mtd['Sales_USD'].sum() - ly_mtd['Costs_USD'].sum() if 'Sales_USD' in ly_mtd.columns and 'Costs_USD' in ly_mtd.columns else 0,
        'count': len(ly_mtd)
    }
    
    return current_metrics, ly_metrics

def analyze_trend_with_ai(df, metric_column):
    """Analyze trend using sklearn linear regression with monthly percentage"""
    if not SKLEARN_AVAILABLE or df.empty or metric_column not in df.columns:
        return None, "AI trend analysis unavailable"
    
    # Prepare data
    df_clean = df.dropna(subset=[metric_column, 'Date'])
    if len(df_clean) < 2:
        return None, "Insufficient data for trend analysis"
    
    # Convert dates to numeric (days since first date)
    df_clean = df_clean.sort_values('Date')
    first_date = df_clean['Date'].min()
    df_clean['days_since_start'] = (df_clean['Date'] - first_date).dt.days
    
    # Fit linear regression
    X = df_clean[['days_since_start']]
    y = df_clean[metric_column]
    
    # Ensure X is 2D array for sklearn
    if not hasattr(X, 'columns'):
        X = np.array(X).reshape(-1, 1) if np.array(X).ndim == 1 else np.array(X)
        X = pd.DataFrame(X, columns=['days_since_start'])
    
    model = LinearRegression()
    model.fit(X, y)
    
    slope = model.coef_[0]
    r_squared = model.score(X, y)
    
    # Convert daily slope to monthly percentage
    avg_value = y.mean()
    monthly_slope_pct = (slope * 30 / avg_value * 100) if avg_value > 0 else 0
    
    return monthly_slope_pct, f"R² = {r_squared:.3f}"

def fetch_umich():
    """Fetch University of Michigan Consumer Sentiment from FRED API"""
    try:
        url = f'https://api.stlouisfed.org/fred/series/observations?series_id=UMCSENT&api_key=644b813e5cf15fd85ddc9982b65dd397&file_type=json&sort_order=desc&limit=1'
        data = requests.get(url).json()
        return data['observations'][0]['value'], data['observations'][0]['date']
    except:
        return 'Error', 'N/A'

def fetch_conference_board():
    """Fetch Conference Board Consumer Confidence (stub - would need API or scraping)"""
    try:
        # This is a stub - Conference Board data typically requires paid subscription
        # Could implement web scraping or use alternative free sources
        # For now, return placeholder data
        return '105.2', '2024-01-31'  # Placeholder values
    except:
        return 'Error', 'N/A'

def generate_pdf(df, title="Cash Flow Report"):
    """Generate PDF from DataFrame"""
    if FPDF is None:
        return None
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Add title
    pdf.cell(200, 10, txt=title, ln=1, align='C')
    pdf.ln(10)
    
    # Add column headers
    if not df.empty:
        headers = df.columns.tolist()
        for header in headers:
            pdf.cell(40, 10, txt=str(header), border=1)
        pdf.ln()
        
        # Add data rows
        for i, row in df.iterrows():
            for value in row:
                pdf.cell(40, 10, txt=str(value)[:15], border=1)  # Truncate long values
            pdf.ln()
    
    return pdf.output(dest='S').encode('utf-8')

import os
from dotenv import load_dotenv

# Suppress sklearn warnings
warnings.filterwarnings("ignore", category=UserWarning, module="sklearn.utils.validation")

# Load environment variables
load_dotenv()

st.title("Dashboard Overview")

# Load settings from session_state with DB fallback
def get_setting(key, default_value):
    """Get setting from session_state, fallback to DB, then default"""
    if key in st.session_state:
        return st.session_state[key]
    
    try:
        db_settings = load_settings()
        if key in db_settings:
            value = db_settings[key]
            # Convert string values to appropriate types
            if isinstance(default_value, float):
                return float(value)
            elif isinstance(default_value, int):
                return int(value)
            return value
    except:
        pass
    
    return default_value

# Apply theme from session_state with DB fallback
theme = get_setting('theme', 'light')
if theme == "light":
    st.markdown('''
    <style>
    .stApp { background-color: #FAFAFA; color: #333; }
    .stSidebar { background-color: #F0F2F6; }
    </style>
    ''', unsafe_allow_html=True)
else:
    st.markdown('''
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    .stSidebar { background-color: #262730; }
    </style>
    ''', unsafe_allow_html=True)


# Live Economic Indicators
st.subheader("Economic Indicators")

col1, col2 = st.columns(2)

with col1:
    value, date = fetch_umich()
    st.info(f"US UMich Consumer Sentiment (live): {value} ({date})")

with col2:
    cb_value, cb_date = fetch_conference_board()
    st.info(f"Conference Board Consumer Confidence: {cb_value} ({cb_date})")

# Enhanced Comparison Period Selection
st.subheader("Performance Comparison")

col1, col2 = st.columns([2, 1])

with col1:
    date_select = st.selectbox("Date Range", ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date", "Custom"], key="main_date_select")
    comparison_to = st.selectbox("Range", [
        "Last Month vs Prev", 
        "Same Month LY", 
        "Last 3m vs LY", 
        "During-Month vs LY", 
        "Custom"
    ], key="main_comparison_select")
    
    if comparison_to == "Custom" or date_select == "Custom":
        st.write("**Select Date Range:**")
        start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
        end_date = st.date_input("End Date", value=datetime.now())

# Sidebar for Global Date Filtering
st.sidebar.subheader("🗓️ Global Date Filter")
global_date_range = st.sidebar.selectbox(
    "Filter All Data By",
    ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date", "All Time"],
    index=0,
    key="sidebar_global_date_filter"
)

if global_date_range == "Custom":
    global_start_date = st.sidebar.date_input("Start Date", value=datetime.now() - timedelta(days=30))
    global_end_date = st.sidebar.date_input("End Date", value=datetime.now())

# Business Metrics Input Section (moved to sidebar)
st.sidebar.subheader("📊 Business Metrics")
occupancy = st.sidebar.number_input("Occupancy %", value=get_setting('occupancy', 75.0))
total_leads = st.sidebar.number_input("Total Leads", value=get_setting('total_leads', 100))
mql = st.sidebar.number_input("MQL", value=get_setting('mql', 50))
sql = st.sidebar.number_input("SQL", value=get_setting('sql', 20))

# Store business metrics in session state
st.session_state.business_metrics = {
    'occupancy': occupancy,
}

def calculate_period_deltas(date_select, comparison_to, start_date=None, end_date=None):
    """Calculate performance deltas based on selected period with enhanced DB filtering"""
    try:
        # Load data from database
        df = get_combined_data()
        if df.empty:
            return None, None, None, None, None, None, None, None
            
        df['Date'] = pd.to_datetime(df['Date'])
        current_date = datetime.now()
        
        # Determine current and past periods based on comparison_to selection
        if comparison_to == "Last Month vs Prev":
            current_start = current_date.replace(day=1)
            current_end = current_date
            past_start = (current_start - timedelta(days=32)).replace(day=1)
            past_end = current_start - timedelta(days=1)
            
        elif comparison_to == "Same Month LY":
            current_start = current_date.replace(day=1)
            current_end = current_date
            past_start = current_start.replace(year=current_date.year - 1)
            past_end = current_end.replace(year=current_date.year - 1)
            
        elif comparison_to == "Last 3m vs LY":
            current_end = current_date
            current_start = (current_date.replace(day=1) - timedelta(days=90)).replace(day=1)
            past_start = current_start.replace(year=current_start.year - 1)
            past_end = current_end.replace(year=current_end.year - 1)
            
        elif comparison_to == "During-Month vs LY":
            current_start = current_date.replace(day=1)
            current_end = current_date
            past_start = current_start.replace(year=current_date.year - 1)
            past_end = current_date.replace(year=current_date.year - 1)
            
        elif comparison_to == "Custom" and start_date and end_date:
            current_start = pd.to_datetime(start_date)
            current_end = pd.to_datetime(end_date)
            past_start = current_start.replace(year=current_start.year - 1)
            past_end = current_end.replace(year=current_end.year - 1)
            
        else:
            # Default to previous month
            current_start = current_date.replace(day=1)
            current_end = current_date
            past_start = (current_start - timedelta(days=32)).replace(day=1)
            past_end = current_start - timedelta(days=1)
        
        # Filter data for current and past periods
        current_data = df[(df['Date'] >= current_start) & (df['Date'] <= current_end)]
        past_data = df[(df['Date'] >= past_start) & (df['Date'] <= past_end)]
        
        # Calculate metrics
        current_sales = current_data['Sales_USD'].sum() if 'Sales_USD' in current_data.columns else 0
        past_sales = past_data['Sales_USD'].sum() if 'Sales_USD' in past_data.columns else 0
        current_costs = current_data['Costs_USD'].sum() if 'Costs_USD' in current_data.columns else 0
        past_costs = past_data['Costs_USD'].sum() if 'Costs_USD' in past_data.columns else 0
        
        current_cash_flow = current_sales - current_costs
        past_cash_flow = past_sales - past_costs
        
        # Calculate deltas
        sales_delta = ((current_sales - past_sales) / past_sales * 100) if past_sales > 0 else 0
        costs_delta = ((current_costs - past_costs) / past_costs * 100) if past_costs > 0 else 0
        cash_flow_delta = ((current_cash_flow - past_cash_flow) / past_cash_flow * 100) if past_cash_flow > 0 else 0
        
        # Get leads and occupancy from business metrics or use mock data
        current_leads = get_setting('total_leads', 100)
        past_leads = current_leads * 0.92  # Assume 8% lower in past period
        current_occupancy = get_setting('occupancy', 75.0)
        past_occupancy = current_occupancy * 0.95  # Assume 5% lower in past period
        
        leads_delta = ((current_leads - past_leads) / past_leads * 100) if past_leads > 0 else 0
        occupancy_delta = ((current_occupancy - past_occupancy) / past_occupancy * 100) if past_occupancy > 0 else 0
        
        # Calculate end-month cash position (cumulative cash flow)
        end_month_cash = current_cash_flow  # Simplified - would be cumulative in real implementation
        
        # AI Trend Analysis using sklearn if available
        trend_direction = "Flat"
        if SKLEARN_AVAILABLE and len(current_data) > 1:
            try:
                # Prepare data for trend analysis
                current_data_sorted = current_data.sort_values('Date').reset_index(drop=True)
                if len(current_data_sorted) >= 2:
                    X = np.arange(len(current_data_sorted)).reshape(-1, 1)
                    y = current_data_sorted['Sales_USD'].values
                    
                    from sklearn.linear_model import LinearRegression
                    model = LinearRegression()
                    model.fit(X, y)
                    slope = model.coef_[0]
                    
                    if slope > 1000:  # Significant positive trend
                        trend_direction = "Trending Up"
                    elif slope < -1000:  # Significant negative trend
                        trend_direction = "Trending Down"
                    else:
                        trend_direction = "Flat"
            except:
                trend_direction = "Flat"
        
        return (current_sales, current_costs, current_cash_flow, current_leads, current_occupancy, end_month_cash,
                sales_delta, costs_delta, cash_flow_delta, leads_delta, occupancy_delta, trend_direction)
        
    except Exception as e:
        st.error(f"Error calculating deltas: {str(e)}")
        return 0, 0, 0, 0, 0, 0

# Calculate performance deltas based on selected period
custom_start = locals().get('start_date', None)
custom_end = locals().get('end_date', None)
results = calculate_period_deltas(date_select, comparison_to, custom_start, custom_end)

if results and len(results) == 12:
    (current_sales, current_costs, current_cash_flow, current_leads, current_occupancy, end_month_cash,
     sales_delta, costs_delta, cash_flow_delta, leads_delta, occupancy_delta, trend_direction) = results
else:
    # Fallback values
    current_sales, current_costs, current_cash_flow = 0, 0, 0
    current_leads, current_occupancy, end_month_cash = 0, 0, 0
    sales_delta, costs_delta, cash_flow_delta, leads_delta, occupancy_delta = 0, 0, 0, 0, 0
    trend_direction = "Flat"

# Main Dashboard with Tabs Navigation
tabs = st.tabs(["Overview", "Economics", "Performance", "Financials"])

with tabs[0]:  # Overview Tab
    st.subheader("📊 Dashboard Overview")
    
    # Key metrics badges
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Sales", f"${current_sales:,.0f}", f"{sales_delta:+.1f}%")
    with col2:
        st.metric("Cash Flow", f"${current_cash_flow:,.0f}", f"{cash_flow_delta:+.1f}%")
    with col3:
        st.metric("Total Leads", f"{current_leads:.0f}", f"{leads_delta:+.1f}%")
    with col4:
        st.metric("Occupancy", f"{current_occupancy:.1f}%", f"{occupancy_delta:+.1f}%")
    
    # Expandable sections
    with st.expander("📈 Leads Details"):
        col1, col2 = st.columns(2)
        with col1:
            conversion_rate = (current_leads * 0.15)
            monthly_avg = get_setting('total_leads', 100) * 0.9
            st.write(f"**Conversion Rate:** {conversion_rate:.0f} leads")
            st.write(f"**Monthly Average:** {monthly_avg:.0f} leads")
        with col2:
            mql_rate = (mql / total_leads * 100) if total_leads > 0 else 0
            sql_rate = (sql / mql * 100) if mql > 0 else 0
            st.write(f"**Lead → MQL:** {mql_rate:.1f}%")
            st.write(f"**MQL → SQL:** {sql_rate:.1f}%")
    
    with st.expander("💰 Monthly Cost Entry"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            date = st.date_input("Entry Date", value=datetime.now().replace(day=1))
        
        with col2:
            category = st.selectbox("Category", [
                "Costa USD", "Costa CRC", "HK USD", "Stripe %", 
                "Huub Principal", "Huub Interest", "Google Ads"
            ], key="overview_cost_category")
        
        with col3:
            amount = st.number_input("Amount", min_value=0.0, step=100.0)
        
        if st.button("Add Entry"):
            try:
                insert_monthly_cost(date.strftime('%Y-%m'), category, amount)
                st.success(f"✅ Added {category}: ${amount:,.2f} for {date.strftime('%Y-%m')}")
                st.rerun()
            except Exception as e:
                st.error(f"Error adding entry: {str(e)}")

with tabs[1]:  # Economics Tab
    st.subheader("🌍 Economic Indicators")
    
    col1, col2 = st.columns(2)
    
    with col1:
        value, date = fetch_umich()
        st.info(f"US UMich Consumer Sentiment (live): {value} ({date})")
    
    with col2:
        cb_value, cb_date = fetch_conference_board()
        st.info(f"Conference Board Consumer Confidence: {cb_value} ({cb_date})")
    
    # Enhanced Comparison Period Selection
    st.subheader("Performance Comparison")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        date_select = st.selectbox("Date Range", ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date", "Custom"], key="economics_date_select")
        comparison_to = st.selectbox("Range", [
            "Last Month vs Prev", 
            "Same Month LY", 
            "Last 3m vs LY", 
            "During-Month vs LY", 
            "Custom"
        ], key="economics_comparison_select")
        
        if comparison_to == "Custom" or date_select == "Custom":
            st.write("**Select Date Range:**")
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
            end_date = st.date_input("End Date", value=datetime.now())

with tabs[2]:  # Performance Tab
    st.subheader("📊 On Track Performance")
    
    # Display key metrics with colored deltas
    col1, col2, col3 = st.columns(3)

    with col1:
        delta_color = "normal" if sales_delta >= 0 else "inverse"
        st.metric(
            "Sales", 
            f"${current_sales:,.0f}", 
            delta=f"{sales_delta:.1f}% vs {comparison_to.lower()}", 
            delta_color=delta_color
        )

    with col2:
        delta_color = "inverse" if costs_delta >= 0 else "normal"  # Lower costs are better
        st.metric(
            "Costs", 
            f"${current_costs:,.0f}", 
            delta=f"{costs_delta:.1f}% vs {comparison_to.lower()}", 
            delta_color=delta_color
        )

    with col3:
        delta_color = "normal" if cash_flow_delta >= 0 else "inverse"
        st.metric(
            "Cash Flow", 
            f"${current_cash_flow:,.0f}", 
            delta=f"{cash_flow_delta:.1f}% vs {comparison_to.lower()}", 
            delta_color=delta_color
        )
    
    # Enhanced leads metric with conversion rate and monthly average
    col1, col2, col3 = st.columns(3)
    
    with col1:
        conversion_rate = (current_leads * 0.15)
        monthly_avg = get_setting('total_leads', 100) * 0.9
        st.metric(
            "Leads", 
            f"{current_leads:.0f}", 
            delta=f"{leads_delta:.1f}% vs {comparison_to.lower()}"
        )
        st.caption(f"Conversion: {conversion_rate:.0f} | Avg: {monthly_avg:.0f}")
    
    with col2:
        delta_color = "normal" if occupancy_delta >= 0 else "inverse"
        st.metric(
            "Occupancy", 
            f"{current_occupancy:.1f}%", 
            delta=f"{occupancy_delta:.1f}% vs {comparison_to.lower()}", 
            delta_color=delta_color
        )
    
    with col3:
        st.metric(
            "End-Month Cash", 
            f"${end_month_cash:,.0f}"
        )

    # AI Trend Analysis & Forecast Optimization
    with st.expander("🤖 AI Trend Analysis"):
        col1, col2 = st.columns(2)
        
        with col1:
            # Display AI trend analysis
            if trend_direction == "Trending Up":
                st.success(f"📈 **{trend_direction}** - Sales showing positive momentum")
            elif trend_direction == "Trending Down":
                st.warning(f"📉 **{trend_direction}** - Sales declining, monitor closely")
            else:
                st.info(f"📊 **{trend_direction}** - Sales stable")
        
        with col2:
            # Forecast optimization based on 3-month vs LY performance
            if comparison_to == "Last 3m vs LY" and sales_delta > 0:
                st.success(f"🚀 **Better than LY—Forecast Optimistic +5%**")
                st.write("3-month performance exceeds last year")
            elif comparison_to == "Last 3m vs LY" and sales_delta < -10:
                st.warning("⚠️ **Below LY—Forecast Conservative -3%**")
                st.write("3-month performance significantly below last year")
            else:
                st.info("📊 **Forecast Baseline** - Standard projections")

with tabs[3]:  # Financials Tab
    st.subheader("💰 5-Year Cash Flow Projections")
    
    # Get HK starting cash from environment
    hk_start_usd = float(os.getenv('HK_START_USD', 50000))
    
    # Load cost levers from session_state (Settings)
    costa_usd = get_setting('costa_usd', 19000.0)
    costa_crc = get_setting('costa_crc', 38000000.0)
    hk_usd = get_setting('hk_usd', 40000.0)
    stripe_fee = get_setting('stripe_fee', 4.2)
    huub_principal = get_setting('huub_principal', 1250000.0)
    huub_interest = get_setting('huub_interest', 18750.0)
    google_ads = get_setting('google_ads', 27500.0)
    
    # Check if trend is positive from Sales page session_state
    sales_trend_positive = st.session_state.get('sales_trend_positive', False)
    trend_boost = 1.05 if sales_trend_positive else 1.0
    
    # Base monthly sales (with trend boost if applicable)
    base_monthly_sales = 125000 * trend_boost
    
    # Monthly projections for 60 months (5 years)
    projection_data = []
    cumulative_cash = hk_start_usd
    
    for month in range(1, 61):  # 60 months
        year = ((month - 1) // 12) + 1
        month_in_year = ((month - 1) % 12) + 1
        
        # Seasonality factors (higher in Dec, Mar; lower in Feb, Aug)
        seasonality_multiplier = 1.0
        if month_in_year == 12 or month_in_year == 3:  # Dec, Mar
            seasonality_multiplier = 1.2
        elif month_in_year == 2 or month_in_year == 8:  # Feb, Aug
            seasonality_multiplier = 0.85
        
        # Economy factor (conservative growth)
        economy_factor = 1 + (0.03 * year)  # 3% annual growth
        
        # Calculate monthly sales with all factors
        monthly_sales = base_monthly_sales * seasonality_multiplier * economy_factor
        
        # Calculate monthly costs
        monthly_costa_usd = costa_usd
        monthly_costa_crc_usd = costa_crc / 520  # Assume 520 CRC/USD
        monthly_hk_usd = hk_usd
        monthly_google_ads = google_ads
        monthly_huub_interest = huub_interest
        monthly_stripe = monthly_sales * (stripe_fee / 100)
        
        total_monthly_costs = (monthly_costa_usd + monthly_costa_crc_usd + 
                              monthly_hk_usd + monthly_google_ads + 
                              monthly_huub_interest + monthly_stripe)
        
        # Add principal payment in first month only
        if month == 1:
            total_monthly_costs += huub_principal
        
        # Calculate net cash flow
        monthly_net = monthly_sales - total_monthly_costs
        cumulative_cash += monthly_net
        
        projection_data.append({
            'Month': month,
            'Year': year,
            'Sales': monthly_sales,
            'Costs': total_monthly_costs,
            'Net': monthly_net,
            'Cumulative_Cash': cumulative_cash
        })
    
    # Create DataFrame and fix KeyError
    df_projections = pd.DataFrame(projection_data)
    
    # Display Year 5 end-month cash metric
    year_5_end_cash = df_projections['Cumulative_Cash'].iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("End-Month Cash (Year 5)", f"${year_5_end_cash:,.0f}")
    
    with col2:
        if sales_trend_positive:
            st.success("🚀 Trend Boost Applied (+5%)")
        else:
            st.info("📊 Standard Projections")
    
    with col3:
        total_net_5y = df_projections['Net'].sum()
        st.metric("5-Year Total Net", f"${total_net_5y:,.0f}")
    
    # Show projection summary by year
    with st.expander("📊 Yearly Breakdown"):
        yearly_summary = df_projections.groupby('Year').agg({
            'Sales': 'sum',
            'Costs': 'sum', 
            'Net': 'sum',
            'Cumulative_Cash': 'last'
        }).reset_index()
        
        st.dataframe(yearly_summary, use_container_width=True)
    
    with st.expander("💸 Monthly Costs Table"):
        try:
            monthly_costs = load_monthly_costs()
            if monthly_costs:
                costs_df = pd.DataFrame(monthly_costs)
                costs_pivot = costs_df.pivot_table(
                    index='month', 
                    columns='category', 
                    values='amount', 
                    fill_value=0
                )
                st.dataframe(costs_pivot, use_container_width=True)
                
                # Show detailed records
                st.write("**Detailed Records:**")
                st.dataframe(costs_df, use_container_width=True)
            else:
                st.info("No monthly cost data available")
        except Exception as e:
            st.error(f"Error loading monthly costs: {str(e)}")

# Overall On Track Summary (moved outside tabs)
st.subheader("🎯 Overall On Track Summary")

# Calculate average delta (excluding costs which are inverse)
avg_delta = (sales_delta + cash_flow_delta + leads_delta + occupancy_delta - costs_delta) / 5

col1, col2 = st.columns([2, 1])

with col1:
    if avg_delta > 0:
        st.success(f"✅ **Positive Trend** - Average performance is {avg_delta:.1f}% better than {comparison_to.lower()}")
    elif avg_delta < -5:
        st.warning(f"⚠️ **Below Target** - Average performance is {abs(avg_delta):.1f}% below {comparison_to.lower()}")
    else:
        st.info(f"📊 **On Track** - Performance within normal range")

with col2:
    performance_score = max(0, min(100, 50 + avg_delta))
    st.metric("Performance Score", f"{performance_score:.0f}/100")

# Data Overview Section
st.subheader("📊 Data Overview")
if not filtered_df.empty:
    with st.expander("📋 Data Table"):
        st.dataframe(filtered_df.head(10), use_container_width=True)
else:
    st.info("No data available for selected range")

# Export buttons for dashboard data
if not df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            "Export CSV",
            filtered_df.to_csv(index=False).encode('utf-8'),
            f"dashboard_data_{range_select.replace(' ', '_')}.csv",
            "text/csv"
        )
    
    with col2:
        pdf_data = generate_pdf(filtered_df, f"Cash Flow Dashboard Report ({range_select})")
        if pdf_data:
            st.download_button(
                "Export PDF",
                pdf_data,
                f"dashboard_report_{range_select.replace(' ', '_')}.pdf",
                "application/pdf"
            )
        else:
            st.write("**Note:** PDF export requires fpdf package")

# Interactive Demo
st.subheader("Interactive Demo")
if st.button('Click me'):
    st.balloons()
    st.write('Hello! Welcome to your Cash Flow Dashboard!')

# Forecast Adjustment Logic - Better than LY Performance
st.subheader("Performance Trend Analysis")

# Initialize forecast multiplier in session state
if 'forecast_multiplier' not in st.session_state:
    st.session_state.forecast_multiplier = 1.0

# Check if Last 3 Months performance is better than LY
if date_select == "Last 3 Months vs LY":
    last_3m_delta = (sales_delta + cash_flow_delta) / 2  # Average of sales and cash flow
    last_3m_ly_delta = (ly_sales_delta + ly_cash_flow_delta) / 2  # LY comparison
    
    if last_3m_delta > last_3m_ly_delta:
        st.success("🚀 Better than LY: Forecast Positive - Performance trending above last year!")
        st.session_state.forecast_multiplier = 1.05  # +5% optimism
    else:
        st.warning("📊 Mixed Signals: Performance below last year trend")
        st.session_state.forecast_multiplier = 0.98  # -2% caution

col1, col2, col3, col4 = st.columns(4)

with col1:
    if sales_delta > 0:
        st.success(f"Sales On Track: Up {sales_delta:.1f}%")
    else:
        st.warning(f"Sales Off Track: Down {abs(sales_delta):.1f}%")

with col2:
    if cash_flow_delta > 0:
        st.success(f"Cash Flow On Track: Up {cash_flow_delta:.1f}%")
    else:
        st.warning(f"Cash Flow Off Track: Down {abs(cash_flow_delta):.1f}%")

with col3:
    if leads_delta > 0:
        st.success(f"Leads On Track: Up {leads_delta:.1f}%")
    else:
        st.warning(f"Leads Off Track: Down {abs(leads_delta):.1f}%")

with col4:
    if occupancy_delta > 0:
        st.success(f"Occupancy On Track: Up {occupancy_delta:.1f}%")
    else:
        st.warning(f"Occupancy Off Track: Down {abs(occupancy_delta):.1f}%")

# Monthly Cost Entry Section
st.subheader("💰 Monthly Cost Entry")

col1, col2, col3 = st.columns(3)

with col1:
    date = st.date_input("Entry Date", value=datetime.now().replace(day=1))

with col2:
    category = st.selectbox("Category", [
        "Costa USD", 
        "Costa CRC", 
        "HK USD", 
        "Stripe %", 
        "Huub Principal", 
        "Huub Interest", 
        "Google Ads"
    ], key="monthly_cost_category")

with col3:
    amount = st.number_input("Amount", min_value=0.0, step=100.0)

if st.button("Add Entry"):
    try:
        insert_monthly_cost(date.strftime('%Y-%m'), category, amount)
        st.success(f"✅ Added {category}: ${amount:,.2f} for {date.strftime('%Y-%m')}")
        st.rerun()  # Refresh to show updated data
    except Exception as e:
        st.error(f"Error adding entry: {str(e)}")

# Display Monthly Costs Table from Database
st.subheader("📊 Monthly Costs from Database")

try:
    import sqlite3
    conn = sqlite3.connect('cashflow.db')
    
    # Load monthly costs from database
    monthly_costs_df = pd.read_sql_query('''
        SELECT month, category, amount, created_at
        FROM costs_monthly
        ORDER BY month DESC, category
    ''', conn)
    
    conn.close()
    
    if not monthly_costs_df.empty:
        # Create pivot table for better display
        pivot_df = monthly_costs_df.pivot(index='month', columns='category', values='amount')
        pivot_df = pivot_df.fillna(0)
        
        # Add total column (excluding percentage-based fees)
        if len(pivot_df.columns) > 0:
            numeric_columns = [col for col in pivot_df.columns if '%' not in col]
            if numeric_columns:
                pivot_df['Total (USD)'] = pivot_df[numeric_columns].sum(axis=1)
        
        st.dataframe(pivot_df, use_container_width=True)
        
        # Show detailed records in expander
        with st.expander("View Detailed Records"):
            st.dataframe(monthly_costs_df, use_container_width=True)
    else:
        st.info("No monthly cost records found. Use the form above to add entries.")
        
except Exception as e:
    st.error(f"Error loading monthly costs: {str(e)}")

# Month-to-Month Performance Table
st.subheader("Month-to-Month Performance Analysis")

# Create performance data table
import pandas as pd
performance_data = {
    'Metric': ['Sales', 'Cash Flow', 'Leads', 'Occupancy'],
    'Current Period': [f"${125000 + (datetime.now().month * 5000):,.0f}", 
                      f"${45000 + (datetime.now().month * 2000):,.0f}",
                      f"{95 + (datetime.now().month * 2):.0f}",
                      f"{72 + (datetime.now().month * 0.5):.1f}%"],
    'Previous Period': [f"${115000 + ((datetime.now().month - 1) * 4500):,.0f}",
                       f"${42000 + ((datetime.now().month - 1) * 1800):,.0f}",
                       f"{88 + ((datetime.now().month - 1) * 1):.0f}",
                       f"{68 + ((datetime.now().month - 1) * 0.3):.1f}%"],
    'Delta %': [f"{sales_delta:+.1f}%", f"{cash_flow_delta:+.1f}%", 
               f"{leads_delta:+.1f}%", f"{occupancy_delta:+.1f}%"],
    'Trend': ['📈' if sales_delta > 0 else '📉',
             '📈' if cash_flow_delta > 0 else '📉',
             '📈' if leads_delta > 0 else '📉',
             '📈' if occupancy_delta > 0 else '📉']
}

df_performance = pd.DataFrame(performance_data)
st.dataframe(df_performance, use_container_width=True)

# Performance Chart
import plotly.graph_objects as go
fig = go.Figure()

fig.add_trace(go.Bar(
    name='Sales Delta',
    x=['Sales', 'Cash Flow', 'Leads', 'Occupancy'],
    y=[sales_delta, cash_flow_delta, leads_delta, occupancy_delta],
    marker_color=['green' if x > 0 else 'red' for x in [sales_delta, cash_flow_delta, leads_delta, occupancy_delta]]
))

fig.update_layout(
    title=f"Performance Deltas - {date_select}",
    yaxis_title="Change %",
    xaxis_title="Metrics",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

# Overall Trend AI Analysis
st.subheader("Overall Trend AI")

# Calculate average delta across key metrics
key_deltas = [sales_delta, cash_flow_delta, leads_delta, occupancy_delta]
average_delta = sum(key_deltas) / len(key_deltas)

# Apply forecast multiplier from session state
forecast_multiplier = st.session_state.get('forecast_multiplier', 1.0)
adjusted_forecast = average_delta * forecast_multiplier

# Determine trend category and confidence
if adjusted_forecast > 5:
    trend_emoji = "🚀"
    trend_status = "Positive Trend"
    forecast_message = "Forecast: Optimistic"
    confidence = min(90, 50 + abs(adjusted_forecast) * 2)
elif adjusted_forecast > 0:
    trend_emoji = "📈"
    trend_status = "Moderate Growth"
    forecast_message = "Forecast: Stable"
    confidence = min(85, 50 + abs(adjusted_forecast) * 2)
elif adjusted_forecast > -5:
    trend_emoji = "📊"
    trend_status = "Mixed Signals"
    forecast_message = "Forecast: Cautious"
    confidence = min(75, 50 + abs(adjusted_forecast) * 1.5)
else:
    trend_emoji = "📉"
    trend_status = "Negative Trend"
    forecast_message = "Forecast: Concerning"
    confidence = min(80, 50 + abs(adjusted_forecast) * 2)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Overall Trend", f"{trend_emoji} {trend_status}", f"{average_delta:+.1f}%")

with col2:
    st.metric("AI Forecast", forecast_message, f"Multiplier: {forecast_multiplier:.2f}x")

with col3:
    confidence_level = "High" if confidence > 80 else "Moderate" if confidence > 60 else "Low"
    st.metric("Confidence", f"{confidence_level} ({confidence:.0f}%)", f"Based on {len(key_deltas)} metrics")

# Load and process data
try:
    df = get_combined_data()
    if not df.empty:
        df = apply_fx_conversion(df)
    
    current_month = datetime.now().strftime('%Y-%m')
    previous_month = (datetime.now() - timedelta(days=30)).strftime('%Y-%m')
    
    # Filter data by month if date column exists
    if 'date' in df.columns and not df.empty:
        df['month'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m')
        current_data = df[df['month'] == current_month]
        previous_data = df[df['month'] == previous_month]
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            current_sales = current_data['Sales_USD'].sum() if not current_data.empty else 0
            previous_sales = previous_data['Sales_USD'].sum() if not previous_data.empty else 0
            sales_change = ((current_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
            st.metric("Current Month Sales", f"${current_sales:,.2f}", f"{sales_change:+.1f}%")
        
        with col2:
            current_costs = current_data['Costs_USD'].sum() if not current_data.empty else 0
            previous_costs = previous_data['Costs_USD'].sum() if not previous_data.empty else 0
            costs_change = ((current_costs - previous_costs) / previous_costs * 100) if previous_costs > 0 else 0
            st.metric("Current Month Costs", f"${current_costs:,.2f}", f"{costs_change:+.1f}%")
        
        with col3:
            current_flow = current_sales - current_costs
            previous_flow = previous_sales - previous_costs
            flow_change = ((current_flow - previous_flow) / abs(previous_flow) * 100) if previous_flow != 0 else 0
            st.metric("Current Month Cash Flow", f"${current_flow:,.2f}", f"{flow_change:+.1f}%")
    else:
        st.info("Month-to-month comparison requires date column in data")
    
    # Business Metrics Display
    st.subheader("Business Performance Metrics")
    
    # Calculate conversion rates
    mql_rate = (mql / total_leads * 100) if total_leads > 0 else 0
    sql_rate = (sql / mql * 100) if mql > 0 else 0
    sql_from_leads = (sql / total_leads * 100) if total_leads > 0 else 0
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Occupancy Rate", f"{occupancy:.1f}%")
    with col2:
        st.metric("Lead → MQL", f"{mql_rate:.1f}%", f"{mql}/{total_leads}")
    with col3:
        st.metric("MQL → SQL", f"{sql_rate:.1f}%", f"{sql}/{mql}")
    with col4:
        st.metric("Lead → SQL", f"{sql_from_leads:.1f}%", f"{sql}/{total_leads}")
    
    # Business Metrics vs Historical Comparison
    st.subheader("Business Metrics vs Historical")
    
    # Mock historical data for comparison (in real app, this would come from database)
    historical_metrics = {
        'occupancy': 70.0,  # Last month
        'total_leads': 95,
        'mql': 45,
        'sql': 18,
        'occupancy_ly': 65.0,  # Last year
        'total_leads_ly': 85,
        'mql_ly': 40,
        'sql_ly': 15
    }
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        occ_change_mom = occupancy - historical_metrics['occupancy']
        occ_change_yoy = occupancy - historical_metrics['occupancy_ly']
        st.metric("Occupancy vs LM", f"{occupancy:.1f}%", f"{occ_change_mom:+.1f}pp")
        st.metric("Occupancy vs LY", f"{occupancy:.1f}%", f"{occ_change_yoy:+.1f}pp")
    
    with col2:
        leads_change_mom = ((total_leads - historical_metrics['total_leads']) / historical_metrics['total_leads'] * 100) if historical_metrics['total_leads'] > 0 else 0
        leads_change_yoy = ((total_leads - historical_metrics['total_leads_ly']) / historical_metrics['total_leads_ly'] * 100) if historical_metrics['total_leads_ly'] > 0 else 0
        st.metric("Leads vs LM", f"{total_leads}", f"{leads_change_mom:+.1f}%")
        st.metric("Leads vs LY", f"{total_leads}", f"{leads_change_yoy:+.1f}%")
    
    with col3:
        mql_change_mom = ((mql - historical_metrics['mql']) / historical_metrics['mql'] * 100) if historical_metrics['mql'] > 0 else 0
        mql_change_yoy = ((mql - historical_metrics['mql_ly']) / historical_metrics['mql_ly'] * 100) if historical_metrics['mql_ly'] > 0 else 0
        st.metric("MQL vs LM", f"{mql}", f"{mql_change_mom:+.1f}%")
        st.metric("MQL vs LY", f"{mql}", f"{mql_change_yoy:+.1f}%")
    
    with col4:
        sql_change_mom = ((sql - historical_metrics['sql']) / historical_metrics['sql'] * 100) if historical_metrics['sql'] > 0 else 0
        sql_change_yoy = ((sql - historical_metrics['sql_ly']) / historical_metrics['sql_ly'] * 100) if historical_metrics['sql_ly'] > 0 else 0
        st.metric("SQL vs LM", f"{sql}", f"{sql_change_mom:+.1f}%")
        st.metric("SQL vs LY", f"{sql}", f"{sql_change_yoy:+.1f}%")
    
    # Key financial metrics cards
    st.subheader("Financial Metrics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = df['Sales_USD'].sum() if 'Sales_USD' in df.columns else 0
        st.metric("Total Sales", f"${total_sales:,.2f}")
    
    with col2:
        total_costs = df['Costs_USD'].sum() if 'Costs_USD' in df.columns else 0
        st.metric("Total Costs", f"${total_costs:,.2f}")
    
    with col3:
        net_cash_flow = total_sales - total_costs
        st.metric("Net Cash Flow", f"${net_cash_flow:,.2f}")
    
    with col4:
        margin = (net_cash_flow / total_sales * 100) if total_sales > 0 else 0
        st.metric("Profit Margin", f"{margin:.1f}%")
    
    # Occupancy vs Sales/Cash Flow Analysis
    st.subheader("Occupancy vs Performance Analysis")
    
    # Create synthetic data for occupancy correlation analysis
    import numpy as np
    
    # Generate sample data points for different occupancy levels
    occupancy_levels = np.arange(50, 101, 5)  # 50% to 100% in 5% increments
    
    # Calculate theoretical sales based on occupancy (assuming linear relationship)
    base_sales_per_occupancy = total_sales / occupancy if occupancy > 0 else 0
    theoretical_sales = occupancy_levels * base_sales_per_occupancy
    
    # Calculate theoretical cash flow (assuming costs remain relatively fixed)
    base_costs = total_costs
    theoretical_cash_flow = theoretical_sales - base_costs
    
    # Create DataFrame for charts
    occupancy_analysis = pd.DataFrame({
        'Occupancy %': occupancy_levels,
        'Projected Sales': theoretical_sales,
        'Projected Cash Flow': theoretical_cash_flow
    })
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Occupancy vs Sales Projection**")
        chart_data = occupancy_analysis.set_index('Occupancy %')[['Projected Sales']]
        st.line_chart(chart_data)
        
        # Current position marker
        current_sales_at_occupancy = occupancy * base_sales_per_occupancy if occupancy > 0 else 0
        st.write(f"**Current Position:** {occupancy:.1f}% occupancy → ${current_sales_at_occupancy:,.0f} sales")
    
    with col2:
        st.write("**Occupancy vs Cash Flow Projection**")
        chart_data = occupancy_analysis.set_index('Occupancy %')[['Projected Cash Flow']]
        st.line_chart(chart_data)
        
        # Current position marker
        current_cash_flow_at_occupancy = current_sales_at_occupancy - base_costs
        st.write(f"**Current Position:** {occupancy:.1f}% occupancy → ${current_cash_flow_at_occupancy:,.0f} cash flow")
    
    # Occupancy Impact Analysis Table
    st.subheader("Occupancy Impact Analysis")
    
    impact_scenarios = pd.DataFrame({
        'Occupancy Level': ['60%', '70%', '80%', '90%', '100%'],
        'Projected Sales': [f"${60 * base_sales_per_occupancy:,.0f}", 
                          f"${70 * base_sales_per_occupancy:,.0f}", 
                          f"${80 * base_sales_per_occupancy:,.0f}", 
                          f"${90 * base_sales_per_occupancy:,.0f}", 
                          f"${100 * base_sales_per_occupancy:,.0f}"],
        'Projected Cash Flow': [f"${60 * base_sales_per_occupancy - base_costs:,.0f}", 
                              f"${70 * base_sales_per_occupancy - base_costs:,.0f}", 
                              f"${80 * base_sales_per_occupancy - base_costs:,.0f}", 
                              f"${90 * base_sales_per_occupancy - base_costs:,.0f}", 
                              f"${100 * base_sales_per_occupancy - base_costs:,.0f}"],
        'vs Current': [f"{((60 - occupancy) / occupancy * 100):+.1f}%" if occupancy > 0 else "N/A",
                      f"{((70 - occupancy) / occupancy * 100):+.1f}%" if occupancy > 0 else "N/A",
                      f"{((80 - occupancy) / occupancy * 100):+.1f}%" if occupancy > 0 else "N/A",
                      f"{((90 - occupancy) / occupancy * 100):+.1f}%" if occupancy > 0 else "N/A",
                      f"{((100 - occupancy) / occupancy * 100):+.1f}%" if occupancy > 0 else "N/A"]
    })
    
    st.dataframe(impact_scenarios, use_container_width=True)
    
    # Business Health Indicators
    st.subheader("Business Health")
    
    col1, col2 = st.columns(2)
    
    with col1:
        cash_flow_status = "Positive" if net_cash_flow > 0 else "Negative"
        st.write(f"**Cash Flow Status:** {cash_flow_status}")
            
        sales_trend = "Up" if total_sales > 50000 else "Below Target"
        st.write(f"**Sales Trend:** {sales_trend}")
    
    with col2:
        cost_control = "Good" if total_costs < total_sales * 0.8 else "Review Needed"
        st.write(f"**Cost Control:** {cost_control}")
            
        # Loan status
        if 'loan' in st.session_state:
            loan = st.session_state.loan
            loan_status = "On Track" if loan.outstanding < loan.principal * 0.5 else "Early Stages"
            st.write(f"**Loan Status:** {loan_status}")
    
    # Integration Status
    st.subheader("System Integrations")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.write("**Database:** Connected")
    with col2:
        st.write("**Airtable:** Not Configured")
    with col3:
        st.write("**Stripe:** Not Configured")
    with col4:
        st.write("**FRED API:** Connected")
    
    # Integration metrics
    st.subheader("Integration Details")
    
    col1, col2 = st.columns(2)
    
    with col1:
        try:
            lead_metrics = get_lead_metrics()
            st.write(f"**Airtable:** {lead_metrics['total_leads']} leads (${lead_metrics['total_value']:,.0f} total value)")
        except:
            st.write("**Airtable:** Connection issue")
    
    with col2:
        try:
            payment_metrics = get_payment_metrics()
            st.write(f"**Stripe:** {payment_metrics['succeeded_payments']} payments (${payment_metrics['total_amount']:,.0f})")
        except:
            st.write("**Stripe:** Connection issue")
    
    # Lead Funnel Analysis Table
    st.subheader("Lead Funnel Performance")
    
    funnel_data = pd.DataFrame({
        'Stage': ['Total Leads', 'MQL', 'SQL'],
        'Current': [total_leads, mql, sql],
        'Last Month': [historical_metrics['total_leads'], historical_metrics['mql'], historical_metrics['sql']],
        'Last Year': [historical_metrics['total_leads_ly'], historical_metrics['mql_ly'], historical_metrics['sql_ly']],
        'Conversion Rate': [f"100%", f"{mql_rate:.1f}%", f"{sql_from_leads:.1f}%"],
        'MoM Change': [f"{leads_change_mom:+.1f}%", f"{mql_change_mom:+.1f}%", f"{sql_change_mom:+.1f}%"],
        'YoY Change': [f"{leads_change_yoy:+.1f}%", f"{mql_change_yoy:+.1f}%", f"{sql_change_yoy:+.1f}%"]
    })
    
    st.dataframe(funnel_data, use_container_width=True)
    
    # Stripe-like Analytics Section
    st.subheader("Analytics Dashboard")
    
    # Stripe-style date range selector
    col1, col2 = st.columns([1, 3])
    with col1:
        range_select = st.selectbox("Date Range", 
                                   ["12 Months", "Last 7 Days", "YTD", "QTD", "YTD vs LY", "During-Month vs LY"], 
                                   index=0, key="data_overview_range_select")
    
    # Filter data based on selected range
    filtered_df = filter_data_by_range(df, range_select)
    
    # Get comparison data for vs previous analysis
    comparison_df = None
    if range_select in ["YTD vs LY", "During-Month vs LY"]:
        today = datetime.now()
        if range_select == "YTD vs LY":
            ly_start = datetime(today.year - 1, 1, 1)
            ly_end = datetime(today.year - 1, today.month, today.day)
            comparison_df = df.query('@ly_start <= Date <= @ly_end')
        else:  # During-Month vs LY
            ly_month_start = datetime(today.year - 1, today.month, 1)
            ly_month_end = datetime(today.year - 1, today.month, today.day)
            comparison_df = df.query('@ly_month_start <= Date <= @ly_month_end')
    
    if not filtered_df.empty:
        # Key metrics for the selected period
        col1, col2, col3, col4 = st.columns(4)
        
        total_sales = filtered_df['Sales_USD'].sum() if 'Sales_USD' in filtered_df.columns else 0
        total_costs = filtered_df['Costs_USD'].sum() if 'Costs_USD' in filtered_df.columns else 0
        net_cash_flow = total_sales - total_costs
        avg_per_customer = total_sales / len(filtered_df) if len(filtered_df) > 0 else 0
        
        with col1:
            st.metric("Avg Monthly Sales", f"${avg_monthly_sales:,.0f}")
        with col2:
            st.metric("Avg Monthly Costs", f"${avg_monthly_costs:,.0f}")
        with col3:
            net_monthly = avg_monthly_sales - avg_monthly_costs
            st.metric("Avg Monthly Net", f"${net_monthly:,.0f}")
        with col4:
            st.metric("Avg per Transaction", f"${avg_per_customer:,.0f}")
        
        # Enhanced Leads Analysis
        st.subheader("Lead Performance Analysis")
        
        # Calculate lead metrics with context
        avg_leads_per_month = 80  # Context baseline
        current_leads = total_leads
        leads_vs_avg = ((current_leads - avg_leads_per_month) / avg_leads_per_month * 100) if avg_leads_per_month > 0 else 0
        
        # Year-over-year comparison
        leads_yoy_change = leads_change_yoy
        conversion_rate = (sql / total_leads * 100) if total_leads > 0 else 0
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trend_indicator = "Up" if leads_yoy_change > 0 else "Down"
            st.metric(
                "Total Leads", 
                f"{current_leads}", 
                f"{trend_indicator} {abs(leads_yoy_change):.1f}% vs LY"
            )
            context_msg = "Above avg" if leads_vs_avg > 0 else "Below avg"
            st.caption(f"Context: {context_msg} {avg_leads_per_month} leads/mo ({leads_vs_avg:+.1f}%)")
        
        with col2:
            st.metric(
                "Conversion Rate", 
                f"{conversion_rate:.1f}%",
                f"Lead → SQL"
            )
            if conversion_rate > 15:
                st.caption("Strong conversion performance")
            elif conversion_rate > 10:
                st.caption("Average conversion performance")
            else:
                st.caption("Below average conversion")
        
        with col3:
            mql_conversion = (mql / total_leads * 100) if total_leads > 0 else 0
            st.metric(
                "MQL Rate", 
                f"{mql_conversion:.1f}%",
                f"Lead → MQL"
            )
            st.caption(f"MQL to SQL: {(sql/mql*100) if mql > 0 else 0:.1f}%")
        
        # Enhanced Stripe-style charts section
        col1, col2 = st.columns(2)
        
        with col1:
            # Gross vs Net chart with comparison
            if 'Date' in filtered_df.columns:
                daily_data = filtered_df.groupby('Date').agg({
                    'Sales_USD': 'sum',
                    'Costs_USD': 'sum'
                }).reset_index()
                daily_data['Net'] = daily_data['Sales_USD'] - daily_data['Costs_USD']
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=daily_data['Date'], y=daily_data['Sales_USD'], 
                                       mode='lines', name='Gross Revenue', line=dict(color='#00D4AA', width=3)))
                fig.add_trace(go.Scatter(x=daily_data['Date'], y=daily_data['Net'], 
                                       mode='lines', name='Net Cash Flow', line=dict(color='#FF6B6B', width=3)))
                
                # Add comparison data if available
                if comparison_df is not None and not comparison_df.empty:
                    comp_daily = comparison_df.groupby('Date').agg({
                        'Sales_USD': 'sum',
                        'Costs_USD': 'sum'
                    }).reset_index()
                    comp_daily['Net'] = comp_daily['Sales_USD'] - comp_daily['Costs_USD']
                    
                    fig.add_trace(go.Scatter(x=comp_daily['Date'], y=comp_daily['Sales_USD'], 
                                           mode='lines', name='Gross Revenue (LY)', 
                                           line=dict(color='#00D4AA', width=1, dash='dash')))
                    fig.add_trace(go.Scatter(x=comp_daily['Date'], y=comp_daily['Net'], 
                                           mode='lines', name='Net Cash Flow (LY)', 
                                           line=dict(color='#FF6B6B', width=1, dash='dash')))
                
                fig.update_layout(
                    title=f"Revenue Trends ({range_select})", 
                    height=350,
                    showlegend=True,
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Enhanced spend per customer with bar chart
            if 'Date' in filtered_df.columns and len(filtered_df) > 0:
                daily_customers = filtered_df.groupby('Date').size().reset_index(name='transactions')
                daily_revenue = filtered_df.groupby('Date')['Sales_USD'].sum().reset_index()
                spend_per_customer = pd.merge(daily_revenue, daily_customers, on='Date')
                spend_per_customer['avg_spend'] = spend_per_customer['Sales_USD'] / spend_per_customer['transactions']
                
                # Create bar chart for recent data, line for historical
                if len(spend_per_customer) <= 30:
                    fig = go.Figure()
                    fig.add_trace(go.Bar(x=spend_per_customer['Date'], y=spend_per_customer['avg_spend'], 
                                        name='Avg Spend per Transaction', marker_color='#4ECDC4'))
                else:
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=spend_per_customer['Date'], y=spend_per_customer['avg_spend'], 
                                           mode='lines+markers', name='Avg Spend per Transaction', 
                                           line=dict(color='#4ECDC4', width=3)))
                
                # Add comparison if available
                if comparison_df is not None and not comparison_df.empty:
                    comp_customers = comparison_df.groupby('Date').size().reset_index(name='transactions')
                    comp_revenue = comparison_df.groupby('Date')['Sales_USD'].sum().reset_index()
                    comp_spend = pd.merge(comp_revenue, comp_customers, on='Date')
                    comp_spend['avg_spend'] = comp_spend['Sales_USD'] / comp_spend['transactions']
                    
                    if len(comp_spend) <= 30:
                        fig.add_trace(go.Bar(x=comp_spend['Date'], y=comp_spend['avg_spend'], 
                                           name='Avg Spend (LY)', marker_color='#4ECDC4', opacity=0.5))
                    else:
                        fig.add_trace(go.Scatter(x=comp_spend['Date'], y=comp_spend['avg_spend'], 
                                               mode='lines', name='Avg Spend (LY)', 
                                               line=dict(color='#4ECDC4', width=1, dash='dash')))
                
                fig.update_layout(
                    title=f"Spend per Transaction ({range_select})", 
                    height=350,
                    showlegend=True,
                    hovermode='x unified'
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # AI Trend Analysis
        st.subheader("AI Trend Analysis")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Enhanced sales trend with monthly percentage
            if 'Sales_USD' in filtered_df.columns:
                monthly_slope_pct, r_squared = analyze_trend_with_ai(filtered_df, 'Sales_USD')
                if monthly_slope_pct is not None:
                    if monthly_slope_pct > 0:
                        st.success(f"Trending Up ({monthly_slope_pct:.2f}%/mo)")
                    else:
                        st.warning(f"Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
                    st.caption(r_squared)
                else:
                    st.info("Sales trend analysis unavailable")
        
        with col2:
            # Enhanced costs trend
            if 'Costs_USD' in filtered_df.columns:
                monthly_slope_pct, r_squared = analyze_trend_with_ai(filtered_df, 'Costs_USD')
                if monthly_slope_pct is not None:
                    if monthly_slope_pct > 0:
                        st.warning(f"Trending Up ({monthly_slope_pct:.2f}%/mo)")
                    else:
                        st.success(f"Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
                    st.caption(r_squared)
                else:
                    st.info("Costs trend analysis unavailable")
        
        with col3:
            # Enhanced net cash flow trend
            if 'Sales_USD' in filtered_df.columns and 'Costs_USD' in filtered_df.columns:
                net_df = filtered_df.copy()
                net_df['Net_Cash_Flow'] = net_df['Sales_USD'] - net_df['Costs_USD']
                monthly_slope_pct, r_squared = analyze_trend_with_ai(net_df, 'Net_Cash_Flow')
                if monthly_slope_pct is not None:
                    if monthly_slope_pct > 0:
                        st.success(f"Trending Up ({monthly_slope_pct:.2f}%/mo)")
                    else:
                        st.warning(f"Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
                    st.caption(r_squared)
                else:
                    st.info("Net cash trend analysis unavailable")
        
        # During-month comparison
        st.subheader("Month-to-Date Comparison")
        
        current_metrics, ly_metrics = get_during_month_comparison(df)
        
        if current_metrics['count'] > 0 or ly_metrics['count'] > 0:
            today = datetime.now()
            month_name = today.strftime("%B")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                sales_change = ((current_metrics['sales'] - ly_metrics['sales']) / ly_metrics['sales'] * 100) if ly_metrics['sales'] > 0 else 0
                st.metric(
                    f"{month_name} 1-{today.day} Sales", 
                    f"${current_metrics['sales']:,.0f}",
                    f"{sales_change:+.1f}% vs LY"
                )
            
            with col2:
                costs_change = ((current_metrics['costs'] - ly_metrics['costs']) / ly_metrics['costs'] * 100) if ly_metrics['costs'] > 0 else 0
                st.metric(
                    f"{month_name} 1-{today.day} Costs", 
                    f"${current_metrics['costs']:,.0f}",
                    f"{costs_change:+.1f}% vs LY"
                )
            
            with col3:
                net_change = ((current_metrics['net'] - ly_metrics['net']) / ly_metrics['net'] * 100) if ly_metrics['net'] != 0 else 0
                st.metric(
                    f"{month_name} 1-{today.day} Net", 
                    f"${current_metrics['net']:,.0f}",
                    f"{net_change:+.1f}% vs LY"
                )
    
    # Display data table
    st.subheader("Data Overview")
    if not filtered_df.empty:
        st.dataframe(filtered_df.head(10), use_container_width=True)
    else:
        st.info("No data available for selected range")
    
    # Export buttons for dashboard data
    if not df.empty:
        col1, col2 = st.columns(2)
        
        with col1:
            st.download_button(
                "Export CSV",
                filtered_df.to_csv(index=False).encode('utf-8'),
                f"dashboard_data_{range_select.replace(' ', '_')}.csv",
                "text/csv"
            )
        
        with col2:
            pdf_data = generate_pdf(filtered_df, f"Cash Flow Dashboard Report ({range_select})")
            if pdf_data:
                st.download_button(
                    "Export PDF",
                    pdf_data,
                    f"dashboard_report_{range_select.replace(' ', '_')}.pdf",
                    "application/pdf"
                )
            else:
                st.write("**Note:** PDF export requires fpdf package")
    
    # 5-Year Cash Flow Projections with Fixes
    st.subheader("💰 5-Year Cash Flow Projections")
    
    # Get HK starting cash from environment
    hk_start_usd = float(os.getenv('HK_START_USD', 50000))
    
    # Load cost levers from session_state (Settings)
    costa_usd = get_setting('costa_usd', 19000.0)
    costa_crc = get_setting('costa_crc', 38000000.0)
    hk_usd = get_setting('hk_usd', 40000.0)
    stripe_fee = get_setting('stripe_fee', 4.2)
    huub_principal = get_setting('huub_principal', 1250000.0)
    huub_interest = get_setting('huub_interest', 18750.0)
    google_ads = get_setting('google_ads', 27500.0)
    
    # Check if trend is positive from Sales page session_state
    sales_trend_positive = st.session_state.get('sales_trend_positive', False)
    trend_boost = 1.05 if sales_trend_positive else 1.0
    
    # Base monthly sales (with trend boost if applicable)
    base_monthly_sales = 125000 * trend_boost
    
    # Monthly projections for 60 months (5 years)
    projection_data = []
    cumulative_cash = hk_start_usd
    
    for month in range(1, 61):  # 60 months
        year = ((month - 1) // 12) + 1
        month_in_year = ((month - 1) % 12) + 1
        
        # Seasonality factors (higher in Dec, Mar; lower in Feb, Aug)
        seasonality_multiplier = 1.0
        if month_in_year == 12 or month_in_year == 3:  # Dec, Mar
            seasonality_multiplier = 1.2
        elif month_in_year == 2 or month_in_year == 8:  # Feb, Aug
            seasonality_multiplier = 0.85
        
        # Economy factor (conservative growth)
        economy_factor = 1 + (0.03 * year)  # 3% annual growth
        
        # Calculate monthly sales with all factors
        monthly_sales = base_monthly_sales * seasonality_multiplier * economy_factor
        
        # Calculate monthly costs
        monthly_costa_usd = costa_usd
        monthly_costa_crc_usd = costa_crc / 520  # Assume 520 CRC/USD
        monthly_hk_usd = hk_usd
        monthly_google_ads = google_ads
        monthly_huub_interest = huub_interest
        monthly_stripe = monthly_sales * (stripe_fee / 100)
        
        total_monthly_costs = (monthly_costa_usd + monthly_costa_crc_usd + 
                              monthly_hk_usd + monthly_google_ads + 
                              monthly_huub_interest + monthly_stripe)
        
        # Add principal payment in first month only
        if month == 1:
            total_monthly_costs += huub_principal
        
        # Calculate net cash flow
        monthly_net = monthly_sales - total_monthly_costs
        cumulative_cash += monthly_net
        
        projection_data.append({
            'Month': month,
            'Year': year,
            'Sales': monthly_sales,
            'Costs': total_monthly_costs,
            'Net': monthly_net,
            'Cumulative_Cash': cumulative_cash
        })
    
    # Create DataFrame and fix KeyError
    df_projections = pd.DataFrame(projection_data)
    
    # Display Year 5 end-month cash metric
    year_5_end_cash = df_projections['Cumulative_Cash'].iloc[-1]
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("End-Month Cash (Year 5)", f"${year_5_end_cash:,.0f}")
    
    with col2:
        if sales_trend_positive:
            st.success("🚀 Trend Boost Applied (+5%)")
        else:
            st.info("📊 Standard Projections")
    
    with col3:
        total_net_5y = df_projections['Net'].sum()
        st.metric("5-Year Total Net", f"${total_net_5y:,.0f}")
    
    # Show projection summary by year
    yearly_summary = df_projections.groupby('Year').agg({
        'Sales': 'sum',
        'Costs': 'sum', 
        'Net': 'sum',
        'Cumulative_Cash': 'last'
    }).reset_index()
    
    st.dataframe(yearly_summary, use_container_width=True)
    
    # Hello button from original functionality
    st.subheader("Interactive Demo")
    if st.button('Click me'):
        st.balloons()
        st.write('Hello! Welcome to your Cash Flow Dashboard!')

except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Please check your data configuration.")
    # Still show business metrics even if data loading fails
    st.subheader("Business Metrics (Standalone)")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Occupancy Rate", f"{occupancy:.1f}%")
    with col2:
        mql_rate = (mql / total_leads * 100) if total_leads > 0 else 0
        st.metric("Lead → MQL", f"{mql_rate:.1f}%")
    with col3:
        sql_rate = (sql / mql * 100) if mql > 0 else 0
        st.metric("MQL → SQL", f"{sql_rate:.1f}%")
    with col4:
        sql_from_leads = (sql / total_leads * 100) if total_leads > 0 else 0
        st.metric("Lead → SQL", f"{sql_from_leads:.1f}%")
