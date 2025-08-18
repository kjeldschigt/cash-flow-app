import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date
import os

# --- Page Configuration ---
st.set_page_config(
    page_title="Cash Flow App",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Pydantic Model (for validation demonstration) ---
# This section demonstrates how a Pydantic model would be used for validation.
# The main logic of this simple app uses direct validation for simplicity.
from pydantic import BaseModel, field_validator, ValidationError

class Transaction(BaseModel):
    transaction_date: date
    description: str
    amount: float
    category: str

    @field_validator('transaction_date')
    def validate_date_not_in_future(cls, v):
        if v > date.today():
            raise ValueError("Date cannot be in the future")
        return v

# --- Custom CSS ---
st.markdown("""
<style>
.stButton>button {
    background-color: #28a745;
    color: white;
    border-radius: 5px;
    border: 1px solid #28a745;
}
.stButton>button:hover {
    background-color: #218838;
    color: white;
    border: 1px solid #218838;
}
</style>
""", unsafe_allow_html=True)

# --- Data and State Management ---
def load_data(filepath, columns):
    """Load data from a CSV file or create an empty DataFrame."""
    if os.path.exists(filepath):
        df = pd.read_csv(filepath)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.date
        return df
    return pd.DataFrame(columns=columns)

if 'data' not in st.session_state:
    st.session_state.data = load_data('transactions.csv', ['date', 'description', 'amount', 'category'])

if 'categories' not in st.session_state:
    categories_df = load_data('categories.csv', ['category'])
    st.session_state.categories = categories_df['category'].tolist() if not categories_df.empty else ["Food", "Bills", "Entertainment", "Salary", "Other"]

# --- Sidebar Navigation ---
st.sidebar.title("Cash Flow App")
page = st.sidebar.radio("Go to", ["Add Transaction", "View History", "Charts"], help="Select a section to view")

# --- Helper Functions ---
def save_data():
    st.session_state.data.to_csv('transactions.csv', index=False)

def save_categories():
    pd.DataFrame({'category': st.session_state.categories}).to_csv('categories.csv', index=False)

# --- Page: Add Transaction ---
if page == "Add Transaction":
    st.header("Add New Transaction")
    with st.form(key='transaction_form'):
        col1, col2 = st.columns(2)
        with col1:
            transaction_date = st.date_input("Date", value=date.today(), help="Select transaction date")
            description = st.text_input("Description", placeholder="e.g., Groceries", help="Enter a brief description")
        with col2:
            amount = st.number_input("Amount", step=0.01, help="Positive for income, negative for expense")
            category_option = st.selectbox("Category", st.session_state.categories + ["Add new category..."], help="Select or add a category")
            
            if category_option == "Add new category...":
                new_category = st.text_input("New Category", placeholder="Enter new category name", key="new_category_input")
                category = new_category if new_category else None
            else:
                category = category_option

        submitted = st.form_submit_button("Add Transaction")
        if submitted:
            try:
                Transaction(transaction_date=transaction_date, description=description, amount=amount, category=category or "")
                if category and category not in st.session_state.categories:
                    st.session_state.categories.append(category)
                    save_categories()
                
                new_row = pd.DataFrame([{'date': transaction_date, 'description': description, 'amount': amount, 'category': category}])
                st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)
                save_data()
                st.success("Transaction added successfully!")
            except ValidationError as e:
                st.error(e.errors()[0]['msg'])
            except Exception:
                 st.error("Please fill in all fields.")

# --- Page: View History ---
elif page == "View History":
    st.header("Transaction History")
    if st.session_state.data.empty:
        st.info("No transactions yet. Add one to see your history!")
    else:
        st.dataframe(st.session_state.data.sort_values(by='date', ascending=False), use_container_width=True)

# --- Page: Charts ---
elif page == "Charts":
    st.header("Visualizations")
    if st.session_state.data.empty:
        st.info("No transactions yet. Add one to see visualizations!")
        st.image("https://via.placeholder.com/300x200.png?text=Add+Data+to+See+Charts", caption="Placeholder for charts")
    else:
        df = st.session_state.data.copy()
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        df['cumulative_balance'] = df['amount'].cumsum()

        # Cumulative Balance Chart
        fig_balance = px.line(df, x='date', y='cumulative_balance', title='Cumulative Balance Over Time')
        fig_balance.update_layout(alt_text="Line chart of cumulative balance over time.")
        st.plotly_chart(fig_balance, use_container_width=True)

        # Income vs. Expense Chart
        income = df[df['amount'] > 0].groupby('category')['amount'].sum().reset_index()
        expense = df[df['amount'] < 0].copy()
        expense['amount'] = expense['amount'].abs()
        expense = expense.groupby('category')['amount'].sum().reset_index()

        fig_income_expense = go.Figure()
        fig_income_expense.add_trace(go.Bar(x=income['category'], y=income['amount'], name='Income'))
        fig_income_expense.add_trace(go.Bar(x=expense['category'], y=expense['amount'], name='Expense'))
        fig_income_expense.update_layout(barmode='group', title='Income vs. Expense by Category', alt_text="Bar chart comparing income and expense by category.")
        st.plotly_chart(fig_income_expense, use_container_width=True)
