"""
Responsive Dashboard Layout Components
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
import json

class ResponsiveGrid:
    """Responsive grid layout system for dashboard widgets"""
    
    @staticmethod
    def render(
        widgets: List[Dict[str, Any]],
        columns_config: Dict[str, int] = None,
        gap: str = "medium"
    ):
        """
        Render widgets in responsive grid layout
        
        Args:
            widgets: List of widget configurations
            columns_config: Column configuration for different screen sizes
            gap: Gap size between widgets ('small', 'medium', 'large')
        """
        if not columns_config:
            columns_config = {
                'desktop': 4,
                'tablet': 2,
                'mobile': 1
            }
        
        # Use desktop configuration for Streamlit
        num_columns = columns_config.get('desktop', 4)
        
        # Create columns with appropriate spacing
        if gap == "small":
            cols = st.columns(num_columns, gap="small")
        elif gap == "large":
            cols = st.columns(num_columns, gap="large")
        else:
            cols = st.columns(num_columns)
        
        # Render widgets in grid
        for i, widget in enumerate(widgets):
            col_index = i % num_columns
            
            with cols[col_index]:
                ResponsiveGrid._render_widget(widget)
    
    @staticmethod
    def _render_widget(widget: Dict[str, Any]):
        """Render individual widget"""
        widget_type = widget.get('type', 'metric')
        widget_config = widget.get('config', {})
        
        # Widget container with styling
        with st.container():
            if widget.get('title'):
                st.markdown(f"**{widget['title']}**")
            
            if widget_type == 'metric':
                ResponsiveGrid._render_metric_widget(widget_config)
            elif widget_type == 'chart':
                ResponsiveGrid._render_chart_widget(widget_config)
            elif widget_type == 'table':
                ResponsiveGrid._render_table_widget(widget_config)
            elif widget_type == 'custom':
                ResponsiveGrid._render_custom_widget(widget_config)
    
    @staticmethod
    def _render_metric_widget(config: Dict[str, Any]):
        """Render metric widget"""
        st.metric(
            label=config.get('label', 'Metric'),
            value=config.get('value', 0),
            delta=config.get('delta'),
            delta_color=config.get('delta_color', 'normal'),
            help=config.get('help')
        )
    
    @staticmethod
    def _render_chart_widget(config: Dict[str, Any]):
        """Render chart widget"""
        chart_type = config.get('chart_type', 'line')
        data = config.get('data')
        
        if data is not None and not data.empty:
            if chart_type == 'line':
                st.line_chart(data)
            elif chart_type == 'bar':
                st.bar_chart(data)
            elif chart_type == 'area':
                st.area_chart(data)
        else:
            st.info("No chart data available")
    
    @staticmethod
    def _render_table_widget(config: Dict[str, Any]):
        """Render table widget"""
        data = config.get('data')
        
        if data is not None and not data.empty:
            st.dataframe(data, use_container_width=True)
        else:
            st.info("No table data available")
    
    @staticmethod
    def _render_custom_widget(config: Dict[str, Any]):
        """Render custom widget"""
        render_function = config.get('render_function')
        
        if callable(render_function):
            render_function(config.get('params', {}))
        else:
            st.info("Custom widget not configured")

class DashboardLayout:
    """Main dashboard layout manager"""
    
    def __init__(self, layout_config: Dict[str, Any] = None):
        """
        Initialize dashboard layout
        
        Args:
            layout_config: Layout configuration dictionary
        """
        self.layout_config = layout_config or self._get_default_config()
        self.user_preferences = self._load_user_preferences()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default layout configuration"""
        return {
            'title': 'Cash Flow Dashboard',
            'sidebar_enabled': True,
            'theme': 'light',
            'sections': [
                {
                    'name': 'overview',
                    'title': 'Financial Overview',
                    'widgets': []
                },
                {
                    'name': 'metrics',
                    'title': 'Key Metrics',
                    'widgets': []
                },
                {
                    'name': 'charts',
                    'title': 'Analytics',
                    'widgets': []
                }
            ]
        }
    
    def _load_user_preferences(self) -> Dict[str, Any]:
        """Load user preferences from session state"""
        if 'dashboard_preferences' not in st.session_state:
            st.session_state.dashboard_preferences = {
                'widget_order': {},
                'hidden_widgets': [],
                'custom_widgets': [],
                'layout_mode': 'default'
            }
        
        return st.session_state.dashboard_preferences
    
    def render(self):
        """Render complete dashboard layout"""
        # Page configuration
        st.set_page_config(
            page_title=self.layout_config['title'],
            page_icon="💰",
            layout="wide",
            initial_sidebar_state="expanded" if self.layout_config.get('sidebar_enabled') else "collapsed"
        )
        
        # Main title
        st.title(self.layout_config['title'])
        
        # Render sidebar if enabled
        if self.layout_config.get('sidebar_enabled'):
            self._render_sidebar()
        
        # Render main content sections
        for section in self.layout_config['sections']:
            self._render_section(section)
    
    def _render_sidebar(self):
        """Render dashboard sidebar with controls"""
        with st.sidebar:
            st.header("Dashboard Controls")
            
            # Layout mode selector
            layout_mode = st.selectbox(
                "Layout Mode",
                ['default', 'compact', 'expanded'],
                index=['default', 'compact', 'expanded'].index(
                    self.user_preferences.get('layout_mode', 'default')
                )
            )
            
            if layout_mode != self.user_preferences['layout_mode']:
                self.user_preferences['layout_mode'] = layout_mode
                st.rerun()
            
            # Widget visibility controls
            st.subheader("Widget Visibility")
            
            all_widgets = []
            for section in self.layout_config['sections']:
                for widget in section.get('widgets', []):
                    all_widgets.append(widget.get('id', widget.get('title', 'Unknown')))
            
            if all_widgets:
                hidden_widgets = st.multiselect(
                    "Hide Widgets",
                    all_widgets,
                    default=self.user_preferences.get('hidden_widgets', [])
                )
                
                self.user_preferences['hidden_widgets'] = hidden_widgets
            
            # Refresh controls
            st.subheader("Data Refresh")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Refresh Data"):
                    st.cache_data.clear()
                    st.success("Data refreshed!")
            
            with col2:
                auto_refresh = st.checkbox("Auto Refresh", value=False)
                if auto_refresh:
                    st.rerun()
            
            # Export controls
            st.subheader("Export Options")
            
            if st.button("📊 Export Dashboard"):
                self._export_dashboard()
            
            if st.button("⚙️ Export Config"):
                self._export_config()
    
    def _render_section(self, section: Dict[str, Any]):
        """Render dashboard section"""
        section_name = section.get('name', 'section')
        section_title = section.get('title', 'Section')
        widgets = section.get('widgets', [])
        
        # Filter out hidden widgets
        visible_widgets = [
            w for w in widgets 
            if w.get('id', w.get('title', '')) not in self.user_preferences.get('hidden_widgets', [])
        ]
        
        if not visible_widgets:
            return
        
        # Section header
        st.header(section_title)
        
        # Section-specific layout
        layout_type = section.get('layout', 'grid')
        
        if layout_type == 'grid':
            ResponsiveGrid.render(
                visible_widgets,
                columns_config=section.get('columns_config'),
                gap=section.get('gap', 'medium')
            )
        elif layout_type == 'tabs':
            self._render_tabbed_section(visible_widgets)
        elif layout_type == 'accordion':
            self._render_accordion_section(visible_widgets)
        else:
            # Default to single column
            for widget in visible_widgets:
                ResponsiveGrid._render_widget(widget)
    
    def _render_tabbed_section(self, widgets: List[Dict[str, Any]]):
        """Render widgets in tabs"""
        if not widgets:
            return
        
        tab_names = [w.get('title', f'Tab {i+1}') for i, w in enumerate(widgets)]
        tabs = st.tabs(tab_names)
        
        for i, (tab, widget) in enumerate(zip(tabs, widgets)):
            with tab:
                ResponsiveGrid._render_widget(widget)
    
    def _render_accordion_section(self, widgets: List[Dict[str, Any]]):
        """Render widgets in accordion/expander layout"""
        for widget in widgets:
            title = widget.get('title', 'Widget')
            expanded = widget.get('expanded', False)
            
            with st.expander(title, expanded=expanded):
                ResponsiveGrid._render_widget(widget)
    
    def _export_dashboard(self):
        """Export dashboard data"""
        # This would implement dashboard export functionality
        st.info("Dashboard export functionality - implement based on requirements")
    
    def _export_config(self):
        """Export dashboard configuration"""
        config_json = json.dumps(self.layout_config, indent=2)
        st.download_button(
            label="Download Configuration",
            data=config_json,
            file_name="dashboard_config.json",
            mime="application/json"
        )

