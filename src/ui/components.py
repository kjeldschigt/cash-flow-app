"""
Reusable UI components for Streamlit application.
"""

import streamlit as st
from typing import Any, Dict, List, Optional, Callable
from decimal import Decimal
from datetime import date, datetime
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from ..utils.currency_utils import CurrencyUtils
from ..utils.date_utils import DateUtils


class UIComponents:
    """Collection of reusable UI components."""
    
    @staticmethod
    def metric_card(
        title: str, 
        value: str, 
        delta: Optional[str] = None,
        delta_color: str = "normal",
        help_text: Optional[str] = None
    ) -> None:
        """Display a metric card with optional delta."""
        st.metric(
            label=title,
            value=value,
            delta=delta,
            delta_color=delta_color,
            help=help_text
        )
    
    @staticmethod
    def currency_metric(
        title: str,
        amount: Decimal,
        currency: str = "USD",
        delta_amount: Optional[Decimal] = None,
        help_text: Optional[str] = None
    ) -> None:
        """Display a currency metric with formatting."""
        formatted_value = CurrencyUtils.format_amount(amount, currency)
        
        delta_str = None
        delta_color = "normal"
        if delta_amount is not None:
            delta_str = CurrencyUtils.format_amount(abs(delta_amount), currency)
            delta_color = "normal" if delta_amount >= 0 else "inverse"
        
        UIComponents.metric_card(title, formatted_value, delta_str, delta_color, help_text)
    
    @staticmethod
    def percentage_metric(
        title: str,
        percentage: Decimal,
        delta_percentage: Optional[Decimal] = None,
        help_text: Optional[str] = None
    ) -> None:
        """Display a percentage metric."""
        formatted_value = CurrencyUtils.format_percentage(percentage, show_sign=False)
        
        delta_str = None
        delta_color = "normal"
        if delta_percentage is not None:
            delta_str = CurrencyUtils.format_percentage(abs(delta_percentage))
            delta_color = "normal" if delta_percentage >= 0 else "inverse"
        
        UIComponents.metric_card(title, formatted_value, delta_str, delta_color, help_text)
    
    @staticmethod
    def data_table(
        data: pd.DataFrame,
        title: Optional[str] = None,
        use_container_width: bool = True,
        hide_index: bool = True,
        column_config: Optional[Dict[str, Any]] = None
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
            column_config=column_config
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
    def loading_spinner(text: str = "Loading...") -> Any:
        """Display loading spinner context manager."""
        return st.spinner(text)
    
    @staticmethod
    def confirmation_dialog(
        message: str,
        confirm_text: str = "Confirm",
        cancel_text: str = "Cancel"
    ) -> bool:
        """Display confirmation dialog and return user choice."""
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(confirm_text, type="primary"):
                return True
        
        with col2:
            if st.button(cancel_text):
                return False
        
        return False
    
    @staticmethod
    def page_header(title: str, subtitle: Optional[str] = None, icon: Optional[str] = None) -> None:
        """Render a consistent page header with icon, title, subtitle, and divider."""
        # Build header text with icon
        header_text = title
        if icon:
            header_text = f"{icon} {title}"
        
        st.title(header_text)
        
        if subtitle:
            st.markdown(f"*{subtitle}*")
        
        st.divider()
    
    @staticmethod
    def section_header(title: str, description: Optional[str] = None) -> None:
        """Display section header with optional description."""
        st.header(title)
        if description:
            st.markdown(f"*{description}*")
        st.divider()
    
    @staticmethod
    def empty_state(
        title: str,
        description: str,
        action_text: Optional[str] = None,
        action_callback: Optional[Callable] = None
    ) -> None:
        """Display empty state with optional action."""
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col2:
            st.markdown(f"### {title}")
            st.markdown(description)
            
            if action_text and action_callback:
                if st.button(action_text, type="primary"):
                    action_callback()
    
    @staticmethod
    def status_badge(status: str, color_map: Optional[Dict[str, str]] = None) -> None:
        """Display status badge with color coding."""
        default_colors = {
            'active': 'green',
            'inactive': 'red',
            'pending': 'orange',
            'completed': 'green',
            'scheduled': 'blue',
            'paid': 'green',
            'overdue': 'red',
            'skipped': 'gray'
        }
        
        colors = color_map or default_colors
        color = colors.get(status.lower(), 'gray')
        
        st.markdown(
            f'<span style="background-color: {color}; color: white; padding: 2px 8px; '
            f'border-radius: 12px; font-size: 12px; font-weight: bold;">{status}</span>',
            unsafe_allow_html=True
        )
    
    @staticmethod
    def progress_bar(value: float, max_value: float = 100.0, text: Optional[str] = None) -> None:
        """Display progress bar with optional text."""
        progress = min(value / max_value, 1.0)
        st.progress(progress, text=text)
    
    @staticmethod
    def key_value_pairs(data: Dict[str, Any], title: Optional[str] = None) -> None:
        """Display key-value pairs in a formatted layout."""
        if title:
            st.subheader(title)
        
        for key, value in data.items():
            col1, col2 = st.columns([1, 2])
            with col1:
                st.write(f"**{key}:**")
            with col2:
                st.write(str(value))
    
    @staticmethod
    def date_range_picker(
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        key: Optional[str] = None
    ) -> tuple[date, date]:
        """Display date range picker and return selected dates."""
        col1, col2 = st.columns(2)
        
        with col1:
            start = st.date_input(
                "Start Date",
                value=start_date or DateUtils.get_current_month_range()[0],
                key=f"{key}_start" if key else None
            )
        
        with col2:
            end = st.date_input(
                "End Date",
                value=end_date or DateUtils.get_current_month_range()[1],
                key=f"{key}_end" if key else None
            )
        
        return start, end
