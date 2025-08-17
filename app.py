import streamlit as st
import pandas as pd
import sys
import os
import sqlite3
import hashlib
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.theme_manager import get_setting, apply_theme
from dotenv import load_dotenv
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Cash Flow Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Authentication functions
def init_auth_db():
    """Initialize authentication database"""
    with sqlite3.connect('users.db') as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        """)

def hash_password(password: str) -> str:
    """Hash password with salt"""
    salt = os.urandom(32)
    pwdhash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    return (salt + pwdhash).hex()

def verify_password(stored_password: str, provided_password: str) -> bool:
    """Verify password against hash"""
    try:
        stored_bytes = bytes.fromhex(stored_password)
        salt = stored_bytes[:32]
        stored_hash = stored_bytes[32:]
        pwdhash = hashlib.pbkdf2_hmac('sha256', provided_password.encode('utf-8'), salt, 100000)
        return pwdhash == stored_hash
    except:
        return False

def register_user(email: str, password: str) -> bool:
    """Register new user"""
    try:
        password_hash = hash_password(password)
        with sqlite3.connect('users.db') as conn:
            conn.execute("INSERT INTO users (email, password_hash) VALUES (?, ?)", 
                       (email, password_hash))
        return True
    except sqlite3.IntegrityError:
        return False

def authenticate_user(email: str, password: str) -> bool:
    """Authenticate user login"""
    with sqlite3.connect('users.db') as conn:
        result = conn.execute("SELECT password_hash FROM users WHERE email = ?", (email,)).fetchone()
        if result and verify_password(result[0], password):
            conn.execute("UPDATE users SET last_login = ? WHERE email = ?", 
                       (datetime.now(), email))
            return True
    return False

def show_login_form():
    """Display login/register form"""
    st.title("🔐 Cash Flow Dashboard - Login")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        st.subheader("Login to your account")
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if email and password:
                    if authenticate_user(email, password):
                        st.session_state.authenticated = True
                        st.session_state.user_email = email
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid email or password")
                else:
                    st.error("Please enter both email and password")
    
    with tab2:
        st.subheader("Create new account")
        with st.form("register_form"):
            email = st.text_input("Email", key="reg_email")
            password = st.text_input("Password", type="password", key="reg_password")
            confirm_password = st.text_input("Confirm Password", type="password")
            submit = st.form_submit_button("Register", use_container_width=True)
            
            if submit:
                if not email or not password:
                    st.error("Please fill in all fields")
                elif password != confirm_password:
                    st.error("Passwords don't match")
                elif len(password) < 6:
                    st.error("Password must be at least 6 characters")
                elif register_user(email, password):
                    st.success("Registration successful! Please login with your credentials.")
                else:
                    st.error("User with this email already exists")

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
        st.write(f"👤 Logged in as: {st.session_state.user_email}")
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user_email = None
            st.rerun()
    
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

# Check authentication
if not st.session_state.get('authenticated', False):
    show_login_form()
else:
    main_dashboard()
