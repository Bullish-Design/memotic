#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "webhooky @ git+https://github.com/Bullish-Design/webhooky.git",
#   "memotic @ git+https://github.com/Bullish-Design/memotic.git",
#   "fastapi>=0.111",
#   "uvicorn>=0.30",
# ]
# ///

"""Live webhook server example for Memos webhook processing."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)8s] %(name)s: %(message)s", datefmt="%H:%M:%S")

logger = logging.getLogger(__name__)

logger.info("📝 Memos Webhook Server Example")


from webhooky import EventBus, create_dev_config
from webhooky.fastapi import create_app, attach_to_app
from memotic import (
    ResearchMemoEvent,
    ProjectMemoEvent,
    UrgentMemoEvent,
    TaggedMemoEvent,
    create_research_handler,
    create_project_handler,
    MemoNotificationHandler,
    init_plugin,
)


async def setup_memos_processing():
    """Setup memos event processing with handlers."""

    # Initialize plugin
    plugin_config = {
        "enable_file_saving": True,
        "enable_notifications": True,
        "enable_search_indexing": True,
        "base_save_path": "./webhook_memos",
        "research_save_path": "./webhook_memos/research",
        "project_save_path": "./webhook_memos/projects",
        "idea_save_path": "./webhook_memos/ideas",
    }
    init_plugin(plugin_config)

    # Setup WebHooky
    config = create_dev_config(enable_plugins=False)  # Manual registration
    bus = EventBus(
        timeout_seconds=config.timeout_seconds,
        max_concurrent_handlers=config.max_concurrent_handlers,
        swallow_exceptions=True,  # Don't crash on handler errors
        enable_metrics=True,
        activity_groups={k: set(v) for k, v in config.activity_groups.items()},
    )

    # Create handlers
    research_handler = create_research_handler("./webhook_memos/research")
    project_handler = create_project_handler("./webhook_memos/projects")
    notification_handler = MemoNotificationHandler(["console"])

    # Ensure directories exist
    Path("./webhook_memos").mkdir(exist_ok=True)
    Path("./webhook_memos/research").mkdir(parents=True, exist_ok=True)
    Path("./webhook_memos/projects").mkdir(parents=True, exist_ok=True)

    logger.info("📚 Setting up Research memo handler...")

    @bus.on_pattern(ResearchMemoEvent)
    async def handle_research_memo(event: ResearchMemoEvent):
        logger.info(f"📚 Research memo detected: {event.payload.memo.name}")

        try:
            path = await research_handler.save_memo(event.payload)
            logger.info(f"   💾 Saved to: {path}")

            await notification_handler.notify(
                "Research Memo", f"Saved research memo: {event.payload.memo.name or 'Untitled'}", event.payload
            )
        except Exception as e:
            logger.error(f"   ❌ Failed to save research memo: {e}")

    logger.info("📋 Setting up Project memo handler...")

    @bus.on_pattern(ProjectMemoEvent)
    async def handle_project_memo(event: ProjectMemoEvent):
        logger.info(f"📋 Project memo detected: {event.payload.memo.name}")

        try:
            path = await project_handler.save_memo(event.payload)
            tags = ", ".join(event.payload.memo.tags or [])
            logger.info(f"   🏷️  Tags: {tags}")
            logger.info(f"   💾 Saved to: {path}")
        except Exception as e:
            logger.error(f"   ❌ Failed to save project memo: {e}")

    logger.info("🚨 Setting up Urgent memo handler...")

    @bus.on_pattern(UrgentMemoEvent)
    async def handle_urgent_memo(event: UrgentMemoEvent):
        logger.warning(f"🚨 URGENT memo detected: {event.payload.memo.name}")

        content_preview = (event.payload.memo.content or "")[:100]
        logger.warning(f"   📄 Preview: {content_preview}...")

        await notification_handler.notify(
            "🚨 URGENT MEMO", f"Urgent attention required: {event.payload.memo.name or 'Untitled'}", event.payload
        )

    logger.info("🏷️  Setting up Tagged memo handler...")

    @bus.on_pattern(TaggedMemoEvent)
    async def handle_tagged_memo(event: TaggedMemoEvent):
        tags = ", ".join(event.payload.memo.tags or [])
        logger.info(f"🏷️  Tagged memo: {tags}")

    # Catch-all handler for debugging
    @bus.on_any()
    async def debug_handler(event):
        logger.debug(f"🔍 Debug - Processed event: {event.__class__.__name__}")

        # Handle structured memo events
        if hasattr(event, "payload") and hasattr(event.payload, "memo"):
            memo = event.payload.memo
            if hasattr(memo, "name"):  # Structured Memo object
                logger.debug(f"    Memo: {memo.name}")
                logger.debug(f"    Tags: {getattr(memo, 'tags', None)}")
                logger.debug(f"    Content preview: {(memo.content or '')[:50]}...")
            elif isinstance(memo, dict):  # Dict payload
                logger.debug(f"    Memo (dict): {memo.get('name', 'untitled')}")
                logger.debug(f"    Tags (dict): {memo.get('tags', [])}")
                logger.debug(f"    Content preview (dict): {(memo.get('content', '') or '')[:50]}...")

        # Handle generic webhook events with raw data
        elif hasattr(event, "payload"):
            payload_dict = getattr(event.payload, "__dict__", {})
            logger.debug(f"    Generic payload keys: {list(payload_dict.keys())}")
            if "memo" in payload_dict:
                memo = payload_dict["memo"]
                logger.debug(f"    Contains memo: {type(memo)}")
        else:
            logger.debug(f"    No structured payload found")

    return bus, config


async def main():
    """Run live webhook server."""
    logger.info("🚀 Starting Memos Webhook Server")

    # Setup processing
    bus, config = await setup_memos_processing()

    # Create FastAPI app
    app = create_app(bus, config)

    # Add custom status endpoint
    @app.get("/")
    async def root():
        metrics = bus.get_metrics()
        return {
            "service": "Memos Webhook Processor",
            "status": "running",
            "total_events": metrics.total_events,
            "success_rate": f"{metrics.success_rate:.1%}",
            "webhook_url": "/webhooks/webhook",
        }

    # Custom webhook processor with debug logging
    @app.post("/webhook")
    async def process_memos_webhook(payload: dict):
        logger.info(
            f"📡 Received webhook: {payload.get('action', 'unknown')} - {payload.get('memo', {}).get('name', 'untitled')}"
        )

        result = await bus.dispatch_raw(payload)

        logger.info(f"   ✅ Processed: {result.success}")
        logger.info(f"   🎯 Patterns: {result.matched_patterns}")
        logger.info(f"   ⚡ Handlers: {result.handler_count}")
        logger.info(f"   ⏱️  Time: {result.processing_time:.3f}s")

        if result.errors:
            logger.error(f"   ❌ Errors: {result.errors}")

        return {
            "status": "processed",
            "success": result.success,
            "matched_patterns": result.matched_patterns,
            "handler_count": result.handler_count,
            "processing_time": result.processing_time,
            "errors": result.errors if not result.success else None,
        }

    logger.info("🌐 Server configuration:")
    logger.info("   - Webhook endpoint: http://localhost:8000/webhook")
    logger.info("   - WebHooky endpoint: http://localhost:8000/webhooks/webhook")
    logger.info("   - Status: http://localhost:8000/")
    logger.info("   - Health: http://localhost:8000/health")
    logger.info("   - Metrics: http://localhost:8000/webhooks/status")

    logger.info("📝 Configure your Memos webhook URL to: http://localhost:8000/webhook")
    logger.info("🔄 Server ready for webhook events...")

    # Test with sample payload on startup
    logger.info("🧪 Testing with sample payload...")

    test_payload = {
        "url": "https://smee.io/DKPU4BqERCd0s4Y1",
        "activityType": "memos.memo.created",
        "creator": "users/1",
        "memo": {
            "name": "memos/kFbfxfPLA2Buii7iQwH4CU",
            "state": 1,
            "creator": "users/1",
            "create_time": {"seconds": 1756836672},
            "update_time": {"seconds": 1756836672},
            "display_time": {"seconds": 1756836672},
            "content": "#test memo",
            "nodes": [
                {
                    "type": 2,
                    "Node": {
                        "ParagraphNode": {
                            "children": [
                                {"type": 59, "Node": {"TagNode": {"content": "test"}}},
                                {"type": 51, "Node": {"TextNode": {"content": " memo"}}},
                            ]
                        }
                    },
                }
            ],
            "visibility": 1,
            "tags": ["test"],
            "property": {},
            "snippet": "#test memo\n",
        },
    }

    result = await bus.dispatch_raw(test_payload)
    logger.info(f"🧪 Test result: {result.success}, patterns: {result.matched_patterns}")

    # Run server
    import uvicorn

    config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
