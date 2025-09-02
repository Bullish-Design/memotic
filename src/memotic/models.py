"""Core Memos models for webhook processing."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, computed_field


class State(str, Enum):
    """Resource state enumeration."""

    STATE_UNSPECIFIED = "STATE_UNSPECIFIED"
    NORMAL = "NORMAL"
    ARCHIVED = "ARCHIVED"


class Visibility(str, Enum):
    """Memo visibility enumeration."""

    VISIBILITY_UNSPECIFIED = "VISIBILITY_UNSPECIFIED"
    PRIVATE = "PRIVATE"
    PROTECTED = "PROTECTED"
    PUBLIC = "PUBLIC"


class MemoProperty(BaseModel):
    """Computed memo properties."""

    has_link: bool = Field(default=False, alias="hasLink")
    has_task_list: bool = Field(default=False, alias="hasTaskList")
    has_code: bool = Field(default=False, alias="hasCode")
    has_incomplete_tasks: bool = Field(default=False, alias="hasIncompleteTasks")

    class Config:
        populate_by_name = True


class Location(BaseModel):
    """Geographic location model."""

    placeholder: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class Attachment(BaseModel):
    """Memo attachment model."""

    name: Optional[str] = None
    filename: str
    content: Optional[bytes] = None
    external_link: Optional[str] = Field(None, alias="externalLink")
    type: str
    size: Optional[int] = None
    memo: Optional[str] = None

    class Config:
        populate_by_name = True


class Memo(BaseModel):
    """Main memo model for webhook processing."""

    name: Optional[str] = None
    state: State = State.NORMAL
    creator: Optional[str] = None
    display_time: Optional[str] = Field(None, alias="displayTime")
    content: str
    visibility: Visibility = Visibility.PRIVATE
    tags: Optional[list[str]] = None
    pinned: bool = False
    attachments: Optional[list[Attachment]] = None
    property: Optional[MemoProperty] = None
    parent: Optional[str] = None
    snippet: Optional[str] = None
    location: Optional[Location] = None
    create_time: Optional[datetime] = Field(None, alias="createTime")
    update_time: Optional[datetime] = Field(None, alias="updateTime")

    class Config:
        populate_by_name = True

    @computed_field
    def has_tags(self) -> bool:
        """Whether memo has any tags."""
        return bool(self.tags)

    @computed_field
    def tag_count(self) -> int:
        """Number of tags on memo."""
        return len(self.tags) if self.tags else 0

    @computed_field
    def word_count(self) -> int:
        """Approximate word count of content."""
        return len(self.content.split()) if self.content else 0

    @computed_field
    def has_attachments(self) -> bool:
        """Whether memo has attachments."""
        return bool(self.attachments)

    def contains_text(self, text: str, case_sensitive: bool = False) -> bool:
        """Check if memo content contains specific text."""
        content = self.content or ""
        if not case_sensitive:
            content = content.lower()
            text = text.lower()
        return text in content

    def has_tag(self, tag: str, case_sensitive: bool = False) -> bool:
        """Check if memo has specific tag."""
        if not self.tags:
            return False

        memo_tags = self.tags
        if not case_sensitive:
            memo_tags = [t.lower() for t in self.tags]
            tag = tag.lower()

        return tag in memo_tags

    def has_any_tags(self, tags: list[str], case_sensitive: bool = False) -> bool:
        """Check if memo has any of the specified tags."""
        return any(self.has_tag(tag, case_sensitive) for tag in tags)

    def has_all_tags(self, tags: list[str], case_sensitive: bool = False) -> bool:
        """Check if memo has all of the specified tags."""
        return all(self.has_tag(tag, case_sensitive) for tag in tags)


class MemoWebhookPayload(BaseModel):
    """Webhook payload wrapper for memo events."""

    action: str
    memo: Memo
    creator: Optional[str] = None
    timestamp: Optional[datetime] = None
    source: Optional[str] = None

    @computed_field
    def event_type(self) -> str:
        """Event type derived from action."""
        return f"memo_{self.action}"

    @computed_field
    def is_create(self) -> bool:
        """Whether this is a memo creation event."""
        return self.action.lower() in {"create", "created", "add", "added"}

    @computed_field
    def is_update(self) -> bool:
        """Whether this is a memo update event."""
        return self.action.lower() in {"update", "updated", "edit", "edited", "modify", "modified"}

    @computed_field
    def is_delete(self) -> bool:
        """Whether this is a memo delete event."""
        return self.action.lower() in {"delete", "deleted", "remove", "removed"}
