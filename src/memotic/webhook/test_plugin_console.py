#!/usr/bin/env python3
"""
Smoke test that your memos plugin prints to the same Rich console used by the
webhooky Typer CLI.

What it does:
1) Imports your plugin module.
2) Replaces the plugin's console with a Rich Console that writes to a buffer.
3) Registers any @webhook_handler-decorated functions onto a fresh EventBus.
4) Dispatches a sample Memos payload.
5) Prints the captured console output and a short result summary.

Adjust MODULE if your plugin module path is different.
"""

from __future__ import annotations

import asyncio
import importlib
import inspect
import io
from typing import Any, Callable

from rich.console import Console

# --- CONFIG: set this to your plugin module path -----------------------------
MODULE = "memotic.webhook.plugin"  # e.g. "memotic.plugin" if that's your package
# -----------------------------------------------------------------------------


def _register_decorated_handlers(bus, plugin_mod) -> None:
    """
    Mimic what the plugin manager would do:
    - If a function has _webhook_pattern: bus.on_pattern(pattern)(fn)
    - If a function has _webhook_activity: bus.on_activity(activity)(fn)
    """
    for name, obj in inspect.getmembers(plugin_mod, inspect.isfunction):
        pattern = getattr(obj, "_webhook_pattern", None)
        activity = getattr(obj, "_webhook_activity", None)

        if pattern is not None:
            bus.on_pattern(pattern)(obj)
        elif activity is not None:
            bus.on_activity(activity)(obj)


async def main() -> None:
    # Import webhooky bits
    from webhooky.bus import EventBus

    # 1) Import your plugin module
    try:
        plugin_mod = importlib.import_module(MODULE)
    except Exception as e:
        print(f"Failed to import plugin module '{MODULE}': {e}")
        return

    # 2) Replace the plugin's console with a buffer-backed Rich console
    buf = io.StringIO()
    cap_console = Console(file=buf, force_terminal=False)
    test_console = Console()
    # - If your plugin follows the earlier pattern with `_cprint` and `_console`,
    #   swap `_console` here so handler prints get captured:
    if hasattr(plugin_mod, "_console"):
        setattr(plugin_mod, "_console", cap_console)

    # - ALSO replace the CLI’s console so any code reading from webhooky.cli.console
    #   writes to our buffer too:
    try:
        import webhooky.cli as cli

        cli.console = cap_console  # type: ignore[attr-defined]
    except Exception:
        pass

    # 3) Fresh bus + register all decorated handlers from the plugin
    bus = EventBus()
    _register_decorated_handlers(bus, plugin_mod)

    # 4) Dispatch a sample memos payload
    SAMPLE = {
        "url": "https://smee.io/DKPU4BqERCd0s4Y1",
        "activityType": "memos.memo.created",
        "creator": "users/1",
        "memo": {
            "name": "memos/dtyUZZ2fU3sgGMbYfX8z5f",
            "state": 1,
            "creator": "users/1",
            "create_time": {"seconds": 1756674863},
            "update_time": {"seconds": 1756674863},
            "display_time": {"seconds": 1756674863},
            "content": "test",
            "nodes": [
                {
                    "type": 2,
                    "Node": {"ParagraphNode": {"children": [{"type": 51, "Node": {"TextNode": {"content": "test"}}}]}},
                }
            ],
            "visibility": 1,
            "property": {},
            "snippet": "test\n",
        },
    }

    result = await bus.dispatch_raw(SAMPLE, headers={"Content-Type": "application/json"})

    # 5) Show the captured output and a summary
    print("=== Captured plugin console output ===")
    print(buf.getvalue().rstrip() or "<no output>")
    print("=== Result ===")
    print(f"success={result.success} matched={result.matched_patterns} errors={result.errors}")
    test_console.print(f"[bold]Done.[/bold]")


if __name__ == "__main__":
    asyncio.run(main())
