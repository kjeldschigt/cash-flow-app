import streamlit as st
import sys
import os
import json
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.settings_manager import get_setting, update_setting, get_all_settings
from services.auth import require_auth
from utils.theme_manager import apply_current_theme

# Check authentication
require_auth()

# Apply theme
apply_current_theme()

st.title("🔌 Integrations")

# Initialize session state for edit modes
if 'edit_integration' not in st.session_state:
    st.session_state.edit_integration = None

# Tab navigation
tab1, tab2, tab3 = st.tabs(["Manage Integrations", "Add Integration", "Test Webhook Payload"])

with tab1:
    st.subheader("Manage Integrations")
    
    # Get all integration settings from database
    all_settings = get_all_settings()
    integration_settings = {k: v for k, v in all_settings.items() if k.startswith('integration_')}
    
    if not integration_settings:
        st.info("No integrations configured yet. Use the 'Add Integration' tab to set up your first integration.")
    else:
        for setting_key, setting_value in integration_settings.items():
            integration_name = setting_key.replace('integration_', '').replace('_', ' ').title()
            
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.write(f"**{integration_name}**")
                
                with col2:
                    # Status toggle
                    enabled_key = f"{setting_key}_enabled"
                    current_status = get_setting(enabled_key, True)
                    status = st.toggle("Enabled", value=current_status, key=f"status_{setting_key}")
                    if status != current_status:
                        update_setting(enabled_key, status)
                        st.rerun()
                
                with col3:
                    # Last updated (mock for now)
                    st.write("Last updated: Today")
                
                with col4:
                    # Edit button
                    if st.button("Edit", key=f"edit_{setting_key}"):
                        st.session_state.edit_integration = setting_key
                        st.rerun()
                
                # Show edit form if this integration is being edited
                if st.session_state.edit_integration == setting_key:
                    with st.form(f"edit_form_{setting_key}"):
                        st.write(f"**Edit {integration_name}**")
                        
                        try:
                            config = json.loads(setting_value) if isinstance(setting_value, str) else setting_value
                        except:
                            config = {}
                        
                        # Dynamic form fields based on integration type
                        integration_type = config.get('type', 'webhook')
                        
                        new_name = st.text_input("Name", value=config.get('name', integration_name))
                        
                        if integration_type in ['stripe', 'airtable', 'google_ads']:
                            new_api_key = st.text_input("API Key", value=config.get('api_key', ''), type="password")
                        
                        if integration_type == 'webhook':
                            new_webhook_url = st.text_input("Webhook URL", value=config.get('webhook_url', ''))
                        
                        if integration_type == 'airtable':
                            new_base_id = st.text_input("Base ID", value=config.get('base_id', ''))
                            new_table_name = st.text_input("Table Name", value=config.get('table_name', ''))
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.form_submit_button("Save Changes"):
                                updated_config = {
                                    'type': integration_type,
                                    'name': new_name,
                                    'updated_at': datetime.now().isoformat()
                                }
                                
                                if integration_type in ['stripe', 'airtable', 'google_ads']:
                                    updated_config['api_key'] = new_api_key
                                if integration_type == 'webhook':
                                    updated_config['webhook_url'] = new_webhook_url
                                if integration_type == 'airtable':
                                    updated_config['base_id'] = new_base_id
                                    updated_config['table_name'] = new_table_name
                                
                                update_setting(setting_key, json.dumps(updated_config))
                                st.session_state.edit_integration = None
                                st.success("Integration updated successfully!")
                                st.rerun()
                        
                        with col2:
                            if st.form_submit_button("Cancel"):
                                st.session_state.edit_integration = None
                                st.rerun()
                
                st.divider()

