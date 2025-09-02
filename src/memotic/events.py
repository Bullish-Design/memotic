"""Memos webhook event classes with pattern matching."""

from __future__ import annotations

import re
from typing import Any, Dict, Optional

from pydantic import BaseModel, field_validator
from webhooky import WebhookEventBase, on_create, on_update, on_delete

from .models import Memo, MemoWebhookPayload


class BaseMemoEvent(WebhookEventBase[MemoWebhookPayload]):
    """Base class for all memo webhook events."""

    @classmethod
    def _transform_raw_data(cls, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw webhook data to MemoWebhookPayload format."""
        # Handle different webhook payload formats
        if "memo" in raw_data and "action" in raw_data:
            # Already in expected format
            return raw_data
        elif "memo" in raw_data:
            # Infer action from memo state or default to "update"
            memo_data = raw_data["memo"]
            action = raw_data.get("event_type", raw_data.get("type", "update"))
            return {"action": action, "memo": memo_data}
        else:
            # Assume raw_data is the memo itself
            action = raw_data.get("action", raw_data.get("event_type", "update"))
            return {"action": action, "memo": raw_data}

    def get_activity(self) -> Optional[str]:
        """Get activity from memo action."""
        return self.payload.action


class TaggedMemoEvent(BaseMemoEvent):
    """Event that matches memos with any tags."""

    @field_validator("payload")
    @classmethod
    def validate_has_tags(cls, payload: MemoWebhookPayload) -> MemoWebhookPayload:
        """Validate that memo has tags."""
        if not payload.memo.has_tags:
            raise ValueError("Memo must have tags")
        return payload

    @on_create()
    async def handle_tagged_memo_created(self):
        """Handle tagged memo creation."""
        tags = ", ".join(self.payload.memo.tags or [])
        print(f"Tagged memo created: {tags}")

    @on_update()
    async def handle_tagged_memo_updated(self):
        """Handle tagged memo update."""
        tags = ", ".join(self.payload.memo.tags or [])
        print(f"Tagged memo updated: {tags}")


class SpecificTagMemoEvent(BaseMemoEvent):
    """Event that matches memos with specific tags."""

    # Override this in subclasses
    REQUIRED_TAGS: list[str] = []
    MATCH_MODE: str = "any"  # "any" or "all"
    CASE_SENSITIVE: bool = False

    @field_validator("payload")
    @classmethod
    def validate_has_required_tags(cls, payload: MemoWebhookPayload) -> MemoWebhookPayload:
        """Validate that memo has required tags."""
        if not cls.REQUIRED_TAGS:
            raise ValueError("REQUIRED_TAGS must be defined")

        memo = payload.memo
        if cls.MATCH_MODE == "all":
            if not memo.has_all_tags(cls.REQUIRED_TAGS, cls.CASE_SENSITIVE):
                raise ValueError(f"Memo must have all tags: {cls.REQUIRED_TAGS}")
        else:
            if not memo.has_any_tags(cls.REQUIRED_TAGS, cls.CASE_SENSITIVE):
                raise ValueError(f"Memo must have any of tags: {cls.REQUIRED_TAGS}")

        return payload


class ContentMatchMemoEvent(BaseMemoEvent):
    """Event that matches memos containing specific text patterns."""

    # Override these in subclasses
    REQUIRED_TEXT: Optional[str] = None
    TEXT_PATTERNS: list[str] = []
    USE_REGEX: bool = False
    CASE_SENSITIVE: bool = False

    @field_validator("payload")
    @classmethod
    def validate_content_matches(cls, payload: MemoWebhookPayload) -> MemoWebhookPayload:
        """Validate that memo content matches text patterns."""
        content = payload.memo.content or ""

        if not cls.CASE_SENSITIVE:
            content = content.lower()

        # Check simple text match
        if cls.REQUIRED_TEXT:
            text = cls.REQUIRED_TEXT
            if not cls.CASE_SENSITIVE:
                text = text.lower()
            if text not in content:
                raise ValueError(f"Memo must contain text: {cls.REQUIRED_TEXT}")

        # Check pattern matches
        if cls.TEXT_PATTERNS:
            for pattern in cls.TEXT_PATTERNS:
                if cls.USE_REGEX:
                    flags = 0 if cls.CASE_SENSITIVE else re.IGNORECASE
                    if re.search(pattern, payload.memo.content or "", flags):
                        return payload
                else:
                    check_pattern = pattern if cls.CASE_SENSITIVE else pattern.lower()
                    if check_pattern in content:
                        return payload

            raise ValueError(f"Memo must match patterns: {cls.TEXT_PATTERNS}")

        return payload


class PrivateMemoEvent(BaseMemoEvent):
    """Event that matches private memos only."""

    @field_validator("payload")
    @classmethod
    def validate_private(cls, payload: MemoWebhookPayload) -> MemoWebhookPayload:
        """Validate that memo is private."""
        from .models import Visibility

        if payload.memo.visibility != Visibility.PRIVATE:
            raise ValueError("Memo must be private")
        return payload


class PublicMemoEvent(BaseMemoEvent):
    """Event that matches public memos only."""

    @field_validator("payload")
    @classmethod
    def validate_public(cls, payload: MemoWebhookPayload) -> MemoWebhookPayload:
        """Validate that memo is public."""
        from .models import Visibility

        if payload.memo.visibility != Visibility.PUBLIC:
            raise ValueError("Memo must be public")
        return payload


class AttachmentMemoEvent(BaseMemoEvent):
    """Event that matches memos with attachments."""

    @field_validator("payload")
    @classmethod
    def validate_has_attachments(cls, payload: MemoWebhookPayload) -> MemoWebhookPayload:
        """Validate that memo has attachments."""
        if not payload.memo.has_attachments:
            raise ValueError("Memo must have attachments")
        return payload


class LongMemoEvent(BaseMemoEvent):
    """Event that matches long memos (configurable word count)."""

    MIN_WORD_COUNT: int = 100

    @field_validator("payload")
    @classmethod
    def validate_word_count(cls, payload: MemoWebhookPayload) -> MemoWebhookPayload:
        """Validate that memo meets minimum word count."""
        if payload.memo.word_count < cls.MIN_WORD_COUNT:
            raise ValueError(f"Memo must have at least {cls.MIN_WORD_COUNT} words")
        return payload


# Specific implementations for common patterns


class ResearchMemoEvent(ContentMatchMemoEvent):
    """Event that matches memos containing research-related content."""

    TEXT_PATTERNS: list[str] = ["research", "study", "investigate", "analyze", "analysis"]
    CASE_SENSITIVE: bool = False

    @on_create()
    async def handle_research_memo_created(self):
        """Handle research memo creation."""
        print(f"Research memo created: {self.payload.memo.name}")

    @on_update()
    async def handle_research_memo_updated(self):
        """Handle research memo update."""
        print(f"Research memo updated: {self.payload.memo.name}")


class ProjectMemoEvent(SpecificTagMemoEvent):
    """Event that matches memos tagged with project-related tags."""

    REQUIRED_TAGS: list[str] = ["project", "todo", "task", "milestone"]
    MATCH_MODE: str = "any"
    CASE_SENSITIVE: bool = False

    @on_create()
    async def handle_project_memo_created(self):
        """Handle project memo creation."""
        tags = ", ".join(self.payload.memo.tags or [])
        print(f"Project memo created with tags: {tags}")


class IdeaMemoEvent(SpecificTagMemoEvent):
    """Event that matches memos tagged as ideas."""

    REQUIRED_TAGS: list[str] = ["idea", "brainstorm", "concept"]
    MATCH_MODE: str = "any"
    CASE_SENSITIVE: bool = False

    @on_create()
    async def handle_idea_memo_created(self):
        """Handle idea memo creation."""
        print(f"New idea memo: {self.payload.memo.content[:100]}...")


class UrgentMemoEvent(BaseMemoEvent):
    """Event that matches urgent memos (based on tags or content)."""

    @field_validator("payload")
    @classmethod
    def validate_urgent(cls, payload: MemoWebhookPayload) -> MemoWebhookPayload:
        """Validate that memo is marked urgent."""
        memo = payload.memo

        # Check for urgent tags
        urgent_tags = ["urgent", "important", "priority", "asap"]
        if memo.has_any_tags(urgent_tags, case_sensitive=False):
            return payload

        # Check for urgent content patterns
        urgent_patterns = ["urgent", "asap", "priority", "important", "!!"]
        content = (memo.content or "").lower()
        if any(pattern in content for pattern in urgent_patterns):
            return payload

        raise ValueError("Memo must be marked as urgent")

    @on_create()
    async def handle_urgent_memo_created(self):
        """Handle urgent memo creation."""
        print(f"🚨 URGENT MEMO CREATED: {self.payload.memo.content[:50]}...")

    @on_update()
    async def handle_urgent_memo_updated(self):
        """Handle urgent memo update."""
        print(f"🚨 URGENT MEMO UPDATED: {self.payload.memo.name}")
