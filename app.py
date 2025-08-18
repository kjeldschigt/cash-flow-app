import streamlit as st
import pandas as pd
import sys
import os
import logging
from datetime import datetime

# Add src directory to path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Import database initialization utilities
from utils.db_init import initialize_database, check_encryption_key, get_database_info

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database and check encryption key on startup
try:
    # Check encryption key first
    encryption_key = check_encryption_key()
    logger.info("Encryption key validated")
    
    # Initialize database
    db_results = initialize_database()
    
    if not db_results['success']:
        st.error("❌ Database initialization failed!")
        for error in db_results['errors']:
            st.error(f"• {error}")
        st.stop()
    
    # Show admin credentials if created
    if db_results.get('admin_password'):
        st.success("✅ Database initialized successfully!")
        st.info(f"""
        🔑 **Default Admin Credentials Created:**
        - Username: `admin`  
        - Password: `{db_results['admin_password']}`
        
        ⚠️ **Please change this password after first login!**
        """)
    
    logger.info("Database initialization completed successfully")
    
except Exception as e:
    st.error(f"❌ Application startup failed: {e}")
    logger.error(f"Application startup failed: {str(e)}")
    st.stop()

# Import components after database is initialized
try:
    # Import new clean architecture components
    from src.container import configure_container, get_container
    from src.ui.auth import AuthComponents
    from src.ui.components import UIComponents
    from src.config.settings import Settings
    from src.security import AuditLogger, AuditAction, DataEncryption, SecureStorage

    # Legacy imports for backward compatibility
    try:
        from src.utils.theme_manager import apply_theme, get_current_theme
    except ImportError:
        # Fallback theme functions
        def apply_theme(theme=None):
            pass
        def get_current_theme():
            return "default"
    
    from dotenv import load_dotenv
    load_dotenv()

    # Initialize clean architecture container
    settings = Settings()
    container = configure_container(settings)
    
    # Initialize settings service
    settings_service = container.get_settings_service()
    def get_setting(key, default=None):
        try:
            return settings_service.get_setting(key, default)
        except TypeError:
            # Fallback for repositories that don't accept default parameter
            result = settings_service.get_setting(key)
            return result if result is not None else default
    
    # Initialize security components
    audit_logger = AuditLogger(container.get_db_connection())
    secure_storage = SecureStorage()
    
    logger.info("Application components initialized successfully")
    
except Exception as e:
    st.error(f"Failed to initialize application components: {e}")
    logger.error(f"Failed to initialize application components: {str(e)}")
    st.stop()

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
    """Display login/register form using new auth components"""
    st.title("🔐 Cash Flow Dashboard - Login")
    
    # Use new auth components with audit logging
    if not AuthComponents.require_authentication():
        return False
    
    # Log successful authentication
    if AuthComponents.is_authenticated():
        user_email = st.session_state.get('user', {}).get('email', 'unknown')
        audit_logger.log_authentication_event(
            user_email=user_email,
            action=AuditAction.LOGIN,
            success=True,
            details={'login_time': datetime.now().isoformat()}
        )
    
    return True

def main_dashboard():
    """Main dashboard application"""
    # Apply theme globally
    theme = get_setting('theme', 'light')
    st.markdown(apply_theme(theme), unsafe_allow_html=True)
    
    # Add user info sidebar using new auth components
    AuthComponents.user_info_sidebar()
    
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
    from src.utils.data_manager import load_combined_data, init_session_filters
    from components.ui_helpers import render_metric_grid
    
    # Initialize session filters
    init_session_filters()
    
    # Quick stats using new analytics service
    try:
        from datetime import date
        from src.utils.date_utils import DateUtils
        
        analytics_service = container.get_container().get_singleton('analytics_service')
        if not analytics_service:
            # Fallback to creating service if not in container
            from src.services.analytics_service import AnalyticsService
            analytics_service = AnalyticsService(container.get_db_connection())
        
        # Get current year metrics
        current_year = date.today().year
        year_start, year_end = DateUtils.get_year_range(current_year)
        metrics = analytics_service.get_cash_flow_metrics(year_start, year_end)
        
        # Display metrics using new UI components
        col1, col2, col3 = st.columns(3)
        
        with col1:
            UIComponents.currency_metric(
                "Total Sales", 
                metrics.total_sales_usd, 
                "USD",
                help_text="Total sales for current year"
            )
        
        with col2:
            UIComponents.currency_metric(
                "Total Costs", 
                metrics.total_costs_usd, 
                "USD",
                help_text="Total costs for current year"
            )
        
        with col3:
            UIComponents.currency_metric(
                "Net Cash Flow", 
                metrics.net_cash_flow, 
                "USD",
                help_text="Net cash flow for current year"
            )
    
    except Exception as e:
        st.info("Navigate to specific pages using the sidebar to view detailed data and functionality.")

# Handle admin setup securely
from src.utils.admin_setup import handle_admin_setup, show_setup_wizard

# Check if admin setup is complete
if not handle_admin_setup():
    # Show setup wizard if no admin exists
    if show_setup_wizard():
        st.rerun()
    else:
        st.stop()  # Stop execution until admin is created

# Check authentication using new auth components
if not AuthComponents.is_authenticated():
    show_login_form()
else:
    # Apply theme after login
    apply_theme(st.session_state.get('theme', get_setting('theme', 'light')))
    main_dashboard()
