import streamlit as st
import sys
import os
from datetime import datetime, date
from decimal import Decimal

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import new clean architecture components
from src.container import get_container
from src.ui.auth import AuthComponents
from src.ui.components.components import UIComponents
from src.ui.forms import FormComponents
from src.models.payment import RecurrenceType, PaymentStatus
from src.models.cost import CostCategory
from src.services.error_handler import ErrorHandler
import traceback

# Legacy imports for theme
from src.utils.theme_manager import apply_current_theme

try:
    # Check authentication using new auth system
    if not AuthComponents.require_authentication():
        st.stop()

    # Apply theme
    apply_current_theme()

    # Get services from container
    container = get_container()
    payment_schedule_service = container.get_payment_schedule_service()
    error_handler = container.get_error_handler()

    st.title("🗓️ Payment Schedule")

    # Initialize session state
    if "show_actual_amount" not in st.session_state:
        st.session_state.show_actual_amount = {}

    # Section 1: Create Recurring Payment
    UIComponents.section_header(
        "Create Recurring Payment", "Set up scheduled payments with automatic reminders"
    )

    # Use new form component
    form_data = FormComponents.payment_schedule_form()

    if form_data:
        try:
            # Convert form data to proper types
            recurrence_type = RecurrenceType(form_data["recurrence_pattern"].value)
            category = form_data["category"]

            # Create payment schedule using service
            schedule = payment_schedule_service.create_payment_schedule(
                name=form_data["name"],
                category=category.value,
                currency=form_data["currency"],
                amount_expected=form_data["amount_expected"],
                recurrence_pattern=recurrence_type,
                due_date=form_data["due_date"],
                comment=form_data["comment"],
            )

            UIComponents.success_message(
                f"Payment schedule '{schedule.name}' created successfully!"
            )
            st.rerun()

        except Exception as e:
            error_result = error_handler.handle_exception(e, "create_payment_schedule")
            UIComponents.error_message(error_result["message"])

    st.divider()

    # Section 2: Upcoming Payments
    UIComponents.section_header(
        "Upcoming Payments", "Manage scheduled payments and mark as paid or skipped"
    )

    try:
        # Load scheduled payments using service
        scheduled_payments = payment_schedule_service.get_scheduled_payments()

        if not scheduled_payments:
            UIComponents.empty_state(
                "No Upcoming Payments",
                "No payments are currently scheduled. Create a payment schedule above to get started.",
            )
        else:
            # Display payments using new UI components
            for payment in scheduled_payments:
                with st.container():
                    col1, col2, col3, col4 = st.columns([3, 2, 1, 1])

                    with col1:
                        st.write(f"**{payment.name}**")
                        st.write(f"Category: {payment.category}")
                        if payment.comment:
                            st.write(f"Note: {payment.comment}")

                    with col2:
                        UIComponents.currency_metric(
                            "Expected Amount", payment.amount_expected, payment.currency
                        )
                        st.write(f"Due: {payment.due_date}")
                        st.write(f"Recurrence: {payment.recurrence.value}")

                    with col3:
                        # Mark Paid button
                        if st.button("Mark Paid", key=f"paid_{payment.id}"):
                            st.session_state.show_actual_amount[payment.id] = True
                            st.rerun()

                    with col4:
                        # Skip button
                        if st.button("Skip", key=f"skip_{payment.id}"):
                            try:
                                payment_schedule_service.skip_payment(payment.id)
                                UIComponents.success_message(
                                    f"Payment '{payment.name}' marked as skipped"
                                )
                                st.rerun()
                            except Exception as e:
                                error_result = error_handler.handle_exception(
                                    e, "skip_payment"
                                )
                                UIComponents.error_message(error_result["message"])

                # Show actual amount input if Mark Paid was clicked
                if st.session_state.show_actual_amount.get(payment.id, False):
                    with st.form(f"actual_amount_form_{payment.id}"):
                        st.write(f"**Enter actual amount paid for '{payment.name}':**")
                        actual_amount = FormComponents.currency_input(
                            "Actual Amount",
                            value=payment.amount_expected,
                            currency=payment.currency,
                        )

                    col_submit, col_cancel = st.columns(2)
                    with col_submit:
                        if st.form_submit_button("Confirm Payment"):
                            try:
                                # Mark payment as paid using service
                                payment_schedule_service.mark_payment_paid(
                                    payment.id, actual_amount
                                )

                                UIComponents.success_message(
                                    f"Payment '{payment.name}' marked as paid and recorded!"
                                )
                                st.session_state.show_actual_amount[payment.id] = False
                                st.rerun()

                            except Exception as e:
                                error_result = error_handler.handle_exception(
                                    e, "mark_payment_paid"
                                )
                                UIComponents.error_message(error_result["message"])

                        with col_cancel:
                            if st.form_submit_button("Cancel"):
                                st.session_state.show_actual_amount[payment.id] = False
                                st.rerun()

                st.divider()

        # Summary section
        if scheduled_payments:
            UIComponents.section_header(
                "Payment Summary", "Overview of scheduled payments"
            )

            # Calculate summary metrics
            total_count = len(scheduled_payments)
            usd_total = sum(
                p.amount_expected for p in scheduled_payments if p.currency == "USD"
            )
            crc_total = sum(
                p.amount_expected for p in scheduled_payments if p.currency == "CRC"
            )

            col1, col2, col3 = st.columns(3)
            with col1:
                UIComponents.metric_card(
                    "Total Scheduled", str(total_count), "payments"
                )
            with col2:
                UIComponents.currency_metric("USD Payments", usd_total, "USD")
            with col3:
                UIComponents.currency_metric("CRC Payments", crc_total, "CRC")

    except Exception as e:
        error_result = error_handler.handle_exception(e, "load_payment_schedule")
        UIComponents.error_message(error_result["message"])

except Exception:
    st.error(traceback.format_exc())
