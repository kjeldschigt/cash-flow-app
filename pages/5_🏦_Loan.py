import streamlit as st
import sys
import os
import pandas as pd
import re
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.loan import Loan

st.title("Loan Tracking & Management")

# Theme Toggle
theme = st.selectbox("Theme", ["Light", "Dark"])
if theme == "Light":
    st.markdown('<style>body{background-color: #FAFAFA; color: #333;} .stApp{background-color: #FAFAFA;}</style>', unsafe_allow_html=True)
else:
    st.markdown('<style>body{background-color: #1E1E1E; color: #FFFFFF;} .stApp{background-color: #1E1E1E;}</style>', unsafe_allow_html=True)

# Fixed loan parameters
LOAN_TERM_YEARS = 5
ANNUAL_INTEREST = 18750
MIN_REPAYMENT = 10000

def extract_from_email(payload):
    """Extract repayment amount from email payload using regex"""
    # Look for dollar amounts in various formats
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

# Initialize loan in session state
if 'loan' not in st.session_state:
    st.session_state.loan = Loan()

loan = st.session_state.loan

# Fixed Loan Terms
st.subheader("Fixed Loan Terms")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Loan Term", f"{LOAN_TERM_YEARS} Years")
with col2:
    st.metric("Annual Interest", f"${ANNUAL_INTEREST:,.0f}")
with col3:
    st.metric("Min Repayment", f"${MIN_REPAYMENT:,.0f}")
with col4:
    next_interest_date = "Dec 31, 2025"  # Example
    st.metric("Next Interest Due", next_interest_date)

# Loan overview
st.subheader("Current Loan Status")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Outstanding Balance", f"${loan.outstanding:,.2f}")
with col2:
    st.metric("Total Repayments", f"${loan.get_total_payments():,.2f}")
with col3:
    remaining_years = loan.get_remaining_years()
    st.metric("Est. Years Remaining", f"{remaining_years:.1f}")

# Email Payment Extraction
st.subheader("Email Payment Processing")

col1, col2 = st.columns([2, 1])

with col1:
    payload = st.text_area("Paste Email Payload", height=100, placeholder="Paste email content containing payment information...")

with col2:
    st.write("**Instructions:**")
    st.write("1. Copy email content")
    st.write("2. Paste in text area")
    st.write("3. Click Extract Repayment")
    st.write(f"4. Min amount: ${MIN_REPAYMENT:,.0f}")

if st.button("Extract", type="primary"):
    if payload.strip():
        match = re.search(r'\$([0-9,]+(?:\.[0-9]{2})?)', payload)
        amount = float(match.group(1).replace(',', '')) if match else 0
        
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

# Repayment tracking only
st.subheader("Repayment Tracking")

loan_summary = loan.get_loan_summary()

col1, col2 = st.columns(2)

with col1:
    st.write("**Loan Structure:**")
    st.write(f"Original Principal: ${loan_summary['original_principal']:,.2f}")
    st.write(f"Annual Interest: ${ANNUAL_INTEREST:,.0f}")
    st.write(f"Total with Interest: ${loan_summary['original_principal'] + (ANNUAL_INTEREST * LOAN_TERM_YEARS):,.2f}")

with col2:
    st.write("**Repayment History:**")
    st.write(f"Number of Repayments: {loan_summary['payment_count']}")
    st.write(f"Total Repaid: ${loan_summary['total_payments']:,.2f}")
    st.write(f"Remaining Balance: ${loan.outstanding:,.2f}")

# Manual repayment input
st.subheader("Manual Repayment Entry")

col1, col2 = st.columns(2)

with col1:
    st.write("**Manual Repayment**")
    payment_amount = st.number_input("Repayment Amount ($)", min_value=float(MIN_REPAYMENT), step=1000.0, key="payment")
    
    if st.button("Process Repayment", type="primary"):
        if payment_amount >= MIN_REPAYMENT:
            loan.make_payment(payment_amount)
            st.success(f"Repayment of ${payment_amount:,.2f} processed successfully!")
            st.rerun()
        else:
            st.warning(f"Minimum repayment is ${MIN_REPAYMENT:,.0f}")

