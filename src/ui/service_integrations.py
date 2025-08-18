"""
Service Integration Management UI Components
"""

import streamlit as st
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from src.services.key_vault import get_key_vault_service
from src.models.user import UserRole
from src.ui.enhanced_auth import require_auth, get_current_user
from src.middleware.session_middleware import get_session_middleware
import logging

logger = logging.getLogger(__name__)

# Service configuration with documentation
SERVICE_CONFIGS = {
    "stripe": {
        "name": "Stripe",
        "icon": "💳",
        "description": "Payment processing and subscription management",
        "key_format": "sk_live_* or sk_test_*",
        "documentation": {
            "where_to_find": "Stripe Dashboard → Developers → API keys",
            "url": "https://dashboard.stripe.com/apikeys",
            "key_types": ["Live Secret Key (sk_live_*)", "Test Secret Key (sk_test_*)"],
            "permissions": "Read/Write access to payments, customers, and subscriptions"
        },
        "test_endpoint": "https://api.stripe.com/v1/account"
    },
    "openai": {
        "name": "OpenAI",
        "icon": "🤖",
        "description": "AI-powered text generation and analysis",
        "key_format": "sk-*",
        "documentation": {
            "where_to_find": "OpenAI Platform → API keys",
            "url": "https://platform.openai.com/api-keys",
            "key_types": ["Project API Key (sk-proj-*)", "User API Key (sk-*)"],
            "permissions": "Access to GPT models, embeddings, and other AI services"
        },
        "test_endpoint": "https://api.openai.com/v1/models"
    },
    "airtable": {
        "name": "Airtable",
        "icon": "📊",
        "description": "Database and workflow management",
        "key_format": "key* or pat*",
        "documentation": {
            "where_to_find": "Airtable → Account → Developer Hub → Personal Access Tokens",
            "url": "https://airtable.com/developers/web/guides/personal-access-tokens",
            "key_types": ["Personal Access Token (pat*)", "Legacy API Key (key*)"],
            "permissions": "Read/Write access to bases and tables"
        },
        "test_endpoint": "https://api.airtable.com/v0/meta/bases"
    },
    "twilio": {
        "name": "Twilio",
        "icon": "📱",
        "description": "SMS, voice, and communication services",
        "key_format": "Account SID + Auth Token",
        "documentation": {
            "where_to_find": "Twilio Console → Account → API Keys & Tokens",
            "url": "https://console.twilio.com/",
            "key_types": ["Account SID", "Auth Token", "API Key"],
            "permissions": "Send SMS, make calls, manage phone numbers"
        },
        "test_endpoint": "https://api.twilio.com/2010-04-01/Accounts"
    },
    "sendgrid": {
        "name": "SendGrid",
        "icon": "📧",
        "description": "Email delivery and marketing automation",
        "key_format": "SG.*",
        "documentation": {
            "where_to_find": "SendGrid → Settings → API Keys",
            "url": "https://app.sendgrid.com/settings/api_keys",
            "key_types": ["Full Access", "Restricted Access", "Billing Access"],
            "permissions": "Send emails, manage templates and lists"
        },
        "test_endpoint": "https://api.sendgrid.com/v3/user/account"
    },
    "aws": {
        "name": "Amazon Web Services",
        "icon": "☁️",
        "description": "Cloud computing and storage services",
        "key_format": "AKIA* (Access Key)",
        "documentation": {
            "where_to_find": "AWS Console → IAM → Users → Security credentials",
            "url": "https://console.aws.amazon.com/iam/",
            "key_types": ["Access Key ID", "Secret Access Key"],
            "permissions": "Varies by IAM policy (S3, EC2, Lambda, etc.)"
        },
        "test_endpoint": "https://sts.amazonaws.com/"
    },
    "google_cloud": {
        "name": "Google Cloud",
        "icon": "🌐",
        "description": "Google Cloud Platform services",
        "key_format": "JSON Service Account Key",
        "documentation": {
            "where_to_find": "Google Cloud Console → IAM & Admin → Service Accounts",
            "url": "https://console.cloud.google.com/iam-admin/serviceaccounts",
            "key_types": ["Service Account Key (JSON)", "API Key"],
            "permissions": "Varies by service account roles"
        },
        "test_endpoint": "https://cloudresourcemanager.googleapis.com/v1/projects"
    },
    "azure": {
        "name": "Microsoft Azure",
        "icon": "🔷",
        "description": "Microsoft cloud computing platform",
        "key_format": "Application ID + Secret",
        "documentation": {
            "where_to_find": "Azure Portal → App registrations → Certificates & secrets",
            "url": "https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade",
            "key_types": ["Application (client) ID", "Client Secret", "Certificate"],
            "permissions": "Varies by application permissions"
        },
        "test_endpoint": "https://management.azure.com/subscriptions"
    }
}

