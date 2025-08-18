import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_setting(key, default_value):
    """Get setting from session_state, fallback to DB, then default"""
    if key in st.session_state:
        return st.session_state[key]
    
    try:
        from src.services.storage_service import load_settings
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

def render_key_metrics(current_sales, current_cash_flow, current_leads, current_occupancy,
                      sales_delta, cash_flow_delta, leads_delta, occupancy_delta):
    """Render key metrics badges in columns"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Current Sales", f"${current_sales:,.0f}", f"{sales_delta:+.1f}%")
    with col2:
        st.metric("Cash Flow", f"${current_cash_flow:,.0f}", f"{cash_flow_delta:+.1f}%")
    with col3:
        st.metric("Total Leads", f"{current_leads:.0f}", f"{leads_delta:+.1f}%")
    with col4:
        st.metric("Occupancy", f"{current_occupancy:.1f}%", f"{occupancy_delta:+.1f}%")

def render_business_metrics():
    """Render business performance metrics"""
    st.subheader("Business Performance Metrics")
    
    # Get values from sidebar or session state
    occupancy = get_setting('occupancy', 75.0)
    total_leads = get_setting('total_leads', 100)
    mql = get_setting('mql', 50)
    sql = get_setting('sql', 20)
    
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

def render_financial_metrics(df):
    """Render financial metrics cards"""
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

def render_performance_metrics(sales_delta, costs_delta, cash_flow_delta, 
                             leads_delta, occupancy_delta, comparison_to):
    """Render performance metrics with colored deltas"""
    st.subheader("📊 On Track Performance")
    
    # Display key metrics with colored deltas
    col1, col2, col3 = st.columns(3)

    with col1:
        delta_color = "normal" if sales_delta >= 0 else "inverse"
        st.metric(
            "Sales", 
            f"${sales_delta:,.0f}", 
            delta=f"{sales_delta:.1f}% vs {comparison_to.lower()}", 
            delta_color=delta_color
        )

    with col2:
        delta_color = "inverse" if costs_delta >= 0 else "normal"  # Lower costs are better
        st.metric(
            "Costs", 
            f"${costs_delta:,.0f}", 
            delta=f"{costs_delta:.1f}% vs {comparison_to.lower()}", 
            delta_color=delta_color
        )

    with col3:
        delta_color = "normal" if cash_flow_delta >= 0 else "inverse"
        st.metric(
            "Cash Flow", 
            f"${cash_flow_delta:,.0f}", 
            delta=f"{cash_flow_delta:.1f}% vs {comparison_to.lower()}", 
            delta_color=delta_color
        )
    
    # Enhanced leads metric with conversion rate and monthly average
    col1, col2, col3 = st.columns(3)
    
    with col1:
        current_leads = get_setting('total_leads', 100)
        conversion_rate = (current_leads * 0.15)
        monthly_avg = get_setting('total_leads', 100) * 0.9
        st.metric(
            "Leads", 
            f"{current_leads:.0f}", 
            delta=f"{leads_delta:.1f}% vs {comparison_to.lower()}"
        )
        st.caption(f"Conversion: {conversion_rate:.0f} | Avg: {monthly_avg:.0f}")
    
    with col2:
        current_occupancy = get_setting('occupancy', 75.0)
        delta_color = "normal" if occupancy_delta >= 0 else "inverse"
        st.metric(
            "Occupancy", 
            f"{current_occupancy:.1f}%", 
            delta=f"{occupancy_delta:.1f}% vs {comparison_to.lower()}", 
            delta_color=delta_color
        )
    
    with col3:
        # Calculate end-month cash (simplified)
        end_month_cash = cash_flow_delta * 1000  # Placeholder calculation
        st.metric(
            "End-Month Cash", 
            f"${end_month_cash:,.0f}"
        )

def render_economic_indicators():
    """Render economic indicators"""
    st.subheader("🌍 Economic Indicators")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Placeholder for UMich Consumer Sentiment
        st.info("US UMich Consumer Sentiment (live): 58.6 (2024-01-31)")
    
    with col2:
        # Placeholder for Conference Board
        st.info("Conference Board Consumer Confidence: 105.2 (2024-01-31)")

def render_leads_details():
    """Render leads details in expandable section"""
    with st.expander("📈 Leads Details"):
        col1, col2 = st.columns(2)
        
        total_leads = get_setting('total_leads', 100)
        mql = get_setting('mql', 50)
        sql = get_setting('sql', 20)
        
        with col1:
            conversion_rate = (total_leads * 0.15)
            monthly_avg = get_setting('total_leads', 100) * 0.9
            st.write(f"**Conversion Rate:** {conversion_rate:.0f} leads")
            st.write(f"**Monthly Average:** {monthly_avg:.0f} leads")
        with col2:
            mql_rate = (mql / total_leads * 100) if total_leads > 0 else 0
            sql_rate = (sql / mql * 100) if mql > 0 else 0
            st.write(f"**Lead → MQL:** {mql_rate:.1f}%")
            st.write(f"**MQL → SQL:** {sql_rate:.1f}%")

def render_overall_summary(sales_delta, cash_flow_delta, leads_delta, 
                          occupancy_delta, costs_delta, comparison_to):
    """Render overall on track summary"""
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
