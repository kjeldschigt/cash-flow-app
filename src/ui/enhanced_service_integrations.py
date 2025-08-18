"""
Enhanced Service Integrations UI with Smart API Key Resolution

This module provides an enhanced UI for managing service integrations with:
- Smart fallback system for API key resolution
- Visual indicators showing key sources
- Real-time connection status
- Source priority information
"""

import os
import streamlit as st
import logging
from typing import Dict, List, Optional
from datetime import datetime

from src.services.api_key_resolver import get_api_key_resolver, APIKeySource, ResolvedAPIKey
from src.services.api_key_test_service import APIKeyTestService
from src.models.user import UserRole
from src.services.auth import get_current_user

# Configure logging
logger = logging.getLogger(__name__)

# Service configurations with enhanced metadata
SERVICE_CONFIGS = {
    'stripe': {
        'name': 'Stripe',
        'icon': '💳',
        'description': 'Payment processing and billing',
        'key_format': 'sk_test_... or sk_live_...',
        'test_endpoint': 'https://api.stripe.com/v1/account',
        'documentation': {
            'where_to_find': 'Stripe Dashboard → Developers → API Keys',
            'url': 'https://dashboard.stripe.com/apikeys',
            'key_types': ['Secret Key (sk_...)'],
            'permissions': 'Read/Write access to your Stripe account'
        }
    },
    'openai': {
        'name': 'OpenAI',
        'icon': '🤖',
        'description': 'AI and language model services',
        'key_format': 'sk-...',
        'test_endpoint': 'https://api.openai.com/v1/models',
        'documentation': {
            'where_to_find': 'OpenAI Platform → API Keys',
            'url': 'https://platform.openai.com/api-keys',
            'key_types': ['API Key (sk-...)'],
            'permissions': 'Access to OpenAI API services'
        }
    },
    'airtable': {
        'name': 'Airtable',
        'icon': '📊',
        'description': 'Database and spreadsheet management',
        'key_format': 'pat...',
        'test_endpoint': 'https://api.airtable.com/v0/meta/bases',
        'documentation': {
            'where_to_find': 'Airtable → Account → Developer Hub → Personal Access Tokens',
            'url': 'https://airtable.com/developers/web/api/introduction',
            'key_types': ['Personal Access Token (pat...)'],
            'permissions': 'Read/Write access to your bases'
        }
    },
    'twilio': {
        'name': 'Twilio',
        'icon': '📱',
        'description': 'SMS, voice, and communication APIs',
        'key_format': 'AC... (Account SID) + Auth Token',
        'test_endpoint': 'https://api.twilio.com/2010-04-01/Accounts',
        'documentation': {
            'where_to_find': 'Twilio Console → Account → API Keys & Tokens',
            'url': 'https://console.twilio.com/',
            'key_types': ['Auth Token', 'API Key'],
            'permissions': 'Send messages and make calls'
        }
    },
    'sendgrid': {
        'name': 'SendGrid',
        'icon': '📧',
        'description': 'Email delivery and marketing',
        'key_format': 'SG...',
        'test_endpoint': 'https://api.sendgrid.com/v3/user/profile',
        'documentation': {
            'where_to_find': 'SendGrid → Settings → API Keys',
            'url': 'https://app.sendgrid.com/settings/api_keys',
            'key_types': ['API Key (SG...)'],
            'permissions': 'Send emails and manage templates'
        }
    },
    'aws': {
        'name': 'AWS',
        'icon': '☁️',
        'description': 'Amazon Web Services',
        'key_format': 'AKIA... + Secret Access Key',
        'test_endpoint': 'https://sts.amazonaws.com/',
        'documentation': {
            'where_to_find': 'AWS Console → IAM → Users → Security Credentials',
            'url': 'https://console.aws.amazon.com/iam/',
            'key_types': ['Access Key ID', 'Secret Access Key'],
            'permissions': 'Programmatic access to AWS services'
        }
    },
    'google_cloud': {
        'name': 'Google Cloud',
        'icon': '🌩️',
        'description': 'Google Cloud Platform services',
        'key_format': 'JSON key file or API key',
        'test_endpoint': 'https://cloudresourcemanager.googleapis.com/v1/projects',
        'documentation': {
            'where_to_find': 'GCP Console → IAM & Admin → Service Accounts',
            'url': 'https://console.cloud.google.com/iam-admin/serviceaccounts',
            'key_types': ['Service Account Key (JSON)', 'API Key'],
            'permissions': 'Access to GCP services'
        }
    },
    'azure': {
        'name': 'Azure',
        'icon': '🔷',
        'description': 'Microsoft Azure cloud services',
        'key_format': 'Client Secret + Application ID',
        'test_endpoint': 'https://management.azure.com/subscriptions',
        'documentation': {
            'where_to_find': 'Azure Portal → App Registrations → Certificates & Secrets',
            'url': 'https://portal.azure.com/#blade/Microsoft_AAD_RegisteredApps/ApplicationsListBlade',
            'key_types': ['Client Secret', 'Application ID'],
            'permissions': 'Access to Azure resources'
        }
    }
}

