import streamlit as st
from typing import List, Dict, Optional, Callable

def render_metric_grid(metrics: List[Dict], columns: int = 4):
    """
    Render a grid of metrics using Streamlit columns and metrics
    
    Args:
        metrics: List of dicts with keys: title, value, delta (optional), caption (optional)
        columns: Number of columns in grid
    """
    cols = st.columns(columns, gap="small")
    
    for i, metric in enumerate(metrics):
        with cols[i % columns]:
            st.metric(
                label=metric["title"],
                value=metric["value"],
                delta=metric.get("delta", None)
            )
            if "caption" in metric:
                st.caption(metric["caption"])

def create_section_header(title: str, subtitle: str = None):
    """
    Create a consistent Stripe-style section header
    
    Args:
        title: Section title
        subtitle: Optional subtitle/description
    """
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)

def render_chart_container(chart_func: Callable, title: str, caption: str = None, spinner_text: str = "Loading chart..."):
    """
    Render a chart with loading spinner and consistent styling
    
    Args:
        chart_func: Function that creates and returns a plotly figure
        title: Chart title
        caption: Optional caption below chart
        spinner_text: Loading message
    """
    st.markdown(f"### {title}")
    if caption:
        st.caption(caption)
    
    with st.spinner(spinner_text):
        chart_func()
