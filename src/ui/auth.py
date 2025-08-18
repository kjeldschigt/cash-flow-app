"""
Authentication UI components.
"""

import streamlit as st
from typing import Optional, Dict, Any
from ..models.user import User, UserRole
from ..services.user_service import UserService
from ..container import get_container


class AuthComponents:
    """Authentication-related UI components."""

    @staticmethod
    def login_form() -> Optional[Dict[str, str]]:
        """Display login form and return credentials if submitted."""
        with st.form("login_form"):
            st.subheader("🔐 Login")

            email = st.text_input("Email", placeholder="user@example.com")

            password = st.text_input("Password", type="password")

            submitted = st.form_submit_button("Login", type="primary")

            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password")
                    return None

                return {"email": email.lower().strip(), "password": password}

        return None

    @staticmethod
    def register_form() -> Optional[Dict[str, str]]:
        """Display registration form and return user data if submitted."""
        with st.form("register_form"):
            st.subheader("📝 Create Account")

            email = st.text_input("Email", placeholder="user@example.com")

            password = st.text_input(
                "Password",
                type="password",
                help="Must be at least 8 characters with uppercase, lowercase, number, and special character",
            )

            confirm_password = st.text_input("Confirm Password", type="password")

            submitted = st.form_submit_button("Create Account", type="primary")

            if submitted:
                if not email or not password or not confirm_password:
                    st.error("Please fill in all fields")
                    return None

                if password != confirm_password:
                    st.error("Passwords do not match")
                    return None

                return {"email": email.lower().strip(), "password": password}

        return None

    @staticmethod
    def authenticate_user(email: str, password: str) -> Optional[User]:
        """Authenticate user and return User object if successful."""
        try:
            container = get_container()
            user_service = container.get_user_service()

            user = user_service.authenticate(email, password)
            if user:
                # Store user in session state
                st.session_state.user = {
                    "id": user.id,
                    "email": user.email,
                    "role": user.role,
                    "is_authenticated": True,
                }
                return user
            else:
                st.error("Invalid email or password")
                return None

        except Exception as e:
            st.error(f"Authentication error: {str(e)}")
            return None

    @staticmethod
    def register_user(email: str, password: str) -> Optional[User]:
        """Register new user and return User object if successful."""
        try:
            container = get_container()
            user_service = container.get_user_service()

            user = user_service.register_user(email, password, UserRole.USER)
            if user:
                st.success("Account created successfully! Please log in.")
                return user

        except ValueError as e:
            st.error(str(e))
            return None
        except Exception as e:
            st.error(f"Registration error: {str(e)}")
            return None

    @staticmethod
    def logout():
        """Log out current user."""
        if "user" in st.session_state:
            del st.session_state.user
        st.rerun()

    @staticmethod
    def get_current_user() -> Optional[Dict[str, Any]]:
        """Get current authenticated user from session state."""
        return st.session_state.get("user")

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated."""
        user = AuthComponents.get_current_user()
        return user is not None and user.get("is_authenticated", False)

    @staticmethod
    def require_authentication() -> bool:
        """Require authentication and redirect to login if not authenticated."""
        if not AuthComponents.is_authenticated():
            st.warning("Please log in to access this page")

            # Show login/register tabs
            tab1, tab2 = st.tabs(["Login", "Register"])

            with tab1:
                login_data = AuthComponents.login_form()
                if login_data:
                    user = AuthComponents.authenticate_user(
                        login_data["email"], login_data["password"]
                    )
                    if user:
                        st.rerun()

            with tab2:
                register_data = AuthComponents.register_form()
                if register_data:
                    user = AuthComponents.register_user(
                        register_data["email"], register_data["password"]
                    )

            return False

        return True

    @staticmethod
    def user_info_sidebar():
        """Display user info in sidebar."""
        user = AuthComponents.get_current_user()
        if user:
            with st.sidebar:
                st.markdown("---")
                st.markdown(f"**Logged in as:**")
                st.markdown(f"📧 {user['email']}")
                st.markdown(f"👤 {user['role'].title()}")

                if st.button("Logout", type="secondary"):
                    AuthComponents.logout()

    @staticmethod
    def require_role(required_role: UserRole) -> bool:
        """Require minimum user role using hierarchy."""
        user = AuthComponents.get_current_user()
        if not user:
            return False

        user_role = UserRole(user["role"])

        # Use the role hierarchy from UserRole enum
        if user_role.level < required_role.level:
            st.error(
                f"Access denied. {required_role.value.title()} role (level {required_role.level}) or higher required."
            )
            return False

        return True

    @staticmethod
    def require_exact_role(required_role: UserRole) -> bool:
        """Require exact user role match."""
        user = AuthComponents.get_current_user()
        if not user:
            return False

        user_role = UserRole(user["role"])

        if user_role != required_role:
            st.error(
                f"Access denied. Exact role required: {required_role.value.title()}"
            )
            return False

        return True
