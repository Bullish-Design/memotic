# src/memotic/app.py
from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from webhooky.bus import EventBus

from .base import MemoWebhookEvent
from .config import get_config, set_config, MemoticConfig
from .container_manager import get_container_manager

logger = logging.getLogger(__name__)


def create_app(config: MemoticConfig | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    if config:
        set_config(config)
    
    app_config = get_config()
    
    app = FastAPI(
        title="Memotic - Memos Webhook Processor",
        description="Process Memos webhooks and execute CLI commands in containers",
        version="0.5.1"
    )

    # Initialize event bus
    bus = EventBus(timeout_seconds=30.0, fallback_to_generic=False)
    
    # Store bus in app state
    app.state.bus = bus
    app.state.config = app_config

    @app.on_event("startup")
    async def startup_event():
        """Initialize application on startup."""
        # Import CLI handlers to ensure they're registered
        try:
            from . import cli
            logger.debug("CLI handlers imported")
        except ImportError as e:
            logger.warning(f"Failed to import CLI handlers: {e}")
        
        # Register all MemoWebhookEvent subclasses
        registered_count = 0
        for cls in MemoWebhookEvent.__subclasses__():
            bus.register(cls)
            logger.info(f"Registered handler: {cls.__name__}")
            registered_count += 1
        
        if registered_count == 0:
            logger.warning("No webhook handlers registered!")
        else:
            logger.info(f"Registered {registered_count} webhook handlers")
        
        # Prepare container if we have CLI handlers
        cli_handlers = [
            cls for cls in MemoWebhookEvent.__subclasses__ 
            if hasattr(cls, 'any_tags') and getattr(cls, 'any_tags', set()) & {'cli'}
        ]
        
        if cli_handlers:
            logger.info(f"Found {len(cli_handlers)} CLI handlers, preparing container...")
            try:
                container_manager = get_container_manager()
                container_name = container_manager.ensure_container()
                logger.info(f"Container ready for CLI execution: {container_name}")
            except Exception as e:
                logger.error(f"Failed to prepare container: {e}")
                logger.warning("CLI commands may fail without a ready container")

    @app.post("/webhooks/webhook")
    async def process_webhook(request: Request):
        """Process incoming Memos webhook."""
        try:
            raw_data: Dict[str, Any] = await request.json()
            headers: Dict[str, Any] = dict(request.headers)
            
            logger.debug(f"Received webhook from {getattr(request.client, 'host', 'unknown')}")
            
            source_info = {
                "client_ip": getattr(request.client, "host", None),
                "user_agent": headers.get("user-agent"),
                "method": request.method,
                "url": str(request.url),
            }
            
            result = await bus.process_webhook(raw_data, headers, source_info)
            
            logger.info(
                f"Processed webhook: {len(result.matched_patterns)} matches, "
                f"{len(result.triggered_methods)} triggers, success={result.success}"
            )
            
            response_data = {
                "status": "processed",
                "success": result.success,
                "matches": result.matched_patterns,
                "triggered": result.triggered_methods,
                "processing_time": result.processing_time,
            }
            
            if result.errors:
                response_data["errors"] = result.errors
                logger.warning(f"Processing errors: {result.errors}")
            
            return JSONResponse(
                content=response_data,
                status_code=200 if result.success else 422
            )
            
        except Exception as e:
            logger.exception(f"Webhook processing failed: {e}")
            return JSONResponse(
                content={"status": "error", "message": str(e)},
                status_code=500
            )

    @app.get("/health")
    async def health_check():
        """Health check endpoint."""
        container_status = None
        container_error = None
        
        try:
            container_manager = get_container_manager()
            status = container_manager.get_container_status()
            container_status = {
                "name": status.name,
                "exists": status.exists,
                "running": status.running,
                "healthy": status.healthy
            }
            if status.error:
                container_error = status.error
                
        except Exception as e:
            logger.warning(f"Could not check container status: {e}")
            container_error = str(e)
        
        response = {
            "status": "healthy",
            "service": "memotic",
            "version": "0.5.1",
            "registered_handlers": len(MemoWebhookEvent.__subclasses__()),
            "container": container_status
        }
        
        if container_error:
            response["container_error"] = container_error
        
        return response

    @app.get("/status")
    async def get_status():
        """Get detailed application status."""
        handlers = []
        for cls in MemoWebhookEvent.__subclasses__():
            handler_info = {"name": cls.__name__}
            if hasattr(cls, 'any_tags'):
                handler_info["any_tags"] = list(getattr(cls, 'any_tags', set()))
            if hasattr(cls, 'all_tags'):
                handler_info["all_tags"] = list(getattr(cls, 'all_tags', set()))
            if hasattr(cls, 'content_contains'):
                handler_info["content_contains"] = getattr(cls, 'content_contains')
            handlers.append(handler_info)
        
        container_status = {}
        try:
            container_manager = get_container_manager()
            status = container_manager.get_container_status()
            container_status = {
                "name": status.name,
                "exists": status.exists,
                "running": status.running,
                "healthy": status.healthy,
                "error": status.error
            }
        except Exception as e:
            container_status = {"error": str(e)}
        
        config_issues = app_config.validate_setup()
        
        return {
            "handlers": handlers,
            "container": container_status,
            "config": {
                "api_configured": app_config.has_api_config(),
                "container_name": app_config.default_container_name,
                "project_root": str(app_config.project_root),
                "issues": config_issues
            },
            "bus_stats": bus.get_stats() if hasattr(bus, 'get_stats') else {}
        }

    @app.post("/test/webhook")
    async def test_webhook(payload: Dict[str, Any]):
        """Test webhook processing with custom payload."""
        try:
            result = await bus.process_webhook(payload)
            return {
                "test_result": "success" if result.success else "failed",
                "matches": result.matched_patterns,
                "triggered": result.triggered_methods,
                "errors": result.errors if result.errors else None,
                "processing_time": result.processing_time
            }
        except Exception as e:
            logger.exception(f"Test webhook failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled exception in {request.method} {request.url}: {exc}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal server error"}
        )

    return app


# Create default app instance
app = create_app()