import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from datetime import datetime, timedelta
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.ui_helpers import render_metric_grid, create_section_header, render_chart_container
# from services.loan import Loan  # Commented out for now
class Loan:
    def __init__(self, amount=0, rate=0, term=0):
        self.amount = amount
        self.rate = rate
        self.term = term
from src.utils.data_manager import load_combined_data, init_session_filters, filter_data_by_range, get_daily_aggregates
from src.utils.theme_manager import apply_theme
from src.services.error_handler import show_error
from src.services.settings_service import get_setting
from src.services.fx_service import get_monthly_rate
from src.services.storage_service import load_table
from src.security.auth import require_auth

# Check authentication
require_auth()

# Apply theme
theme = get_setting('theme', 'light')
st.markdown(apply_theme(theme), unsafe_allow_html=True)

st.title("🏦 Loan Tracking & Management")

# Fixed loan parameters
LOAN_TERM_YEARS = 5
ANNUAL_INTEREST = 18750
MIN_REPAYMENT = 10000

def extract_from_email(payload):
    """Extract repayment amount from email payload using regex"""
    match = re.search(r'\$([0-9,]+(?:\.[0-9]{2})?)', payload)
    if match:
        amount_str = match.group(1).replace(',', '')
        try:
            return float(amount_str)
        except ValueError:
            return 0
    return 0

def make_payment(amount):
    """Process a payment and update loan"""
    if amount >= MIN_REPAYMENT:
        st.session_state.loan.make_payment(amount)
        return True
    return False

