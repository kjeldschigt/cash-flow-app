"""
Theme manager for consistent application styling and theming.
"""

import streamlit as st
from typing import Dict, Any, Optional
import os


class ThemeManager:
    """Manages application theming and styling."""
    
    # Default theme configuration
    DEFAULT_THEMES = {
        'light': {
            'primary_color': '#1f77b4',
            'background_color': '#ffffff',
            'secondary_background_color': '#f0f2f6',
            'text_color': '#262730',
            'font': 'sans serif'
        },
        'dark': {
            'primary_color': '#ff6b6b',
            'background_color': '#0e1117',
            'secondary_background_color': '#262730',
            'text_color': '#fafafa',
            'font': 'sans serif'
        },
        'corporate': {
            'primary_color': '#2e86de',
            'background_color': '#ffffff',
            'secondary_background_color': '#f8f9fa',
            'text_color': '#2c3e50',
            'font': 'sans serif'
        },
        'financial': {
            'primary_color': '#27ae60',
            'background_color': '#ffffff',
            'secondary_background_color': '#ecf0f1',
            'text_color': '#2c3e50',
            'font': 'monospace'
        }
    }
    
    # Custom CSS styles
    CUSTOM_CSS = """
    <style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    
    /* Header styling */
    .stApp > header {
        background-color: transparent;
    }
    
    /* Sidebar styling */
    .css-1d391kg {
        padding-top: 3rem;
    }
    
    /* Metric cards styling */
    [data-testid="metric-container"] {
        background-color: var(--secondary-background-color);
        border: 1px solid #e0e0e0;
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 0.5rem;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 500;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Success/Error message styling */
    .stSuccess, .stError, .stWarning, .stInfo {
        border-radius: 0.5rem;
        border-left: 4px solid;
        padding: 1rem;
        margin: 1rem 0;
    }
    
    /* Data table styling */
    .stDataFrame {
        border-radius: 0.5rem;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    /* Chart styling */
    .stPlotlyChart {
        border-radius: 0.5rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        background-color: var(--background-color);
    }
    
    /* Form styling */
    .stForm {
        border: 1px solid #e0e0e0;
        border-radius: 0.5rem;
        padding: 1.5rem;
        background-color: var(--secondary-background-color);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px;
    }
    
    .stTabs [data-baseweb="tab"] {
        border-radius: 0.5rem 0.5rem 0 0;
        padding: 0.5rem 1rem;
    }
    
    /* Status badge styling */
    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 1rem;
        font-size: 0.875rem;
        font-weight: 500;
        text-align: center;
    }
    
    .status-badge.success {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    
    .status-badge.warning {
        background-color: #fff3cd;
        color: #856404;
        border: 1px solid #ffeaa7;
    }
    
    .status-badge.error {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    
    .status-badge.info {
        background-color: #d1ecf1;
        color: #0c5460;
        border: 1px solid #bee5eb;
    }
    
    /* Loading spinner styling */
    .stSpinner {
        text-align: center;
        padding: 2rem;
    }
    
    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stDeployButton {display: none;}
    
    /* Responsive design */
    @media (max-width: 768px) {
        .main .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        
        [data-testid="metric-container"] {
            margin-bottom: 1rem;
        }
    }
    </style>
    """
    
    def __init__(self):
        self.current_theme = self._get_current_theme()
    
    def _get_current_theme(self) -> str:
        """Get current theme from session state or environment."""
        # Check session state first
        if hasattr(st, 'session_state') and 'theme' in st.session_state:
            return st.session_state.theme
        
        # Check environment variable
        env_theme = os.getenv('STREAMLIT_THEME', 'light')
        return env_theme if env_theme in self.DEFAULT_THEMES else 'light'
    
    def apply_theme(self, theme_name: Optional[str] = None) -> None:
        """
        Apply theme to the Streamlit application.
        
        Args:
            theme_name: Name of the theme to apply. If None, uses current theme.
        """
        if theme_name and theme_name in self.DEFAULT_THEMES:
            self.current_theme = theme_name
            if hasattr(st, 'session_state'):
                st.session_state.theme = theme_name
        
        theme_config = self.DEFAULT_THEMES[self.current_theme]
        
        # Apply custom CSS with theme variables
        css_with_vars = self._inject_theme_variables(self.CUSTOM_CSS, theme_config)
        st.markdown(css_with_vars, unsafe_allow_html=True)
        
        # Apply additional theme-specific styling
        self._apply_theme_specific_styles(self.current_theme)
    
    def _inject_theme_variables(self, css: str, theme_config: Dict[str, str]) -> str:
        """Inject theme variables into CSS."""
        css_vars = ":root {\n"
        for key, value in theme_config.items():
            css_var_name = key.replace('_', '-')
            css_vars += f"  --{css_var_name}: {value};\n"
        css_vars += "}\n"
        
        return f"<style>{css_vars}{css}</style>"
    
    def _apply_theme_specific_styles(self, theme_name: str) -> None:
        """Apply theme-specific additional styles."""
        if theme_name == 'dark':
            dark_css = """
            <style>
            /* Dark theme specific styles */
            .stApp {
                background-color: #0e1117;
            }
            
            .stSidebar {
                background-color: #262730;
            }
            
            [data-testid="metric-container"] {
                background-color: #262730;
                border-color: #4a4a4a;
            }
            
            .stForm {
                background-color: #262730;
                border-color: #4a4a4a;
            }
            </style>
            """
            st.markdown(dark_css, unsafe_allow_html=True)
        
        elif theme_name == 'financial':
            financial_css = """
            <style>
            /* Financial theme specific styles */
            .metric-positive {
                color: #27ae60 !important;
                font-weight: bold;
            }
            
            .metric-negative {
                color: #e74c3c !important;
                font-weight: bold;
            }
            
            .financial-table {
                font-family: 'Courier New', monospace;
            }
            
            .currency-symbol {
                font-weight: bold;
                color: #27ae60;
            }
            </style>
            """
            st.markdown(financial_css, unsafe_allow_html=True)
    
    def get_theme_config(self, theme_name: Optional[str] = None) -> Dict[str, str]:
        """Get theme configuration."""
        theme = theme_name or self.current_theme
        return self.DEFAULT_THEMES.get(theme, self.DEFAULT_THEMES['light'])
    
    def get_available_themes(self) -> list[str]:
        """Get list of available themes."""
        return list(self.DEFAULT_THEMES.keys())
    
    def set_page_config(self, **kwargs) -> None:
        """Set page config with theme-appropriate defaults."""
        theme_config = self.get_theme_config()
        
        default_config = {
            'page_title': 'Cash Flow Dashboard',
            'page_icon': '💰',
            'layout': 'wide',
            'initial_sidebar_state': 'expanded'
        }
        
        # Merge with provided kwargs
        config = {**default_config, **kwargs}
        
        try:
            st.set_page_config(**config)
        except st.errors.StreamlitAPIException:
            # Page config already set, ignore
            pass


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def apply_theme(theme_name: Optional[str] = None) -> None:
    """
    Apply theme to the current Streamlit application.
    
    Args:
        theme_name: Name of the theme to apply ('light', 'dark', 'corporate', 'financial').
                   If None, uses the current theme.
    """
    theme_manager = get_theme_manager()
    theme_manager.apply_theme(theme_name)


