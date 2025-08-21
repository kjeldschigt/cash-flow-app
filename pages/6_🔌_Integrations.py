import streamlit as st
import sys
import os
import json
import requests
from datetime import datetime, date, timedelta

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
tab1, tab2, tab3, tab4 = st.tabs(
    ["Manage Integrations", "Add Integration", "Test Webhook Payload", "Stripe"]
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

with tab4:
    UIComponents.section_header("Stripe", "Import Stripe payouts into the cash ledger")
    try:
        stripe_service = container.get_stripe_service()
        bank_service = container.get_bank_service()

        # API key status
        api_key = os.environ.get("STRIPE_API_KEY", "")
        if api_key:
            masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) > 8 else "********"
            st.success(f"Stripe API key detected in environment: {masked}")
        else:
            st.info("Set STRIPE_API_KEY in your environment to enable Stripe integration.")

        # Date range
        col_a, col_b = st.columns(2)
        with col_a:
            start_date = st.date_input("Start date", value=date.today() - timedelta(days=90))
        with col_b:
            end_date = st.date_input("End date", value=date.today())

        # Bank account selection for tagging payouts
        accounts = []
        try:
            accounts = bank_service.list_accounts() or []
        except Exception as e:
            error_handler.handle_error(e, user_message="Unable to load bank accounts")
            accounts = []

        account_options = ["— None —"] + [f"{a.get('name')} ({a.get('currency','USD')}) | {a.get('id')}" for a in accounts]
        sel = st.selectbox("Tag imported payouts to bank account", options=account_options, index=0)
        selected_bank_id = None
        if sel != "— None —":
            try:
                selected_bank_id = sel.split("|")[-1].strip()
            except Exception:
                selected_bank_id = None

        # Actions
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Fetch Recent Payouts"):
                payouts = stripe_service.fetch_payouts(start_date, end_date)
                if payouts:
                    st.session_state["stripe_payouts_preview"] = payouts
                    st.success(f"Fetched {len(payouts)} payouts")
                else:
                    st.info("No payouts found for selected range.")
        with col2:
            if st.button("Import Stripe Payouts", type="primary"):
                result = stripe_service.import_payouts_to_ledger(
                    bank_account_id=selected_bank_id,
                    start_date=start_date,
                    end_date=end_date,
                )
                st.success(f"Imported: {result.get('created',0)} new, Skipped: {result.get('skipped',0)}")
                st.rerun()

        # Recent payouts table (preview or live fetch if not cached)
        payouts = st.session_state.get("stripe_payouts_preview") if "stripe_payouts_preview" in st.session_state else stripe_service.fetch_payouts(start_date, end_date)
        if payouts:
            # Sort by date desc and limit to 20
            try:
                payouts_sorted = sorted(payouts, key=lambda x: x.get("date"), reverse=True)[:20]
            except Exception:
                payouts_sorted = payouts[:20]
            rows = [
                {
                    "Date": p.get("date").isoformat() if isinstance(p.get("date"), date) else str(p.get("date")),
                    "Amount": f"{p.get('amount',0):,.2f} {p.get('currency','').upper()}",
                    "Status": p.get("status", ""),
                    "Payout ID": p.get("payout_id", ""),
                }
                for p in payouts_sorted
            ]
            st.caption("Recent Payouts (max 20)")
            st.table(rows)
        else:
            st.info("No payouts to display.")
    except Exception as e:
        error_handler.handle_error(e, user_message="Stripe section error")
