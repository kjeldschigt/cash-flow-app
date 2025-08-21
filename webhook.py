from fastapi import FastAPI, HTTPException
import uvicorn
import sqlite3
from datetime import datetime
from typing import Dict, Any, Optional

app = FastAPI()

def parse_date(date_str: Optional[str]) -> str:
    """Parse date string into YYYY-MM-DD format."""
    if not date_str:
        return datetime.now().strftime("%Y-%m-%d")
    try:
        # Try parsing ISO format
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        # Fallback to current date if parsing fails
        return datetime.now().strftime("%Y-%m-%d")

def get_category_for_recipient(recipient: str) -> str:
    """Map recipient to cost category."""
    recipient = str(recipient).lower()
    if "google" in recipient:
        return "Marketing"
    elif "costa" in recipient:
        return "Operations"
    elif "agent" in recipient:
        return "Admin"
    elif "us" in recipient:
        return "Operations"
    elif "supplier" in recipient:
        return "Inventory/COGS"
    return "Other"

@app.post("/update_loan")
async def update_loan(data: dict):
    """Legacy endpoint for loan updates."""
    amount = data.get('amount')
    date = data.get('date')
    
    conn = sqlite3.connect('cashflow.db')
    cur = conn.cursor()
    cur.execute('INSERT INTO loan_payments (date, amount, type) VALUES (?, ?, "wire")', (date, amount))
    conn.commit()
    conn.close()
    
    return {"status": "updated"}

@app.post("/webhook")
async def handle_webhook(payload: Dict[str, Any]):
    """Handle incoming webhook events for various payment types."""
    event_type = payload.get("type")
    
    if not event_type:
        raise HTTPException(status_code=400, detail="Missing 'type' in payload")
    
    # Handle incoming payouts
    if event_type == "incoming_stripe_payout":
        category = "Cash In – Stripe"
    elif event_type == "incoming_wire":
        category = "Cash In – Wire"
    # Handle outgoing payments
    elif event_type == "outgoing_payment":
        category = get_category_for_recipient(payload.get("to", ""))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported event type: {event_type}")
    
    # Create cost record
    cost_record = {
        "name": payload.get("description", "Webhook Event"),
        "amount": abs(float(payload.get("amount", 0))),  # Ensure positive amount
        "currency": payload.get("currency", "USD"),
        "category": category,
        "cost_date": parse_date(payload.get("date")),
        "description": payload.get("description", ""),
        "is_recurring": False
    }
    
    # Insert into database
    conn = sqlite3.connect('cashflow.db')
    cur = conn.cursor()
    
    try:
        # Create costs table if it doesn't exist
        cur.execute('''
            CREATE TABLE IF NOT EXISTS costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                amount REAL NOT NULL,
                currency TEXT NOT NULL,
                category TEXT NOT NULL,
                cost_date TEXT NOT NULL,
                description TEXT,
                is_recurring INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Insert the new cost record
        cur.execute('''
            INSERT INTO costs 
            (name, amount, currency, category, cost_date, description, is_recurring)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            cost_record["name"],
            cost_record["amount"],
            cost_record["currency"],
            cost_record["category"],
            cost_record["cost_date"],
            cost_record["description"],
            1 if cost_record["is_recurring"] else 0
        ))
        
        conn.commit()
        return {"status": "success", "message": "Cost record created successfully"}
        
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")
    finally:
        conn.close()

# Legacy endpoint for backward compatibility
@app.post("/backoffice_wire")
async def handle_wire(data: dict):
    """Legacy endpoint for backoffice wire transfers."""
    # Convert to new webhook format
    webhook_data = {
        "type": "incoming_wire",
        "amount": data.get('amount', 0),
        "date": data.get('date', ''),
        "description": "Backoffice wire transfer"
    }
    return await handle_webhook(webhook_data)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
