# src/memotic/app.py
"""
Minimal FastAPI demo.

Run with uvicorn:
    uvicorn memotic.app:app --reload
"""

from __future__ import annotations

import logging
import json
from typing import Any, Dict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from webhooky.bus import EventBus

from .base import MemoWebhookEvent  # ensure package imports resolve
from .handlers.base import *

# from .cli import *
import memotic.cli

logger = logging.getLogger(__name__)

app = FastAPI(title="memotic demo")
bus = EventBus(timeout_seconds=30.0, fallback_to_generic=False)
# Register your MemoWebhookEvent subclasses (import side-effect from .handlers)


# print(f"\n\nRegistering handlers for MemoWebhookEvent subclasses:")
# print(f"    Bus: {bus}")
# print(f"        Class name: {bus.__class__.__name__}")
# print(f"        Class type: {type(bus)}")
# for attr in dir(bus):
#    if not attr.startswith("_"):
#        print(f"            Attribute: {attr} = {getattr(bus, attr)}")
# print(f"\n\n")
for cls in MemoWebhookEvent.__subclasses__():
    bus.register(cls)


def print_result(result):
    formatted_result = json.dumps(result.model_dump(mode="json"), indent=4)
    print(f"\n\n{'=' * 40} \nResult: {result.raw_data['memo']['content']}")
    # print(f"Processed webhook: \n{result}\n")
    print(f"Summary:\n")
    print(
        json.dumps(
            {
                "status": "processed",
                "success": result.success,
                "matches": result.matched_patterns,
                "triggered": result.triggered_methods,
                "errors": result.errors,
            },
            indent=4,
        )
    )
    print("=" * 40)
    print("\n\n")


@app.on_event("startup")
async def _startup():
    # Register all known subclasses
    for cls in MemoWebhookEvent.__subclasses__():
        bus.register(cls)
    # Sanity log
    names = [c.__name__ for c in MemoWebhookEvent.__subclasses__()]
    print("[memotic] Registered handlers:", names)


@app.post("/webhooks/webhook")
async def memos_webhook(request: Request):
    raw_data: Dict[str, Any] = await request.json()
    headers: Dict[str, Any] = dict(request.headers)
    source_info = {
        "client_ip": getattr(request.client, "host", None),
        "user_agent": headers.get("user-agent"),
        "method": request.method,
        "url": str(request.url),
    }
    result = await bus.process_webhook(raw_data, headers, source_info)
    logger.info(f"Processed webhook: {result}")
    # print(f"Processed webhook: {result}")
    # print_result(result)
    return JSONResponse(
        content={
            "status": "processed",
            "success": result.success,
            "matches": result.matched_patterns,
            "triggered": result.triggered_methods,
            "errors": result.errors,
        }
    )
