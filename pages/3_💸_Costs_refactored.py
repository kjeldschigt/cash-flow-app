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
from components.cost_entry import cost_entry_form, monthly_cost_form, bulk_cost_entry_form, display_recent_costs, display_monthly_costs_table
from utils.data_manager import load_combined_data, init_session_filters
from utils.theme_manager import apply_theme
from utils.error_handler import show_error, validate_dataframe
from services.fx import apply_fx_conversion, get_monthly_rate
from services.settings_manager import get_setting
from services.storage import load_costs_data, load_table, upsert_from_csv

# Apply theme
theme = get_setting('theme', 'light')
st.markdown(apply_theme(theme), unsafe_allow_html=True)

st.title("💸 Cost Analysis & Management")

try:
    # Initialize and load data
    init_session_filters()
    
    with st.spinner("Loading cost data..."):
        df = load_combined_data()
        costs_df = load_costs_data()
        
        # Get cost values from settings
        costa_usd_cr = get_setting('costa_usd', 19000.0)
        costa_crc = get_setting('costa_crc', 38000000.0)
        hk_usd = get_setting('hk_usd', 40000.0)
        stripe_fee_pct = get_setting('stripe_fee', 4.2)
        huub_principal = get_setting('huub_principal', 1250000.0)
        huub_interest = get_setting('huub_interest', 18750.0)
        google_ads = get_setting('google_ads', 27500.0)
        
        # Convert CRC to USD
        current_fx_rate = get_monthly_rate('2024-08', 'base')
        costa_crc_usd = costa_crc / current_fx_rate if current_fx_rate > 0 else 0
        
        # Calculate totals
        total_monthly_costs = costa_usd_cr + costa_crc_usd + hk_usd + huub_principal + huub_interest + google_ads
        fixed_costs = costa_usd_cr + costa_crc_usd + hk_usd + huub_interest
        variable_costs = google_ads
        cost_per_day = total_monthly_costs / 30
    
    # Sidebar filters
    with st.sidebar:
        st.header("Cost Filters")
        date_range = st.selectbox(
            "Date Range",
            ["Last 30 Days", "Last 60 Days", "Last 90 Days", "Year to Date", "All Time"],
            index=0
        )
    
    # Key Cost Metrics
    create_section_header("Key Cost Metrics", "Overview of operational expenses")
    
    primary_metrics = [
        {"title": "Total Monthly Costs", "value": f"${total_monthly_costs:,.0f}", "delta": "+2.1%", "caption": "All expenses"},
        {"title": "Fixed Costs", "value": f"${fixed_costs:,.0f}", "delta": "Stable", "caption": "Recurring expenses"},
        {"title": "Variable Costs", "value": f"${variable_costs:,.0f}", "delta": "+8.5%", "caption": "Marketing & fees"},
        {"title": "Cost per Day", "value": f"${cost_per_day:,.0f}", "caption": "Daily burn rate"}
    ]
    
    render_metric_grid(primary_metrics, columns=4)
    
    # Cost Breakdown Chart
    create_section_header("Cost Distribution", "Breakdown by category")
    
    def create_cost_breakdown_chart():
        categories = ['Costa Rica USD', 'Costa Rica CRC', 'Hong Kong', 'Huub Interest', 'Google Ads']
        values = [costa_usd_cr, costa_crc_usd, hk_usd, huub_interest, google_ads]
        
        fig = go.Figure(data=[go.Pie(
            labels=categories,
            values=values,
            hole=0.4,
            marker_colors=['#635BFF'] * len(categories),
            hovertemplate='<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>'
        )])
        
        fig.update_layout(
            title="",
            showlegend=True,
            height=400,
            margin=dict(l=0, r=0, t=20, b=0),
            plot_bgcolor='white',
            paper_bgcolor='white'
        )
        return fig
    
    render_chart_container(
        create_cost_breakdown_chart,
        "Monthly Cost Distribution",
        "Current month breakdown",
        "Loading cost breakdown..."
    )
    
    # Revenue Impact Analysis
    create_section_header("Revenue Impact Analysis", "Cost efficiency and margins")
    
    if not df.empty and 'Sales_USD' in df.columns:
        total_sales = df['Sales_USD'].sum()
        stripe_fees = total_sales * (stripe_fee_pct / 100)
        total_all_costs = total_monthly_costs + stripe_fees
        gross_margin = total_sales - total_all_costs
        margin_percentage = (gross_margin / total_sales * 100) if total_sales > 0 else 0
        
        revenue_metrics = [
            {"title": "Total Revenue", "value": f"${total_sales:,.0f}", "caption": "This period"},
            {"title": "Total Costs", "value": f"${total_all_costs:,.0f}", "caption": "Including fees"},
            {"title": "Gross Margin", "value": f"${gross_margin:,.0f}", "caption": "Net profit"},
            {"title": "Margin %", "value": f"{margin_percentage:.1f}%", "caption": "Profit margin"}
        ]
        
        render_metric_grid(revenue_metrics, columns=4)
    
    # Cost Trends
    create_section_header("Cost Trends", "Historical cost analysis")
    
    def create_cost_trend_chart():
        if not costs_df.empty and 'Date' in costs_df.columns:
            costs_df_sorted = costs_df.sort_values('Date')
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=costs_df_sorted['Date'],
                y=costs_df_sorted['Costs_USD'],
                mode='lines+markers',
                name='Costs',
                line=dict(color='#635BFF', width=3),
                marker=dict(size=6, color='#635BFF'),
                hovertemplate='<b>$%{y:,.0f}</b><br>%{x}<extra></extra>'
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
        create_cost_trend_chart,
        "Cost Trend Over Time",
        "Last 12 months",
        "Loading cost trends..."
    )
    
    # Cost Entry Forms
    create_section_header("Cost Entry", "Add and manage cost entries")
    
    # Monthly cost form
    monthly_cost_form(form_key="main_monthly")
    
    # Recent entries
    st.subheader("Recent Cost Entries")
    display_recent_costs(limit=10)
    st.caption("Last 10 cost entries from database")
    
    # Monthly costs table
    st.subheader("Monthly Cost Summary")
    display_monthly_costs_table()
    st.caption("Monthly cost breakdown from database")

except Exception as e:
    show_error("Cost Analysis Error", f"An error occurred while loading the cost analysis: {str(e)}")
    st.info("Please check your data connections and try again.")
