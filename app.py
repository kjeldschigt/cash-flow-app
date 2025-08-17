import streamlit as st
import pandas as pd
import sys
import os
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.theme_manager import apply_theme, get_current_theme
from services.auth import init_auth_db, register_user, login_user, is_authenticated, logout_user
from services.settings_manager import get_setting
from dotenv import load_dotenv
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Cash Flow Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize settings on app start
if 'theme' not in st.session_state:
    apply_theme(get_setting('theme', 'light'))

def show_login_form():
    """Display login/register form"""
    st.title("🔐 Cash Flow Dashboard - Login")
    
    # Show registration form if requested
    if st.session_state.get('show_register', False):
        st.subheader("Create new account")
        with st.form("register_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            col1, col2 = st.columns(2)
            
            with col1:
                register_submit = st.form_submit_button("Register", use_container_width=True)
            with col2:
                cancel_register = st.form_submit_button("Cancel", use_container_width=True)
            
            if register_submit:
                if not email or not password:
                    st.error("Please fill in all fields")
                elif password != confirm_password:
                    st.error("Passwords don't match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, message = register_user(email, password)
                    if success:
                        st.success(message)
                        st.session_state.show_register = False
                        st.rerun()
                    else:
                        st.error(message)
            
            if cancel_register:
                st.session_state.show_register = False
                st.rerun()
    else:
        # Login form
        st.subheader("Login to your account")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            col1, col2 = st.columns(2)
            
            with col1:
                login_submit = st.form_submit_button("Login", use_container_width=True)
            with col2:
                register_button = st.form_submit_button("Register", use_container_width=True)
            
            if login_submit:
                if email and password:
                    success, result = login_user(email, password)
                    if success:
                        st.session_state.user = result
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error(result)
                else:
                    st.error("Please enter both email and password")
            
            if register_button:
                st.session_state.show_register = True
                st.rerun()

def main_dashboard():
    """Main dashboard application"""
    # Apply theme globally
    theme = get_setting('theme', 'light')
    st.markdown(apply_theme(theme), unsafe_allow_html=True)
    
    # Sidebar with logout
    with st.sidebar:
        st.title("Navigation")
        st.markdown("Use the pages in the sidebar to navigate through different sections of the dashboard.")
        
        st.markdown("---")
        user_email = st.session_state.user.get('email', 'Unknown') if st.session_state.user else 'Unknown'
        st.write(f"👤 Logged in as: {user_email}")
        
        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
    
    # Main title
    st.title("💰 Cash Flow Dashboard")
    
    # Welcome message
    st.markdown("""
    Welcome to your comprehensive Cash Flow Dashboard! 
    
    This application provides detailed insights into your business performance, including:
    
    - **📊 Dashboard**: Overview of key metrics and performance indicators
    - **📈 Sales & Cash Flow Analysis**: Detailed revenue and cash flow trends
    - **💸 Costs**: Cost breakdown and expense management
    - **🧮 Scenarios**: Financial projections and scenario planning
    - **🏦 Loan**: Loan management and repayment tracking
    - **🔌 Integrations**: API connections to Airtable and Stripe
    - **⚙️ Settings**: Configuration and preferences
    
    Navigate using the sidebar to explore different sections of your dashboard.
    """)
    
    # Load data once at top level using data manager
    from utils.data_manager import load_combined_data, init_session_filters
    from components.ui_helpers import render_metric_grid
    
    # Initialize session filters
    init_session_filters()
    
    # Quick stats on main page
    try:
        df = load_combined_data()
        
        if not df.empty:
            total_sales = df['Sales_USD'].sum() if 'Sales_USD' in df.columns else 0
            total_costs = df['Costs_USD'].sum() if 'Costs_USD' in df.columns else 0
            cash_flow = total_sales - total_costs
            
            metrics = [
                {"title": "Total Sales", "value": f"${total_sales:,.0f}", "caption": "All time"},
                {"title": "Total Costs", "value": f"${total_costs:,.0f}", "caption": "All time"},
                {"title": "Net Cash Flow", "value": f"${cash_flow:,.0f}", "caption": "All time"}
            ]
            
            render_metric_grid(metrics, columns=3)
    
    except Exception as e:
        st.info("Navigate to specific pages using the sidebar to view detailed data and functionality.")

# Initialize auth database
init_auth_db()

# Create initial admin user if no users exist
try:
    import sqlite3
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    user_count = cursor.fetchone()[0]
    conn.close()
    
    if user_count == 0:
        success, message = register_user("admin@kalonsurf.com", "Kalon2025")
        if success:
            st.info("Initial admin user created: admin@kalonsurf.com")
except Exception as e:
    pass  # Silently handle any database errors

# Check authentication
if not is_authenticated():
    show_login_form()
else:
    # Apply theme after login (in case session state is reset)
    apply_theme(st.session_state.get('theme', get_setting('theme', 'light')))
    main_dashboard()