with col2:
    st.write("**Quick Repayments**")
    
    col2a, col2b = st.columns(2)
    
    with col2a:
        if st.button(f"Pay ${MIN_REPAYMENT:,.0f}"):
            loan.make_payment(MIN_REPAYMENT)
            st.success(f"${MIN_REPAYMENT:,.0f} repayment processed!")
            st.rerun()
    
    with col2b:
        if st.button(f"Pay ${MIN_REPAYMENT * 2:,.0f}"):
            loan.make_payment(MIN_REPAYMENT * 2)
            st.success(f"${MIN_REPAYMENT * 2:,.0f} repayment processed!")
            st.rerun()

# Loan progress visualization
st.subheader("Loan Progress")

original_total = loan_summary['original_principal'] + loan_summary['original_interest']
paid_amount = loan_summary['total_payments']
remaining_amount = loan.outstanding

# Progress bar
if original_total > 0:
    progress = min(paid_amount / original_total, 1.0)
    st.progress(progress)
    st.write(f"**Progress: {progress*100:.1f}% paid**")

# Loan Schedule Display
st.subheader("Loan Schedule & Projections")

if loan.outstanding > 0:
    # Calculate schedule metrics
    remaining_balance = loan.outstanding
    total_interest_5yr = ANNUAL_INTEREST * LOAN_TERM_YEARS
    annual_payment_needed = (remaining_balance + total_interest_5yr) / LOAN_TERM_YEARS
    monthly_payment_needed = annual_payment_needed / 12
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Remaining Balance", f"${remaining_balance:,.0f}")
    with col2:
        st.metric("Total Interest (5yr)", f"${total_interest_5yr:,.0f}")
    with col3:
        st.metric("Annual Payment Needed", f"${annual_payment_needed:,.0f}")
    with col4:
        remaining_years = loan.get_remaining_years()
        st.metric("Remaining Years", f"{remaining_years:.1f}")
    
    # Generate repayment schedule
    schedule_data = []
    current_balance = remaining_balance
    
    for year in range(1, LOAN_TERM_YEARS + 1):
        year_start_balance = current_balance
        # Principal payment is the amount that reduces the balance
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
    
    st.write("**5-Year Repayment Schedule:**")
    schedule_df = pd.DataFrame(schedule_data)
    st.dataframe(schedule_df, use_container_width=True)
    
    # Interest payment dates
    st.subheader("Annual Interest Payment Schedule")
    
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

# Loan progress tracking
st.subheader("Repayment Progress")

original_total = loan_summary['original_principal'] + (ANNUAL_INTEREST * LOAN_TERM_YEARS)
paid_amount = loan_summary['total_payments']
remaining_amount = loan.outstanding

# Progress visualization
if original_total > 0:
    progress = min(paid_amount / original_total, 1.0)
    st.progress(progress)
    st.write(f"**Progress: {progress*100:.1f}% of total loan repaid**")

col1, col2, col3 = st.columns(3)

with col1:
    st.write("**Total Loan Value:**")
    st.write(f"${original_total:,.0f}")

with col2:
    st.write("**Amount Repaid:**")
    st.write(f"${paid_amount:,.0f}")

with col3:
    st.write("**Remaining Balance:**")
    st.write(f"${remaining_amount:,.0f}")

# Reset option
if st.button("Reset Loan Tracking", type="secondary"):
    st.session_state.loan = Loan()
    st.success("Loan tracking reset to original state!")
    st.rerun()

# Complete loan summary
with st.expander("Complete Loan Summary"):
    summary_data = {
        'Metric': [
            'Original Principal', 
            'Fixed Annual Interest', 
            'Total 5-Year Interest', 
            'Total Loan Value', 
            'Total Repayments Made', 
            'Current Outstanding Balance',
            'Minimum Repayment',
            'Years Remaining (Est.)'
        ],
        'Amount': [
            f"${loan_summary['original_principal']:,.0f}",
            f"${ANNUAL_INTEREST:,.0f}",
            f"${ANNUAL_INTEREST * LOAN_TERM_YEARS:,.0f}",
            f"${loan_summary['original_principal'] + (ANNUAL_INTEREST * LOAN_TERM_YEARS):,.0f}",
            f"${loan_summary['total_payments']:,.0f}",
            f"${loan.outstanding:,.0f}",
            f"${MIN_REPAYMENT:,.0f}",
            f"{loan.get_remaining_years():.1f} years"
        ]
    }
    summary_df = pd.DataFrame(summary_data)
    st.dataframe(summary_df, use_container_width=True, hide_index=True)
