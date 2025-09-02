"""WebHooky Memos plugin entry point."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

from webhooky import EventBus, webhook_handler

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

logger = logging.getLogger(__name__)

__version__ = "0.1.0"
__author__ = "WebHooky Memos Plugin"
__description__ = "Memos webhook event processing plugin for WebHooky"

# Plugin configuration
DEFAULT_CONFIG = {
    "enable_file_saving": True,
    "enable_notifications": True,
    "enable_search_indexing": True,
    "base_save_path": "./saved_memos",
    "research_save_path": "./research_memos",
    "project_save_path": "./project_memos",
    "idea_save_path": "./ideas",
}

# Activity groups for memos
ACTIVITY_GROUPS = {
    "memo_crud": ["create", "update", "delete", "archive"],
    "memo_content": ["tag_added", "tag_removed", "content_updated"],
    "memo_organization": ["pinned", "unpinned", "visibility_changed"],
}

# Global handlers
_file_handlers: Dict[str, MemoFileHandler] = {}
_notification_handler: MemoNotificationHandler = None
_search_indexer: MemoSearchIndexer = None


def get_plugin_info() -> Dict[str, Any]:
    """Plugin information for WebHooky discovery."""
    return {
        "name": "memos",
        "version": __version__,
        "description": __description__,
        "author": __author__,
        "event_classes": [
            BaseMemoEvent,
            TaggedMemoEvent,
            SpecificTagMemoEvent,
            ContentMatchMemoEvent,
            ResearchMemoEvent,
            ProjectMemoEvent,
            IdeaMemoEvent,
            UrgentMemoEvent,
            PrivateMemoEvent,
            PublicMemoEvent,
            AttachmentMemoEvent,
            LongMemoEvent,
        ],
        "activity_groups": ACTIVITY_GROUPS,
    }


def init_plugin(config: Dict[str, Any] = None) -> None:
    """Initialize plugin with configuration."""
    global _file_handlers, _notification_handler, _search_indexer
    
    config = {**DEFAULT_CONFIG, **(config or {})}
    logger.info("Initializing Memos plugin")
    
    # Initialize file handlers if enabled
    if config["enable_file_saving"]:
        _file_handlers["default"] = MemoFileHandler(config["base_save_path"])
        _file_handlers["research"] = create_research_handler(config["research_save_path"])
        _file_handlers["project"] = create_project_handler(config["project_save_path"])
        _file_handlers["idea"] = create_idea_handler(config["idea_save_path"])
        logger.info("File handlers initialized")
    
    # Initialize notification handler if enabled
    if config["enable_notifications"]:
        _notification_handler = MemoNotificationHandler()
        logger.info("Notification handler initialized")
    
    # Initialize search indexer if enabled
    if config["enable_search_indexing"]:
        _search_indexer = MemoSearchIndexer()
        logger.info("Search indexer initialized")


def cleanup_plugin() -> None:
    """Cleanup plugin resources."""
    global _file_handlers, _notification_handler, _search_indexer
    
    logger.info("Cleaning up Memos plugin")
    _file_handlers.clear()
    _notification_handler = None
    _search_indexer = None


# Handler functions for integration with WebHooky bus

@webhook_handler
async def handle_research_memos(event: ResearchMemoEvent) -> None:
    """Handle research memo events."""
    if _file_handlers.get("research"):
        saved_path = await _file_handlers["research"].save_memo(event.payload)
        logger.info(f"Saved research memo to: {saved_path}")
    
    if _notification_handler:
        await _notification_handler.notify(
            "Research Memo",
            f"New research memo: {event.payload.memo.name or 'Untitled'}",
            event.payload
        )
    
    if _search_indexer:
        await _search_indexer.index_memo(event.payload)


@webhook_handler  
async def handle_project_memos(event: ProjectMemoEvent) -> None:
    """Handle project memo events."""
    if _file_handlers.get("project"):
        saved_path = await _file_handlers["project"].save_memo(event.payload)
        logger.info(f"Saved project memo to: {saved_path}")
    
    if _notification_handler:
        tags = ", ".join(event.payload.memo.tags or [])
        await _notification_handler.notify(
            "Project Memo",
            f"Project memo with tags: {tags}",
            event.payload
        )
    
    if _search_indexer:
        await _search_indexer.index_memo(event.payload)


@webhook_handler
async def handle_idea_memos(event: IdeaMemoEvent) -> None:
    """Handle idea memo events."""
    if _file_handlers.get("idea"):
        saved_path = await _file_handlers["idea"].save_memo(event.payload)
        logger.info(f"Saved idea memo to: {saved_path}")
    
    if _notification_handler:
        preview = (event.payload.memo.content or "")[:100]
        await _notification_handler.notify(
            "New Idea",
            f"Idea captured: {preview}...",
            event.payload
        )
    
    if _search_indexer:
        await _search_indexer.index_memo(event.payload)


@webhook_handler
async def handle_urgent_memos(event: UrgentMemoEvent) -> None:
    """Handle urgent memo events."""
    # Save to default location with urgent prefix
    if _file_handlers.get("default"):
        handler = _file_handlers["default"]
        # Temporarily modify filename pattern for urgent memos
        original_pattern = handler.filename_pattern
        handler.filename_pattern = "URGENT_{timestamp}_{memo_name}.md"
        
        try:
            saved_path = await handler.save_memo(event.payload)
            logger.warning(f"🚨 Saved URGENT memo to: {saved_path}")
        finally:
            handler.filename_pattern = original_pattern
    
    if _notification_handler:
        await _notification_handler.notify(
            "🚨 URGENT MEMO",
            f"Urgent memo requires attention: {event.payload.memo.name or 'Untitled'}",
            event.payload
        )
    
    if _search_indexer:
        await _search_indexer.index_memo(event.payload)


@webhook_handler
async def handle_tagged_memos(event: TaggedMemoEvent) -> None:
    """Handle general tagged memo events."""
    if _search_indexer:
        await _search_indexer.index_memo(event.payload)
    
    logger.info(f"Tagged memo processed: {', '.join(event.payload.memo.tags or [])}")


@webhook_handler
async def handle_attachment_memos(event: AttachmentMemoEvent) -> None:
    """Handle memos with attachments."""
    if _file_handlers.get("default"):
        saved_path = await _file_handlers["default"].save_memo(event.payload)
        logger.info(f"Saved memo with attachments to: {saved_path}")
    
    if _notification_handler:
        attachment_count = len(event.payload.memo.attachments or [])
        await _notification_handler.notify(
            "Memo with Attachments",
            f"Memo has {attachment_count} attachment(s)",
            event.payload
        )


def register_handlers_with_bus(bus: EventBus) -> None:
    """Register all plugin handlers with the event bus."""
    # Pattern-based handlers
    bus.register_handler(ResearchMemoEvent, handle_research_memos)
    bus.register_handler(ProjectMemoEvent, handle_project_memos)
    bus.register_handler(IdeaMemoEvent, handle_idea_memos)
    bus.register_handler(UrgentMemoEvent, handle_urgent_memos)
    bus.register_handler(TaggedMemoEvent, handle_tagged_memos)
    bus.register_handler(AttachmentMemoEvent, handle_attachment_memos)
    
    logger.info("Registered Memos plugin handlers with WebHooky bus")


# Utility functions for end users

def get_file_handler(handler_type: str = "default") -> MemoFileHandler:
    """Get configured file handler."""
    return _file_handlers.get(handler_type)


def get_notification_handler() -> MemoNotificationHandler:
    """Get configured notification handler."""
    return _notification_handler


def get_search_indexer() -> MemoSearchIndexer:
    """Get configured search indexer."""
    return _search_indexer


async def search_saved_memos(query: str, tags: list[str] = None) -> list[Dict[str, Any]]:
    """Search through saved/indexed memos."""
    if _search_indexer:
        return await _search_indexer.search_memos(query, tags)
    return []
