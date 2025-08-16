import streamlit as st
import pandas as pd
import sys
import os

# Apply high contrast light theme CSS
st.markdown('''
<style>
.stApp {
    background-color: #FAFAFA;
    color: #333;
}
.stMetric {
    color: #000 !important;
}
.stAlert {
    background-color: #EEE;
}
.stSelectbox label, .stNumberInput label, .stTextInput label {
    color: #000 !important;
}
.stDataFrame {
    background-color: #FFF;
}
</style>
''', unsafe_allow_html=True)

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

# Configure page
st.set_page_config(
    page_title="Cash Flow Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Main title
st.title("💰 Cash Flow Dashboard")

# Sidebar navigation info
st.sidebar.title("Navigation")
st.sidebar.markdown("Use the pages in the sidebar to navigate through different sections of the dashboard.")

# Welcome message
st.markdown("""
Welcome to your comprehensive Cash Flow Dashboard! 

Use the sidebar to navigate between different sections:
- 🏠 **Dashboard**: Overview with key metrics and indicators
- 📈 **Sales vs Cash**: Compare sales and cash flow data
- 💸 **Costs**: Detailed cost breakdown and analysis
- 🧮 **Scenarios**: Financial projections and forecasting
- 🏦 **Loan**: Loan tracking and management
- 🔌 **Integrations**: External data connections

Select a page from the sidebar to get started!
""")

# Quick stats on main page
try:
    from services.storage import get_combined_data
    from services.fx import apply_fx_conversion
    
    df = get_combined_data()
    
    if not df.empty:
        col1, col2, col3 = st.columns(3)
        
        with col1:
            total_sales = df['Sales_USD'].sum() if 'Sales_USD' in df.columns else 0
            st.metric("Total Sales", f"${total_sales:,.0f}")
        
        with col2:
            total_costs = df['Costs_USD'].sum() if 'Costs_USD' in df.columns else 0
            st.metric("Total Costs", f"${total_costs:,.0f}")
        
        with col3:
            cash_flow = total_sales - total_costs
            st.metric("Net Cash Flow", f"${cash_flow:,.0f}")

except Exception as e:
    st.info("Navigate to specific pages using the sidebar to view detailed data and functionality.")
