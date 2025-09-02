"""Utility handlers for memos events."""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from .models import Memo, MemoWebhookPayload


class MemoFileHandler:
    """Handler for saving memos to files."""
    
    def __init__(
        self,
        base_path: Path | str = "./saved_memos",
        organize_by: str = "date",  # "date", "tags", "content_type"
        filename_pattern: str = "{timestamp}_{memo_name}.md",
        include_metadata: bool = True
    ):
        self.base_path = Path(base_path)
        self.organize_by = organize_by
        self.filename_pattern = filename_pattern
        self.include_metadata = include_metadata
        
        # Ensure base directory exists
        self.base_path.mkdir(parents=True, exist_ok=True)

    def get_save_path(self, memo: Memo) -> Path:
        """Determine save path based on organization strategy."""
        if self.organize_by == "date":
            if memo.create_time:
                date_str = memo.create_time.strftime("%Y/%m")
            else:
                date_str = datetime.now().strftime("%Y/%m")
            return self.base_path / date_str
            
        elif self.organize_by == "tags":
            if memo.tags:
                # Use first tag as directory
                tag = self._sanitize_filename(memo.tags[0])
                return self.base_path / "by_tag" / tag
            else:
                return self.base_path / "by_tag" / "untagged"
                
        elif self.organize_by == "content_type":
            content = memo.content or ""
            if memo.has_attachments:
                return self.base_path / "with_attachments"
            elif len(content.split()) > 200:
                return self.base_path / "long_form"
            elif any(marker in content for marker in ["- [ ]", "- [x]", "* [ ]", "* [x]"]):
                return self.base_path / "todo_lists"
            elif content.count("#") > 3:
                return self.base_path / "structured"
            else:
                return self.base_path / "notes"
        else:
            return self.base_path

    def generate_filename(self, memo: Memo) -> str:
        """Generate filename from pattern."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        memo_name = self._sanitize_filename(memo.name or "untitled")
        
        # Truncate long names
        if len(memo_name) > 50:
            memo_name = memo_name[:47] + "..."
            
        return self.filename_pattern.format(
            timestamp=timestamp,
            memo_name=memo_name,
            memo_id=memo.name or timestamp
        )

    def _sanitize_filename(self, name: str) -> str:
        """Sanitize string for use as filename."""
        # Remove/replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', name)
        # Replace multiple spaces/underscores with single underscore
        sanitized = re.sub(r'[_\s]+', '_', sanitized)
        # Remove leading/trailing underscores
        return sanitized.strip('_')

    def create_memo_content(self, payload: MemoWebhookPayload) -> str:
        """Create markdown content for saved memo."""
        memo = payload.memo
        content_lines = []
        
        if self.include_metadata:
            content_lines.append("---")
            content_lines.append(f"title: {memo.name or 'Untitled'}")
            if memo.tags:
                content_lines.append(f"tags: [{', '.join(memo.tags)}]")
            content_lines.append(f"visibility: {memo.visibility}")
            content_lines.append(f"created: {memo.create_time or datetime.now()}")
            if memo.creator:
                content_lines.append(f"creator: {memo.creator}")
            content_lines.append(f"source: memos_webhook")
            content_lines.append(f"action: {payload.action}")
            content_lines.append("---")
            content_lines.append("")
        
        # Add memo content
        content_lines.append(memo.content or "")
        
        # Add attachments info
        if memo.attachments:
            content_lines.append("")
            content_lines.append("## Attachments")
            for attachment in memo.attachments:
                if attachment.external_link:
                    content_lines.append(f"- [{attachment.filename}]({attachment.external_link})")
                else:
                    content_lines.append(f"- {attachment.filename} ({attachment.type})")
        
        return "\n".join(content_lines)

    async def save_memo(self, payload: MemoWebhookPayload) -> Path:
        """Save memo to file system."""
        save_path = self.get_save_path(payload.memo)
        save_path.mkdir(parents=True, exist_ok=True)
        
        filename = self.generate_filename(payload.memo)
        file_path = save_path / filename
        
        content = self.create_memo_content(payload)
        
        # Write file asynchronously
        def write_file():
            file_path.write_text(content, encoding='utf-8')
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_file)
        
        return file_path


class MemoNotificationHandler:
    """Handler for sending notifications about memos."""
    
    def __init__(
        self,
        notification_types: list[str] = None,
        webhook_url: Optional[str] = None,
        email_config: Optional[Dict[str, Any]] = None
    ):
        self.notification_types = notification_types or ["console"]
        self.webhook_url = webhook_url
        self.email_config = email_config

    async def notify(self, title: str, message: str, payload: MemoWebhookPayload) -> None:
        """Send notification about memo event."""
        for notification_type in self.notification_types:
            if notification_type == "console":
                await self._notify_console(title, message, payload)
            elif notification_type == "webhook" and self.webhook_url:
                await self._notify_webhook(title, message, payload)
            elif notification_type == "email" and self.email_config:
                await self._notify_email(title, message, payload)

    async def _notify_console(self, title: str, message: str, payload: MemoWebhookPayload) -> None:
        """Send console notification."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {title}: {message}")
        if payload.memo.tags:
            print(f"  Tags: {', '.join(payload.memo.tags)}")
        print(f"  Preview: {(payload.memo.content or '')[:100]}...")

    async def _notify_webhook(self, title: str, message: str, payload: MemoWebhookPayload) -> None:
        """Send webhook notification."""
        try:
            import aiohttp
            
            notification_data = {
                "title": title,
                "message": message,
                "memo": {
                    "name": payload.memo.name,
                    "tags": payload.memo.tags,
                    "content_preview": (payload.memo.content or "")[:200],
                    "action": payload.action,
                    "timestamp": datetime.now().isoformat()
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=notification_data) as response:
                    if response.status != 200:
                        print(f"Webhook notification failed: {response.status}")
        except ImportError:
            print("aiohttp not available for webhook notifications")
        except Exception as e:
            print(f"Webhook notification error: {e}")

    async def _notify_email(self, title: str, message: str, payload: MemoWebhookPayload) -> None:
        """Send email notification."""
        # Placeholder for email implementation
        print(f"Email notification: {title} - {message}")


class MemoSearchIndexer:
    """Handler for indexing memos for search."""
    
    def __init__(self, index_path: Path | str = "./memo_index"):
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)
        self.index_file = self.index_path / "memo_index.json"
        
    async def index_memo(self, payload: MemoWebhookPayload) -> None:
        """Add memo to search index."""
        import json
        
        # Load existing index
        index_data = {}
        if self.index_file.exists():
            try:
                index_data = json.loads(self.index_file.read_text())
            except Exception:
                index_data = {}
        
        # Create memo entry
        memo_id = payload.memo.name or f"memo_{datetime.now().timestamp()}"
        index_entry = {
            "id": memo_id,
            "content": payload.memo.content,
            "tags": payload.memo.tags or [],
            "created": (payload.memo.create_time or datetime.now()).isoformat(),
            "action": payload.action,
            "word_count": payload.memo.word_count,
            "visibility": payload.memo.visibility,
            "indexed_at": datetime.now().isoformat()
        }
        
        index_data[memo_id] = index_entry
        
        # Save index
        def write_index():
            self.index_file.write_text(json.dumps(index_data, indent=2))
            
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, write_index)

    async def search_memos(self, query: str, tags: list[str] = None) -> list[Dict[str, Any]]:
        """Search indexed memos."""
        import json
        
        if not self.index_file.exists():
            return []
            
        try:
            index_data = json.loads(self.index_file.read_text())
        except Exception:
            return []
        
        results = []
        query_lower = query.lower()
        
        for memo_id, entry in index_data.items():
            # Text search
            if query and query_lower not in (entry.get("content", "") or "").lower():
                continue
                
            # Tag filter
            if tags:
                memo_tags = [t.lower() for t in entry.get("tags", [])]
                if not any(tag.lower() in memo_tags for tag in tags):
                    continue
                    
            results.append(entry)
        
        # Sort by creation date (newest first)
        results.sort(key=lambda x: x.get("created", ""), reverse=True)
        return results


# Factory functions for common handler combinations

def create_research_handler(base_path: str = "./research_memos") -> MemoFileHandler:
    """Create handler optimized for research memos."""
    return MemoFileHandler(
        base_path=base_path,
        organize_by="tags",
        filename_pattern="research_{timestamp}_{memo_name}.md",
        include_metadata=True
    )

def create_project_handler(base_path: str = "./project_memos") -> MemoFileHandler:
    """Create handler optimized for project memos."""
    return MemoFileHandler(
        base_path=base_path,
        organize_by="date",
        filename_pattern="project_{memo_name}_{timestamp}.md", 
        include_metadata=True
    )

def create_idea_handler(base_path: str = "./ideas") -> MemoFileHandler:
    """Create handler optimized for idea memos."""
    return MemoFileHandler(
        base_path=base_path,
        organize_by="content_type",
        filename_pattern="idea_{timestamp}.md",
        include_metadata=False  # Keep ideas clean
    )