try:
    # Initialize loan in session state
    if 'loan' not in st.session_state:
        st.session_state.loan = Loan()

    loan = st.session_state.loan
    loan_summary = loan.get_loan_summary()

    # Sidebar Controls
    with st.sidebar:
        st.header("Loan Controls")
        
        # Email Payment Processing
        st.subheader("Email Payment")
        payload = st.text_area("Paste Email Content", height=100, 
                              placeholder="Paste email content containing payment information...")
        
        if st.button("Extract Payment", type="primary"):
            if payload.strip():
                amount = extract_from_email(payload)
                if amount > 0:
                    if amount >= MIN_REPAYMENT:
                        success = make_payment(amount)
                        if success:
                            st.success(f"Extracted ${amount:,.0f}")
                            st.rerun()
                        else:
                            st.error("Failed to process payment")
                    else:
                        st.warning(f"Amount ${amount:,.0f} below minimum ${MIN_REPAYMENT:,.0f}")
                else:
                    st.error("No dollar amount found in email")
            else:
                st.warning("Please paste email content first")
        
        # Manual Payment
        st.subheader("Manual Payment")
        payment_amount = st.number_input("Payment Amount ($)", 
                                       min_value=float(MIN_REPAYMENT), 
                                       step=1000.0, key="payment")
        
        if st.button("Process Payment", type="primary"):
            if payment_amount >= MIN_REPAYMENT:
                loan.make_payment(payment_amount)
                st.success(f"Payment of ${payment_amount:,.2f} processed!")
                st.rerun()
            else:
                st.warning(f"Minimum payment is ${MIN_REPAYMENT:,.0f}")
        
        # Quick Payments
        st.subheader("Quick Payments")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(f"${MIN_REPAYMENT:,.0f}"):
                loan.make_payment(MIN_REPAYMENT)
                st.success(f"${MIN_REPAYMENT:,.0f} processed!")
                st.rerun()
        
        with col2:
            if st.button(f"${MIN_REPAYMENT * 2:,.0f}"):
                loan.make_payment(MIN_REPAYMENT * 2)
                st.success(f"${MIN_REPAYMENT * 2:,.0f} processed!")
                st.rerun()
        
        # Reset Option
        st.subheader("Reset")
        if st.button("Reset Loan", type="secondary"):
            st.session_state.loan = Loan()
            st.success("Loan tracking reset!")
            st.rerun()

    # Loan Terms Overview
    create_section_header("Loan Terms", "Fixed loan structure and terms")
    
    loan_terms = [
        {"title": "Loan Term", "value": f"{LOAN_TERM_YEARS} Years", "caption": "Fixed term"},
        {"title": "Annual Interest", "value": f"${ANNUAL_INTEREST:,.0f}", "caption": "Fixed rate"},
        {"title": "Min Payment", "value": f"${MIN_REPAYMENT:,.0f}", "caption": "Minimum required"},
        {"title": "Next Interest Due", "value": "Dec 31, 2025", "caption": "Annual payment"}
    ]
    
    render_metric_grid(loan_terms, columns=4)

    # Current Status
    create_section_header("Current Status", "Outstanding balance and payment history")
    
    remaining_years = loan.get_remaining_years()
    original_total = loan_summary['original_principal'] + (ANNUAL_INTEREST * LOAN_TERM_YEARS)
    paid_amount = loan_summary['total_payments']
    remaining_amount = original_total - paid_amount
    progress_pct = (paid_amount / original_total * 100) if original_total > 0 else 0
    
    status_metrics = [
        {"title": "Outstanding Balance", "value": f"${loan.outstanding:,.0f}", "caption": "Remaining principal"},
        {"title": "Total Payments", "value": f"${loan.get_total_payments():,.0f}", "caption": f"{loan_summary['payment_count']} payments made"},
        {"title": "Years Remaining", "value": f"{remaining_years:.1f}", "caption": "Estimated completion"},
        {"title": "Progress", "value": f"{progress_pct:.1f}%", "caption": "Loan completion"}
    ]
    
    render_metric_grid(status_metrics, columns=4)

    # Repayment Schedule
    create_section_header("Repayment Schedule", "5-year payment breakdown and projections")
    
    if loan.outstanding > 0:
        with st.spinner("Calculating repayment schedule..."):
            remaining_balance = loan.outstanding
            total_interest_5yr = ANNUAL_INTEREST * LOAN_TERM_YEARS
            annual_payment_needed = (remaining_balance + total_interest_5yr) / LOAN_TERM_YEARS
            
            schedule_metrics = [
                {"title": "Remaining Balance", "value": f"${remaining_balance:,.0f}", "caption": "Principal outstanding"},
                {"title": "Total Interest (5yr)", "value": f"${total_interest_5yr:,.0f}", "caption": "Fixed annual interest"},
                {"title": "Annual Payment Needed", "value": f"${annual_payment_needed:,.0f}", "caption": "To complete in 5 years"},
                {"title": "Monthly Equivalent", "value": f"${annual_payment_needed/12:,.0f}", "caption": "Average monthly amount"}
            ]
            
            render_metric_grid(schedule_metrics, columns=4)
            
            # Generate repayment schedule table
            schedule_data = []
            current_balance = remaining_balance
            
            for year in range(1, LOAN_TERM_YEARS + 1):
                year_start_balance = current_balance
                principal_payment = min(annual_payment_needed - ANNUAL_INTEREST, current_balance)
                current_balance = max(0, current_balance - principal_payment)
                
                schedule_data.append({
                    'Year': year,
                    'Start Balance': f"${year_start_balance:,.0f}",
                    'Principal Payment': f"${principal_payment:,.0f}",
                    'Interest Payment': f"${ANNUAL_INTEREST:,.0f}",
                    'Total Payment': f"${principal_payment + ANNUAL_INTEREST:,.0f}",
                    'End Balance': f"${current_balance:,.0f}"
                })
                
                if current_balance <= 0:
                    break
            
            schedule_df = pd.DataFrame(schedule_data)
            st.dataframe(schedule_df, use_container_width=True)
            st.caption("Annual repayment schedule showing principal and interest breakdown")

    # Progress Visualization
    create_section_header("Repayment Progress", "Visual progress tracking and completion status")
    
    with st.spinner("Loading progress visualization..."):
        # Progress bar
        if original_total > 0:
            progress = min(paid_amount / original_total, 1.0)
            st.progress(progress)
            st.write(f"**Progress: {progress*100:.1f}% of total loan repaid**")
        
        # Progress chart
        def render_progress_chart():
            fig = go.Figure()
            
            # Add paid amount
            fig.add_trace(go.Bar(
                name='Paid',
                x=['Loan Progress'],
                y=[paid_amount],
                marker_color='#635BFF',
                text=f'${paid_amount:,.0f}',
                textposition='inside'
            ))
            
            # Add remaining amount
            fig.add_trace(go.Bar(
                name='Remaining',
                x=['Loan Progress'],
                y=[remaining_amount],
                marker_color='#E6E6FA',
                text=f'${remaining_amount:,.0f}',
                textposition='inside'
            ))
            
            fig.update_layout(
                barmode='stack',
                title='Loan Repayment Progress',
                xaxis_title='',
                yaxis_title='Amount ($)',
                showlegend=True,
                height=400,
                plot_bgcolor='white',
                paper_bgcolor='white'
            )
            
            fig.update_xaxes(showgrid=False)
            fig.update_yaxes(showgrid=True, gridcolor='lightgray')
            
            st.plotly_chart(fig, use_container_width=True)
        
        render_chart_container(
            render_progress_chart,
            "Repayment Progress",
            "Visual breakdown of paid vs remaining loan balance",
            "Rendering progress chart..."
        )
        
        st.caption(f"Total loan value: ${original_total:,.0f} | Paid: ${paid_amount:,.0f} | Remaining: ${remaining_amount:,.0f}")

    # Interest Payment Schedule
    create_section_header("Interest Payment Schedule", "Annual interest payment dates and amounts")
    
    with st.spinner("Loading interest schedule..."):
        interest_dates = []
        current_year = datetime.now().year
        
        for i in range(LOAN_TERM_YEARS):
            interest_dates.append({
                'Year': current_year + i,
                'Due Date': f"December 31, {current_year + i}",
                'Interest Amount': f"${ANNUAL_INTEREST:,.0f}",
                'Status': 'Upcoming' if i > 0 else 'Current Year'
            })
        
        interest_df = pd.DataFrame(interest_dates)
        st.dataframe(interest_df, use_container_width=True)
        st.caption("Fixed annual interest payments due December 31st each year")

except Exception as e:
    show_error("Loan Management Error", str(e))
