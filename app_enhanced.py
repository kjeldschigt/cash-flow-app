import streamlit as st
import pandas as pd
import sys
import os
import logging
from datetime import datetime
import plotly.express as px
from pathlib import Path

# Add src directory to path for imports
src_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
if src_path not in sys.path:
    sys.path.insert(0, src_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Custom CSS for better styling
st.markdown("""
    <style>
    /* Main content area */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Sidebar */
    .css-1d391kg {
        padding: 2rem 1rem;
    }
    
    /* Buttons */
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 500;
    }
    
    /* Form elements */
    .stTextInput>div>div>input, 
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>div>div {
        border-radius: 5px;
        border: 1px solid #ccc;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .stButton>button {
            width: 100%;
        }
    }
    </style>
""", unsafe_allow_html=True)

# File paths
TRANSACTIONS_FILE = 'transactions.csv'
CATEGORIES_FILE = 'categories.csv'
DEFAULT_CATEGORIES = ["Food", "Bills", "Entertainment", "Salary", "Other"]

# Initialize session state
if 'transactions' not in st.session_state:
    if os.path.exists(TRANSACTIONS_FILE):
        st.session_state.transactions = pd.read_csv(TRANSACTIONS_FILE)
    else:
        st.session_state.transactions = pd.DataFrame(columns=['date', 'description', 'amount', 'category', 'type'])

# Initialize categories
if 'categories' not in st.session_state:
    if os.path.exists(CATEGORIES_FILE):
        try:
            st.session_state.categories = pd.read_csv(CATEGORIES_FILE)['Category'].tolist()
        except:
            st.session_state.categories = DEFAULT_CATEGORIES.copy()
    else:
        st.session_state.categories = DEFAULT_CATEGORIES.copy()

# Save categories to file
def save_categories():
    pd.DataFrame({'Category': st.session_state.categories}).to_csv(CATEGORIES_FILE, index=False)

# Add new category
def add_category(new_category):
    if new_category and new_category not in st.session_state.categories:
        st.session_state.categories.append(new_category)
        save_categories()
        st.success(f"Category '{new_category}' added!")
        return True
    return False

# Save transactions to file
def save_transactions():
    st.session_state.transactions.to_csv(TRANSACTIONS_FILE, index=False)

# Add transaction
def add_transaction(date, description, amount, category, transaction_type):
    new_row = {
        'date': date.strftime('%Y-%m-%d'),
        'description': description,
        'amount': amount if transaction_type == 'Income' else -amount,
        'category': category,
        'type': transaction_type
    }
    st.session_state.transactions = pd.concat(
        [st.session_state.transactions, pd.DataFrame([new_row])], 
        ignore_index=True
    )
    save_transactions()

# Sidebar Navigation
st.sidebar.title("💵 Cash Flow App")
page = st.sidebar.radio("Navigation", ["➕ Add Transaction", "📋 View History", "📊 Charts"])

# Add custom category in sidebar
with st.sidebar.expander("➕ Add Custom Category"):
    with st.form("category_form"):
        new_category = st.text_input("New Category", "", help="Enter a new category name")
        if st.form_submit_button("Add Category"):
            add_category(new_category)

# Main content area
if page == "➕ Add Transaction":
    st.header("Add New Transaction")
    
    with st.form("transaction_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            date = st.date_input("Date", value=datetime.now(), 
                               help="Select the transaction date (accessible via screen readers)")
            description = st.text_input("Description", "", 
                                      help="Enter a description for the transaction")
        
        with col2:
            amount = st.number_input("Amount", min_value=0.01, step=0.01, format="%.2f",
                                   help="Enter the transaction amount")
            transaction_type = st.radio("Type", ["Expense", "Income"], 
                                      help="Select transaction type")
            category = st.selectbox("Category", st.session_state.categories,
                                  help="Select or add a category")
        
        if st.form_submit_button("Add Transaction"):
            add_transaction(date, description, amount, category, transaction_type)
            st.success("Transaction added successfully!")

elif page == "📋 View History":
    st.header("Transaction History")
    
    if st.session_state.transactions.empty:
        st.info("📭 No transactions yet. Add one to get started!")
    else:
        # Display transactions with proper formatting
        display_df = st.session_state.transactions.copy()
        display_df['amount'] = display_df['amount'].apply(lambda x: f"${abs(x):.2f} ({'Expense' if x < 0 else 'Income'})")
        st.dataframe(
            display_df[['date', 'description', 'amount', 'category']],
            column_config={
                "date": "Date",
                "description": "Description",
                "amount": "Amount",
                "category": "Category"
            },
            use_container_width=True,
            hide_index=True
        )

elif page == "📊 Charts":
    st.header("Financial Overview")
    
    if st.session_state.transactions.empty:
        st.info("📊 No data to display. Add transactions to see visualizations!")
        st.image("https://cdn-icons-png.flaticon.com/512/4059/4059980.png", 
                width=200, 
                caption="No data available")
    else:
        # Create a copy of transactions for visualization
        df = st.session_state.transactions.copy()
        df['date'] = pd.to_datetime(df['date'])
        
        # Income vs Expenses
        st.subheader("Income vs Expenses")
        fig1 = px.pie(
            df.groupby('type')['amount'].sum().reset_index(),
            values='amount',
            names='type',
            color='type',
            color_discrete_map={'Expense': '#FF4B4B', 'Income': '#4CAF50'},
            hole=0.4
        )
        fig1.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0))
        st.plotly_chart(fig1, use_container_width=True)
        
        # Expenses by Category
        st.subheader("Expenses by Category")
        expenses = df[df['amount'] < 0].copy()
        if not expenses.empty:
            expenses['amount'] = expenses['amount'].abs()
            fig2 = px.bar(
                expenses.groupby('category')['amount'].sum().reset_index().sort_values('amount', ascending=False),
                x='category',
                y='amount',
                labels={'amount': 'Amount ($)', 'category': 'Category'},
                color='category',
                text_auto=True
            )
            fig2.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig2, use_container_width=True)
        else:
            st.info("No expense data to display")

# Add some space at the bottom
st.sidebar.markdown("---")
st.sidebar.markdown("*Built with ❤️ using Streamlit*")

# Initialize the app
if __name__ == "__main__":
    st.set_page_config(
        page_title="Cash Flow App",
        page_icon="💵",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Add some custom JavaScript for better mobile experience
    st.markdown("""
    <script>
    // Make iframe content fit mobile screens
    window.addEventListener('load', function() {
        const iframes = document.getElementsByTagName('iframe');
        for (let iframe of iframes) {
            iframe.style.width = '100%';
            iframe.style.maxWidth = '100%';
        }
    });
    </script>
    """, unsafe_allow_html=True)
