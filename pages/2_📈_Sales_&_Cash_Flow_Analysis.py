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

with forecasting_tab:
    st.subheader("AI-Powered Forecasting")
    
    if not monthly_data.empty:
        # Forecast metrics selection
        col1, col2 = st.columns([1, 3])
        
        with col1:
            forecast_months = st.slider("Forecast Months", 3, 24, 12)
            metrics_to_forecast = st.multiselect(
                "Metrics to Forecast", 
                ['Sales_USD', 'Costs_USD', 'Net_Cash_Flow', 'Occupancy', 'Leads'],
                default=['Sales_USD', 'Net_Cash_Flow']
            )
        
        # Generate forecasts
        forecasts = {}
        for metric in metrics_to_forecast:
            forecast_df, r_squared = create_ai_forecast(monthly_data, metric, forecast_months)
            if forecast_df is not None:
                forecasts[metric] = {'data': forecast_df, 'r_squared': r_squared}
        
        # Display forecasts
        if forecasts:
            st.subheader("Forecast Results")
            
            # Metrics overview
            cols = st.columns(len(forecasts))
            for i, (metric, forecast_info) in enumerate(forecasts.items()):
                with cols[i]:
                    last_actual = monthly_data[metric].iloc[-1] if not monthly_data.empty else 0
                    next_predicted = forecast_info['data']['Predicted'].iloc[0]
                    change_pct = ((next_predicted - last_actual) / last_actual * 100) if last_actual != 0 else 0
                    
                    st.metric(
                        metric.replace('_', ' ').title(),
                        f"${next_predicted:,.0f}" if 'USD' in metric else f"{next_predicted:.1f}",
                        f"{change_pct:+.1f}% next month"
                    )
                    st.caption(f"R² = {forecast_info['r_squared']:.3f}")
            
            # Forecast charts
            for metric, forecast_info in forecasts.items():
                st.subheader(f"{metric.replace('_', ' ').title()} Forecast")
                
                # Create combined chart with historical and forecast
                fig = go.Figure()
                
                # Historical data
                fig.add_trace(go.Scatter(
                    x=monthly_data['Date'], 
                    y=monthly_data[metric],
                    mode='lines+markers',
                    name='Historical',
                    line=dict(color='#00D4AA', width=3)
                ))
                
                # Forecast data
                fig.add_trace(go.Scatter(
                    x=forecast_info['data']['Date'], 
                    y=forecast_info['data']['Predicted'],
                    mode='lines+markers',
                    name='Forecast',
                    line=dict(color='#FF6B6B', width=3, dash='dash')
                ))
                
                fig.update_layout(
                    title=f"{metric.replace('_', ' ').title()} - Historical vs Forecast",
                    height=400,
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Month-to-month comparisons
                comparisons = calculate_month_comparisons(monthly_data, metric)
                if comparisons:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        if 'vs_last_month' in comparisons:
                            st.metric(
                                "vs Last Month",
                                f"{comparisons['vs_last_month']:+.1f}%",
                                "Month-over-Month"
                            )
                    
                    with col2:
                        if 'vs_last_year' in comparisons:
                            st.metric(
                                "vs Last Year",
                                f"{comparisons['vs_last_year']:+.1f}%",
                                "Year-over-Year"
                            )
                    
                    with col3:
                        # During-month comparison (simplified)
                        current_value = monthly_data[metric].iloc[-1] if not monthly_data.empty else 0
                        avg_value = monthly_data[metric].mean() if not monthly_data.empty else 0
                        vs_avg = ((current_value - avg_value) / avg_value * 100) if avg_value != 0 else 0
                        st.metric(
                            "vs Average",
                            f"{vs_avg:+.1f}%",
                            "Historical Average"
                        )
        else:
            st.info("Select metrics to generate forecasts")
    else:
        st.warning("No data available for forecasting")

with scenarios_tab:
    st.subheader("Scenario Planning")
    
    if not monthly_data.empty and 'forecasts' in locals() and forecasts:
        # Economy impact slider
        col1, col2 = st.columns([1, 2])
        
        with col1:
            economy_slider = st.slider("Economy Impact", -20, 20, 0, help="Negative = recession, Positive = growth")
            
            st.write("**Scenario Adjustments:**")
            sales_adjustment = -economy_slider / 2
            costs_adjustment = economy_slider
            
            st.write(f"• Sales: {sales_adjustment:+.1f}%")
            st.write(f"• Costs: {costs_adjustment:+.1f}%")
            
            # Additional levers
            marketing_multiplier = st.slider("Marketing Spend", 0.5, 2.0, 1.0, 0.1)
            efficiency_gain = st.slider("Operational Efficiency", -10, 20, 0, help="Cost reduction %")
        
        with col2:
            st.write("**Scenario Impact:**")
            if economy_slider > 10:
                st.success("Strong Growth Scenario")
                st.write("• Increased consumer spending")
                st.write("• Higher operational costs")
                st.write("• Market expansion opportunities")
            elif economy_slider > 0:
                st.info("Moderate Growth Scenario")
                st.write("• Steady market conditions")
                st.write("• Balanced cost structure")
            elif economy_slider < -10:
                st.error("Recession Scenario")
                st.write("• Reduced consumer demand")
                st.write("• Cost optimization critical")
                st.write("• Focus on efficiency")
            else:
                st.warning("Economic Uncertainty")
                st.write("• Mixed market signals")
                st.write("• Conservative planning advised")
        
        # Apply scenario adjustments to forecasts
        st.subheader("Adjusted Forecasts")
        
        for metric in ['Sales_USD', 'Costs_USD', 'Net_Cash_Flow']:
            if metric in forecasts:
                forecast_data = forecasts[metric]['data'].copy()
                
                # Apply adjustments
                if metric == 'Sales_USD':
                    adjustment_factor = 1 + (sales_adjustment / 100) * (marketing_multiplier)
                    forecast_data['Adjusted'] = forecast_data['Predicted'] * adjustment_factor
                elif metric == 'Costs_USD':
                    cost_factor = 1 + (costs_adjustment / 100) - (efficiency_gain / 100)
                    forecast_data['Adjusted'] = forecast_data['Predicted'] * cost_factor
                else:  # Net_Cash_Flow
                    # Recalculate based on adjusted sales and costs
                    if 'Sales_USD' in forecasts and 'Costs_USD' in forecasts:
                        adj_sales = forecasts['Sales_USD']['data']['Predicted'] * (1 + (sales_adjustment / 100) * marketing_multiplier)
                        adj_costs = forecasts['Costs_USD']['data']['Predicted'] * (1 + (costs_adjustment / 100) - (efficiency_gain / 100))
                        forecast_data['Adjusted'] = adj_sales - adj_costs
                    else:
                        forecast_data['Adjusted'] = forecast_data['Predicted']
                
                # Calculate per-month differences
                forecast_data['Difference'] = forecast_data['Adjusted'] - forecast_data['Predicted']
                forecast_data['Difference_Pct'] = (forecast_data['Difference'] / forecast_data['Predicted'] * 100).fillna(0)
                
                # Display scenario results
                fig = go.Figure()
                
                # Original forecast
                fig.add_trace(go.Scatter(
                    x=forecast_data['Date'], 
                    y=forecast_data['Predicted'],
                    mode='lines+markers',
                    name='Base Forecast',
                    line=dict(color='#00D4AA', width=2)
                ))
                
                # Adjusted forecast
                fig.add_trace(go.Scatter(
                    x=forecast_data['Date'], 
                    y=forecast_data['Adjusted'],
                    mode='lines+markers',
                    name='Scenario Adjusted',
                    line=dict(color='#FF6B6B', width=3)
                ))
                
                fig.update_layout(
                    title=f"{metric.replace('_', ' ').title()} - Base vs Scenario",
                    height=400,
                    showlegend=True
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # Per-month differences table
                with st.expander(f"{metric.replace('_', ' ').title()} - Monthly Differences"):
                    display_data = forecast_data[['Date', 'Predicted', 'Adjusted', 'Difference', 'Difference_Pct']].copy()
                    display_data['Date'] = display_data['Date'].dt.strftime('%Y-%m')
                    display_data['Predicted'] = display_data['Predicted'].apply(lambda x: f"${x:,.0f}" if 'USD' in metric else f"{x:.1f}")
                    display_data['Adjusted'] = display_data['Adjusted'].apply(lambda x: f"${x:,.0f}" if 'USD' in metric else f"{x:.1f}")
                    display_data['Difference'] = display_data['Difference'].apply(lambda x: f"${x:+,.0f}" if 'USD' in metric else f"{x:+.1f}")
                    display_data['Difference_Pct'] = display_data['Difference_Pct'].apply(lambda x: f"{x:+.1f}%")
                    
                    display_data.columns = ['Month', 'Base Forecast', 'Scenario Forecast', 'Difference', 'Difference %']
                    st.dataframe(display_data, use_container_width=True)
    
    else:
        st.info("Generate forecasts first to run scenarios")