def get_current_theme() -> str:
    """Get the current theme name."""
    theme_manager = get_theme_manager()
    return theme_manager.current_theme


def get_theme_config(theme_name: Optional[str] = None) -> Dict[str, str]:
    """Get theme configuration dictionary."""
    theme_manager = get_theme_manager()
    return theme_manager.get_theme_config(theme_name)


def get_available_themes() -> list[str]:
    """Get list of available theme names."""
    theme_manager = get_theme_manager()
    return theme_manager.get_available_themes()


def apply_current_theme() -> None:
    """Apply the current theme (convenience function)."""
    apply_theme()


def set_theme_page_config(**kwargs) -> None:
    """Set page config with theme-appropriate defaults."""
    theme_manager = get_theme_manager()
    theme_manager.set_page_config(**kwargs)


# Utility functions for theme-aware styling
def get_success_color() -> str:
    """Get success color for current theme."""
    return '#27ae60'


def get_error_color() -> str:
    """Get error color for current theme."""
    return '#e74c3c'


def get_warning_color() -> str:
    """Get warning color for current theme."""
    return '#f39c12'


def get_info_color() -> str:
    """Get info color for current theme."""
    return '#3498db'


def create_status_badge(text: str, status: str = 'info') -> str:
    """
    Create a styled status badge.
    
    Args:
        text: Badge text
        status: Badge status ('success', 'warning', 'error', 'info')
    
    Returns:
        HTML string for the badge
    """
    return f'<span class="status-badge {status}">{text}</span>'
