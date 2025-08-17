import streamlit as st
from typing import List, Dict, Optional

def render_metric_grid(metrics: List[Dict], columns: int = 4, accent_color: str = "#635BFF"):
    """
    Render a grid of metrics in Stripe style
    
    Args:
        metrics: List of dicts with keys: title, value, delta, caption
        columns: Number of columns in grid
        accent_color: Primary accent color
    """
    cols = st.columns(columns, gap="small")
    
    for i, metric in enumerate(metrics):
        with cols[i % columns]:
            # Clean metric display
            st.metric(
                label=metric['title'],
                value=metric['value'],
                delta=metric.get('delta'),
                help=metric.get('caption')
            )

def render_stripe_metric_card(title: str, value: str, delta: str = None, caption: str = None):
    """
    Render a single metric card in Stripe style
    
    Args:
        title: Metric title
        value: Main metric value
        delta: Change indicator (optional)
        caption: Additional context (optional)
    """
    st.markdown(f"""
        <div style="
            padding: 20px;
            border: 1px solid #e6e6e6;
            border-radius: 8px;
            background: white;
            margin-bottom: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        ">
            <div style="color: #6b7280; font-size: 14px; margin-bottom: 8px; font-weight: 500;">
                {title}
            </div>
            <div style="font-size: 28px; font-weight: 600; color: #111827; margin-bottom: 4px;">
                {value}
            </div>
            {f'<div style="color: #635BFF; font-size: 14px; font-weight: 500; margin-bottom: 4px;">{delta}</div>' if delta else ""}
            {f'<div style="color: #9ca3af; font-size: 12px;">{caption}</div>' if caption else ""}
        </div>
    """, unsafe_allow_html=True)

def create_section_header(title: str, subtitle: str = None):
    """
    Create a consistent section header
    
    Args:
        title: Section title
        subtitle: Optional subtitle/description
    """
    st.subheader(title)
    if subtitle:
        st.caption(subtitle)
    st.markdown("---")

def render_chart_container(chart_func, title: str, caption: str = None, spinner_text: str = "Rendering chart..."):
    """
    Render a chart with consistent styling and loading state
    
    Args:
        chart_func: Function that returns a plotly figure
        title: Chart title
        caption: Optional caption below chart
        spinner_text: Loading message
    """
    st.subheader(title)
    
    with st.spinner(spinner_text):
        fig = chart_func()
        st.plotly_chart(fig, use_container_width=True)
    
    if caption:
        st.caption(caption)
