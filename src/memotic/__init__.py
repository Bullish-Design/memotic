# src/memotic/__init__.py
from __future__ import annotations

from .base import MemoWebhookEvent
from .config import MemoticConfig, get_config, set_config, reset_config
from .container_manager import (
    ContainerManager,
    ContainerStatus,
    get_container_manager,
    set_container_manager,
    reset_container_manager,
)
from .dependencies import check_solitary, check_rich, require_solitary, get_console

__all__ = [
    # Core event handling
    "MemoWebhookEvent",
    # Configuration management
    "MemoticConfig",
    "get_config",
    "set_config",
    "reset_config",
    # Container management
    "ContainerManager",
    "ContainerStatus",
    "get_container_manager",
    "set_container_manager",
    "reset_container_manager",
    # Dependency management
    "check_solitary",
    "check_rich",
    "require_solitary",
    "get_console",
]

__version__ = "0.6.1"

