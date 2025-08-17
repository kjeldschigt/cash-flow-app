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
from utils.data_manager import load_combined_data, filter_data_by_range, get_daily_aggregates, generate_due_costs
from utils.theme_manager import apply_current_theme
from utils.error_handler import show_error, validate_dataframe
from services.fx import apply_fx_conversion, get_monthly_rate
from services.settings_manager import get_setting
from services.storage import load_costs_data, load_table, upsert_from_csv, get_recurring_costs, add_recurring_cost, update_recurring_cost
from services.auth import require_auth

# Check authentication
require_auth()

# Apply theme
apply_current_theme()

st.title("💸 Cost Analysis & Management")

# Generate due costs from recurring costs
generate_due_costs()

try:
    # Load and process data
    df = load_combined_data()
    filtered_df = filter_data_by_range(df, "Last 30 Days")
    daily_agg = get_daily_aggregates(filtered_df)
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
    
    # Sidebar for cost entry forms
    with st.sidebar:
        st.header("Cost Management")
        
        # Cost entry options
        entry_type = st.radio(
            "Entry Type",
            ["One-off", "Recurring"],
            key="cost_entry_type"
        )
        
        if entry_type == "One-off":
            cost_entry_form()
        else:  # Recurring
            st.subheader("Recurring Cost Setup")
            
            with st.form("recurring_cost_form"):
                name = st.text_input("Cost Name", help="e.g., Office Rent, Software License")
                
                cost_categories = [
                    "Costa Rica USD", "Costa Rica CRC", "Hong Kong", 
                    "Huub Interest", "Google Ads", "Software", "Other"
                ]
                category = st.selectbox("Category", cost_categories)
                
                currency = st.selectbox("Currency", ["USD", "CRC"])
                amount = st.number_input("Amount", min_value=0.0, step=100.0)
                comment = st.text_area("Comment", help="Optional description")
                
                recurrence = st.selectbox(
                    "Recurrence",
                    ["Weekly", "Bi-weekly", "Monthly", "Every 2 months", "Quarterly", "Semiannual", "Yearly"]
                )
                
                next_due = st.date_input("Next Due Date")
                
                if st.form_submit_button("Add Recurring Cost"):
                    import uuid
                    recurring_cost = {
                        'id': str(uuid.uuid4()),
                        'name': name,
                        'category': category,
                        'currency': currency,
                        'amount_expected': amount,
                        'comment': comment,
                        'recurrence': recurrence.lower(),
                        'next_due_date': next_due.strftime('%Y-%m-%d'),
                        'active': True
                    }
                    
                    try:
                        add_recurring_cost(recurring_cost)
                        st.success(f"Added recurring cost: {name}")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error adding recurring cost: {str(e)}")
    
    # Cost Overview
    create_section_header("Cost Overview", "Monthly cost breakdown and analysis")
    
    cost_metrics = [
        {"title": "Total Monthly Costs", "value": f"${total_monthly_costs:,.0f}", "caption": "All categories combined"},
        {"title": "Fixed Costs", "value": f"${fixed_costs:,.0f}", "caption": "Costa Rica + HK + Interest"},
        {"title": "Variable Costs", "value": f"${variable_costs:,.0f}", "caption": "Principal + Google Ads"},
        {"title": "Stripe Fees", "value": f"{stripe_fee_pct:.1f}%", "caption": "Transaction fees"}
    ]
    
    render_metric_grid(cost_metrics, columns=4)
    
    # Cost Breakdown
    create_section_header("Cost Breakdown", "Detailed cost analysis by category")
    
    if not costs_df.empty:
        def create_cost_trend_chart():
            # Rename Amount_USD to Costs_USD for consistency with data_manager
            costs_df_renamed = costs_df.rename(columns={'Amount_USD': 'Costs_USD'})
            costs_df_renamed['Sales_USD'] = 0  # Add dummy sales column
            
            # Get daily aggregates and resample to monthly
            daily_data = get_daily_aggregates(costs_df_renamed)
            if not daily_data.empty:
                monthly_data = daily_data.set_index('Date').resample('ME').sum().reset_index()
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=monthly_data['Date'],
                    y=monthly_data['Costs_USD'],
                    mode='lines+markers',
                    name='Monthly Costs',
                    line=dict(color='#635BFF', width=3),
                    marker=dict(size=8, color='#635BFF')
                ))
                
                fig.update_layout(
                    title="",
                    xaxis_title="",
                    yaxis_title="Cost (USD)",
                    height=400,
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white'
                )
                
                fig.update_xaxes(showgrid=True, gridcolor='#f3f4f6')
                fig.update_yaxes(showgrid=True, gridcolor='#f3f4f6')
                
                st.plotly_chart(fig, use_container_width=True)
        
        render_chart_container(
            create_cost_trend_chart,
            "Monthly Cost Trends",
            "Cost tracking over time",
            "Loading cost analysis..."
        )
    
    # Cost Categories
    create_section_header("Cost Categories", "Breakdown by expense type")
    
    category_metrics = [
        {"title": "Costa Rica Operations", "value": f"${costa_usd_cr + costa_crc_usd:,.0f}", "caption": f"USD: ${costa_usd_cr:,.0f} + CRC: ${costa_crc_usd:,.0f}"},
        {"title": "Hong Kong Operations", "value": f"${hk_usd:,.0f}", "caption": "Monthly operational costs"},
        {"title": "Loan Payments", "value": f"${huub_principal + huub_interest:,.0f}", "caption": f"Principal: ${huub_principal:,.0f} + Interest: ${huub_interest:,.0f}"},
        {"title": "Marketing", "value": f"${google_ads:,.0f}", "caption": "Google Ads spend"}
    ]
    
    render_metric_grid(category_metrics, columns=2)
    
    # Recent Costs Table
    create_section_header("Recent Cost Entries", "Latest cost transactions")
    
    df = load_combined_data()
    recent_entries = df.sort_values('Date', ascending=False).head(10)
    if not recent_entries.empty:
        st.dataframe(recent_entries[['Date', 'Sales_USD', 'Costs_USD']], use_container_width=True)
    else:
        st.info("No recent cost entries available")
    st.caption("Recent cost entries from database")
    
    # Recurring Costs Management
    create_section_header("Recurring Costs", "Manage recurring cost schedules")
    
    recurring_costs_df = get_recurring_costs()
    if not recurring_costs_df.empty:
        for _, cost in recurring_costs_df.iterrows():
            col1, col2, col3, col4 = st.columns([3, 2, 1, 1])
            
            with col1:
                st.write(f"**{cost['name']}** - {cost['category']}")
                st.caption(f"${cost['amount_expected']:,.0f} {cost.get('currency', 'USD')} - {cost['recurrence']}")
            
            with col2:
                st.write(f"Next: {cost['next_due_date']}")
                if cost.get('comment'):
                    st.caption(cost['comment'])
            
            with col3:
                if st.button("Edit", key=f"edit_{cost['id']}"):
                    st.session_state[f"edit_mode_{cost['id']}"] = True
            
            with col4:
                current_status = "Active" if cost.get('active', True) else "Paused"
                new_status = st.toggle(current_status, value=cost.get('active', True), key=f"toggle_{cost['id']}")
                if new_status != cost.get('active', True):
                    update_recurring_cost(cost['id'], active=new_status)
                    st.rerun()
            
            # Edit mode
            if st.session_state.get(f"edit_mode_{cost['id']}", False):
                with st.expander(f"Edit {cost['name']}", expanded=True):
                    with st.form(f"edit_form_{cost['id']}"):
                        new_amount = st.number_input("Amount", value=float(cost['amount_expected']), min_value=0.0, step=100.0)
                        new_recurrence = st.selectbox(
                            "Recurrence",
                            ["Weekly", "Bi-weekly", "Monthly", "Every 2 months", "Quarterly", "Semiannual", "Yearly"],
                            index=["weekly", "bi-weekly", "monthly", "every 2 months", "quarterly", "semiannual", "yearly"].index(cost['recurrence'].lower()) if cost['recurrence'].lower() in ["weekly", "bi-weekly", "monthly", "every 2 months", "quarterly", "semiannual", "yearly"] else 0
                        )
                        
                        col_save, col_cancel = st.columns(2)
                        with col_save:
                            if st.form_submit_button("Save Changes"):
                                update_recurring_cost(cost['id'], 
                                                    amount_expected=new_amount,
                                                    recurrence=new_recurrence.lower())
                                st.session_state[f"edit_mode_{cost['id']}"] = False
                                st.success("Updated recurring cost")
                                st.rerun()
                        
                        with col_cancel:
                            if st.form_submit_button("Cancel"):
                                st.session_state[f"edit_mode_{cost['id']}"] = False
                                st.rerun()
            
            st.divider()
    else:
        st.info("No recurring costs configured. Use the sidebar to add recurring costs.")
    
    # Monthly Costs Summary
    create_section_header("Monthly Summary", "Cost breakdown by month")
    
    # Replace SQL queries with data_manager functions
    df = load_combined_data()
    daily = get_daily_aggregates(df)
    if not daily.empty:
        monthly = daily.groupby(daily['Date'].dt.to_period('M').dt.to_timestamp()).agg({'Costs_USD': 'sum'}).reset_index()
        monthly['Month'] = monthly['Date'].astype(str)
        
        if not monthly.empty:
            st.dataframe(monthly[['Month', 'Costs_USD']], use_container_width=True)
        else:
            st.info("No monthly cost data available")
    else:
        st.info("No cost data available for monthly summary")

except Exception as e:
    show_error("Cost Analysis Error", f"An error occurred while loading the cost analysis: {str(e)}")
    st.info("Please check your data connections and try again.")
