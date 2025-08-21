from fastapi import HTTPException
from typing import Dict, Any
import logging
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

def handle_webhook_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process incoming webhook events and route them to appropriate handlers.
    
    Args:
        payload: The webhook payload
        
    Returns:
        Dict containing status and processing results
    """
    try:
        event_type = payload.get("type")
        
        # Log the incoming webhook
        logger.info(f"Processing webhook event: {event_type}")
        logger.debug(f"Webhook payload: {payload}")
        
        # Route to appropriate handler based on event type
        if event_type == "incoming_stripe_payout":
            return _handle_stripe_payout(payload)
        elif event_type == "incoming_wire":
            return _handle_incoming_wire(payload)
        elif event_type == "outgoing_payment":
            return _handle_outgoing_payment(payload)
        else:
            error_msg = f"Unsupported event type: {event_type}"
            logger.warning(error_msg)
            raise HTTPException(status_code=400, detail=error_msg)
            
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing webhook: {str(e)}")

def _handle_stripe_payout(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle Stripe payout webhook events."""
    return {
        "status": "success",
        "event_type": "stripe_payout",
        "processed_at": datetime.utcnow().isoformat(),
        "data": payload
    }

def _handle_incoming_wire(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle incoming wire transfer webhook events."""
    return {
        "status": "success",
        "event_type": "incoming_wire",
        "processed_at": datetime.utcnow().isoformat(),
        "data": payload
    }

def _handle_outgoing_payment(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Handle outgoing payment webhook events."""
    return {
        "status": "success",
        "event_type": "outgoing_payment",
        "processed_at": datetime.utcnow().isoformat(),
        "data": payload
    }
