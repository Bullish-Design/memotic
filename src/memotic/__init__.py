"""WebHooky Memos Plugin - Memos webhook event processing for WebHooky."""

from __future__ import annotations

from .events import (
    AttachmentMemoEvent,
    BaseMemoEvent,
    ContentMatchMemoEvent,
    IdeaMemoEvent,
    LongMemoEvent,
    PrivateMemoEvent,
    ProjectMemoEvent,
    PublicMemoEvent,
    ResearchMemoEvent,
    SpecificTagMemoEvent,
    TaggedMemoEvent,
    UrgentMemoEvent,
)
from .handlers import (
    MemoFileHandler,
    MemoNotificationHandler,
    MemoSearchIndexer,
    create_idea_handler,
    create_project_handler,
    create_research_handler,
)
from .models import Memo, MemoWebhookPayload
from .plugin import (
    get_plugin_info,
    init_plugin,
    cleanup_plugin,
    register_handlers_with_bus,
    get_file_handler,
    get_notification_handler,
    get_search_indexer,
    search_saved_memos,
)

__version__ = "0.1.0"
__author__ = "WebHooky Memos Plugin"

__all__ = [
    # Events
    "BaseMemoEvent",
    "TaggedMemoEvent", 
    "SpecificTagMemoEvent",
    "ContentMatchMemoEvent",
    "ResearchMemoEvent",
    "ProjectMemoEvent",
    "IdeaMemoEvent",
    "UrgentMemoEvent",
    "PrivateMemoEvent",
    "PublicMemoEvent",
    "AttachmentMemoEvent",
    "LongMemoEvent",
    # Handlers
    "MemoFileHandler",
    "MemoNotificationHandler",
    "MemoSearchIndexer",
    "create_research_handler",
    "create_project_handler",
    "create_idea_handler",
    # Models
    "Memo",
    "MemoWebhookPayload",
    # Plugin functions
    "get_plugin_info",
    "init_plugin", 
    "cleanup_plugin",
    "register_handlers_with_bus",
    "get_file_handler",
    "get_notification_handler",
    "get_search_indexer",
    "search_saved_memos",
]
