from pydantic import BaseModel
from datetime import date
from enum import Enum

class Account(Enum):
    OCBC_USD = "OCBC_USD"
    OCBC_HKD = "OCBC_HKD"
    STATRYS_USD = "STATRYS_USD"
    STATRYS_HKD = "STATRYS_HKD"

class CashLedgerEntry(BaseModel):
    id: int | None = None
    entry_date: date
    description: str
    amount: float
    currency: str
    account: Account
    category: str = "General"
    # Optional metadata for integrations and balances
    source: str | None = None
    external_id: str | None = None
    bank_account_id: str | None = None
