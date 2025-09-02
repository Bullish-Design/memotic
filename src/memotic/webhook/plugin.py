"""
webhooky-memos plugin: exposes Memos events and (optional) default handlers.
Once installed, WebHooky will discover this via the 'webhooky.plugins' entry-point.
"""

# plugin.py
from __future__ import annotations

import logging
from typing import Any

# --- Use the same Rich console the CLI uses (fallback to a plain Console) ----
try:
    from webhooky.cli import console as _console  # Typer/Rich console

    _tty = True
except Exception:  # tests / non-CLI environments
    from rich.console import Console

    _console = Console()
    _tty = False

# De-dupe banner if imported twice
if not globals().get("_MEMOS_PLUGIN_BANNER", False):
    try:
        _console.print(f"Using webhooky.cli console for plugin output (TTY={_tty})")
    except Exception:
        pass
    globals()["_MEMOS_PLUGIN_BANNER"] = True

logger = logging.getLogger(__name__)


def _cprint(*args: Any, **kwargs: Any) -> None:
    try:
        _console.print(*args, **kwargs)
    except Exception:
        logger.info(" ".join(map(str, args)))


# --- Import your events so subclasses auto-register in the registry ----------
from .events import (
    MemosEvent,
    MemosMemoCreated,
    MemosMemoUpdated,
    MemosMemoDeleted,
)


# --- Optional: registry summary, version-safe (never raises on import) -------
def _registry_summary() -> None:
    try:
        from webhooky.registry import event_registry  # << ensure we import it

        try:
            # Newer builds may expose a structured info object
            info = event_registry.get_registry_info()  # type: ignore[attr-defined]
            names = sorted(c.__name__ for c in info.registered_classes)
        except Exception:
            # Older builds: fall back to internal dict
            classes = getattr(event_registry, "_event_classes", {})  # type: ignore[attr-defined]
            names = sorted(classes.keys()) if isinstance(classes, dict) else []
        _cprint(f"[dim]memos plugin ready; registry classes: {', '.join(names) or '—'}[/dim]")
    except Exception as e:
        logger.debug("memos plugin registry inspection skipped: %s", e)


_registry_summary()  # safe to call at import; fully guarded

# --- Handlers ----------------------------------------------------------------
from webhooky.plugins import webhook_handler


@webhook_handler(MemosMemoCreated)  # class-based pattern
def handle_memo_created(event: MemosMemoCreated):
    memo = event.payload.memo
    _console.print(f"[bold green][MEMOS][/bold green] created: {memo.name} → {memo.content!r}")


@webhook_handler(MemosMemoUpdated)
def handle_memo_updated(event: MemosMemoUpdated):
    _console.print(f"[yellow][MEMOS][/yellow] updated: {event.payload.memo.name}")


@webhook_handler(MemosMemoDeleted)
def handle_memo_deleted(event: MemosMemoDeleted):
    _console.print(f"[red][MEMOS][/red] deleted: {event.payload.memo.name}")


# Optional: activity-based (fires even if only Generic matches IF activity is extracted)
@webhook_handler(activity="memos.memo.created")
def on_created_activity(event: MemosEvent):
    _console.print("[dim]activity handler → memos.memo.created[/dim]")
