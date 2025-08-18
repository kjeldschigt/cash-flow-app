"""
Secure admin setup utilities for first-run initialization.
"""

import os
import secrets
import logging
import streamlit as st
from typing import Optional, Tuple
from ..models.user import UserRole
from ..services.user_service import UserService
from ..container import get_container

logger = logging.getLogger(__name__)


def generate_secure_password(length: int = 16) -> str:
    """Generate a cryptographically secure random password."""
    return secrets.token_urlsafe(length)


def get_admin_credentials_from_env() -> Tuple[Optional[str], Optional[str]]:
    """Get admin credentials from environment variables."""
    admin_email = os.getenv('ADMIN_EMAIL')
    admin_password = os.getenv('ADMIN_PASSWORD')
    return admin_email, admin_password


def check_admin_exists() -> bool:
    """Check if any admin user exists in the system."""
    try:
        container = get_container()
        user_service = container.get_user_service()
        users = user_service.get_all_active_users()
        
        # Check if any user has admin role
        for user in users:
            if hasattr(user, 'role') and user.role == UserRole.ADMIN:
                return True
        return False
    except Exception as e:
        logger.error(f"Error checking admin existence: {e}")
        return False


def create_admin_user(email: str, password: str) -> Tuple[bool, str]:
    """Create an admin user with the provided credentials."""
    try:
        container = get_container()
        user_service = container.get_user_service()
        
        admin_user = user_service.register_user(email, password, UserRole.ADMIN)
        if admin_user:
            logger.info(f"Admin user created successfully: {email}")
            return True, f"Admin user created: {email}"
        else:
            return False, "Failed to create admin user"
    except Exception as e:
        logger.error(f"Error creating admin user: {e}")
        return False, f"Error creating admin user: {str(e)}"


def setup_initial_admin() -> Optional[Tuple[str, str]]:
    """
    Set up initial admin user using secure methods.
    Returns (email, password) tuple if created, None if admin already exists.
    """
    # Check if admin already exists
    if check_admin_exists():
        logger.info("Admin user already exists, skipping setup")
        return None
    
    # Try to get credentials from environment
    admin_email, admin_password = get_admin_credentials_from_env()
    
    if admin_email and admin_password:
        # Use environment credentials
        success, message = create_admin_user(admin_email, admin_password)
        if success:
            logger.info(f"Admin user created from environment: {admin_email}")
            return admin_email, admin_password
        else:
            logger.error(f"Failed to create admin from environment: {message}")
    
    # Generate secure credentials
    if not admin_email:
        admin_email = "admin@localhost"
    
    secure_password = generate_secure_password()
    success, message = create_admin_user(admin_email, secure_password)
    
    if success:
        logger.info(f"Admin user created with generated password: {admin_email}")
        return admin_email, secure_password
    else:
        logger.error(f"Failed to create admin user: {message}")
        return None


def display_admin_setup_info(email: str, password: str):
    """Display admin setup information to the user."""
    st.success("🔐 **Initial Admin User Created**")
    st.info(f"**Email:** {email}")
    st.warning(f"**Password:** `{password}`")
    st.error("⚠️ **IMPORTANT:** Save these credentials immediately! The password will not be shown again.")
    
    with st.expander("🔒 Security Recommendations"):
        st.markdown("""
        1. **Change the password** after first login
        2. **Use a strong, unique password**
        3. **Enable two-factor authentication** if available
        4. **Never share these credentials**
        5. **Store them in a secure password manager**
        """)


def show_setup_wizard():
    """Show the setup wizard for creating initial admin user."""
    st.title("🚀 Welcome to Cash Flow Dashboard")
    st.markdown("### Initial Setup Required")
    
    st.info("No admin user found. Let's create your first administrator account.")
    
    with st.form("admin_setup_form"):
        st.subheader("Create Admin Account")
        
        admin_email = st.text_input(
            "Admin Email",
            value="admin@localhost",
            help="This will be your login email"
        )
        
        password_option = st.radio(
            "Password Option",
            ["Generate secure password", "Set custom password"],
            help="We recommend using a generated secure password"
        )
        
        custom_password = None
        if password_option == "Set custom password":
            custom_password = st.text_input(
                "Custom Password",
                type="password",
                help="Must be at least 8 characters long"
            )
            confirm_password = st.text_input(
                "Confirm Password",
                type="password"
            )
            
            if custom_password and custom_password != confirm_password:
                st.error("Passwords do not match!")
                return False
            
            if custom_password and len(custom_password) < 8:
                st.error("Password must be at least 8 characters long!")
                return False
        
        submitted = st.form_submit_button("Create Admin User", type="primary")
        
        if submitted:
            if not admin_email or "@" not in admin_email:
                st.error("Please enter a valid email address!")
                return False
            
            # Use custom password or generate secure one
            password = custom_password if password_option == "Set custom password" else generate_secure_password()
            
            success, message = create_admin_user(admin_email, password)
            
            if success:
                display_admin_setup_info(admin_email, password)
                st.balloons()
                
                # Add a rerun button to continue to the app
                if st.button("Continue to Dashboard", type="primary"):
                    st.rerun()
                return True
            else:
                st.error(f"Failed to create admin user: {message}")
                return False
    
    return False


def handle_admin_setup():
    """
    Handle admin setup process.
    Returns True if setup is complete, False if setup wizard should be shown.
    """
    # Check if admin exists
    if check_admin_exists():
        return True
    
    # Try automatic setup first
    result = setup_initial_admin()
    
    if result:
        email, password = result
        # Only show credentials if they were auto-generated (not from env)
        admin_email_env, admin_password_env = get_admin_credentials_from_env()
        
        if not admin_password_env:  # Password was generated, show it
            display_admin_setup_info(email, password)
            return True
        else:  # Password from env, just show success
            st.success(f"✅ Admin user initialized: {email}")
            return True
    
    # If automatic setup failed, show wizard
    return False
