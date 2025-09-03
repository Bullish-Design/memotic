# src/memotic/dependencies.py
from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Track availability of optional dependencies
_solitary_available: Optional[bool] = None
_rich_available: Optional[bool] = None


def check_solitary() -> bool:
    """Check if solitary is available for container execution."""
    global _solitary_available
    if _solitary_available is None:
        try:
            import solitary
            _solitary_available = True
        except ImportError:
            _solitary_available = False
            logger.warning("solitary not available - CLI execution will fail")
    return _solitary_available


def check_rich() -> bool:
    """Check if rich is available for CLI formatting."""
    global _rich_available
    if _rich_available is None:
        try:
            import rich
            _rich_available = True
        except ImportError:
            _rich_available = False
            logger.debug("rich not available - basic formatting will be used")
    return _rich_available


def require_solitary():
    """Raise error if solitary is not available."""
    if not check_solitary():
        raise RuntimeError(
            "solitary is required for CLI execution. Install with: "
            "pip install solitary"
        )


def get_console():
    """Get rich console or fallback to basic print."""
    if check_rich():
        from rich.console import Console
        return Console()
    else:
        # Fallback console-like object
        class BasicConsole:
            def print(self, *args, **kwargs):
                print(*args)
        return BasicConsole()