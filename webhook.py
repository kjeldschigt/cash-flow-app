from fastapi import FastAPI
import uvicorn
import sqlite3

app = FastAPI()

@app.post("/update_loan")
async def update_loan(data: dict):
    amount = data.get('amount')
    date = data.get('date')
    
    conn = sqlite3.connect('cashflow.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO loan_payments (date, amount, type) VALUES (?, ?, "wire")', (date, amount))
    conn.commit()
    conn.close()
    
    return {"status": "updated"}

@app.post("/backoffice_wire")
async def handle_wire(data: dict):
    amount = data['amount']
    
    # Update DB sales/cash_in
    conn = sqlite3.connect('cashflow.db')
    cur = conn.cursor()
    
    # Insert into sales/cash flow table (assuming a cash_flow table exists)
    try:
        cur.execute('INSERT INTO cash_flow (date, amount, type, description) VALUES (?, ?, ?, ?)', 
                   (data.get('date', ''), amount, 'cash_in', 'Backoffice wire transfer'))
        conn.commit()
    except Exception as e:
        # If table doesn't exist, create it
        cur.execute('''
            CREATE TABLE IF NOT EXISTS cash_flow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                amount REAL,
                type TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cur.execute('INSERT INTO cash_flow (date, amount, type, description) VALUES (?, ?, ?, ?)', 
                   (data.get('date', ''), amount, 'cash_in', 'Backoffice wire transfer'))
        conn.commit()
    
    conn.close()
    
    return {"received": True}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
