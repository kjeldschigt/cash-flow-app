"""
UIComponents class for the components package.
"""

import streamlit as st
from typing import Any, Dict, List, Optional, Callable
from decimal import Decimal
from datetime import date, datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


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
        delta: Optional[Decimal] = None,
    ) -> None:
        """Display a currency metric with formatting."""
        # Handle delta alias for backward compatibility
        if delta_amount is None and delta is not None:
            delta_amount = delta
            
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

    @staticmethod
    def sidebar_metric(
        title: str,
        value: str,
        delta: Optional[str] = None,
        help_text: Optional[str] = None,
    ) -> None:
        """Display a metric in the sidebar."""
        with st.sidebar:
            st.metric(
                label=title,
                value=value,
                delta=delta,
                help=help_text,
            )

    @staticmethod
    def create_tabs(tab_names: List[str]) -> List[Any]:
        """Create tabs and return tab objects."""
        return st.tabs(tab_names)

    @staticmethod
    def create_columns(num_cols: int) -> List[Any]:
        """Create columns and return column objects."""
        return st.columns(num_cols)

    @staticmethod
    def expander(title: str, expanded: bool = False) -> Any:
        """Create an expander."""
        return st.expander(title, expanded=expanded)

    @staticmethod
    def section_header(title: str, subtitle: str = "") -> None:
        """Render a section header with optional subtitle."""
        st.subheader(title)
        if subtitle:
            st.caption(subtitle)

    @staticmethod
    def page_header(title: str, subtitle: str = "") -> None:
        """Render a page header with optional subtitle."""
        st.title(title)
        if subtitle:
            st.caption(subtitle)

    @staticmethod
    def cost_form(*args, **kwargs) -> None:
        """Development placeholder for the cost creation form."""
        st.info("Cost form component is not yet implemented.")

    @staticmethod
    def cost_history_table(*args, **kwargs) -> None:
        """Development placeholder for the cost history table."""
        st.info("Cost history table is not yet implemented.")


# Re-export UIComponents
__all__ = ["UIComponents"]
