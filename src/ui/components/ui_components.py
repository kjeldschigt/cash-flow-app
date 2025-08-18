"""
Simple UIComponents class for the components package.
"""

import streamlit as st
from typing import Any, Dict, List, Optional
from decimal import Decimal
import pandas as pd


class UIComponents:
    """Collection of reusable UI components."""

    @staticmethod
    def metric_card(
        title: str,
        value: str,
        delta: Optional[str] = None,
        delta_color: str = "normal",
        help_text: Optional[str] = None,
    ) -> None:
        """Display a metric card with optional delta."""
        st.metric(
            label=title,
            value=value,
            delta=delta,
            delta_color=delta_color,
            help=help_text,
        )

    @staticmethod
    def currency_metric(
        title: str,
        amount: Decimal,
        currency: str = "USD",
        delta_amount: Optional[Decimal] = None,
        help_text: Optional[str] = None,
    ) -> None:
        """Display a currency metric with formatting."""
        # Simple formatting without external dependencies
        formatted_value = f"${amount:,.2f}" if currency == "USD" else f"{amount:,.2f} {currency}"

        delta_str = None
        delta_color = "normal"
        if delta_amount is not None:
            delta_str = f"${abs(delta_amount):,.2f}" if currency == "USD" else f"{abs(delta_amount):,.2f} {currency}"
            delta_color = "normal" if delta_amount >= 0 else "inverse"

        UIComponents.metric_card(
            title, formatted_value, delta_str, delta_color, help_text
        )

    @staticmethod
    def percentage_metric(
        title: str,
        percentage: Decimal,
        delta_percentage: Optional[Decimal] = None,
        help_text: Optional[str] = None,
    ) -> None:
        """Display a percentage metric."""
        formatted_value = f"{percentage:.2f}%"

        delta_str = None
        delta_color = "normal"
        if delta_percentage is not None:
            delta_str = f"{abs(delta_percentage):.2f}%"
            delta_color = "normal" if delta_percentage >= 0 else "inverse"

        UIComponents.metric_card(
            title, formatted_value, delta_str, delta_color, help_text
        )

    @staticmethod
    def data_table(
        data: pd.DataFrame,
        title: Optional[str] = None,
        use_container_width: bool = True,
        hide_index: bool = True,
        column_config: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Display a formatted data table."""
        if title:
            st.subheader(title)

        if data.empty:
            st.info("No data available")
            return

        st.dataframe(
            data,
            use_container_width=use_container_width,
            hide_index=hide_index,
            column_config=column_config,
        )

    @staticmethod
    def success_message(message: str) -> None:
        """Display success message."""
        st.success(f"✅ {message}")

    @staticmethod
    def error_message(message: str) -> None:
        """Display error message."""
        st.error(f"❌ {message}")

    @staticmethod
    def warning_message(message: str) -> None:
        """Display warning message."""
        st.warning(f"⚠️ {message}")

    @staticmethod
    def info_message(message: str) -> None:
        """Display info message."""
        st.info(f"ℹ️ {message}")
