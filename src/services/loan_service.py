# src/services/loan_service.py

class LoanService:
    """
    Development placeholder for LoanService.

    In production, this will handle CRUD operations
    for loans and compute amortization schedules, etc.
    """

    def __init__(self, db_connection):
        self.db_connection = db_connection

    def get_loan_summary(self):
        """
        Temporary fallback.
        Returns a mock loan summary for development.
        """
        return {
            "total_loan": 0,
            "remaining_balance": 0,
            "next_payment_date": None,
        }

    def get_all_loans(self):
        """
        Returns an empty list for now.
        """
        return []
