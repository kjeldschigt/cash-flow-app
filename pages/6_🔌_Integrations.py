import streamlit as st
import sys
import os
import json
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.theme_manager import get_setting, apply_theme
from services.airtable import get_airtable_data, get_lead_metrics, fetch_airtable
from services.stripe import get_stripe_payments, get_payment_metrics, fetch_stripe_payments

# Apply theme
theme = get_setting('theme', 'light')
st.markdown(apply_theme(theme), unsafe_allow_html=True)

st.title("API Integrations & Data Sources")

# Integration overview
st.subheader("Integration Status")

col1, col2 = st.columns(2, gap="small")

with col1:
    st.subheader("Airtable Integration")
    
    # Get status from fetch_airtable()[1]
    with st.spinner("Checking Airtable connection..."):
        df, airtable_status = fetch_airtable()
    
    # Display status with appropriate styling
    if airtable_status == "Not Configured":
        st.error(f"🔴 Airtable: {airtable_status}")
        st.info("Configure AIRTABLE_API_KEY, AIRTABLE_BASE_ID, and AIRTABLE_TABLE_NAME in .env file")
    elif "Connected" in airtable_status:
        st.success(f"🟢 Airtable: {airtable_status}")
    else:
        st.warning(f"🟡 Airtable: {airtable_status}")
    
    if not df.empty:
        total_leads = len(df)
        st.metric("Total Leads", total_leads)
    else:
        st.metric("Total Leads", 0)
    
    st.write("Purpose: Lead and sales pipeline data")

with col2:
    st.subheader("Stripe Integration")
    
    # Get status from fetch_stripe_payments()[1]
    with st.spinner("Checking Stripe connection..."):
        stripe_status = fetch_stripe_payments()[1]
        st.write(f"Stripe: {stripe_status}")
        
        df, _ = fetch_stripe_payments()
    if not df.empty:
        gross_volume = df['amount'].sum()
        st.metric("Gross Volume", f"${gross_volume:,.0f}")
    
    st.write("Purpose: Payment processing data")

# Airtable section
st.subheader("Airtable Data")

col1, col2 = st.columns(2, gap="small")

with col1:
    if st.button('Fetch Airtable Leads', type="primary"):
        try:
            airtable_data = get_airtable_data()
            st.session_state.airtable_data = airtable_data
            st.success("Airtable data fetched successfully!")
        except Exception as e:
            st.error(f"Error fetching Airtable data: {str(e)}")

with col2:
    if st.button('Get Lead Metrics', type="secondary"):
        try:
            lead_metrics = get_lead_metrics()
            st.session_state.lead_metrics = lead_metrics
            st.success("Lead metrics calculated!")
        except Exception as e:
            st.error(f"Error calculating lead metrics: {str(e)}")

# Display Airtable data
if 'airtable_data' in st.session_state:
    st.write("**Airtable Leads Data:**")
    leads_df = pd.DataFrame(st.session_state.airtable_data['leads'])
    st.dataframe(leads_df, use_container_width=True)
    
    # Lead status breakdown
    status_counts = leads_df['status'].value_counts()
    col1, col2 = st.columns(2, gap="small")
    
    with col1:
        st.write("**Lead Status Breakdown:**")
        for status, count in status_counts.items():
            st.write(f"• {status.title()}: {count}")
    
    with col2:
        st.bar_chart(status_counts)

if 'lead_metrics' in st.session_state:
    st.write("**📈 Lead Metrics Summary:**")
    metrics = st.session_state.lead_metrics
    
    col1, col2, col3, col4 = st.columns(4, gap="small")
    with col1:
        st.metric("Total Leads", metrics['total_leads'])
    with col2:
        st.metric("Total Value", f"${metrics['total_value']:,.0f}")
    with col3:
        st.metric("Qualified Leads", metrics['qualified_leads'])
    with col4:
        st.metric("Avg Lead Value", f"${metrics['avg_lead_value']:,.0f}")

# Stripe section with range selector and visualization
st.subheader("Stripe Payments")

# Range selector
range_select = st.selectbox("Range", ["YTD", "Last 12m", "QTD", "Last 7d", "YTD vs LY"])

# Fetch Stripe data with selected range
with st.spinner(f"Fetching Stripe data for {range_select}..."):
    df_stripe, stripe_status = fetch_stripe_payments(range_select.lower())

