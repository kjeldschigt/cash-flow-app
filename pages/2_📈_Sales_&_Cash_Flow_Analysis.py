import streamlit as st

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
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.storage import get_combined_data, load_settings
from services.fx import apply_fx_conversion

try:
    from sklearn.linear_model import LinearRegression
    from sklearn.preprocessing import PolynomialFeatures
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

st.title("Sales & Cash Flow Analysis")

# Sidebar for Global Date Filtering
st.sidebar.subheader("🗓️ Global Date Filter")
global_date_range = st.sidebar.selectbox(
    "Filter All Data By",
    ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date", "All Time"],
    index=0,
    key="sales_global_date_filter"
)

# Load data from database
try:
    from services.airtable import load_combined_data
    df = load_combined_data()
    
    if df.empty:
        st.warning("No data available. Please check your Airtable configuration.")
        st.stop()
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.stop()

# Main Navigation Tabs
tabs = st.tabs(["Metrics", "Comparisons", "Graphs", "Trends"])

with tabs[0]:  # Metrics Tab
    st.subheader("📊 Key Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_sales = df['Sales_USD'].sum() if 'Sales_USD' in df.columns else 0
        st.metric("Total Sales", f"${total_sales:,.0f}")
    
    with col2:
        avg_deal = df['Sales_USD'].mean() if 'Sales_USD' in df.columns else 0
        st.metric("Avg Deal Size", f"${avg_deal:,.0f}")
    
    with col3:
        total_leads = len(df) if not df.empty else 0
        st.metric("Total Leads", f"{total_leads:,}")
    
    with col4:
        conversion_rate = (df['Sales_USD'] > 0).mean() * 100 if 'Sales_USD' in df.columns else 0
        st.metric("Conversion Rate", f"{conversion_rate:.1f}%")
    
    # Additional metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        occupancy = get_setting('occupancy', 75.0)
        st.metric("Occupancy Rate", f"{occupancy:.1f}%")
    
    with col2:
        cash_flow = df['Sales_USD'].sum() - (df['Sales_USD'].sum() * 0.3) if 'Sales_USD' in df.columns else 0
        st.metric("Net Cash Flow", f"${cash_flow:,.0f}")
    
    with col3:
        monthly_avg = total_sales / 12 if total_sales > 0 else 0
        st.metric("Monthly Avg", f"${monthly_avg:,.0f}")
    
    with col4:
        pipeline_value = total_leads * avg_deal * (conversion_rate / 100) if total_leads > 0 else 0
        st.metric("Pipeline Value", f"${pipeline_value:,.0f}")

with tabs[1]:  # Comparisons Tab
    st.subheader("📊 Performance Comparisons")
    
    # Date range selector
    col1, col2 = st.columns(2)
    
    with col1:
        comparison_period = st.selectbox(
            "Compare Against",
            ["Previous Month", "Same Month Last Year", "Last 3 Months", "During-Month vs LY"],
            key="sales_comparison_period"
        )
    
    with col2:
        date_range = st.selectbox(
            "Date Range",
            ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date"],
            key="sales_date_range"
        )
    
    # Performance deltas with expanders
    with st.expander("📈 Sales Performance Deltas"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            current_sales = df['Sales_USD'].sum() if 'Sales_USD' in df.columns else 0
            previous_sales = current_sales * 0.85  # Mock comparison
            delta = ((current_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
            st.metric("Sales vs Previous", f"${current_sales:,.0f}", f"{delta:+.1f}%")
        
        with col2:
            current_leads = len(df)
            previous_leads = current_leads * 0.92  # Mock comparison
            delta_leads = ((current_leads - previous_leads) / previous_leads * 100) if previous_leads > 0 else 0
            st.metric("Leads vs Previous", f"{current_leads:,}", f"{delta_leads:+.1f}%")
        
        with col3:
            current_conversion = conversion_rate
            previous_conversion = current_conversion * 0.95  # Mock comparison
            delta_conversion = current_conversion - previous_conversion
            st.metric("Conversion vs Previous", f"{current_conversion:.1f}%", f"{delta_conversion:+.1f}pp")
    
    with st.expander("📋 Detailed Comparison Table"):
        comparison_data = {
            'Metric': ['Sales', 'Leads', 'Conversion Rate', 'Avg Deal Size'],
            'Current': [f"${current_sales:,.0f}", f"{total_leads:,}", f"{conversion_rate:.1f}%", f"${avg_deal:,.0f}"],
            'Previous': [f"${previous_sales:,.0f}", f"{previous_leads:,.0f}", f"{previous_conversion:.1f}%", f"${avg_deal*0.9:,.0f}"],
            'Change': [f"{delta:+.1f}%", f"{delta_leads:+.1f}%", f"{delta_conversion:+.1f}pp", "+10.0%"]
        }
        st.dataframe(pd.DataFrame(comparison_data), use_container_width=True)

with tabs[2]:  # Graphs Tab
    st.subheader("📈 Sales & Cash Flow Analysis")

    # Load and process data
    try:
        df = get_combined_data()
        if not df.empty:
            df = apply_fx_conversion(df)
            df['Date'] = pd.to_datetime(df['Date'])
            df = df.sort_values('Date')
            
            # Calculate monthly aggregates
            df['YearMonth'] = df['Date'].dt.to_period('M')
            monthly_data = df.groupby('YearMonth').agg({
                'Sales_USD': 'sum',
                'Costs_USD': 'sum'
            }).reset_index()
            monthly_data['Net_Cash_Flow'] = monthly_data['Sales_USD'] - monthly_data['Costs_USD']
            monthly_data['Date'] = monthly_data['YearMonth'].dt.to_timestamp()
            
            # Add occupancy and leads data (mock for now)
            monthly_data['Occupancy'] = np.random.uniform(75, 95, len(monthly_data))
            monthly_data['Leads'] = np.random.randint(60, 120, len(monthly_data))
            
            st.success(f"Loaded {len(df)} records, {len(monthly_data)} months of data")
        else:
            st.warning("No data available")
            monthly_data = pd.DataFrame()
    except Exception as e:
        st.error(f"Error loading data: {e}")
        monthly_data = pd.DataFrame()

    # Create tabs for Forecasting and Scenarios
    forecasting_tab, scenarios_tab = st.tabs(["AI Forecasting", "Scenarios"])

    def create_ai_forecast(data, metric_column, months_ahead=12):
        """Create AI forecast using sklearn regression"""
        if not SKLEARN_AVAILABLE or data.empty or metric_column not in data.columns:
            return None, None
        
        # Prepare data
        data_clean = data.dropna(subset=[metric_column, 'Date'])
        if len(data_clean) < 3:
            return None, None
        
        # Convert dates to numeric
        data_clean = data_clean.sort_values('Date')
        start_date = data_clean['Date'].min()
        data_clean['days_since_start'] = (data_clean['Date'] - start_date).dt.days
        
        # Fit regression model
        X = data_clean[['days_since_start']]
        y = data_clean[metric_column]
        
        # Ensure X is 2D array for sklearn
        if not hasattr(X, 'columns'):
            X = np.array(X).reshape(-1, 1) if np.array(X).ndim == 1 else np.array(X)
            X = pd.DataFrame(X, columns=['days_since_start'])
        
        model = LinearRegression()
        model.fit(X, y)
        
        # Generate future predictions
        last_date = data_clean['Date'].max()
        future_dates = [last_date + timedelta(days=30*i) for i in range(1, months_ahead + 1)]
        future_days = [(date - start_date).days for date in future_dates]
        
        # Ensure prediction input is 2D array
        future_X = np.array(future_days).reshape(-1, 1)
        if not hasattr(future_X, 'shape') or future_X.ndim == 1:
            future_X = future_X.reshape(-1, 1)
        
        predictions = model.predict(future_X)
        
        forecast_df = pd.DataFrame({
            'Date': future_dates,
            'Predicted': predictions,
            'Metric': metric_column
        })
        
        return forecast_df, model.score(X, y)

    def calculate_month_comparisons(data, metric_column):
        """Calculate month-to-month comparisons"""
        if data.empty or metric_column not in data.columns:
            return {}
        
        current_month = data.iloc[-1] if not data.empty else None
        last_month = data.iloc[-2] if len(data) > 1 else None
        
        # Last year same month
        current_date = current_month['Date'] if current_month is not None else datetime.now()
        ly_date = current_date - timedelta(days=365)
        ly_data = data[abs((data['Date'] - ly_date).dt.days) < 15]
        ly_month = ly_data.iloc[0] if not ly_data.empty else None
        
        comparisons = {}
        if current_month is not None and last_month is not None:
            mom_change = ((current_month[metric_column] - last_month[metric_column]) / last_month[metric_column] * 100) if last_month[metric_column] != 0 else 0
            comparisons['vs_last_month'] = mom_change
        
        if current_month is not None and ly_month is not None:
            yoy_change = ((current_month[metric_column] - ly_month[metric_column]) / ly_month[metric_column] * 100) if ly_month[metric_column] != 0 else 0
            comparisons['vs_last_year'] = yoy_change
        
        return comparisons
