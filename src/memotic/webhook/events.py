from __future__ import annotations
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, ConfigDict
from webhooky.events import WebhookEventBase, on_activity

# --- console hook reused by plugin.py ----------------------------------------
try:
    # import the console helper you defined in plugin.py
    from .plugin import _cprint  # type: ignore
except Exception:
    from rich.console import Console

    _cprint = Console().print

try:
    from webhooky.cli import console as _console  # Typer/Rich console

    _tty = True
except Exception:  # tests / non-CLI environments
    from rich.console import Console

    _console = Console()
    _tty = False

# ---- Payloads ---------------------------------------------------------------


class Timestamp(BaseModel):
    seconds: int
    model_config = ConfigDict(extra="ignore")


class Memo(BaseModel):
    name: str
    state: int
    creator: str
    content: Optional[str] = None
    snippet: Optional[str] = None
    create_time: Timestamp | Dict[str, Any] | None = None
    update_time: Timestamp | Dict[str, Any] | None = None
    display_time: Timestamp | Dict[str, Any] | None = None
    nodes: List[Any] = []
    visibility: Optional[int] = None
    property: Dict[str, Any] = {}
    model_config = ConfigDict(extra="allow")


class MemosPayload(BaseModel):
    url: Optional[str] = None
    activityType: str
    creator: str
    memo: Memo
    model_config = ConfigDict(extra="allow")


# ---- Events -----------------------------------------------------------------


class MemosEvent(WebhookEventBase[MemosPayload]):
    """Base for all memos.* events; normalizes activity field."""

    @classmethod
    def _transform_raw_data(cls, raw: Dict[str, Any]) -> Dict[str, Any]:
        # normalize camelCase for core lookups while keeping original payload intact
        if raw and "activityType" in raw and "activity_type" not in raw:
            raw = dict(raw)
            raw["activity_type"] = raw["activityType"]
        return raw or {}

    def get_activity(self) -> Optional[str]:
        # make activity extraction unambiguous for trigger routing
        try:
            return self.payload.activityType  # camelCase from upstream
        except Exception:
            pd = self.payload.model_dump() if hasattr(self.payload, "model_dump") else {}
            return pd.get("activity_type")

    @classmethod
    def matches(cls, raw: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
        return isinstance(raw.get("activityType"), str) and raw["activityType"].startswith("memos.")

    # ---- Class-method triggers that WILL run during process_triggers() ----

    @on_activity("memos.memo.created")
    async def _on_created(self) -> None:
        m = self.payload.memo
        _console.print(f"[bold green][MEMOS][/bold green] created: {m.name} → {m.content!r}")

    @on_activity("memos.memo.updated")
    async def _on_updated(self) -> None:
        _console.print(f"[yellow][MEMOS][/yellow] updated: {self.payload.memo.name}")

    @on_activity("memos.memo.deleted")
    async def _on_deleted(self) -> None:
        _console.print(f"[red][MEMOS][/red] deleted: {self.payload.memo.name}")


class MemosMemoCreated(MemosEvent):
    @classmethod
    def matches(cls, raw: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
        return raw.get("activityType") == "memos.memo.created"


class MemosMemoUpdated(MemosEvent):
    @classmethod
    def matches(cls, raw: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
        return raw.get("activityType") == "memos.memo.updated"


class MemosMemoDeleted(MemosEvent):
    @classmethod
    def matches(cls, raw: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
        return raw.get("activityType") == "memos.memo.deleted"
