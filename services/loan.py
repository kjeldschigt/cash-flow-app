import sqlite3
from datetime import datetime

class Loan:
    """Loan tracking class with fixed terms and repayment-only functionality"""
    
    def __init__(self, principal=1250000):
        self.principal = principal
        self.term_years = 5
        self.annual_interest = 18750
        self.min_repayment = 10000
        self.payment_history = []
        
        # Initialize database table
        self._init_database()
        
        # Load payment history from database and calculate outstanding
        self._load_payment_history()
        self._calculate_outstanding()
    
    def _init_database(self):
        """Initialize database table for loan payments"""
        try:
            conn = sqlite3.connect('cashflow.db')
            cur = conn.cursor()
            cur.execute('''
                CREATE TABLE IF NOT EXISTS loan_repayments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    amount REAL NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"Database initialization error: {e}")
    
    def _load_payment_history(self):
        """Load repayment history from database"""
        try:
            conn = sqlite3.connect('cashflow.db')
            cur = conn.cursor()
            cur.execute('SELECT amount FROM loan_repayments ORDER BY date')
            payments = cur.fetchall()
            conn.close()
            
            self.payment_history = [amount[0] for amount in payments]
                    
        except Exception as e:
            # If database doesn't exist or has issues, start with empty history
            self.payment_history = []
    
    def _calculate_outstanding(self):
        """Calculate outstanding balance from payment history"""
        total_payments = sum(self.payment_history)
        # Outstanding = Original Principal - Total Repayments Made
        # Interest is calculated separately and due annually
        self.outstanding = max(0, self.principal - total_payments)
    
    def make_payment(self, amount):
        """Make a repayment towards the loan principal"""
        if amount >= self.min_repayment:
            self.payment_history.append(amount)
            self._calculate_outstanding()  # Recalculate after adding payment
            
            # Save to database
            try:
                conn = sqlite3.connect('cashflow.db')
                cur = conn.cursor()
                cur.execute('INSERT INTO loan_repayments (date, amount) VALUES (?, ?)', 
                           (datetime.now().isoformat(), amount))
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Database error: {e}")
                return False
        return False
    
    def get_remaining_years(self):
        """Calculate estimated remaining years based on current balance"""
        if self.outstanding <= 0:
            return 0
        
        # Simple calculation: remaining balance / (minimum annual repayment)
        min_annual_repayment = self.min_repayment * 12  # Assuming monthly minimum
        if min_annual_repayment > 0:
            return min(self.term_years, self.outstanding / min_annual_repayment)
        return self.term_years
    
    def get_total_payments(self):
        """Get total payments made"""
        return sum(self.payment_history)
    
    def get_total_interest_due(self):
        """Get total interest due over loan term"""
        return self.annual_interest * self.term_years
    
    def get_loan_summary(self):
        """Get loan summary dictionary"""
        return {
            'original_principal': self.principal,
            'original_interest': self.get_total_interest_due(),
            'current_outstanding': self.outstanding,
            'total_payments': self.get_total_payments(),
            'payment_count': len(self.payment_history),
            'term_years': self.term_years,
            'annual_interest': self.annual_interest,
            'min_repayment': self.min_repayment,
            'remaining_years': self.get_remaining_years()
        }
