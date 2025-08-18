"""
Form components for user input and data collection.
"""

import streamlit as st
from typing import Any, Dict, List, Optional, Tuple, Union
from decimal import Decimal
from datetime import date, datetime
from ..models.cost import CostCategory
from ..models.payment import RecurrenceType
from ..utils.validation_utils import ValidationUtils
from ..utils.currency_utils import CurrencyUtils


class FormComponents:
    """Collection of reusable form components."""

    @staticmethod
    def currency_input(
        label: str,
        value: Optional[Decimal] = None,
        currency: str = "USD",
        key: Optional[str] = None,
        help_text: Optional[str] = None,
    ) -> Optional[Decimal]:
        """Currency input with validation."""
        symbol = CurrencyUtils.CURRENCY_SYMBOLS.get(currency, currency)

        amount_str = st.text_input(
            f"{label} ({symbol})",
            value=str(value) if value else "",
            key=key,
            help=help_text,
            placeholder="0.00",
        )

        if amount_str:
            amount = CurrencyUtils.parse_amount(amount_str)
            if amount is None:
                st.error("Invalid amount format")
                return None

            is_valid, error_msg = ValidationUtils.validate_amount(amount)
            if not is_valid:
                st.error(error_msg)
                return None

            return amount

        return None

    @staticmethod
    def category_select(
        label: str = "Category",
        value: Optional[CostCategory] = None,
        key: Optional[str] = None,
    ) -> Optional[CostCategory]:
        """Category selection dropdown."""
        categories = [cat.value for cat in CostCategory]

        selected = st.selectbox(
            label,
            options=categories,
            index=categories.index(value.value) if value else 0,
            key=key,
        )

        return CostCategory(selected) if selected else None

    @staticmethod
    def recurrence_select(
        label: str = "Recurrence",
        value: Optional[RecurrenceType] = None,
        key: Optional[str] = None,
    ) -> Optional[RecurrenceType]:
        """Recurrence type selection dropdown."""
        recurrence_options = [rec.value for rec in RecurrenceType]

        selected = st.selectbox(
            label,
            options=recurrence_options,
            index=recurrence_options.index(value.value) if value else 0,
            key=key,
        )

        return RecurrenceType(selected) if selected else None

    @staticmethod
    def validated_text_input(
        label: str,
        value: str = "",
        max_length: Optional[int] = None,
        required: bool = False,
        key: Optional[str] = None,
        help_text: Optional[str] = None,
    ) -> Optional[str]:
        """Text input with validation."""
        text = st.text_input(
            label, value=value, key=key, help=help_text, max_chars=max_length
        )

        if required and not text.strip():
            st.error(f"{label} is required")
            return None

        if text:
            return ValidationUtils.sanitize_string(text, max_length)

        return text if not required else None

    @staticmethod
    def email_input(
        label: str = "Email",
        value: str = "",
        key: Optional[str] = None,
        required: bool = True,
    ) -> Optional[str]:
        """Email input with validation."""
        email = st.text_input(
            label, value=value, key=key, placeholder="user@example.com"
        )

        if email:
            is_valid, error_msg = ValidationUtils.validate_email_address(email)
            if not is_valid:
                st.error(error_msg)
                return None
            return email.lower().strip()

        if required:
            st.error("Email is required")
            return None

        return email

    @staticmethod
    def password_input(
        label: str = "Password",
        key: Optional[str] = None,
        validate_strength: bool = True,
    ) -> Optional[str]:
        """Password input with strength validation."""
        password = st.text_input(label, type="password", key=key)

        if password and validate_strength:
            is_strong, issues = ValidationUtils.validate_password_strength(password)
            if not is_strong:
                for issue in issues:
                    st.error(issue)
                return None

        return password

    @staticmethod
    def cost_form(
        submit_label: str = "Add Cost", initial_values: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Complete cost entry form."""
        initial = initial_values or {}

        with st.form("cost_form"):
            col1, col2 = st.columns(2)

            with col1:
                cost_date = st.date_input(
                    "Date", value=initial.get("date", date.today())
                )

                category = FormComponents.category_select(value=initial.get("category"))

            with col2:
                currency = st.selectbox(
                    "Currency",
                    options=["USD", "CRC"],
                    index=0 if initial.get("currency", "USD") == "USD" else 1,
                )

                amount = FormComponents.currency_input(
                    "Amount", value=initial.get("amount"), currency=currency
                )

            description = st.text_area(
                "Description (Optional)",
                value=initial.get("description", ""),
                max_chars=500,
            )

            is_paid = st.checkbox("Mark as Paid", value=initial.get("is_paid", False))

            submitted = st.form_submit_button(submit_label, type="primary")

            if submitted:
                if not amount or not category:
                    st.error("Please fill in all required fields")
                    return None

                return {
                    "date": cost_date,
                    "category": category,
                    "currency": currency,
                    "amount": amount,
                    "description": description.strip() if description else None,
                    "is_paid": is_paid,
                }

        return None

    @staticmethod
    def payment_schedule_form(
        submit_label: str = "Create Schedule",
        initial_values: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Complete payment schedule form."""
        initial = initial_values or {}

        with st.form("payment_schedule_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = FormComponents.validated_text_input(
                    "Payment Name",
                    value=initial.get("name", ""),
                    required=True,
                    max_length=100,
                )

                category = FormComponents.category_select(value=initial.get("category"))

                currency = st.selectbox(
                    "Currency",
                    options=["USD", "CRC"],
                    index=0 if initial.get("currency", "USD") == "USD" else 1,
                )

            with col2:
                amount = FormComponents.currency_input(
                    "Expected Amount",
                    value=initial.get("amount_expected"),
                    currency=currency,
                )

                recurrence = FormComponents.recurrence_select(
                    value=initial.get("recurrence")
                )

                due_date = st.date_input(
                    "Due Date", value=initial.get("due_date", date.today())
                )

            comment = st.text_area(
                "Comment (Optional)", value=initial.get("comment", ""), max_chars=500
            )

            submitted = st.form_submit_button(submit_label, type="primary")

            if submitted:
                if not name or not amount or not category or not recurrence:
                    st.error("Please fill in all required fields")
                    return None

                return {
                    "name": name,
                    "category": category,
                    "currency": currency,
                    "amount_expected": amount,
                    "recurrence": recurrence,
                    "due_date": due_date,
                    "comment": comment.strip() if comment else None,
                }

        return None

    @staticmethod
    def integration_config_form(
        integration_type: str, initial_config: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """Dynamic integration configuration form."""
        config = initial_config or {}

        with st.form(f"{integration_type}_config_form"):
            st.subheader(f"{integration_type.title()} Configuration")

            if integration_type.lower() == "stripe":
                api_key = st.text_input(
                    "API Key",
                    value=config.get("api_key", ""),
                    type="password",
                    help="Your Stripe secret key (sk_...)",
                )

                webhook_endpoint = st.text_input(
                    "Webhook Endpoint (Optional)",
                    value=config.get("webhook_endpoint", ""),
                    help="URL to receive Stripe webhooks",
                )

                result_config = {
                    "api_key": api_key,
                    "webhook_endpoint": webhook_endpoint,
                }

            elif integration_type.lower() == "airtable":
                api_key = st.text_input(
                    "API Key",
                    value=config.get("api_key", ""),
                    type="password",
                    help="Your Airtable personal access token",
                )

                base_id = st.text_input(
                    "Base ID",
                    value=config.get("base_id", ""),
                    help="Airtable base ID (app...)",
                )

                table_name = st.text_input(
                    "Table Name",
                    value=config.get("table_name", ""),
                    help="Name of the table to sync with",
                )

                result_config = {
                    "api_key": api_key,
                    "base_id": base_id,
                    "table_name": table_name,
                }

            elif integration_type.lower() == "webhook":
                webhook_url = st.text_input(
                    "Webhook URL",
                    value=config.get("webhook_url", ""),
                    help="URL to send webhook requests to",
                )

                secret = st.text_input(
                    "Secret (Optional)",
                    value=config.get("secret", ""),
                    type="password",
                    help="Secret for webhook authentication",
                )

                result_config = {"webhook_url": webhook_url, "secret": secret}

            else:
                st.error(f"Unknown integration type: {integration_type}")
                return None

            submitted = st.form_submit_button("Save Configuration", type="primary")

            if submitted:
                # Validate configuration
                is_valid, errors = ValidationUtils.validate_integration_config(
                    integration_type, result_config
                )

                if not is_valid:
                    for error in errors:
                        st.error(error)
                    return None

                return result_config

        return None
