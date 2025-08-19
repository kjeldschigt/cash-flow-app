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
from src.ui.components.components import UIComponents
from src.ui.forms import FormComponents
from src.models.integration import IntegrationType, IntegrationStatus
from src.services.error_handler import ErrorHandler

# Legacy imports for theme
from src.utils.theme_manager import apply_current_theme
import traceback

# Check authentication using new auth system
if not AuthComponents.require_authentication():
    st.stop()

# Apply theme
apply_current_theme()

# Get services from container
container = get_container()
integration_service = container.get_integration_service()
error_handler = container.get_error_handler()

st.title("🔌 Integrations")

# Initialize session state for edit modes
if "edit_integration" not in st.session_state:
    st.session_state.edit_integration = None

# Tab navigation
tab1, tab2, tab3 = st.tabs(
    ["Manage Integrations", "Add Integration", "Test Webhook Payload"]
)

with tab1:
    try:
        integrations = integration_service.get_all_integrations() if hasattr(integration_service, "get_all_integrations") else []
        if integrations:
            for integration in integrations:
                st.write(f"**{getattr(integration, 'name', 'Unnamed Integration')}**")
        else:
            st.info("No integrations configured yet.")
    except Exception as e:
        error_handler.handle_error(e, "Failed to load integrations")

with tab2:
    UIComponents.section_header("Add Integration", "Set up new external integrations")

    # Use new form component for integration setup
    integration_form_data = FormComponents.integration_form()

    if integration_form_data:
        try:
            # Create integration using service
            integration = integration_service.create_integration(
                name=integration_form_data["name"],
                integration_type=integration_form_data["type"],
                config=integration_form_data["config"],
            )

            UIComponents.success_message(
                f"Integration '{integration.name}' created successfully!"
            )
            st.rerun()

        except Exception as e:
            error_result = error_handler.handle_exception(e, "create_integration")
            UIComponents.error_message(error_result["message"])

with tab3:
    UIComponents.section_header(
        "Test Webhook", "Send test payloads to webhook integrations"
    )

    try:
        # Some development containers use a mock integration service without this method
        if hasattr(integration_service, "get_integrations_by_type"):
            webhook_integrations = integration_service.get_integrations_by_type(
                IntegrationType.WEBHOOK
            )
        else:
            webhook_integrations = []
        
        # Fallback: render empty state if no integrations

        if not webhook_integrations:
            st.info("No webhook integrations found.")
        else:
            # Webhook selector
            integration_names = [
                integration.name for integration in webhook_integrations
            ]
            selected_integration_name = st.selectbox(
                "Select Webhook Integration", integration_names
            )

            selected_integration = next(
                (
                    integration
                    for integration in webhook_integrations
                    if integration.name == selected_integration_name
                ),
                None,
            )

            if selected_integration:
                webhook_url = selected_integration.config.get("webhook_url", "")
                st.write(f"**Target URL:** `{webhook_url}`")

                # Payload editor
                default_payload = {
                    "event": "test.webhook",
                    "timestamp": datetime.now().isoformat(),
                    "data": {
                        "amount": 2500,
                        "currency": "usd",
                        "customer_id": "cust_123456",
                    },
                }

                payload_text = st.text_area(
                    "Webhook Payload (JSON)",
                    value=json.dumps(default_payload, indent=2),
                    height=200,
                    help="Edit the JSON payload to test different webhook scenarios",
                )

                col1, col2 = st.columns([1, 3])

                with col1:
                    if st.button("Send Test", type="primary"):
                        try:
                            # Validate and send payload using service
                            payload = json.loads(payload_text)

                            result = integration_service.send_webhook_payload(
                                selected_integration.id, payload
                            )

                            if result:
                                UIComponents.success_message(
                                    "✅ Webhook test successful!"
                                )
                                st.json(result)
                            else:
                                UIComponents.error_message("Webhook test failed")

                        except json.JSONDecodeError as e:
                            UIComponents.error_message(f"Invalid JSON: {str(e)}")
                        except Exception as e:
                            error_result = error_handler.handle_exception(
                                e, "send_webhook"
                            )
                            UIComponents.error_message(error_result["message"])

                with col2:
                    st.write("**Payload Preview:**")
                    try:
                        payload = json.loads(payload_text)
                        st.json(payload)
                    except:
                        UIComponents.error_message("Invalid JSON format")

    except Exception as e:
        st.error(traceback.format_exc())
