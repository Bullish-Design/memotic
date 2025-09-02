# sse_runner.py
from __future__ import annotations
import os, json, asyncio
from typing import Optional, List
import httpx
from pydantic import BaseModel, Field
from sqlmodel import SQLModel, Field as SQLField, create_engine, Session
from dotenv import load_dotenv

load_dotenv()


# ---- Config / models ----
class Settings(BaseModel):
    base_url: str = Field(default_factory=lambda: os.getenv("MEMOS_URL", "http://localhost:5232"))
    token: Optional[str] = Field(default_factory=lambda: os.getenv("MEMOS_TOKEN"))
    stream_path: str = "/events/memos"
    workflows_dir: str = "workflows"
    db_url: str = "sqlite:///trigger_state.db"


class RunLog(SQLModel, table=True):
    id: Optional[int] = SQLField(default=None, primary_key=True)
    event_id: int
    memo_id: int
    trigger: str
    status: str
    error: Optional[str] = None


# ---- Your existing plugin protocol ----
class BaseTrigger(BaseModel):
    name: str

    async def match(self, memo: dict) -> bool: ...
    async def run(self, memo: dict) -> None: ...


def load_triggers(dir_: str) -> list[BaseTrigger]:
    import importlib, pkgutil, pathlib, sys

    pkg = dir_.replace("/", ".")
    sys.path.append(str(pathlib.Path(".").resolve()))
    triggers: list[BaseTrigger] = []
    for m in pkgutil.iter_modules([dir_]):
        mod = importlib.import_module(f"{pkg}.{m.name}")
        if hasattr(mod, "get_triggers"):
            triggers += list(mod.get_triggers())
    return triggers


# ---- SSE parsing ----
def parse_sse_blocks(lines: List[str]):
    block = {"id": None, "event": None, "data": []}
    for line in lines:
        if not line:  # blank line -> dispatch
            if block["data"]:
                data = "\n".join(block["data"])
                yield block["id"], block["event"], data
            block = {"id": None, "event": None, "data": []}
            continue
        if line.startswith("id:"):
            block["id"] = int(line[3:].strip())
        elif line.startswith("event:"):
            block["event"] = line[6:].strip()
        elif line.startswith("data:"):
            block["data"].append(line[5:].strip())
        # ignore other fields/comments


async def main():
    s = Settings()
    print(f"Connecting to {s.base_url}{s.stream_path}...")
    engine = create_engine(s.db_url, echo=False)
    SQLModel.metadata.create_all(engine)
    triggers = load_triggers(s.workflows_dir)
    print(f"Loaded {len(triggers)} triggers.")
    headers = {"Accept": "text/event-stream"}
    if s.token:
        headers["Authorization"] = f"Bearer {s.token}"

    last_id: Optional[int] = None
    while True:
        try:
            async with httpx.AsyncClient(base_url=s.base_url, timeout=None) as client:
                req_headers = dict(headers)
                if last_id is not None:
                    req_headers["Last-Event-ID"] = str(last_id)
                async with client.stream("GET", s.stream_path, headers=req_headers) as r:
                    async for raw_line in r.aiter_lines():
                        if raw_line is None:
                            break
                        # Build blocks separated by blanks
                        # Accumulate and parse in small batches for simplicity
                        # (We use an internal buffer per connection)
                        # For brevity, parse line-by-line:
                        for evt in parse_sse_blocks([raw_line, ""] if raw_line == "" else [raw_line]):
                            ev_id, ev_type, data = evt
                            if ev_id is not None:
                                last_id = ev_id
                            payload = json.loads(data)
                            memo = payload.get("memo", {})
                            memo_id = (
                                int(str(memo.get("name", "")).split("/")[-1])
                                if memo.get("name")
                                else memo.get("id", -1)
                            )

                            # Dispatch to all matching triggers
                            for trig in triggers:
                                try:
                                    if await trig.match(memo):
                                        await trig.run(memo)
                                        with Session(engine) as db:
                                            db.add(
                                                RunLog(
                                                    event_id=last_id or -1,
                                                    memo_id=memo_id,
                                                    trigger=trig.name,
                                                    status="OK",
                                                )
                                            )
                                            db.commit()
                                except Exception as e:
                                    with Session(engine) as db:
                                        db.add(
                                            RunLog(
                                                event_id=last_id or -1,
                                                memo_id=memo_id,
                                                trigger=trig.name,
                                                status="ERR",
                                                error=f"{type(e).__name__}: {e}",
                                            )
                                        )
                                        db.commit()
        except Exception:
            # Backoff on disconnects; SSE clients should reconnect
            await asyncio.sleep(1.0)


if __name__ == "__main__":
    asyncio.run(main())
