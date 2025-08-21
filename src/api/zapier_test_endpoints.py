from fastapi import APIRouter
from src.api.webhook_handler import handle_webhook_event

router = APIRouter()

@router.post("/zapier/test/stripe_payout")
def test_stripe_payout():
    payload = {
        "type": "incoming_stripe_payout",
        "date": "2025-08-19",
        "amount": 18500.75,
        "currency": "USD",
        "description": "Stripe payout batch #107381"
    }
    
    # Call the actual webhook handler
    return handle_webhook_event(payload)

@router.post("/zapier/test/incoming_wire")
def test_incoming_wire():
    payload = {
        "type": "incoming_wire",
        "date": "2025-08-19",
        "amount": 25000.00,
        "currency": "USD",
        "description": "Wire from Guest (Invoice #7851)"
    }
    
    # Call the actual webhook handler
    return handle_webhook_event(payload)

@router.post("/zapier/test/outgoing_ocbc")
def test_outgoing_ocbc():
    payload = {
        "type": "outgoing_payment",
        "date": "2025-08-19",
        "amount": 9500,
        "currency": "USD",
        "to": "Google Ads",
        "description": "Monthly Google Ads payment"
    }
    
    # Call the actual webhook handler
    return handle_webhook_event(payload)