if not df_stripe.empty:
    # Calculate metrics
    gross_volume = df_stripe['amount'].sum()
    fee_pct = 0.029  # Stripe standard fee ~2.9%
    net_sales = gross_volume * (1 - fee_pct)
    spend_per_customer = gross_volume / df_stripe.shape[0] if df_stripe.shape[0] > 0 else 0
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4, gap="small")
    with col1:
        st.metric("Gross Volume", f"${gross_volume:,.0f}")
    with col2:
        st.metric("Net Sales", f"${net_sales:,.0f}")
    with col3:
        st.metric("Spend per Customer", f"${spend_per_customer:,.0f}")
    with col4:
        st.metric("Total Transactions", len(df_stripe))
    
    # Line chart for gross volume over time
    st.subheader("Gross Volume Trend")
    chart_data = df_stripe.set_index('date')['amount']
    st.line_chart(chart_data)
    
    # Store in session state for compatibility
    st.session_state.stripe_data = df_stripe.to_dict('records')
else:
    st.warning(f"Stripe Status: {stripe_status}")

col1, col2 = st.columns(2, gap="small")

with col1:
    if st.button('Refresh Stripe Data', type="primary"):
        st.session_state.stripe_refresh_requested = True

with col2:
    if st.button('Get Payment Metrics', type="secondary"):
        try:
            payment_metrics = get_payment_metrics()
            st.session_state.payment_metrics = payment_metrics
            st.success("Payment metrics calculated!")
        except Exception as e:
            st.error(f"Error calculating payment metrics: {str(e)}")

# Display Stripe data
if 'stripe_data' in st.session_state:
    st.write("**Stripe Payments Data:**")
    payments_df = pd.DataFrame(st.session_state.stripe_data)
    st.dataframe(payments_df, use_container_width=True)
    
    # Payment status breakdown
    status_counts = payments_df['status'].value_counts()
    col1, col2 = st.columns(2, gap="small")
    
    with col1:
        st.write("**Payment Status Breakdown:**")
        for status, count in status_counts.items():
            st.write(f"• {status.title()}: {count}")
    
    with col2:
        st.bar_chart(status_counts)

if 'payment_metrics' in st.session_state:
    st.write("**📊 Payment Metrics Summary:**")
    metrics = st.session_state.payment_metrics
    
    col1, col2, col3, col4 = st.columns(4, gap="small")
    with col1:
        st.metric("Total Payments", metrics['total_payments'])
    with col2:
        st.metric("Succeeded", metrics['succeeded_payments'])
    with col3:
        st.metric("Total Amount", f"${metrics['total_amount']:,.0f}")
    with col4:
        st.metric("Avg Payment", f"${metrics['avg_payment']:,.0f}")

# Webhook simulation
st.subheader("Webhook Simulation")

st.write("**Test webhook payload processing:**")

webhook_payload = st.text_area(
    "Webhook Payload (JSON format)", 
    placeholder='{"event": "payment.succeeded", "amount": 2500, "currency": "usd"}',
    height=100
)

if webhook_payload:
    try:
        parsed_data = json.loads(webhook_payload)
        st.success("Valid JSON payload!")
        
        st.write("**Parsed Webhook Data:**")
        st.json(parsed_data)
        
        # Process webhook based on event type
        if 'event' in parsed_data:
            event_type = parsed_data['event']
            
            if event_type == 'payment.succeeded':
                st.success("Payment succeeded webhook processed!")
                if 'amount' in parsed_data:
                    st.write(f"Payment amount: ${parsed_data['amount']:,.2f}")
            
            elif event_type == 'lead.created':
                st.info("New lead webhook processed!")
                if 'value' in parsed_data:
                    st.write(f"Lead value: ${parsed_data['value']:,.2f}")
            
            else:
                st.info(f"Webhook event '{event_type}' received and logged")
        
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON format: {str(e)}")

# API Configuration
st.subheader("API Configuration")

with st.expander("API Settings"):
    st.write("**Environment Variables Status:**")
    
    # Check for API keys (without displaying them)
    airtable_key_status = "Set" if os.getenv('AIRTABLE_API_KEY') else "Not Set"
    stripe_key_status = "Set" if os.getenv('STRIPE_API_KEY') else "Not Set"
    
    col1, col2 = st.columns(2, gap="small")
    with col1:
        st.write(f"Airtable API Key: {airtable_key_status}")
    with col2:
        st.write(f"Stripe API Key: {stripe_key_status}")
    
    st.info("API keys are loaded from the .env file. Update the .env file to configure real API connections.")

# Integration health check
st.subheader("API Health Checks")

if st.button("Run Health Check", type="primary"):
    st.write("**Running integration health check...**")
    
    # Check Airtable
    try:
        airtable_data = get_airtable_data()
        st.success("Airtable: Connection OK")
    except Exception as e:
        st.error(f"Airtable: {str(e)}")
    
    # Check Stripe
    try:
        stripe_data = get_stripe_payments()
        st.success("Stripe: Connection OK")
    except Exception as e:
        st.error(f"Stripe: {str(e)}")
    
    st.info("Health check completed. All integrations are using mock data until API keys are configured.")