class WidgetManager:
    """Widget management system for dashboard customization"""
    
    @staticmethod
    def create_metric_widget(
        widget_id: str,
        title: str,
        label: str,
        value: Union[str, int, float],
        delta: Optional[Union[str, int, float]] = None,
        help_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create metric widget configuration"""
        return {
            'id': widget_id,
            'type': 'metric',
            'title': title,
            'config': {
                'label': label,
                'value': value,
                'delta': delta,
                'help': help_text
            }
        }
    
    @staticmethod
    def create_chart_widget(
        widget_id: str,
        title: str,
        chart_type: str,
        data: pd.DataFrame,
        chart_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create chart widget configuration"""
        return {
            'id': widget_id,
            'type': 'chart',
            'title': title,
            'config': {
                'chart_type': chart_type,
                'data': data,
                **(chart_config or {})
            }
        }
    
    @staticmethod
    def create_table_widget(
        widget_id: str,
        title: str,
        data: pd.DataFrame,
        table_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create table widget configuration"""
        return {
            'id': widget_id,
            'type': 'table',
            'title': title,
            'config': {
                'data': data,
                **(table_config or {})
            }
        }
    
    @staticmethod
    def create_custom_widget(
        widget_id: str,
        title: str,
        render_function: Callable,
        params: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Create custom widget configuration"""
        return {
            'id': widget_id,
            'type': 'custom',
            'title': title,
            'config': {
                'render_function': render_function,
                'params': params or {}
            }
        }

class DragDropInterface:
    """Drag and drop interface for widget arrangement"""
    
    def __init__(self):
        """Initialize drag and drop interface"""
        if 'widget_positions' not in st.session_state:
            st.session_state.widget_positions = {}
    
    def render_sortable_widgets(self, widgets: List[Dict[str, Any]], section_name: str):
        """Render widgets with drag and drop capability"""
        # Note: Streamlit doesn't have native drag-drop, so we simulate with selectbox reordering
        
        st.subheader(f"Arrange {section_name} Widgets")
        
        widget_names = [w.get('title', f"Widget {i}") for i, w in enumerate(widgets)]
        
        if len(widget_names) > 1:
            # Widget reordering interface
            with st.expander("🔧 Reorder Widgets"):
                new_order = []
                
                for i in range(len(widgets)):
                    available_widgets = [w for w in widget_names if w not in new_order]
                    
                    if available_widgets:
                        selected = st.selectbox(
                            f"Position {i+1}",
                            available_widgets,
                            key=f"position_{section_name}_{i}"
                        )
                        new_order.append(selected)
                
                if st.button(f"Apply Order to {section_name}", key=f"apply_{section_name}"):
                    # Reorder widgets based on selection
                    reordered_widgets = []
                    for name in new_order:
                        for widget in widgets:
                            if widget.get('title') == name:
                                reordered_widgets.append(widget)
                                break
                    
                    # Update session state
                    st.session_state.widget_positions[section_name] = new_order
                    st.success(f"{section_name} widgets reordered!")
                    
                    return reordered_widgets
        
        return widgets

class ThemeManager:
    """Theme management for dashboard styling"""
    
    THEMES = {
        'light': {
            'primary_color': '#1f77b4',
            'background_color': '#ffffff',
            'secondary_background_color': '#f0f2f6',
            'text_color': '#262730'
        },
        'dark': {
            'primary_color': '#ff6b6b',
            'background_color': '#0e1117',
            'secondary_background_color': '#262730',
            'text_color': '#fafafa'
        },
        'corporate': {
            'primary_color': '#635bff',
            'background_color': '#ffffff',
            'secondary_background_color': '#f8f9fa',
            'text_color': '#1a1a1a'
        }
    }
    
    @staticmethod
    def apply_theme(theme_name: str = 'light'):
        """Apply theme to dashboard"""
        if theme_name not in ThemeManager.THEMES:
            theme_name = 'light'
        
        theme = ThemeManager.THEMES[theme_name]
        
        # Apply theme via CSS (would need custom CSS injection)
        st.markdown(f"""
        <style>
        .main {{
            background-color: {theme['background_color']};
            color: {theme['text_color']};
        }}
        .sidebar .sidebar-content {{
            background-color: {theme['secondary_background_color']};
        }}
        </style>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def get_theme_selector():
        """Render theme selector widget"""
        return st.selectbox(
            "Dashboard Theme",
            list(ThemeManager.THEMES.keys()),
            key="theme_selector"
        )

# Convenience functions for common dashboard patterns
def create_financial_overview_layout(data: Dict[str, Any]) -> Dict[str, Any]:
    """Create standard financial overview layout"""
    return {
        'title': 'Financial Dashboard',
        'sidebar_enabled': True,
        'sections': [
            {
                'name': 'kpis',
                'title': 'Key Performance Indicators',
                'layout': 'grid',
                'columns_config': {'desktop': 4, 'tablet': 2, 'mobile': 1},
                'widgets': [
                    WidgetManager.create_metric_widget(
                        'revenue', 'Revenue', 'Monthly Revenue',
                        data.get('revenue', 0), data.get('revenue_delta')
                    ),
                    WidgetManager.create_metric_widget(
                        'costs', 'Costs', 'Monthly Costs',
                        data.get('costs', 0), data.get('costs_delta')
                    ),
                    WidgetManager.create_metric_widget(
                        'profit', 'Profit', 'Net Profit',
                        data.get('profit', 0), data.get('profit_delta')
                    ),
                    WidgetManager.create_metric_widget(
                        'margin', 'Margin', 'Profit Margin',
                        f"{data.get('margin', 0):.1f}%", data.get('margin_delta')
                    )
                ]
            },
            {
                'name': 'charts',
                'title': 'Financial Analytics',
                'layout': 'grid',
                'columns_config': {'desktop': 2, 'tablet': 1, 'mobile': 1},
                'widgets': [
                    WidgetManager.create_chart_widget(
                        'cash_flow', 'Cash Flow Trend', 'line',
                        data.get('cash_flow_data', pd.DataFrame())
                    ),
                    WidgetManager.create_chart_widget(
                        'revenue_breakdown', 'Revenue Breakdown', 'bar',
                        data.get('revenue_breakdown_data', pd.DataFrame())
                    )
                ]
            }
        ]
    }

def create_executive_summary_layout(summary_data: Dict[str, Any]) -> Dict[str, Any]:
    """Create executive summary layout"""
    return {
        'title': 'Executive Summary',
        'sidebar_enabled': False,
        'sections': [
            {
                'name': 'summary_metrics',
                'title': 'Executive Summary',
                'layout': 'grid',
                'columns_config': {'desktop': 3, 'tablet': 2, 'mobile': 1},
                'widgets': [
                    WidgetManager.create_metric_widget(
                        'ytd_revenue', 'YTD Performance', 'Year-to-Date Revenue',
                        summary_data.get('ytd_revenue', 0)
                    ),
                    WidgetManager.create_metric_widget(
                        'quarterly_growth', 'Growth', 'Quarterly Growth',
                        f"{summary_data.get('quarterly_growth', 0):.1f}%"
                    ),
                    WidgetManager.create_metric_widget(
                        'forecast_accuracy', 'Accuracy', 'Forecast Accuracy',
                        f"{summary_data.get('forecast_accuracy', 0):.1f}%"
                    )
                ]
            }
        ]
    }