def get_source_badge(source: APIKeySource) -> str:
    """Get a colored badge for the API key source"""
    badges = {
        APIKeySource.DATABASE: "🗄️ **Database**",
        APIKeySource.ENVIRONMENT: "🌍 **Environment**", 
        APIKeySource.STREAMLIT_SECRETS: "☁️ **Streamlit Cloud**",
        APIKeySource.NOT_FOUND: "❌ **Not Found**"
    }
    return badges.get(source, "❓ **Unknown**")

def get_source_color(source: APIKeySource) -> str:
    """Get color for source indicators"""
    colors = {
        APIKeySource.DATABASE: "green",
        APIKeySource.ENVIRONMENT: "blue",
        APIKeySource.STREAMLIT_SECRETS: "orange", 
        APIKeySource.NOT_FOUND: "red"
    }
    return colors.get(source, "gray")

class EnhancedServiceIntegrationsUI:
    """Enhanced UI component for service integrations with smart API key resolution"""
    
    def __init__(self):
        """Initialize the enhanced service integrations UI"""
        current_user = get_current_user()
        if not current_user:
            st.error("Authentication required")
            return
            
        self.current_user = current_user
        self.session_id = st.session_state.get('session_id', 'default')
        
        # Initialize services
        self.resolver = get_api_key_resolver(self.session_id, current_user.id)
        self.test_service = APIKeyTestService()
    
    def render_source_priority_info(self):
        """Render information about the source priority system"""
        with st.expander("📋 API Key Source Priority System", expanded=False):
            st.markdown("""
            The system checks for API keys in the following order:
            
            1. **🗄️ Database (UI Settings)** - Highest Priority
               - Keys stored through the Settings UI
               - Encrypted and secure
               - User-specific configuration
            
            2. **🌍 Environment Variables** - Fallback
               - System environment variables
               - Useful for development and deployment
               - Server-wide configuration
            
            3. **☁️ Streamlit Cloud Secrets** - Platform Fallback
               - Streamlit Cloud's secret management
               - Ideal for cloud deployments
               - Platform-specific configuration
            """)
            
            # Show environment variable mappings
            st.subheader("Environment Variable Mappings")
            priority_info = self.resolver.get_source_priority_info()
            
            for service, env_vars in priority_info["environment_mappings"].items():
                config = SERVICE_CONFIGS.get(service, {})
                st.markdown(f"**{config.get('icon', '🔧')} {config.get('name', service.title())}**: `{', '.join(env_vars)}`")
    
    def render_service_overview(self):
        """Render overview of all services with their current status"""
        st.subheader("🔌 Service Integration Overview")
        
        # Get all resolved keys
        resolved_keys = self.resolver.get_all_resolved_keys()
        
        # Create columns for the overview
        cols = st.columns(4)
        
        for idx, (service_key, resolved_key) in enumerate(resolved_keys.items()):
            col = cols[idx % 4]
            config = SERVICE_CONFIGS.get(service_key, {})
            
            with col:
                # Service header
                st.markdown(f"### {config.get('icon', '🔧')} {config.get('name', service_key.title())}")
                
                # Connection status
                if resolved_key.is_valid:
                    st.success("✅ Connected")
                    st.caption(f"Source: {get_source_badge(resolved_key.source)}")
                    if resolved_key.masked_value:
                        st.caption(f"Key: `{resolved_key.masked_value}`")
                else:
                    st.error("❌ Not Connected")
                    st.caption("No API key found")
                
                # Quick actions
                if st.button(f"Configure {config.get('name', service_key)}", key=f"config_{service_key}"):
                    st.session_state[f"show_config_{service_key}"] = True
    
    def render_service_configuration(self, service_key: str):
        """Render detailed configuration for a specific service"""
        config = SERVICE_CONFIGS.get(service_key, {})
        resolved_key = self.resolver.resolve_api_key(f"{service_key}_api_key", service_key)
        
        st.markdown(f"## {config.get('icon', '🔧')} {config.get('name', service_key.title())} Configuration")
        
        # Current status section
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("### Current Status")
            if resolved_key.is_valid:
                st.success(f"✅ **Connected** via {get_source_badge(resolved_key.source)}")
                st.info(f"**Masked Key**: `{resolved_key.masked_value}`")
                
                # Test connection button
                if st.button(f"🔍 Test Connection", key=f"test_{service_key}"):
                    with st.spinner("Testing connection..."):
                        success, message, details = self.test_service.test_api_key(
                            resolved_key.key_value, service_key
                        )
                        if success:
                            st.success(f"✅ Connection test successful: {message}")
                        else:
                            st.error(f"❌ Connection test failed: {message}")
            else:
                st.error("❌ **Not Connected** - No API key found in any source")
        
        with col2:
            # Source priority indicator
            st.markdown("### Source Priority")
            sources = [
                (APIKeySource.DATABASE, "Database"),
                (APIKeySource.ENVIRONMENT, "Environment"),
                (APIKeySource.STREAMLIT_SECRETS, "Streamlit Cloud")
            ]
            
            for source, label in sources:
                if source == resolved_key.source:
                    st.markdown(f"🎯 **{label}** ← *Current*")
                else:
                    st.markdown(f"   {label}")
        
        # Configuration options
        st.markdown("### Configuration Options")
        
        tab1, tab2, tab3 = st.tabs(["🗄️ Database (UI)", "🌍 Environment", "☁️ Streamlit Cloud"])
        
        with tab1:
            self._render_database_config(service_key, config, resolved_key)
        
        with tab2:
            self._render_environment_config(service_key, config)
        
        with tab3:
            self._render_streamlit_secrets_config(service_key, config)
        
        # Documentation section
        self._render_service_documentation(config)
    
    def _render_database_config(self, service_key: str, config: Dict, resolved_key: ResolvedAPIKey):
        """Render database configuration section"""
        st.markdown("**Store API key in encrypted database (Recommended)**")
        
        # Check if key exists in database
        db_key = self.resolver._check_database_source(f"{service_key}_api_key", service_key)
        
        if db_key:
            st.success("✅ API key is stored in database")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Update Key", key=f"update_db_{service_key}"):
                    st.session_state[f"update_mode_{service_key}"] = True
            with col2:
                if st.button("🗑️ Remove Key", key=f"remove_db_{service_key}"):
                    st.session_state[f"confirm_remove_{service_key}"] = True
        else:
            st.info("💡 No key stored in database. Add one below for secure storage.")
        
        # Add/Update form
        if db_key is None or st.session_state.get(f"update_mode_{service_key}", False):
            with st.form(f"add_key_form_{service_key}"):
                st.markdown(f"**Add {config.get('name')} API Key**")
                
                new_key = st.text_input(
                    "API Key",
                    type="password",
                    placeholder=config.get('key_format', 'Enter your API key'),
                    key=f"new_key_{service_key}"
                )
                
                description = st.text_input(
                    "Description (Optional)",
                    placeholder=f"{config.get('name')} API key for production",
                    key=f"description_{service_key}"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    test_before_save = st.checkbox("🔍 Test before saving", value=True)
                
                with col2:
                    submitted = st.form_submit_button("💾 Save Key", type="primary")
                
                if submitted and new_key:
                    self._handle_database_key_save(service_key, new_key, description, test_before_save)
        
        # Remove confirmation
        if st.session_state.get(f"confirm_remove_{service_key}", False):
            st.warning("⚠️ Are you sure you want to remove this API key from the database?")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🗑️ Yes, Remove", key=f"confirm_remove_yes_{service_key}"):
                    self._handle_database_key_removal(service_key)
            with col2:
                if st.button("❌ Cancel", key=f"confirm_remove_no_{service_key}"):
                    st.session_state[f"confirm_remove_{service_key}"] = False
                    st.rerun()
    
    def _render_environment_config(self, service_key: str, config: Dict):
        """Render environment configuration section"""
        st.markdown("**Environment Variables (Development/Deployment)**")
        
        env_vars = self.resolver.ENV_VAR_MAPPINGS.get(service_key, [])
        env_key = self.resolver._check_environment_source(service_key)
        
        if env_key:
            st.success(f"✅ Found in environment variables")
            st.info(f"**Masked Value**: `{env_key[:4]}...{env_key[-4:] if len(env_key) > 8 else '***'}`")
        else:
            st.info("💡 No environment variables found")
        
        st.markdown("**Supported Environment Variables:**")
        for env_var in env_vars:
            status = "✅" if env_key and env_var in [k for k in env_vars if os.getenv(k)] else "❌"
            st.markdown(f"- `{env_var}` {status}")
        
        with st.expander("How to set environment variables"):
            st.code(f"""
# Linux/Mac
export {env_vars[0] if env_vars else 'API_KEY'}="your_api_key_here"

# Windows
set {env_vars[0] if env_vars else 'API_KEY'}=your_api_key_here

# Docker
docker run -e {env_vars[0] if env_vars else 'API_KEY'}="your_api_key_here" your_app

# .env file
{env_vars[0] if env_vars else 'API_KEY'}=your_api_key_here
            """)
    
    def _render_streamlit_secrets_config(self, service_key: str, config: Dict):
        """Render Streamlit secrets configuration section"""
        st.markdown("**Streamlit Cloud Secrets (Cloud Deployment)**")
        
        secrets_keys = self.resolver.SECRETS_MAPPINGS.get(service_key, [])
        secrets_key = self.resolver._check_streamlit_secrets(service_key)
        
        if secrets_key:
            st.success("✅ Found in Streamlit secrets")
            st.info(f"**Masked Value**: `{secrets_key[:4]}...{secrets_key[-4:] if len(secrets_key) > 8 else '***'}`")
        else:
            st.info("💡 No Streamlit secrets found")
        
        st.markdown("**Supported Secret Keys:**")
        for secret_key in secrets_keys:
            st.markdown(f"- `{secret_key}`")
        
        with st.expander("How to set Streamlit secrets"):
            st.markdown("""
            1. Go to your Streamlit Cloud app settings
            2. Navigate to the "Secrets" section
            3. Add your secrets in TOML format:
            """)
            
            secrets_example = "\n".join([f'{key} = "your_api_key_here"' for key in secrets_keys[:2]])
            st.code(f"""
# .streamlit/secrets.toml
{secrets_example}
            """)
    
    def _render_service_documentation(self, config: Dict):
        """Render service documentation section"""
        doc = config.get('documentation', {})
        
        with st.expander(f"📚 {config.get('name')} Documentation", expanded=False):
            st.markdown(f"**Where to find your API key:**")
            st.markdown(f"🔗 {doc.get('where_to_find', 'Check service documentation')}")
            
            if doc.get('url'):
                st.markdown(f"[Open {config.get('name')} Dashboard]({doc['url']})")
            
            if doc.get('key_types'):
                st.markdown("**Key Types:**")
                for key_type in doc['key_types']:
                    st.markdown(f"- {key_type}")
            
            if doc.get('permissions'):
                st.markdown(f"**Required Permissions:** {doc['permissions']}")
    
    def _handle_database_key_save(self, service_key: str, api_key: str, description: str, test_first: bool):
        """Handle saving API key to database"""
        if test_first:
            with st.spinner("Testing API key..."):
                success, message, details = self.test_service.test_api_key(api_key, service_key)
                if not success:
                    st.error(f"❌ API key test failed: {message}")
                    return
                st.success("✅ API key test successful")
        
        # Save to database via vault service
        try:
            if hasattr(self.resolver, 'vault_service') and self.resolver.vault_service:
                success, message = self.resolver.vault_service.store_api_key(
                    key_name=f"{service_key}_api_key",
                    api_key=api_key,
                    service_type=service_key,
                    description=description or f"{SERVICE_CONFIGS[service_key]['name']} API key"
                )
                
                if success:
                    st.success(f"✅ {SERVICE_CONFIGS[service_key]['name']} API key saved successfully")
                    # Clear cache to force refresh
                    self.resolver.invalidate_cache(service_type=service_key)
                    # Clear form state
                    if f"update_mode_{service_key}" in st.session_state:
                        del st.session_state[f"update_mode_{service_key}"]
                    st.rerun()
                else:
                    st.error(f"❌ Failed to save API key: {message}")
            else:
                st.error("❌ Database service not available")
        except Exception as e:
            st.error(f"❌ Error saving API key: {str(e)}")
    
    def _handle_database_key_removal(self, service_key: str):
        """Handle removing API key from database"""
        try:
            if hasattr(self.resolver, 'vault_service') and self.resolver.vault_service:
                success, message = self.resolver.vault_service.delete_api_key(
                    key_name=f"{service_key}_api_key"
                )
                
                if success:
                    st.success(f"✅ {SERVICE_CONFIGS[service_key]['name']} API key removed")
                    # Clear cache and state
                    self.resolver.invalidate_cache(service_type=service_key)
                    st.session_state[f"confirm_remove_{service_key}"] = False
                    st.rerun()
                else:
                    st.error(f"❌ Failed to remove API key: {message}")
            else:
                st.error("❌ Database service not available")
        except Exception as e:
            st.error(f"❌ Error removing API key: {str(e)}")

def render_enhanced_service_integrations():
    """Main function to render the enhanced service integrations UI"""
    # Check authentication and admin access
    current_user = get_current_user()
    if not current_user:
        st.error("🔒 Please log in to access service integrations.")
        return
    
    if current_user.role != UserRole.ADMIN:
        st.error("🔒 Admin access required for service integrations.")
        return
    
    # Initialize UI
    ui = EnhancedServiceIntegrationsUI()
    
    # Header
    st.title("🔌 Enhanced Service Integrations")
    st.markdown("Manage API keys with smart fallback system and source transparency")
    
    # Source priority information
    ui.render_source_priority_info()
    
    st.divider()
    
    # Service overview
    ui.render_service_overview()
    
    st.divider()
    
    # Individual service configuration
    st.subheader("🛠️ Service Configuration")
    
    # Service selection
    service_options = {f"{config['icon']} {config['name']}": key 
                      for key, config in SERVICE_CONFIGS.items()}
    
    selected_service_display = st.selectbox(
        "Select a service to configure:",
        options=list(service_options.keys()),
        key="selected_service"
    )
    
    if selected_service_display:
        selected_service = service_options[selected_service_display]
        ui.render_service_configuration(selected_service)
    
    # Cache management (Admin only)
    with st.expander("🧹 Cache Management", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔄 Refresh All Keys"):
                ui.resolver.invalidate_cache()
                st.success("Cache cleared - keys will be re-resolved")
                st.rerun()
        
        with col2:
            if st.button("📊 Show Cache Stats"):
                cache = ui.resolver._get_cache()
                st.info(f"Cached entries: {len(cache)}")
                for key, resolved in cache.items():
                    st.caption(f"- {key}: {resolved.source.value}")
        
        with col3:
            if st.button("🗑️ Clear Session Cache"):
                if ui.resolver._cache_key in st.session_state:
                    del st.session_state[ui.resolver._cache_key]
                st.success("Session cache cleared")
                st.rerun()

# Global UI instance management
_ui_instance = None

def get_enhanced_service_integrations_ui() -> EnhancedServiceIntegrationsUI:
    """Get or create enhanced service integrations UI instance"""
    global _ui_instance
    if _ui_instance is None:
        _ui_instance = EnhancedServiceIntegrationsUI()
    return _ui_instance
