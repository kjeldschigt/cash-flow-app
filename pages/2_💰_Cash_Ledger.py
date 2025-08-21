import streamlit as st
from datetime import date
from src.container import get_cash_ledger_service
from src.container import get_bank_service
from src.models.cash_ledger import CashLedgerEntry, Account

st.title("💰 Cash Ledger")
st.write("Track all cash inflows and outflows across your HK accounts")

service = get_cash_ledger_service()
bank_service = get_bank_service()

# Sidebar: Bank Account Balances
st.sidebar.subheader("🏦 Bank Account Balances")
try:
    balances = bank_service.balance_for_all_accounts(date.today())
    if balances:
        # Show a compact table with name, currency, current_balance
        display_rows = [
            {
                "Account": f"{b.get('name')} ({b.get('currency')})",
                "Balance": f"{b.get('current_balance', 0.0):,.2f} {b.get('currency')}",
            }
            for b in balances
        ]
        st.sidebar.table(display_rows)
    else:
        st.sidebar.info("No bank accounts configured.")
except Exception as e:
    st.sidebar.error("Failed to load balances.")

with st.form("add_ledger_entry"):
    entry_date = st.date_input("Date", value=date.today())
    description = st.text_input("Description")
    amount = st.number_input("Amount", step=0.01)
    currency = st.selectbox("Currency", ["USD", "HKD"])
    account = st.selectbox(
        "Account",
        [Account.OCBC_USD.value, Account.OCBC_HKD.value, Account.STATRYS_USD.value, Account.STATRYS_HKD.value],
    )
    category = st.text_input("Category", value="General")
    
    submitted = st.form_submit_button("Add Entry")
    
    if submitted and description and amount:
        service.create_entry(
            CashLedgerEntry(
                entry_date=entry_date,
                description=description,
                amount=float(amount),
                currency=currency,
                account=Account(account),
                category=category,
            )
        )
        st.success("Entry added!")
        st.rerun()

st.subheader("📄 Ledger Entries")
entries = service.get_all_entries()

if entries:
    for e in entries:
        st.write(f"- {e.entry_date} | {e.description} | {e.amount} {e.currency} | {e.account.value} | {e.category}")
else:
    st.info("No entries yet.")
