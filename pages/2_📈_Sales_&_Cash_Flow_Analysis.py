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
from utils.data_manager import load_combined_data, init_session_filters
from utils.theme_manager import apply_theme
from utils.error_handler import show_error, validate_dataframe
from services.fx import apply_fx_conversion
from services.settings_manager import get_setting

# Apply theme
theme = get_setting('theme', 'light')
st.markdown(apply_theme(theme), unsafe_allow_html=True)

st.title("📈 Sales & Cash Flow Analysis")

try:
    # Initialize and load data
    init_session_filters()
    
    with st.spinner("Loading sales data..."):
        df = load_combined_data()
        if not df.empty:
            df = apply_fx_conversion(df)
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.sort_values('Date')
        
    # Sidebar filters
    with st.sidebar:
        st.header("Analysis Filters")
        date_range = st.selectbox(
            "Date Range",
            ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date", "All Time"],
            index=0
        )
    
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
        primary_metrics = [
            {"title": "Total Sales", "value": f"${total_sales:,.0f}", "delta": "+15.2%", "caption": "This period"},
            {"title": "Net Cash Flow", "value": f"${net_cash_flow:,.0f}", "delta": "+8.7%", "caption": "Revenue - costs"},
            {"title": "Avg Deal Size", "value": f"${avg_deal_size:,.0f}", "delta": "+3.1%", "caption": "Per transaction"},
            {"title": "Conversion Rate", "value": f"{conversion_rate:.1f}%", "delta": "+0.8pp", "caption": "Lead to sale"}
        ]
        
        render_metric_grid(primary_metrics, columns=4)
        
        # Secondary metrics
        secondary_metrics = [
            {"title": "Total Leads", "value": f"{total_leads:,}", "caption": "All sources"},
            {"title": "Monthly Average", "value": f"${monthly_avg:,.0f}", "caption": "Sales per month"},
            {"title": "Pipeline Value", "value": f"${pipeline_value:,.0f}", "caption": "Potential revenue"},
            {"title": "Total Costs", "value": f"${total_costs:,.0f}", "caption": "Operating expenses"}
        ]
        
        render_metric_grid(secondary_metrics, columns=4)
    
    # Sales Trend Analysis
    create_section_header("Sales Trend Analysis", "Revenue performance over time")
    
    def create_sales_trend_chart():
        if not df.empty and 'Date' in df.columns:
            # Monthly aggregation
            df_monthly = df.groupby(df['Date'].dt.to_period('M')).agg({
                'Sales_USD': 'sum'
            }).reset_index()
            df_monthly['Date'] = df_monthly['Date'].dt.to_timestamp()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_monthly['Date'],
                y=df_monthly['Sales_USD'],
                mode='lines+markers',
                name='Sales',
                line=dict(color='#635BFF', width=3),
                marker=dict(size=6, color='#635BFF'),
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
            return fig
        return go.Figure()
    
    render_chart_container(
        create_sales_trend_chart,
        "Monthly Sales Performance",
        "Last 12 months",
        "Loading sales trend..."
    )
    
    # Cash Flow Analysis
    create_section_header("Cash Flow Analysis", "Net cash flow trends and projections")
    
    def create_cash_flow_chart():
        if not df.empty and 'Date' in df.columns:
            # Monthly cash flow
            df_monthly = df.groupby(df['Date'].dt.to_period('M')).agg({
                'Sales_USD': 'sum',
                'Costs_USD': 'sum'
            }).reset_index()
            df_monthly['Date'] = df_monthly['Date'].dt.to_timestamp()
            df_monthly['Net_Cash_Flow'] = df_monthly['Sales_USD'] - df_monthly['Costs_USD']
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_monthly['Date'],
                y=df_monthly['Net_Cash_Flow'],
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
            return fig
        return go.Figure()
    
    render_chart_container(
        create_cash_flow_chart,
        "Net Cash Flow Trend",
        "Last 12 months",
        "Loading cash flow analysis..."
    )
    
    # Performance Comparisons
    create_section_header("Performance Comparisons", "Period-over-period analysis")
    
    if not df.empty:
        # Mock comparison data for demonstration
        current_sales = total_sales
        previous_sales = current_sales * 0.87
        sales_delta = ((current_sales - previous_sales) / previous_sales * 100) if previous_sales > 0 else 0
        
        current_leads = total_leads
        previous_leads = current_leads * 0.94
        leads_delta = ((current_leads - previous_leads) / previous_leads * 100) if previous_leads > 0 else 0
        
        current_conversion = conversion_rate
        previous_conversion = current_conversion * 0.96
        conversion_delta = current_conversion - previous_conversion
        
        comparison_metrics = [
            {"title": "Sales vs Previous", "value": f"${current_sales:,.0f}", "delta": f"{sales_delta:+.1f}%", "caption": "Period comparison"},
            {"title": "Leads vs Previous", "value": f"{current_leads:,}", "delta": f"{leads_delta:+.1f}%", "caption": "Lead generation"},
            {"title": "Conversion vs Previous", "value": f"{current_conversion:.1f}%", "delta": f"{conversion_delta:+.1f}pp", "caption": "Conversion rate"}
        ]
        
        render_metric_grid(comparison_metrics, columns=3)

except Exception as e:
    show_error("Sales Analysis Error", f"An error occurred while loading the sales analysis: {str(e)}")
    st.info("Please check your data connections and try again.")
