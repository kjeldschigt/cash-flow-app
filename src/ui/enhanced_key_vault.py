"""
Enhanced API Key Management UI using KeyVaultService
"""

import streamlit as st
from typing import Optional, Dict, Any
from datetime import datetime
from src.services.key_vault import get_key_vault_service, APIKeyInfo
from src.models.user import UserRole
from src.ui.enhanced_auth import require_auth, get_current_user
from src.middleware.session_middleware import get_session_middleware
import logging

logger = logging.getLogger(__name__)

class EnhancedKeyVaultUI:
    """Enhanced UI components for secure API key management using KeyVaultService"""
    
    def __init__(self):
        self.middleware = get_session_middleware()
        current_user = get_current_user()
        session_token = self.middleware.cookie_manager.get_session_cookie()
        
        self.vault_service = get_key_vault_service(
            session_id=session_token,
            user_id=current_user.id if current_user else None
        )
        logger.info("Enhanced KeyVault UI initialized")
    
    @require_auth(UserRole.ADMIN)
    def render_key_vault_management(self):
        """Render the complete KeyVault management interface"""
        st.header("🔐 Secure Key Vault")
        st.markdown("Enterprise-grade API key management with encryption and audit logging")
        
        # Check admin permissions
        current_user = get_current_user()
        if not current_user or current_user.role != UserRole.ADMIN:
            st.error("🚫 Access denied. Administrator privileges required.")
            return
        
        # Create tabs for different operations
        tab1, tab2, tab3, tab4 = st.tabs(["📋 Vault Keys", "➕ Store Key", "📊 Vault Status", "📜 Audit Logs"])
        
        with tab1:
            self._render_vault_keys_list()
        
        with tab2:
            self._render_store_key_form()
        
        with tab3:
            self._render_vault_status()
        
        with tab4:
            self._render_audit_logs()
    
    def _render_vault_keys_list(self):
        """Render list of vault keys with management options"""
        st.subheader("Vault Keys")
        
        # Filter options
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            service_filter = st.selectbox(
                "Filter by Service",
                ["All", "stripe", "openai", "airtable", "twilio", "sendgrid", "aws", "google_cloud", "azure", "other"],
                key="vault_service_filter"
            )
        with col2:
            show_inactive = st.checkbox("Show Inactive", key="vault_show_inactive")
        with col3:
            if st.button("🔄 Refresh", key="vault_refresh"):
                st.rerun()
        
        # Get API keys from vault
        service_type = None if service_filter == "All" else service_filter.lower()
        api_keys = self.vault_service.list_api_keys(
            service_type=service_type,
            include_inactive=show_inactive
        )
        
        if not api_keys:
            st.info("No API keys found in vault. Store your first key using the 'Store Key' tab.")
            return
        
        # Display API keys in enhanced format
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
                    st.caption(f"Added: {api_key.created_at.strftime('%Y-%m-%d %H:%M')}")
                    st.caption(f"By: {api_key.added_by_user}")
                
                with col3:
                    if st.button("🧪 Test", key=f"vault_test_{api_key.id}"):
                        self._test_vault_key(api_key)
                    
                    if st.button("✏️ Update", key=f"vault_update_{api_key.id}"):
                        self._show_update_form(api_key)
                
                with col4:
                    if api_key.is_active:
                        if st.button("🗑️ Delete", key=f"vault_delete_{api_key.id}", type="secondary"):
                            self._confirm_delete_vault_key(api_key)
                    else:
                        st.caption("Inactive")
                
                st.divider()
    
    def _render_store_key_form(self):
        """Render form to store new API key in vault"""
        st.subheader("Store New API Key")
        
        with st.form("store_vault_key_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            
            with col1:
                key_name = st.text_input(
                    "Key Name *",
                    placeholder="e.g., stripe_production, openai_main",
                    help="Unique identifier for this API key"
                )
                
                service_type = st.selectbox(
                    "Service Type *",
                    ["stripe", "openai", "airtable", "twilio", "sendgrid", "aws", "google_cloud", "azure", "other"],
                    format_func=lambda x: x.replace('_', ' ').title()
                )
            
            with col2:
                api_key = st.text_input(
                    "API Key *",
                    type="password",
                    placeholder="Enter your API key here",
                    help="The key will be encrypted before storage in the vault"
                )
                
                description = st.text_area(
                    "Description",
                    placeholder="Optional description of this API key",
                    height=100
                )
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                test_before_store = st.checkbox("Test connection before storing", value=True)
            
            with col2:
                submitted = st.form_submit_button("🔒 Store in Vault", type="primary")
            
            if submitted:
                self._handle_store_key(key_name, api_key, service_type, description, test_before_store)
    
    def _render_vault_status(self):
        """Render vault status and cache information"""
        st.subheader("Vault Status")
        
        # Cache statistics
        cache_stats = self.vault_service.get_cache_stats()
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Cached Keys", cache_stats["cached_keys"])
            st.metric("Session ID", cache_stats["session_id"][:8] + "...")
        
        with col2:
            st.metric("Cache Timeout", f"{cache_stats['cache_timeout_minutes']:.0f} min")
            if st.button("🧹 Clear Cache"):
                self.vault_service.clear_cache()
                st.success("Cache cleared successfully")
                st.rerun()
        
        with col3:
            if st.button("🔧 Cleanup Expired"):
                self.vault_service.cleanup_expired_cache()
                st.success("Expired cache entries cleaned up")
                st.rerun()
        
        # Cache details
        if cache_stats["keys"]:
            st.subheader("Cache Details")
            for key_name, key_stats in cache_stats["keys"].items():
                with st.expander(f"🔑 {key_name}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Cached:** {key_stats['cached_at'][:19]}")
                        st.write(f"**Age:** {key_stats['age_minutes']:.1f} minutes")
                    with col2:
                        st.write(f"**Access Count:** {key_stats['access_count']}")
                        if key_stats['last_accessed']:
                            st.write(f"**Last Access:** {key_stats['last_accessed'][:19]}")
        
        # Service overview
        st.subheader("Service Overview")
        api_keys = self.vault_service.list_api_keys()
        
        if api_keys:
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
                            if st.button("Test", key=f"status_vault_test_{api_key.id}"):
                                self._test_vault_key(api_key)
    
    def _render_audit_logs(self):
        """Render audit logs for vault operations"""
        st.subheader("Audit Logs")
        
        col1, col2 = st.columns([1, 3])
        with col1:
            log_limit = st.selectbox("Show logs", [25, 50, 100, 200], index=1)
        with col2:
            if st.button("🔄 Refresh Logs"):
                st.rerun()
        
        # Get audit logs
        audit_logs = self.vault_service.get_audit_logs(limit=log_limit)
        
        if not audit_logs:
            st.info("No audit logs available for this session.")
            return
        
        # Display logs in table format
        for log in audit_logs:
            with st.container():
                col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
                
                with col1:
                    status_icon = "✅" if log['success'] else "❌"
                    st.write(f"{status_icon} **{log['operation']}**")
                    st.caption(f"Key: {log['key_name']}")
                
                with col2:
                    st.write(f"User: {log['user_id']}")
                    st.caption(f"Time: {log['timestamp'][:19]}")
                
                with col3:
                    if log['ip_address']:
                        st.caption(f"IP: {log['ip_address']}")
                    if log['user_agent']:
                        st.caption(f"Agent: {log['user_agent'][:30]}...")
                
                with col4:
                    if not log['success'] and log['error_message']:
                        st.error("Error")
                        with st.expander("Details"):
                            st.text(log['error_message'])
                
                st.divider()
    
    def _handle_store_key(self, key_name: str, api_key: str, service_type: str, 
                         description: str, test_before_store: bool):
        """Handle storing a new API key in vault"""
        if not key_name or not api_key:
            st.error("Key name and API key are required.")
            return
        
        # Get client info for audit logging
        ip_address = st.session_state.get('client_ip')
        user_agent = st.session_state.get('user_agent')
        
        # Test connection if requested
        if test_before_store:
            with st.spinner("Testing API key connection..."):
                # Store temporarily to test
                temp_success, temp_message = self.vault_service.store_api_key(
                    key_name=f"temp_{key_name}_{int(datetime.now().timestamp())}",
                    api_key=api_key,
                    service_type=service_type,
                    description="Temporary key for testing",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if temp_success:
                    # Test the temporary key
                    test_success, test_message, test_details = self.vault_service.test_api_key(
                        f"temp_{key_name}_{int(datetime.now().timestamp())}",
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    # Delete temporary key
                    self.vault_service.delete_api_key(
                        f"temp_{key_name}_{int(datetime.now().timestamp())}",
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    if not test_success:
                        st.error(f"❌ Connection test failed: {test_message}")
                        st.info("You can still store the key by unchecking 'Test connection before storing'")
                        return
                    else:
                        st.success(f"✅ Connection test passed: {test_message}")
        
        # Store API key in vault
        with st.spinner("Encrypting and storing API key in vault..."):
            success, message = self.vault_service.store_api_key(
                key_name=key_name,
                api_key=api_key,
                service_type=service_type,
                description=description if description else None,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        if success:
            st.success(f"✅ {message}")
            logger.info(f"API key stored in vault: {key_name}")
            st.rerun()
        else:
            st.error(f"❌ {message}")
    
    def _test_vault_key(self, api_key: APIKeyInfo):
        """Test API key connection using vault service"""
        ip_address = st.session_state.get('client_ip')
        user_agent = st.session_state.get('user_agent')
        
        with st.spinner(f"Testing connection for {api_key.key_name}..."):
            success, message, details = self.vault_service.test_api_key(
                api_key.key_name,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        if success:
            st.success(f"✅ {message}")
            if details.get('validation_only'):
                st.info("ℹ️ Only format validation performed for this service type")
        else:
            st.error(f"❌ {message}")
            if details.get('status_code'):
                st.caption(f"HTTP Status: {details['status_code']}")
    
    def _show_update_form(self, api_key: APIKeyInfo):
        """Show update form for API key"""
        st.session_state[f"vault_update_mode_{api_key.id}"] = True
        
        with st.form(f"vault_update_form_{api_key.id}"):
            st.subheader(f"Update Vault Key: {api_key.key_name}")
            
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
                if st.form_submit_button("🔒 Update in Vault", type="primary"):
                    self._handle_update_vault_key(api_key, new_api_key, new_description)
            
            with col2:
                if st.form_submit_button("❌ Cancel"):
                    if f"vault_update_mode_{api_key.id}" in st.session_state:
                        del st.session_state[f"vault_update_mode_{api_key.id}"]
                    st.rerun()
    
    def _handle_update_vault_key(self, api_key: APIKeyInfo, new_api_key: str, new_description: str):
        """Handle updating an API key in vault"""
        if not new_api_key and new_description == (api_key.description or ""):
            st.warning("No changes detected.")
            return
        
        ip_address = st.session_state.get('client_ip')
        user_agent = st.session_state.get('user_agent')
        
        # Update API key in vault
        if new_api_key:
            success, message = self.vault_service.update_api_key(
                api_key.key_name, 
                new_api_key, 
                new_description,
                ip_address=ip_address,
                user_agent=user_agent
            )
        else:
            # Only description update - need to get current key
            with self.vault_service.retrieve_api_key(api_key.key_name, ip_address, user_agent) as key_context:
                if key_context:
                    success, message = self.vault_service.update_api_key(
                        api_key.key_name,
                        key_context.key_value,
                        new_description,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                else:
                    success, message = False, "Failed to retrieve current key for update"
        
        if success:
            st.success(f"✅ {message}")
            if f"vault_update_mode_{api_key.id}" in st.session_state:
                del st.session_state[f"vault_update_mode_{api_key.id}"]
            st.rerun()
        else:
            st.error(f"❌ {message}")
    
    def _confirm_delete_vault_key(self, api_key: APIKeyInfo):
        """Show confirmation dialog for deleting vault key"""
        st.session_state[f"vault_confirm_delete_{api_key.id}"] = True
        
        st.warning(f"⚠️ Are you sure you want to delete the vault key '{api_key.key_name}'?")
        st.caption("This action will mark the key as inactive and clear it from cache.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Yes, Delete", key=f"vault_confirm_yes_{api_key.id}", type="secondary"):
                ip_address = st.session_state.get('client_ip')
                user_agent = st.session_state.get('user_agent')
                
                success, message = self.vault_service.delete_api_key(
                    api_key.key_name,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    st.success(f"✅ {message}")
                    logger.info(f"API key deleted from vault: {api_key.key_name}")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        with col2:
            if st.button("❌ Cancel", key=f"vault_confirm_no_{api_key.id}"):
                if f"vault_confirm_delete_{api_key.id}" in st.session_state:
                    del st.session_state[f"vault_confirm_delete_{api_key.id}"]
                st.rerun()

# Global instance
_enhanced_key_vault_ui = None

def get_enhanced_key_vault_ui() -> EnhancedKeyVaultUI:
    """Get global enhanced KeyVault UI instance"""
    global _enhanced_key_vault_ui
    if _enhanced_key_vault_ui is None:
        _enhanced_key_vault_ui = EnhancedKeyVaultUI()
    return _enhanced_key_vault_ui

def render_key_vault_management():
    """Convenience function to render KeyVault management interface"""
    ui = get_enhanced_key_vault_ui()
    ui.render_key_vault_management()
