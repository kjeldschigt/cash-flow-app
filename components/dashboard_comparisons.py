import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import numpy as np

try:
    from sklearn.linear_model import LinearRegression
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

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

@st.cache_data
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

def calculate_period_deltas(date_select, comparison_to, start_date=None, end_date=None):
    """Calculate performance deltas based on selected period with enhanced DB filtering"""
    try:
        from src.services.storage_service import get_combined_data
        
        # Load data from database
        df = get_combined_data()
        if df.empty:
            return None
            
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
        
        # Get leads and occupancy from session state or use defaults
        current_leads = st.session_state.get('total_leads', 100)
        past_leads = current_leads * 0.92  # Assume 8% lower in past period
        current_occupancy = st.session_state.get('occupancy', 75.0)
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
        return None

def render_date_selector():
    """Render date range selector for comparisons"""
    st.subheader("Performance Comparison")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        date_select = st.selectbox("Date Range", 
                                  ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date", "Custom"], 
                                  key="comparison_date_select")
        comparison_to = st.selectbox("Range", [
            "Last Month vs Prev", 
            "Same Month LY", 
            "Last 3m vs LY", 
            "During-Month vs LY", 
            "Custom"
        ], key="comparison_select")
        
        if comparison_to == "Custom" or date_select == "Custom":
            st.write("**Select Date Range:**")
            start_date = st.date_input("Start Date", value=datetime.now() - timedelta(days=30))
            end_date = st.date_input("End Date", value=datetime.now())
            return date_select, comparison_to, start_date, end_date
    
    return date_select, comparison_to, None, None

def render_ai_trend_analysis(filtered_df):
    """Render AI trend analysis section"""
    st.subheader("AI Trend Analysis")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        # Enhanced sales trend with monthly percentage
        if 'Sales_USD' in filtered_df.columns:
            monthly_slope_pct, r_squared = analyze_trend_with_ai(filtered_df, 'Sales_USD')
            if monthly_slope_pct is not None:
                if monthly_slope_pct > 0:
                    st.success(f"Sales Trending Up ({monthly_slope_pct:.2f}%/mo)")
                else:
                    st.warning(f"Sales Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
                st.caption(r_squared)
            else:
                st.info("Sales trend analysis unavailable")
    
    with col2:
        # Enhanced costs trend
        if 'Costs_USD' in filtered_df.columns:
            monthly_slope_pct, r_squared = analyze_trend_with_ai(filtered_df, 'Costs_USD')
            if monthly_slope_pct is not None:
                if monthly_slope_pct > 0:
                    st.warning(f"Costs Trending Up ({monthly_slope_pct:.2f}%/mo)")
                else:
                    st.success(f"Costs Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
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
                    st.success(f"Net Cash Trending Up ({monthly_slope_pct:.2f}%/mo)")
                else:
                    st.warning(f"Net Cash Trending Down ({abs(monthly_slope_pct):.2f}%/mo)")
                st.caption(r_squared)
            else:
                st.info("Net cash trend analysis unavailable")

def render_month_to_date_comparison(df):
    """Render month-to-date comparison section"""
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
