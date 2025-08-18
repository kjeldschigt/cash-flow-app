import streamlit as st
import sys
import os
import json
import requests
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import new clean architecture components
from src.container import get_container
from src.ui.auth import AuthComponents
from src.ui.components import UIComponents
from src.ui.forms import FormComponents
from src.models.integration import IntegrationType, IntegrationStatus
from src.services.error_handler import get_error_handler

# Legacy imports for theme
from utils.theme_manager import apply_current_theme

# Check authentication using new auth system
if not AuthComponents.require_authentication():
    st.stop()

# Apply theme
apply_current_theme()

# Get services from container
container = get_container()
integration_service = container.get_integration_service()
error_handler = get_error_handler()

st.title("🔌 Integrations")

# Initialize session state for edit modes
if 'edit_integration' not in st.session_state:
    st.session_state.edit_integration = None

# Tab navigation
tab1, tab2, tab3 = st.tabs(["Manage Integrations", "Add Integration", "Test Webhook Payload"])

with tab1:
    UIComponents.section_header("Manage Integrations", "Configure and monitor your external integrations")
    
    try:
        # Get all integrations using service
        integrations = integration_service.get_all_integrations()
        
        if not integrations:
            UIComponents.empty_state(
                "No Integrations Configured",
                "Use the 'Add Integration' tab to set up your first integration."
            )
        else:
            for integration in integrations:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                    
                    with col1:
                        st.write(f"**{integration.name}**")
                        st.write(f"Type: {integration.integration_type.value}")
                    
                    with col2:
                        # Status display with badge
                        if integration.status == IntegrationStatus.ACTIVE:
                            UIComponents.status_badge("Active", "success")
                        elif integration.status == IntegrationStatus.INACTIVE:
                            UIComponents.status_badge("Inactive", "warning")
                        else:
                            UIComponents.status_badge("Error", "error")
                    
                    with col3:
                        # Enable/Disable toggle
                        if st.button(
                            "Disable" if integration.status == IntegrationStatus.ACTIVE else "Enable",
                            key=f"toggle_{integration.id}"
                        ):
                            try:
                                if integration.status == IntegrationStatus.ACTIVE:
                                    integration_service.disable_integration(integration.id)
                                    UIComponents.success_message(f"Integration '{integration.name}' disabled")
                                else:
                                    integration_service.enable_integration(integration.id)
                                    UIComponents.success_message(f"Integration '{integration.name}' enabled")
                                st.rerun()
                            except Exception as e:
                                error_result = error_handler.handle_exception(e, "toggle_integration")
                                UIComponents.error_message(error_result['message'])
                    
                    with col4:
                        # Test button
                        if st.button("Test", key=f"test_{integration.id}"):
                            try:
                                test_result = integration_service.test_integration(integration.id)
                                if test_result:
                                    UIComponents.success_message("Integration test successful!")
                                else:
                                    UIComponents.error_message("Integration test failed")
                            except Exception as e:
                                error_result = error_handler.handle_exception(e, "test_integration")
                                UIComponents.error_message(error_result['message'])
                    
                    st.divider()
    
    except Exception as e:
        error_result = error_handler.handle_exception(e, "load_integrations")
        UIComponents.error_message(error_result['message'])

with tab2:
    UIComponents.section_header("Add Integration", "Set up new external integrations")
    
    # Use new form component for integration setup
    integration_form_data = FormComponents.integration_form()
    
    if integration_form_data:
        try:
            # Create integration using service
            integration = integration_service.create_integration(
                name=integration_form_data['name'],
                integration_type=integration_form_data['type'],
                config=integration_form_data['config']
            )
            
            UIComponents.success_message(f"Integration '{integration.name}' created successfully!")
            st.rerun()
            
        except Exception as e:
            error_result = error_handler.handle_exception(e, "create_integration")
            UIComponents.error_message(error_result['message'])

with tab3:
    UIComponents.section_header("Test Webhook", "Send test payloads to webhook integrations")
    
    try:
        # Get webhook integrations using service
        webhook_integrations = integration_service.get_integrations_by_type(IntegrationType.WEBHOOK)
        
        if not webhook_integrations:
            UIComponents.empty_state(
                "No Webhook Integrations",
                "Add a webhook integration first to test payloads."
            )
        else:
            # Webhook selector
            integration_names = [integration.name for integration in webhook_integrations]
            selected_integration_name = st.selectbox(
                "Select Webhook Integration",
                integration_names
            )
            
            selected_integration = next(
                (integration for integration in webhook_integrations 
                 if integration.name == selected_integration_name), 
                None
            )
            
            if selected_integration:
                webhook_url = selected_integration.config.get('webhook_url', '')
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
                            # Validate and send payload using service
                            payload = json.loads(payload_text)
                            
                            result = integration_service.send_webhook_payload(
                                selected_integration.id,
                                payload
                            )
                            
                            if result:
                                UIComponents.success_message("✅ Webhook test successful!")
                                st.json(result)
                            else:
                                UIComponents.error_message("Webhook test failed")
                                
                        except json.JSONDecodeError as e:
                            UIComponents.error_message(f"Invalid JSON: {str(e)}")
                        except Exception as e:
                            error_result = error_handler.handle_exception(e, "send_webhook")
                            UIComponents.error_message(error_result['message'])
                
                with col2:
                    st.write("**Payload Preview:**")
                    try:
                        payload = json.loads(payload_text)
                        st.json(payload)
                    except:
                        UIComponents.error_message("Invalid JSON format")
    
    except Exception as e:
        error_result = error_handler.handle_exception(e, "load_webhook_integrations")
        UIComponents.error_message(error_result['message'])
