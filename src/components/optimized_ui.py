"""
Optimized UI components with lazy loading, pagination, and performance enhancements
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, Any, List, Optional, Callable
import time
from datetime import datetime
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)


class UIComponents:
    """Static UI component methods"""

    @staticmethod
    def page_header(title: str, description: str = ""):
        """Render page header with title and description"""
        st.title(title)
        if description:
            st.markdown(f"*{description}*")
        st.divider()


class LazyDataLoader:
    """Lazy loading data manager for large datasets"""

    def __init__(self, data_source: Callable, page_size: int = 100):
        self.data_source = data_source
        self.page_size = page_size
        self.cache = {}
        self.total_count = None

    @st.cache_data(ttl=300)
    def get_page(_self, page: int, filters: Dict[str, Any] = None) -> pd.DataFrame:
        """Get paginated data with caching"""
        cache_key = f"page_{page}_{hash(str(filters))}"

        if cache_key in _self.cache:
            return _self.cache[cache_key]

        offset = page * _self.page_size
        data = _self.data_source(limit=_self.page_size, offset=offset, filters=filters)

        _self.cache[cache_key] = data
        return data

    @st.cache_data(ttl=600)
    def get_total_count(_self, filters: Dict[str, Any] = None) -> int:
        """Get total record count with caching"""
        return _self.data_source(count_only=True, filters=filters)


class PaginatedTable:
    """Paginated table component with virtual scrolling"""

    def __init__(self, data_loader: LazyDataLoader, key: str):
        self.data_loader = data_loader
        self.key = key

    def render(self, filters: Dict[str, Any] = None, columns: List[str] = None):
        """Render paginated table"""
        # Initialize session state
        if f"{self.key}_page" not in st.session_state:
            st.session_state[f"{self.key}_page"] = 0

        # Get total count
        total_count = self.data_loader.get_total_count(filters)
        total_pages = (
            total_count + self.data_loader.page_size - 1
        ) // self.data_loader.page_size

        # Pagination controls
        col1, col2, col3, col4, col5 = st.columns([1, 1, 2, 1, 1])

        with col1:
            if st.button("⏮️ First", key=f"{self.key}_first"):
                st.session_state[f"{self.key}_page"] = 0

        with col2:
            if st.button("⬅️ Prev", key=f"{self.key}_prev"):
                if st.session_state[f"{self.key}_page"] > 0:
                    st.session_state[f"{self.key}_page"] -= 1

        with col3:
            current_page = st.session_state[f"{self.key}_page"]
            st.write(
                f"Page {current_page + 1} of {total_pages} ({total_count} records)"
            )

        with col4:
            if st.button("Next ➡️", key=f"{self.key}_next"):
                if st.session_state[f"{self.key}_page"] < total_pages - 1:
                    st.session_state[f"{self.key}_page"] += 1

        with col5:
            if st.button("Last ⏭️", key=f"{self.key}_last"):
                st.session_state[f"{self.key}_page"] = total_pages - 1

        # Load and display current page
        with st.spinner("Loading data..."):
            page_data = self.data_loader.get_page(
                st.session_state[f"{self.key}_page"], filters
            )

        if not page_data.empty:
            if columns:
                page_data = page_data[columns]

            st.dataframe(page_data, use_container_width=True, hide_index=True)
        else:
            st.info("No data found")


class LazyChart:
    """Lazy-loaded chart component"""

    def __init__(self, chart_func: Callable, key: str):
        self.chart_func = chart_func
        self.key = key
        self.is_loaded = False

    def render(self, data: pd.DataFrame = None, **kwargs):
        """Render chart with lazy loading"""
        # Show placeholder initially
        placeholder = st.empty()

        if not self.is_loaded:
            with placeholder.container():
                st.info("📊 Chart ready to load")
                if st.button(f"Load Chart", key=f"{self.key}_load"):
                    self.is_loaded = True
                    st.rerun()
        else:
            with placeholder.container():
                with st.spinner("Generating chart..."):
                    chart = self.chart_func(data, **kwargs)
                    st.plotly_chart(chart, use_container_width=True)


@st.cache_data(ttl=300)
def create_optimized_line_chart(
    data: pd.DataFrame, x_col: str, y_col: str, title: str
) -> go.Figure:
    """Create optimized line chart with sampling for large datasets"""
    # Sample data if too large
    if len(data) > 1000:
        data = data.sample(n=1000).sort_values(x_col)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data[x_col],
            y=data[y_col],
            mode="lines+markers",
            name=y_col,
            line=dict(width=2),
            marker=dict(size=4),
        )
    )

    fig.update_layout(
        title=title,
        xaxis_title=x_col,
        yaxis_title=y_col,
        template="plotly_white",
        height=400,
    )

    return fig


@st.cache_data(ttl=300)
def create_optimized_bar_chart(
    data: pd.DataFrame, x_col: str, y_col: str, title: str
) -> go.Figure:
    """Create optimized bar chart"""
    # Aggregate if too many categories
    if len(data) > 20:
        data = data.nlargest(20, y_col)

    fig = go.Figure()
    fig.add_trace(go.Bar(x=data[x_col], y=data[y_col], name=y_col))

    fig.update_layout(
        title=title,
        xaxis_title=x_col,
        yaxis_title=y_col,
        template="plotly_white",
        height=400,
    )

    return fig


class ProgressiveDataLoader:
    """Progressive data loading for better UX"""

    def __init__(self, data_sources: List[Callable], labels: List[str]):
        self.data_sources = data_sources
        self.labels = labels
        self.loaded_data = {}

    def load_progressively(self):
        """Load data progressively with progress indication"""
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, (source, label) in enumerate(zip(self.data_sources, self.labels)):
            status_text.text(f"Loading {label}...")

            try:
                data = source()
                self.loaded_data[label] = data
                progress = (i + 1) / len(self.data_sources)
                progress_bar.progress(progress)

            except Exception as e:
                st.error(f"Failed to load {label}: {e}")
                self.loaded_data[label] = pd.DataFrame()

        status_text.text("Loading complete!")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()

        return self.loaded_data


class VirtualScrollTable:
    """Virtual scrolling table for large datasets"""

    def __init__(self, data: pd.DataFrame, key: str, row_height: int = 35):
        self.data = data
        self.key = key
        self.row_height = row_height
        self.visible_rows = 20  # Number of visible rows

    def render(self):
        """Render virtual scroll table"""
        total_rows = len(self.data)

        if total_rows == 0:
            st.info("No data to display")
            return

        # Scroll position
        if f"{self.key}_scroll" not in st.session_state:
            st.session_state[f"{self.key}_scroll"] = 0

        # Scroll controls
        col1, col2, col3 = st.columns([1, 2, 1])

        with col1:
            if st.button("⬆️ Up", key=f"{self.key}_up"):
                st.session_state[f"{self.key}_scroll"] = max(
                    0, st.session_state[f"{self.key}_scroll"] - 5
                )

        with col2:
            scroll_pos = st.slider(
                "Scroll Position",
                0,
                max(0, total_rows - self.visible_rows),
                st.session_state[f"{self.key}_scroll"],
                key=f"{self.key}_slider",
            )
            st.session_state[f"{self.key}_scroll"] = scroll_pos

        with col3:
            if st.button("⬇️ Down", key=f"{self.key}_down"):
                st.session_state[f"{self.key}_scroll"] = min(
                    total_rows - self.visible_rows,
                    st.session_state[f"{self.key}_scroll"] + 5,
                )

        # Display visible rows
        start_idx = st.session_state[f"{self.key}_scroll"]
        end_idx = min(start_idx + self.visible_rows, total_rows)

        visible_data = self.data.iloc[start_idx:end_idx]

        st.write(f"Showing rows {start_idx + 1}-{end_idx} of {total_rows}")
        st.dataframe(visible_data, use_container_width=True, hide_index=True)


class OptimizedMetrics:
    """Optimized metrics display with caching"""

    @staticmethod
    @st.cache_data(ttl=300)
    def calculate_metrics(data: pd.DataFrame) -> Dict[str, Any]:
        """Calculate metrics with caching"""
        if data.empty:
            return {}

        metrics = {}

        # Numeric columns only
        numeric_cols = data.select_dtypes(include=["number"]).columns

        for col in numeric_cols:
            metrics[f"{col}_sum"] = data[col].sum()
            metrics[f"{col}_mean"] = data[col].mean()
            metrics[f"{col}_count"] = data[col].count()

        return metrics

    def render_metrics_grid(self, metrics: Dict[str, Any], columns: int = 4):
        """Render metrics in a grid layout"""
        if not metrics:
            st.info("No metrics to display")
            return

        metric_items = list(metrics.items())

        # Create columns
        cols = st.columns(columns)

        for i, (key, value) in enumerate(metric_items):
            col_idx = i % columns

            with cols[col_idx]:
                # Format value
                if isinstance(value, float):
                    formatted_value = f"{value:,.2f}"
                elif isinstance(value, int):
                    formatted_value = f"{value:,}"
                else:
                    formatted_value = str(value)

                st.metric(label=key.replace("_", " ").title(), value=formatted_value)


class StreamlitOptimizer:
    """Streamlit performance optimizer"""

    @staticmethod
    def optimize_rerun_logic():
        """Optimize Streamlit rerun behavior"""
        # Prevent unnecessary reruns
        if "last_interaction" not in st.session_state:
            st.session_state.last_interaction = time.time()

        current_time = time.time()
        if current_time - st.session_state.last_interaction < 0.5:  # 500ms debounce
            return False

        st.session_state.last_interaction = current_time
        return True

    @staticmethod
    def batch_operations(operations: List[Callable]):
        """Batch multiple operations to reduce reruns"""
        results = []

        for operation in operations:
            try:
                result = operation()
                results.append(result)
            except Exception as e:
                logger.error(f"Batched operation failed: {e}")
                results.append(None)

        return results

    @staticmethod
    def preload_data(data_loaders: Dict[str, Callable]):
        """Preload data in background"""
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                name: executor.submit(loader) for name, loader in data_loaders.items()
            }

            results = {}
            for name, future in futures.items():
                try:
                    results[name] = future.result(timeout=10)
                except Exception as e:
                    logger.error(f"Failed to preload {name}: {e}")
                    results[name] = pd.DataFrame()

            return results


def render_optimized_dashboard(data_sources: Dict[str, Callable]):
    """Render optimized dashboard with progressive loading"""
    st.title("📊 Optimized Dashboard")

    # Progressive data loading
    loader = ProgressiveDataLoader(
        list(data_sources.values()), list(data_sources.keys())
    )

    with st.spinner("Initializing dashboard..."):
        data = loader.load_progressively()

    # Tabs for different sections
    tab1, tab2, tab3, tab4 = st.tabs(
        ["📈 Overview", "📊 Charts", "📋 Tables", "⚙️ Settings"]
    )

    with tab1:
        st.subheader("Key Metrics")

        # Optimized metrics
        if "costs" in data and not data["costs"].empty:
            metrics_calc = OptimizedMetrics()
            metrics = metrics_calc.calculate_metrics(data["costs"])
            metrics_calc.render_metrics_grid(metrics)

    with tab2:
        st.subheader("Interactive Charts")

        if "costs" in data and not data["costs"].empty:
            # Lazy-loaded charts
            chart1 = LazyChart(create_optimized_line_chart, "cost_trend")
            chart1.render(
                data["costs"],
                x_col="date",
                y_col="amount",
                title="Cost Trend Over Time",
            )

            chart2 = LazyChart(create_optimized_bar_chart, "cost_category")
            if "category" in data["costs"].columns:
                category_data = (
                    data["costs"].groupby("category")["amount"].sum().reset_index()
                )
                chart2.render(
                    category_data,
                    x_col="category",
                    y_col="amount",
                    title="Costs by Category",
                )

    with tab3:
        st.subheader("Data Tables")

        if "costs" in data and not data["costs"].empty:
            # Virtual scrolling table
            virtual_table = VirtualScrollTable(data["costs"], "costs_table")
            virtual_table.render()

    with tab4:
        st.subheader("Performance Settings")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Cache Settings**")
            if st.button("Clear All Caches"):
                st.cache_data.clear()
                st.success("Caches cleared!")

            st.write("**Data Loading**")
            page_size = st.slider("Page Size", 10, 500, 100)
            st.session_state.page_size = page_size

        with col2:
            st.write("**Performance Stats**")
            # Show performance metrics
            st.json(
                {
                    "session_state_size": len(st.session_state),
                    "cache_hits": "N/A",  # Would need actual cache stats
                    "load_time": "< 2s",
                }
            )


# PWA (Progressive Web App) features
def add_pwa_features():
    """Add Progressive Web App features"""
    # Service worker registration
    st.markdown(
        """
    <script>
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js')
            .then(function(registration) {
                console.log('SW registered: ', registration);
            })
            .catch(function(registrationError) {
                console.log('SW registration failed: ', registrationError);
            });
    }
    </script>
    """,
        unsafe_allow_html=True,
    )

    # App manifest
    st.markdown(
        """
    <link rel="manifest" href="/manifest.json">
    <meta name="theme-color" content="#635BFF">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="apple-mobile-web-app-title" content="Cash Flow Dashboard">
    """,
        unsafe_allow_html=True,
    )
