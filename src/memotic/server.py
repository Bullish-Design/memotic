from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Dict, Any, Optional, Callable
import logging
import os

logger = logging.getLogger(__name__)

app = FastAPI(title="Memos Webhook Server", version="1.0.0")
security = HTTPBearer(auto_error=False)

# Webhook handlers storage
webhook_handlers: Dict[str, Callable] = {}


class WebhookPayload(BaseModel):
    event: str
    data: Dict[str, Any]
    timestamp: str


def register_webhook_handler(event: str):
    """Decorator to register webhook handlers for specific events"""
    def decorator(func: Callable):
        webhook_handlers[event] = func
        return func
    return decorator


async def verify_webhook(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Optional webhook verification - implement your own logic"""
    # You can implement signature verification here
    return True


@app.post("/webhook")
async def handle_webhook(payload: WebhookPayload, request: Request, verified: bool = Depends(verify_webhook)):
    """Main webhook endpoint"""
    logger.info(f"Received webhook: {payload.event}")
    
    if payload.event in webhook_handlers:
        try:
            await webhook_handlers[payload.event](payload.data)
            return {"status": "processed"}
        except Exception as e:
            logger.error(f"Error processing webhook {payload.event}: {e}")
            raise HTTPException(status_code=500, detail="Webhook processing failed")
    else:
        logger.warning(f"No handler for webhook event: {payload.event}")
        return {"status": "no_handler"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


# Example webhook handlers
@register_webhook_handler("memo.created")
async def handle_memo_created(data: Dict[str, Any]):
    """Handle memo creation webhook"""
    logger.info(f"New memo created: {data.get('id')}")
    # Add your custom logic here


@register_webhook_handler("memo.updated")
async def handle_memo_updated(data: Dict[str, Any]):
    """Handle memo update webhook"""
    logger.info(f"Memo updated: {data.get('id')}")
    # Add your custom logic here


@register_webhook_handler("memo.deleted")
async def handle_memo_deleted(data: Dict[str, Any]):
    """Handle memo deletion webhook"""
    logger.info(f"Memo deleted: {data.get('id')}")
    # Add your custom logic here


def main():
    """Main entry point for the webhook server"""
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))
    log_level = os.getenv("LOG_LEVEL", "info")
    
    logging.basicConfig(level=log_level.upper())
    
    uvicorn.run(app, host=host, port=port, log_level=log_level)


if __name__ == "__main__":
    main()