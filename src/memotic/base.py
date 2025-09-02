from __future__ import annotations

import asyncio
import re
from typing import Any, Dict, Iterable, List, Optional, Set, ClassVar

from pydantic import Field, computed_field, model_validator, ConfigDict

# memos model classes (user supplied)
from .old_models.memo import Memo
from .old_models.user import User

# webhooky primitives (already in your repo)
from webhooky import (
    WebhookEventBase,
    EventBus,
    on_activity,
    on_any,
    on_create,
    on_update,
    on_delete,
)


# Public alias that reads natural for Memos
def on_edit():
    return on_update()


class MemoWebhookyBase(WebhookEventBase):
    """Webhooky adapter for Memos payloads.

    Usage:
        Subclass and optionally set class-level *matchers*; then implement
        @on_create / @on_edit / @on_delete handlers.

    Matchers (all optional):
        - any_tags: set[str]  -> match if memo has ANY of these tags
        - all_tags: set[str]  -> match if memo has ALL of these tags
        - content_contains: str -> case-insensitive substring in memo.content
        - content_regex: str -> regex applied to memo.content (re.I|re.S)

    Parsed fields:
        - memo: Memo                    (required)
        - previous_memo: Optional[Memo] (if present in payload)
        - user: Optional[User]          (actor/creator)
        - activity_hint: Optional[str]  (normalized if headers/payload include one)
    """

    memo: Memo
    previous_memo: Optional[Memo] = None
    user: Optional[User] = None
    activity_hint: Optional[str] = Field(default=None, repr=False)

    # ----- optional class-level matchers developers may set -----
    any_tags: ClassVar[Set[str]] = set()
    all_tags: ClassVar[Set[str]] = set()
    content_contains: ClassVar[Optional[str]] = None
    content_regex: ClassVar[Optional[str]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, populate_by_name=True)

    # -------------------- Input coercion --------------------
    @model_validator(mode="before")
    @classmethod
    def _coerce_from_raw(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        raw = data.get("raw_data") or {}

        # If the incoming payload already looks like a Memo dict (as in examples),
        # treat 'raw' itself as the memo object.
        # Otherwise, fall back to common envelopes.
        if isinstance(raw, dict) and ("content" in raw or "name" in raw) and "memo" not in raw:
            memo_dict = raw
        else:
            memo_dict = (
                raw.get("memo")
                or raw.get("data")
                or raw.get("after")
                or raw.get("resource")
                or raw.get("new")
                or raw.get("object")
                or {}
            )

        prev_dict = raw.get("before") or raw.get("prev") or raw.get("old") or raw.get("previous") or {}

        # Actor/creator if provided
        user_dict = raw.get("user") or raw.get("actor") or raw.get("creator") or {}

        # Activity detection:
        # 1) Header like X-Memos-Event: memo.created / memo.updated / memo.deleted
        # 2) Field 'activity'/'action'/'event'
        # 3) Compare create_time vs update_time seconds (equal => create, gt => update)
        headers = data.get("headers") or {}
        event_header = (headers.get("x-memos-event") or headers.get("X-Memos-Event") or "").lower()
        if event_header:
            act = _normalize_activity(event_header)
        else:
            event_like = (
                raw.get("activity")
                or raw.get("action")
                or raw.get("event")
                or raw.get("type")
                or raw.get("event_type")
                or ""
            )
            act = _normalize_activity(str(event_like))

            if not act:
                try:
                    ct = (
                        (((memo_dict.get("create_time") or {}).get("seconds")) or 0)
                        if isinstance(memo_dict, dict)
                        else 0
                    )
                    ut = (
                        (((memo_dict.get("update_time") or {}).get("seconds")) or 0)
                        if isinstance(memo_dict, dict)
                        else 0
                    )
                    if ct and ut:
                        if ut == ct:
                            act = "create"
                        elif ut > ct:
                            act = "update"
                except Exception:
                    pass

        data.setdefault("memo", memo_dict)
        if prev_dict:
            data.setdefault("previous_memo", prev_dict)
        if user_dict:
            data.setdefault("user", user_dict)
        if act:
            data.setdefault("activity_hint", act)
        return data

    # -------------------- Activity plumbing --------------------
    def get_activity(self) -> str:
        if self.activity_hint:
            return self.activity_hint
        return super().get_activity()

    # -------------------- Matchers --------------------
    @classmethod
    def matches(cls, raw_data: Dict[str, Any], headers: Optional[Dict[str, str]] = None) -> bool:
        try:
            instance = cls(raw_data=raw_data, headers=headers or {})
        except Exception:
            return False

        if cls.any_tags:
            if not (set(instance.tags_normalized) & {t.lower() for t in cls.any_tags}):
                return False
        if cls.all_tags:
            wanted = {t.lower() for t in cls.all_tags}
            if not wanted.issubset(set(instance.tags_normalized)):
                return False
        if cls.content_contains:
            if (cls.content_contains or "").lower() not in (instance.memo.content or "").lower():
                return False
        if cls.content_regex:
            try:
                pat = re.compile(cls.content_regex, re.I | re.S)
            except re.error:
                return False
            if not pat.search(instance.memo.content or ""):
                return False
        return True

    # -------------------- Convenience computed fields --------------------
    @computed_field
    @property
    def tags(self) -> List[str]:
        # Prefer explicit Memo.tags if present
        tags: List[str] = []
        if hasattr(self.memo, "tags") and self.memo.tags:
            tags.extend(self.memo.tags)  # type: ignore[attr-defined]

        # Augment by scanning node tree for TagNode
        nodes = getattr(self.memo, "nodes", None)
        if nodes:
            tags.extend(_extract_tags_from_nodes_generic(nodes))

        # Deduplicate preserving order
        out: List[str] = []
        seen = set()
        for t in tags:
            if not isinstance(t, str):
                continue
            if t not in seen:
                out.append(t)
                seen.add(t)
        return out

    @computed_field
    @property
    def tags_normalized(self) -> List[str]:
        return [t.lstrip("#").strip().lower() for t in self.tags if isinstance(t, str) and t.strip()]


# -------------------- Helpers --------------------
def _normalize_activity(s: str) -> Optional[str]:
    s = (s or "").lower()
    if not s:
        return None
    # allow 'memo.created' / 'memos.memo.updated' / 'created'
    if "created" in s or "create" in s or "add" in s:
        return "create"
    if "updated" in s or "update" in s or "edit" in s or "modified" in s:
        return "update"
    if "deleted" in s or "delete" in s or "remove" in s:
        return "delete"
    return None


def _extract_tags_from_nodes_generic(nodes: Iterable[Any]) -> List[str]:
    """
    Traverse the example Memos node shape, which looks like:
        {'type': 2, 'Node': {'ParagraphNode': {'children': [
            {'type': 59, 'Node': {'TagNode': {'content': 'idea'}}}, ...
        ]}}}
    Strategy:
        - Perform a generic DFS over dicts/lists.
        - Anytime we see a key 'TagNode' with a mapping that has 'content': str,
          collect it.
    """
    results: List[str] = []

    def walk(obj: Any):
        if isinstance(obj, dict):
            # If this dict has a 'TagNode', extract its content
            if "TagNode" in obj and isinstance(obj["TagNode"], dict):
                content = obj["TagNode"].get("content")
                if isinstance(content, str):
                    results.append(content)
            # Recurse all values
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(nodes)
    return results
