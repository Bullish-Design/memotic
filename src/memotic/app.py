from __future__ import annotations

import pathlib
from typing import Dict, Any

from fastapi import FastAPI, Request, BackgroundTasks

# Import webhooky + our adapter
# If installed normally, this works:
from .base import EventBus, MemoWebhookyBase, on_create, on_edit, on_any

## In local dev, ensure package root is importable (optional fallback):
# try:
#    from memotic import
# except Exception:
#    import sys
#
#    sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))
#    from memotic import MemoWebhookyBase, on_create, on_edit, on_any

from .handlers import TaggedMemo, SaysHiMemo

app = FastAPI(title="Memos Webhooky Example")
bus = EventBus()


# Register your matching classes at startup
@app.on_event("startup")
async def _startup():
    bus.register(TaggedMemo)
    bus.register(SaysHiMemo)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/webhooks/memos")
async def memos_webhook(request: Request, background: BackgroundTasks):
    payload: Dict[str, Any] = await request.json()
    headers = dict(request.headers)

    # Process in the background to respond quickly
    background.add_task(bus.process, raw_data=payload, headers=headers)
    return {"status": "accepted"}
