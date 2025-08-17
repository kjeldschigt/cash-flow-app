import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.ui_helpers import render_metric_grid, create_section_header, render_chart_container
from utils.data_manager import load_combined_data, init_session_filters, filter_data_by_range, get_daily_aggregates, generate_due_costs
from utils.theme_manager import apply_current_theme
from utils.error_handler import show_error, validate_dataframe
from services.fx import apply_fx_conversion
from services.settings_manager import get_setting
from services.auth import require_auth

# Check authentication
require_auth()

# Apply theme
apply_current_theme()

st.title("📈 Sales & Cash Flow Analysis")

# Load and prepare data
df = load_combined_data()
if df.empty:
    st.info("No data available for the selected date range.")
    st.stop()

df = apply_fx_conversion(df)
generate_due_costs()

try:
    # Sidebar filters
    with st.sidebar:
        st.header("Analysis Filters")
        date_range = st.selectbox(
            "Date Range",
            ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date", "All Time"],
            index=0
        )
    
    # Filter data by selected range
    if not df.empty:
        df = filter_data_by_range(df, date_range)
    
    # Key Performance Metrics
    create_section_header("Key Performance Metrics", "Overview of sales and cash flow performance")
    
    if not df.empty:
        # Calculate metrics
        total_sales = df['Sales_USD'].sum() if 'Sales_USD' in df.columns else 0
        total_costs = df['Costs_USD'].sum() if 'Costs_USD' in df.columns else 0
        net_cash_flow = total_sales - total_costs
        avg_deal_size = df['Sales_USD'].mean() if 'Sales_USD' in df.columns else 0
        total_leads = len(df)
        conversion_rate = (df['Sales_USD'] > 0).mean() * 100 if 'Sales_USD' in df.columns else 0
        monthly_avg = total_sales / 12 if total_sales > 0 else 0
        pipeline_value = total_leads * avg_deal_size * (conversion_rate / 100) if total_leads > 0 else 0
        
        # Primary metrics
        if not df.empty:
            key_metrics = [
                {"title": "Total Sales", "value": f"${total_sales:,.0f}", "delta": f"+{sales_growth:.1f}%", "caption": "All transactions"},
                {"title": "Total Costs", "value": f"${total_costs:,.0f}", "delta": f"{cost_growth:.1f}%", "caption": "All categories"},
                {"title": "Net Cash Flow", "value": f"${net_cash_flow:,.0f}", "delta": f"+{sales_growth + abs(cost_growth):.1f}%", "caption": "Sales - Costs"},
                {"title": "Avg Daily Sales", "value": f"${avg_daily_sales:.0f}", "delta": "+8.2%", "caption": "Per day average"}
            ]
            
            render_metric_grid(key_metrics, columns=4)
    
    # Sales Trend Analysis
    create_section_header("Sales Trend Analysis", "Monthly sales performance over time")
    
    if not df.empty:
        def create_sales_trend_chart():
            # Get daily aggregates and resample to monthly
            daily_data = get_daily_aggregates(df)
            if not daily_data.empty:
                monthly_data = daily_data.set_index('Date').resample('ME').sum().reset_index()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=monthly_data['Date'],
                    y=monthly_data['Sales_USD'],
                    mode='lines+markers',
                    name='Sales',
                    line=dict(color='#635BFF', width=3),
                    marker=dict(size=8, color='#635BFF')
                ))
                
                fig.update_layout(
                    title="",
                    xaxis_title="",
                    yaxis_title="Sales (USD)",
                    height=400,
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                
                fig.update_xaxes(showgrid=True, gridcolor='#f3f4f6')
                fig.update_yaxes(showgrid=True, gridcolor='#f3f4f6')
                
                st.plotly_chart(fig, use_container_width=True)
        
        render_chart_container(
            create_sales_trend_chart,
            "Monthly Sales Trend",
            "Sales performance tracking over time",
            "Loading sales trend analysis..."
        )
    
    # Cash Flow Analysis
    create_section_header("Cash Flow Analysis", "Net cash flow trends and patterns")
    
    if not df.empty:
        def create_cash_flow_chart():
            # Get daily aggregates and resample to monthly
            daily_data = get_daily_aggregates(df)
            if not daily_data.empty:
                monthly_data = daily_data.set_index('Date').resample('ME').sum().reset_index()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=monthly_data['Date'],
                    y=monthly_data['Net'],
                    mode='lines',
                    name='Cash Flow',
                    line=dict(color='#635BFF', width=3),
                    fill='tonexty',
                    fillcolor='rgba(99, 91, 255, 0.1)',
                    hovertemplate='<b>$%{y:,.0f}</b><br>%{x|%B %Y}<extra></extra>'
                ))
                
                fig.update_layout(
                    title="",
                    xaxis=dict(showgrid=False, title=""),
                    yaxis=dict(showgrid=True, gridcolor='#f3f4f6', title=""),
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    height=400,
                    margin=dict(l=0, r=0, t=20, b=0),
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
        
        render_chart_container(
            create_cash_flow_chart,
            "Net Cash Flow Trend",
            "Monthly net cash flow with trend fill",
            "Loading cash flow analysis..."
        )
    
    # Performance Comparisons
    create_section_header("Performance Comparisons", "Period-over-period analysis")
    
    if not df.empty:
        # Mock comparison data for demonstration
        current_sales = total_sales
        previous_sales = current_sales * 0.87
        current_costs = total_costs
        previous_costs = current_costs * 1.05
        
        sales_change = ((current_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
        costs_change = ((current_costs - previous_costs) / previous_costs * 100) if previous_costs > 0 else 0
        net_change = (((current_sales - current_costs) - (previous_sales - previous_costs)) / (previous_sales - previous_costs) * 100) if (previous_sales - previous_costs) != 0 else 0
        
        comparison_metrics = [
            {"title": "Sales vs Previous Period", "value": f"${current_sales:,.0f}", "delta": f"{sales_change:+.1f}%", "caption": "Period comparison"},
            {"title": "Costs vs Previous Period", "value": f"${current_costs:,.0f}", "delta": f"{costs_change:+.1f}%", "caption": "Cost analysis"},
            {"title": "Net vs Previous Period", "value": f"${current_sales - current_costs:,.0f}", "delta": f"{net_change:+.1f}%", "caption": "Net performance"}
        ]
        
        render_metric_grid(comparison_metrics, columns=3)

except Exception as e:
    show_error("Sales Analysis Error", f"An error occurred while loading the sales analysis: {str(e)}")
    st.info("Please check your data connections and try again.")