class ServiceIntegrationsUI:
    """UI components for service integration management"""
    
    def __init__(self):
        self.middleware = get_session_middleware()
        current_user = get_current_user()
        session_token = self.middleware.cookie_manager.get_session_cookie()
        
        self.vault_service = get_key_vault_service(
            session_id=session_token,
            user_id=current_user.id if current_user else None
        )
        logger.info("Service Integrations UI initialized")
    
    @require_auth(UserRole.ADMIN)
    def render_service_integrations(self):
        """Render the complete service integrations interface"""
        st.header("🔌 Service Integrations")
        st.markdown("Manage API keys and connections for external services")
        
        # Check admin permissions
        current_user = get_current_user()
        if not current_user or current_user.role != UserRole.ADMIN:
            st.error("🚫 Access denied. Administrator privileges required.")
            return
        
        # Get current API keys
        api_keys = self.vault_service.list_api_keys()
        current_services = {key.service_type: key for key in api_keys if key.is_active}
        
        # Service overview cards
        self._render_service_overview(current_services)
        
        st.divider()
        
        # Service-specific configuration tabs
        self._render_service_tabs(current_services)
    
    def _render_service_overview(self, current_services: Dict):
        """Render service overview with connection status"""
        st.subheader("📊 Integration Status")
        
        # Create columns for service cards
        cols = st.columns(4)
        
        for idx, (service_key, config) in enumerate(SERVICE_CONFIGS.items()):
            col = cols[idx % 4]
            
            with col:
                # Connection status
                is_connected = service_key in current_services
                status_icon = "✅" if is_connected else "❌"
                status_text = "Connected" if is_connected else "Not configured"
                status_color = "green" if is_connected else "red"
                
                # Service card
                with st.container():
                    st.markdown(f"""
                    <div style="padding: 1rem; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 1rem;">
                        <h4>{config['icon']} {config['name']}</h4>
                        <p style="font-size: 0.9rem; color: #666;">{config['description']}</p>
                        <p style="color: {status_color}; font-weight: bold;">{status_icon} {status_text}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if is_connected:
                        key_info = current_services[service_key]
                        st.caption(f"Key: {key_info.masked_value}")
                        st.caption(f"Added: {key_info.created_at.strftime('%Y-%m-%d')}")
    
    def _render_service_tabs(self, current_services: Dict):
        """Render service-specific configuration tabs"""
        st.subheader("⚙️ Service Configuration")
        
        # Create tabs for each service
        service_names = [config['name'] for config in SERVICE_CONFIGS.values()]
        tabs = st.tabs(service_names)
        
        for idx, (service_key, config) in enumerate(SERVICE_CONFIGS.items()):
            with tabs[idx]:
                self._render_service_config(service_key, config, current_services.get(service_key))
    
    def _render_service_config(self, service_key: str, config: Dict, current_key=None):
        """Render configuration for a specific service"""
        st.markdown(f"## {config['icon']} {config['name']} Integration")
        st.markdown(f"*{config['description']}*")
        
        # Connection status
        col1, col2 = st.columns([2, 1])
        
        with col1:
            if current_key:
                st.success(f"✅ Connected - Key: {current_key.masked_value}")
                if st.button(f"🧪 Test {config['name']} Connection", key=f"test_{service_key}"):
                    self._test_service_connection(service_key, current_key.key_name)
            else:
                st.warning(f"❌ Not configured - No API key found")
        
        with col2:
            if current_key:
                if st.button(f"🗑️ Remove", key=f"remove_{service_key}", type="secondary"):
                    self._confirm_remove_key(service_key, current_key.key_name)
        
        st.divider()
        
        # Documentation section
        with st.expander(f"📖 How to get {config['name']} API keys"):
            doc = config['documentation']
            st.markdown(f"**Where to find:** {doc['where_to_find']}")
            st.markdown(f"**URL:** [{doc['url']}]({doc['url']})")
            st.markdown(f"**Key format:** `{config['key_format']}`")
            st.markdown("**Key types:**")
            for key_type in doc['key_types']:
                st.markdown(f"- {key_type}")
            st.markdown(f"**Permissions:** {doc['permissions']}")
        
        # API Key configuration form
        if current_key:
            self._render_update_key_form(service_key, config, current_key)
        else:
            self._render_add_key_form(service_key, config)
    
    def _render_add_key_form(self, service_key: str, config: Dict):
        """Render form to add new API key"""
        st.markdown("### ➕ Add API Key")
        
        with st.form(f"add_{service_key}_key"):
            # Key name
            key_name = st.text_input(
                "Key Name",
                value=f"{service_key}_main",
                help="Unique identifier for this API key"
            )
            
            # API key input
            api_key = st.text_input(
                f"{config['name']} API Key",
                type="password",
                placeholder=f"Enter your {config['name']} API key here",
                help=f"Expected format: {config['key_format']}"
            )
            
            # Description
            description = st.text_area(
                "Description (optional)",
                placeholder=f"e.g., Production {config['name']} key for payments",
                height=80
            )
            
            # Options
            col1, col2 = st.columns(2)
            with col1:
                test_before_save = st.checkbox("Test connection before saving", value=True)
            with col2:
                submitted = st.form_submit_button(f"💾 Save {config['name']} Key", type="primary")
            
            if submitted:
                self._handle_add_key(service_key, key_name, api_key, description, test_before_save)
    
    def _render_update_key_form(self, service_key: str, config: Dict, current_key):
        """Render form to update existing API key"""
        st.markdown("### ✏️ Update API Key")
        
        with st.form(f"update_{service_key}_key"):
            # Show current key info
            st.info(f"Current key: {current_key.masked_value} (Added: {current_key.created_at.strftime('%Y-%m-%d %H:%M')})")
            
            # New API key input
            new_api_key = st.text_input(
                f"New {config['name']} API Key",
                type="password",
                placeholder="Enter new API key (leave empty to keep current)",
                help=f"Expected format: {config['key_format']}"
            )
            
            # Updated description
            new_description = st.text_area(
                "Description",
                value=current_key.description or "",
                height=80
            )
            
            # Options
            col1, col2 = st.columns(2)
            with col1:
                test_before_update = st.checkbox("Test connection before updating", value=True)
            with col2:
                submitted = st.form_submit_button(f"🔄 Update {config['name']} Key", type="primary")
            
            if submitted:
                self._handle_update_key(service_key, current_key.key_name, new_api_key, new_description, test_before_update)
    
    def _handle_add_key(self, service_key: str, key_name: str, api_key: str, description: str, test_before_save: bool):
        """Handle adding a new API key"""
        if not key_name or not api_key:
            st.error("Key name and API key are required.")
            return
        
        # Get client info for audit
        ip_address = st.session_state.get('client_ip')
        user_agent = st.session_state.get('user_agent')
        
        # Test connection if requested
        if test_before_save:
            with st.spinner(f"Testing {SERVICE_CONFIGS[service_key]['name']} connection..."):
                success, message, details = self.vault_service.test_api_key(
                    key_name=f"temp_{service_key}_{int(datetime.now().timestamp())}",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                # Store temporarily for testing
                temp_success, _ = self.vault_service.store_api_key(
                    key_name=f"temp_{service_key}_{int(datetime.now().timestamp())}",
                    api_key=api_key,
                    service_type=service_key,
                    description="Temporary key for testing",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if temp_success:
                    test_success, test_message, test_details = self.vault_service.test_api_key(
                        f"temp_{service_key}_{int(datetime.now().timestamp())}",
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    # Clean up temporary key
                    self.vault_service.delete_api_key(
                        f"temp_{service_key}_{int(datetime.now().timestamp())}",
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    if not test_success:
                        st.error(f"❌ Connection test failed: {test_message}")
                        return
                    else:
                        st.success(f"✅ Connection test passed: {test_message}")
        
        # Store the API key
        with st.spinner(f"Saving {SERVICE_CONFIGS[service_key]['name']} API key..."):
            success, message = self.vault_service.store_api_key(
                key_name=key_name,
                api_key=api_key,
                service_type=service_key,
                description=description,
                ip_address=ip_address,
                user_agent=user_agent
            )
        
        if success:
            st.success(f"✅ {message}")
            st.rerun()
        else:
            st.error(f"❌ {message}")
    
    def _handle_update_key(self, service_key: str, key_name: str, new_api_key: str, new_description: str, test_before_update: bool):
        """Handle updating an existing API key"""
        if not new_api_key and new_description == "":
            st.warning("No changes detected.")
            return
        
        ip_address = st.session_state.get('client_ip')
        user_agent = st.session_state.get('user_agent')
        
        # Test connection if new key provided and testing enabled
        if new_api_key and test_before_update:
            with st.spinner(f"Testing new {SERVICE_CONFIGS[service_key]['name']} connection..."):
                # Test with temporary key
                temp_key_name = f"temp_update_{service_key}_{int(datetime.now().timestamp())}"
                temp_success, _ = self.vault_service.store_api_key(
                    key_name=temp_key_name,
                    api_key=new_api_key,
                    service_type=service_key,
                    description="Temporary key for testing update",
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if temp_success:
                    test_success, test_message, _ = self.vault_service.test_api_key(
                        temp_key_name,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    
                    # Clean up temporary key
                    self.vault_service.delete_api_key(temp_key_name, ip_address, user_agent)
                    
                    if not test_success:
                        st.error(f"❌ Connection test failed: {test_message}")
                        return
                    else:
                        st.success(f"✅ Connection test passed: {test_message}")
        
        # Update the API key
        if new_api_key:
            success, message = self.vault_service.update_api_key(
                key_name=key_name,
                new_api_key=new_api_key,
                description=new_description,
                ip_address=ip_address,
                user_agent=user_agent
            )
        else:
            # Only description update
            with self.vault_service.retrieve_api_key(key_name, ip_address, user_agent) as key_context:
                if key_context:
                    success, message = self.vault_service.update_api_key(
                        key_name=key_name,
                        new_api_key=key_context.key_value,
                        description=new_description,
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                else:
                    success, message = False, "Failed to retrieve current key"
        
        if success:
            st.success(f"✅ {message}")
            st.rerun()
        else:
            st.error(f"❌ {message}")
    
    def _test_service_connection(self, service_key: str, key_name: str):
        """Test connection for a service"""
        ip_address = st.session_state.get('client_ip')
        user_agent = st.session_state.get('user_agent')
        
        with st.spinner(f"Testing {SERVICE_CONFIGS[service_key]['name']} connection..."):
            success, message, details = self.vault_service.test_api_key(
                key_name,
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
    
    def _confirm_remove_key(self, service_key: str, key_name: str):
        """Show confirmation dialog for removing a key"""
        st.session_state[f"confirm_remove_{service_key}"] = True
        
        st.warning(f"⚠️ Are you sure you want to remove the {SERVICE_CONFIGS[service_key]['name']} API key?")
        st.caption("This action will disable the integration and cannot be undone.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Yes, Remove", key=f"confirm_remove_yes_{service_key}", type="secondary"):
                ip_address = st.session_state.get('client_ip')
                user_agent = st.session_state.get('user_agent')
                
                success, message = self.vault_service.delete_api_key(
                    key_name,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                
                if success:
                    st.success(f"✅ {SERVICE_CONFIGS[service_key]['name']} integration removed")
                    st.rerun()
                else:
                    st.error(f"❌ {message}")
        
        with col2:
            if st.button("❌ Cancel", key=f"confirm_remove_no_{service_key}"):
                if f"confirm_remove_{service_key}" in st.session_state:
                    del st.session_state[f"confirm_remove_{service_key}"]
                st.rerun()

# Global instance
_service_integrations_ui = None

def get_service_integrations_ui() -> ServiceIntegrationsUI:
    """Get global service integrations UI instance"""
    global _service_integrations_ui
    if _service_integrations_ui is None:
        _service_integrations_ui = ServiceIntegrationsUI()
    return _service_integrations_ui

def render_service_integrations():
    """Convenience function to render service integrations interface"""
    ui = get_service_integrations_ui()
    ui.render_service_integrations()
