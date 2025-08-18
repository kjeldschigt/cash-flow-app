"""
Secure API Key Management UI Components for Settings Page
"""

import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime
from src.services.api_key_service import get_api_key_service, APIKeyInfo
from src.services.api_key_test_service import get_api_key_test_service
from src.models.user import UserRole
from src.ui.enhanced_auth import require_auth, get_current_user
from src.security.pii_protection import get_structured_logger

logger = get_structured_logger()

class APIKeyManagementUI:
    """UI components for secure API key management"""
    
    def __init__(self):
        self.api_key_service = get_api_key_service()
        self.test_service = get_api_key_test_service()
        logger.info("API key management UI initialized", operation="ui_init")
    
    @require_auth(UserRole.ADMIN)
    def render_api_key_management(self):
        """Render the complete API key management interface"""
        st.header("🔐 API Key Management")
        st.markdown("Securely manage API keys for external services")
        
        # Check admin permissions
        current_user = get_current_user()
        if not current_user or current_user.role != UserRole.ADMIN:
            st.error("🚫 Access denied. Administrator privileges required.")
            return
        
        # Create tabs for different operations
        tab1, tab2, tab3 = st.tabs(["📋 View Keys", "➕ Add Key", "📊 Service Status"])
        
        with tab1:
            self._render_api_keys_list()
        
        with tab2:
            self._render_add_api_key_form()
        
        with tab3:
            self._render_service_status()
    
    def _render_api_keys_list(self):
        """Render list of existing API keys with management options"""
        st.subheader("Existing API Keys")
        
        # Filter options
        col1, col2 = st.columns([2, 1])
        with col1:
            service_filter = st.selectbox(
                "Filter by Service",
                ["All"] + self.api_key_service.get_service_types(),
                key="service_filter"
            )
        with col2:
            show_inactive = st.checkbox("Show Inactive", key="show_inactive")
        
        # Get API keys
        service_type = None if service_filter == "All" else service_filter.lower()
        api_keys = self.api_key_service.get_api_keys(
            service_type=service_type,
            include_inactive=show_inactive
        )
        
        if not api_keys:
            st.info("No API keys found. Add your first API key using the 'Add Key' tab.")
            return
        
        # Display API keys in a table-like format
        for api_key in api_keys:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
                
                with col1:
                    status_icon = "🟢" if api_key.is_active else "🔴"
                    st.markdown(f"**{status_icon} {api_key.key_name}**")
                    st.caption(f"Service: {api_key.service_type.title()}")
                    if api_key.description:
                        st.caption(f"Description: {api_key.description}")
                
                with col2:
                    st.code(api_key.masked_value, language=None)
                    st.caption(f"Added: {api_key.created_at.strftime('%Y-%m-%d')}")
                
                with col3:
                    if st.button("🧪 Test", key=f"test_{api_key.id}"):
                        self._test_api_key_connection(api_key)
                    
                    if st.button("✏️ Edit", key=f"edit_{api_key.id}"):
                        self._show_edit_form(api_key)
                
                with col4:
                    if api_key.is_active:
                        if st.button("🗑️ Delete", key=f"delete_{api_key.id}", type="secondary"):
                            self._confirm_delete_api_key(api_key)
                    else:
                        st.caption("Inactive")
                
                st.divider()
    
    def _render_add_api_key_form(self):
        """Render form to add new API key"""
        st.subheader("Add New API Key")
        
        with st.form("add_api_key_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                key_name = st.text_input(
                    "Key Name *",
                    placeholder="e.g., stripe_production, openai_main",
                    help="Unique identifier for this API key"
                )
                
                service_type = st.selectbox(
                    "Service Type *",
                    self.api_key_service.get_service_types(),
                    format_func=lambda x: x.replace('_', ' ').title()
                )
            
            with col2:
                api_key = st.text_input(
                    "API Key *",
                    type="password",
                    placeholder="Enter your API key here",
                    help="The actual API key will be encrypted before storage"
                )
                
                description = st.text_area(
                    "Description",
                    placeholder="Optional description of this API key",
                    height=100
                )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                test_before_save = st.checkbox("Test connection before saving", value=True)
            
            with col2:
                submitted = st.form_submit_button("💾 Add API Key", type="primary")
            
            if submitted:
                self._handle_add_api_key(key_name, api_key, service_type, description, test_before_save)
    
    def _render_service_status(self):
        """Render service connection status overview"""
        st.subheader("Service Connection Status")
        
        api_keys = self.api_key_service.get_api_keys()
        
        if not api_keys:
            st.info("No API keys configured yet.")
            return
        
        # Group by service type
        services = {}
        for api_key in api_keys:
            if api_key.service_type not in services:
                services[api_key.service_type] = []
            services[api_key.service_type].append(api_key)
        
        # Display service status
        for service_type, keys in services.items():
            with st.expander(f"📡 {service_type.replace('_', ' ').title()} ({len(keys)} keys)"):
                for api_key in keys:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    
                    with col1:
                        status_icon = "🟢" if api_key.is_active else "🔴"
                        st.markdown(f"{status_icon} **{api_key.key_name}**")
                        st.caption(api_key.masked_value)
                    
                    with col2:
                        st.caption(f"Added: {api_key.created_at.strftime('%Y-%m-%d')}")
                    
                    with col3:
                        if st.button("Test Now", key=f"status_test_{api_key.id}"):
                            self._test_api_key_connection(api_key)
    
    def _handle_add_api_key(self, key_name: str, api_key: str, service_type: str, 
                           description: str, test_before_save: bool):
        """Handle adding a new API key"""
        if not key_name or not api_key:
            st.error("Key name and API key are required.")
            return
        
        current_user = get_current_user()
        if not current_user:
            st.error("User not authenticated.")
            return
        
        # Test connection if requested
        if test_before_save:
            with st.spinner("Testing API key connection..."):
                success, message, details = self.test_service.test_api_key(api_key, service_type)
                
                if not success:
                    st.error(f"❌ Connection test failed: {message}")
                    st.info("You can still save the key by unchecking 'Test connection before saving'")
                    return
                else:
                    st.success(f"✅ Connection test passed: {message}")
        
        # Add API key
        with st.spinner("Encrypting and saving API key..."):
            success, message = self.api_key_service.add_api_key(
                key_name=key_name,
                api_key=api_key,
                service_type=service_type.lower(),
                added_by_user=current_user.id,
                description=description if description else None
            )
        
        if success:
            st.success(f"✅ {message}")
            logger.info("API key added via UI",
                       operation="ui_add_api_key",
                       key_name=key_name,
                       service_type=service_type,
                       added_by=current_user.id)
            st.rerun()
        else:
            st.error(f"❌ {message}")
    
    def _test_api_key_connection(self, api_key: APIKeyInfo):
        """Test API key connection and display results"""
        # Get the actual API key value
        actual_key = self.api_key_service.get_api_key_value(api_key.key_name)
        if not actual_key:
            st.error("Failed to retrieve API key for testing")
            return
        
        with st.spinner(f"Testing connection for {api_key.key_name}..."):
            success, message, details = self.test_service.test_api_key(
                actual_key, api_key.service_type
            )
        
        if success:
            st.success(f"✅ {message}")
            if details.get('validation_only'):
                st.info("ℹ️ Only format validation performed for this service type")
        else:
            st.error(f"❌ {message}")
            if details.get('status_code'):
                st.caption(f"HTTP Status: {details['status_code']}")
    
    def _show_edit_form(self, api_key: APIKeyInfo):
        """Show edit form for API key"""
        st.session_state[f"edit_mode_{api_key.id}"] = True
        
        with st.form(f"edit_form_{api_key.id}"):
            st.subheader(f"Edit API Key: {api_key.key_name}")
            
            new_api_key = st.text_input(
                "New API Key",
                type="password",
                placeholder="Enter new API key (leave empty to keep current)",
                help="Only enter a new key if you want to update it"
            )
            
            new_description = st.text_area(
                "Description",
                value=api_key.description or "",
                help="Update the description for this API key"
            )
            
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Update", type="primary"):
                    self._handle_edit_api_key(api_key, new_api_key, new_description)
            
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    if f"edit_mode_{api_key.id}" in st.session_state:
                        del st.session_state[f"edit_mode_{api_key.id}"]
                    st.rerun()
    
    def _handle_edit_api_key(self, api_key: APIKeyInfo, new_api_key: str, new_description: str):
        """Handle editing an API key"""
        if not new_api_key and new_description == (api_key.description or ""):
            st.warning("No changes detected.")
            return
        
        # Update API key
        if new_api_key:
            success, message = self.api_key_service.update_api_key(
                api_key.key_name, new_api_key, new_description
            )
        else:
            # Only update description
            success, message = self.api_key_service.update_api_key(
                api_key.key_name, 
                self.api_key_service.get_api_key_value(api_key.key_name),
                new_description
            )
        
        if success:
            st.success(f"✅ {message}")
            if f"edit_mode_{api_key.id}" in st.session_state:
                del st.session_state[f"edit_mode_{api_key.id}"]
            st.rerun()
        else:
            st.error(f"❌ {message}")
    
    def _confirm_delete_api_key(self, api_key: APIKeyInfo):
        """Show confirmation dialog for deleting API key"""
        st.session_state[f"confirm_delete_{api_key.id}"] = True
        
        st.warning(f"⚠️ Are you sure you want to delete the API key '{api_key.key_name}'?")
        st.caption("This action cannot be undone. The key will be marked as inactive.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Yes, Delete", key=f"confirm_yes_{api_key.id}", type="secondary"):
                success, message = self.api_key_service.delete_api_key(api_key.key_name)
                if success:
                    st.success(f"✅ {message}")
                    logger.info("API key deleted via UI",
                               operation="ui_delete_api_key",
                               key_name=api_key.key_name)
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        with col2:
            if st.button("❌ Cancel", key=f"confirm_no_{api_key.id}"):
                if f"confirm_delete_{api_key.id}" in st.session_state:
                    del st.session_state[f"confirm_delete_{api_key.id}"]
                st.rerun()

# Global instance
_api_key_management_ui = None

def get_api_key_management_ui() -> APIKeyManagementUI:
    """Get global API key management UI instance"""
    global _api_key_management_ui
    if _api_key_management_ui is None:
        _api_key_management_ui = APIKeyManagementUI()
    return _api_key_management_ui

def render_api_key_management():
    """Convenience function to render API key management interface"""
    ui = get_api_key_management_ui()
    ui.render_api_key_management()