with tab2:
    st.subheader("Add Integration")
    
    # Integration type selector
    integration_type = st.selectbox(
        "Integration Type",
        ["Stripe", "AbleCDP", "Airtable", "Google Ads", "Webhook", "Custom"],
        key="new_integration_type"
    )
    
    with st.form("add_integration_form"):
        st.write(f"**Configure {integration_type} Integration**")
        
        # Common fields
        integration_name = st.text_input("Integration Name", placeholder=f"My {integration_type} Integration")
        
        # Type-specific fields
        api_key = None
        webhook_url = None
        base_id = None
        table_name = None
        
        if integration_type in ["Stripe", "AbleCDP", "Google Ads"]:
            api_key = st.text_input("API Key", type="password", help="Enter your API key")
        
        if integration_type == "Webhook":
            webhook_url = st.text_input("Webhook URL", placeholder="https://your-app.com/webhook")
        
        if integration_type == "Airtable":
            api_key = st.text_input("API Key", type="password", help="Your Airtable API key")
            base_id = st.text_input("Base ID", placeholder="appXXXXXXXXXXXXXX")
            table_name = st.text_input("Table Name", placeholder="Leads")
        
        if integration_type == "Custom":
            webhook_url = st.text_input("Endpoint URL", placeholder="https://api.example.com/endpoint")
            api_key = st.text_input("API Key/Token", type="password", help="Authentication token")
        
        # Additional settings
        with st.expander("Advanced Settings"):
            events_to_subscribe = st.multiselect(
                "Events to Subscribe",
                ["payment.succeeded", "payment.failed", "lead.created", "lead.updated", "custom.event"],
                default=["payment.succeeded"]
            )
        
        if st.form_submit_button("Save Integration", type="primary"):
            if not integration_name:
                st.error("Please provide an integration name")
            else:
                # Create integration config
                config = {
                    'type': integration_type.lower().replace(' ', '_'),
                    'name': integration_name,
                    'events': events_to_subscribe,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                if api_key:
                    config['api_key'] = api_key
                if webhook_url:
                    config['webhook_url'] = webhook_url
                if base_id:
                    config['base_id'] = base_id
                if table_name:
                    config['table_name'] = table_name
                
                # Save to settings
                setting_key = f"integration_{integration_type.lower().replace(' ', '_')}_{integration_name.lower().replace(' ', '_')}"
                update_setting(setting_key, json.dumps(config))
                update_setting(f"{setting_key}_enabled", True)
                
                st.success(f"{integration_type} integration '{integration_name}' saved successfully!")
                st.rerun()

with tab3:
    st.subheader("Test Webhook Payload")
    
    # Get available webhook integrations
    all_settings = get_all_settings()
    webhook_integrations = {}
    
    for key, value in all_settings.items():
        if key.startswith('integration_'):
            try:
                config = json.loads(value) if isinstance(value, str) else value
                if 'webhook_url' in config:
                    webhook_integrations[config['name']] = config['webhook_url']
            except:
                continue
    
    if not webhook_integrations:
        st.info("No webhook integrations configured. Add a webhook integration first.")
    else:
        # Webhook selector
        selected_webhook = st.selectbox(
            "Select Webhook Integration",
            list(webhook_integrations.keys())
        )
        
        webhook_url = webhook_integrations[selected_webhook]
        st.write(f"**Target URL:** `{webhook_url}`")
        
        # Payload editor
        default_payload = {
            "event": "test.webhook",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "amount": 2500,
                "currency": "usd",
                "customer_id": "cust_123456"
            }
        }
        
        payload_text = st.text_area(
            "Webhook Payload (JSON)",
            value=json.dumps(default_payload, indent=2),
            height=200,
            help="Edit the JSON payload to test different webhook scenarios"
        )
        
        col1, col2 = st.columns([1, 3])
        
        with col1:
            if st.button("Send Test", type="primary"):
                try:
                    # Validate JSON
                    payload = json.loads(payload_text)
                    
                    # Send POST request (mock for now since we don't have real endpoints)
                    st.info(f"Sending test payload to {webhook_url}...")
                    
                    # Mock response (in real implementation, use requests.post)
                    mock_response = {
                        "status": "success",
                        "message": "Webhook received successfully",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    st.success("✅ Webhook test successful!")
                    st.json(mock_response)
                    
                except json.JSONDecodeError as e:
                    st.error(f"Invalid JSON: {str(e)}")
                except Exception as e:
                    st.error(f"Error sending webhook: {str(e)}")
        
        with col2:
            st.write("**Payload Preview:**")
            try:
                payload = json.loads(payload_text)
                st.json(payload)
            except:
                st.error("Invalid JSON format")
