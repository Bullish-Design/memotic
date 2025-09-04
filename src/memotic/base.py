# src/memotic/base.py
from __future__ import annotations

import asyncio
import inspect
import logging
import re
from datetime import datetime
from typing import Any, ClassVar, Dict, Iterable, List, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from memos_api.models import Memo as BaseMemo, User as BaseUser


# Re-export webhooky primitives
from webhooky import (
    WebhookEventBase,
    GenericWebhookEvent,
    EventBus,
    on_activity,
    on_any,
    on_create,
    on_update,
    on_delete,
    on_push,
    on_pull_request,
)

logger = logging.getLogger(__name__)


# ---------- Minimal data models ----------

'''
class User(BaseModel):
    """Subset of Memos user fields we actually consume."""

    model_config = ConfigDict(extra="allow")

    id: Optional[int] = None
    username: Optional[str] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    email: Optional[str] = None


class Memo(BaseModel):
    """Subset of Memos memo fields we actually consume."""

    model_config = ConfigDict(extra="allow")
    name: Optional[str] = None
    id: Optional[int] = None
    content: str = ""
    tags: List[str] = Field(default_factory=list)

    # Keep nodes flexible so TagNode survives: dict/list/anything
    nodes: Optional[Any] = None

    # Support both snake & camel case timestamp inputs as strings/ints
    create_time: Optional[datetime] = Field(None, alias="createTime")
    update_time: Optional[datetime] = Field(None, alias="updateTime")

    @model_validator(mode="before")
    @classmethod
    def _coerce_timestamps(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data

        def parse_dt(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            # already datetime
            if isinstance(value, datetime):
                return value
            # Firestore-ish dict {"seconds": int}
            if isinstance(value, dict) and "seconds" in value:
                try:
                    return datetime.fromtimestamp(int(value["seconds"]))
                except Exception:
                    return None
            # epoch seconds
            if isinstance(value, (int, float)):
                try:
                    return datetime.fromtimestamp(float(value))
                except Exception:
                    return None
            # ISO-ish string
            if isinstance(value, str):
                try:
                    # allow 'Z'
                    s = value.replace("Z", "+00:00")
                    return datetime.fromisoformat(s)
                except Exception:
                    return None
            return None

        # Accept both styles
        ct = data.get("create_time", data.get("createTime"))
        ut = data.get("update_time", data.get("updateTime"))
        if ct is not None:
            data["create_time"] = parse_dt(ct)
        if ut is not None:
            data["update_time"] = parse_dt(ut)
        return data
'''


# ---------- Enhanced models for webhook processing ----------


class User(BaseUser):
    """Extended User model with flexible parsing for webhook processing."""

    pass


class Memo(BaseMemo):
    """Extended Memo model with robust webhook format coercion."""

    @model_validator(mode="before")
    @classmethod
    def _coerce_webhook_formats(cls, data: Any) -> Any:
        """Convert webhook integer/dict formats to expected string/datetime formats."""
        if not isinstance(data, dict):
            return data

        data = dict(data)  # Don't modify original

        def parse_dt(value: Any) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            # Firestore-ish dict {"seconds": int}
            if isinstance(value, dict) and "seconds" in value:
                try:
                    return datetime.fromtimestamp(int(value["seconds"]))
                except Exception:
                    return None
            # epoch seconds
            if isinstance(value, (int, float)):
                try:
                    return datetime.fromtimestamp(float(value))
                except Exception:
                    return None
            # ISO-ish string
            if isinstance(value, str):
                try:
                    s = value.replace("Z", "+00:00")
                    return datetime.fromisoformat(s)
                except Exception:
                    return None
            return None

        # Coerce timestamps - display_time stays as string, others become datetime
        datetime_fields = ["create_time", "createTime", "update_time", "updateTime"]
        string_time_fields = ["display_time", "displayTime"]

        for field in datetime_fields:
            if field in data:
                parsed = parse_dt(data[field])
                if parsed:
                    snake_field = field.replace("createTime", "create_time").replace("updateTime", "update_time")
                    data[snake_field] = parsed

        for field in string_time_fields:
            if field in data:
                parsed = parse_dt(data[field])
                if parsed:
                    snake_field = field.replace("displayTime", "display_time")
                    data[snake_field] = parsed.isoformat()

        # Coerce enums from int to string
        enum_mappings = {
            "state": {1: "NORMAL", 2: "ARCHIVED"},
            "visibility": {1: "PRIVATE", 2: "PROTECTED", 3: "PUBLIC"},
        }

        for field, mapping in enum_mappings.items():
            if field in data and isinstance(data[field], int):
                data[field] = mapping.get(data[field], data[field])

        # Coerce node types in nodes array
        if "nodes" in data and isinstance(data["nodes"], list):
            node_type_mapping = {
                1: "LINE_BREAK",
                2: "PARAGRAPH",
                3: "CODE_BLOCK",
                4: "HEADING",
                5: "HORIZONTAL_RULE",
                6: "BLOCKQUOTE",
                7: "LIST",
                8: "ORDERED_LIST_ITEM",
                9: "UNORDERED_LIST_ITEM",
                10: "TASK_LIST_ITEM",
                11: "MATH_BLOCK",
                12: "TABLE",
                13: "EMBEDDED_CONTENT",
                51: "TEXT",
                52: "BOLD",
                53: "ITALIC",
                54: "BOLD_ITALIC",
                55: "CODE",
                56: "IMAGE",
                57: "LINK",
                58: "AUTO_LINK",
                59: "TAG",
                60: "STRIKETHROUGH",
                61: "ESCAPING_CHARACTER",
                62: "MATH",
                63: "HIGHLIGHT",
                64: "SUBSCRIPT",
                65: "SUPERSCRIPT",
                66: "SPOILER",
            }

            for node in data["nodes"]:
                if isinstance(node, dict) and "type" in node and isinstance(node["type"], int):
                    node["type"] = node_type_mapping.get(node["type"], f"UNKNOWN_{node['type']}")

        return data


class WebhookEnvelope(BaseModel):
    memo: Memo


# ---------- Utility helpers ----------


def _normalize_activity(s: Optional[str]) -> Optional[str]:
    if not s:
        return None
    s = str(s).strip().lower()
    if any(x in s for x in ("create", "created", "new", "insert")):
        return "create"
    if any(x in s for x in ("update", "edit", "edited", "modify", "modified", "change", "changed")):
        return "update"
    if any(x in s for x in ("delete", "deleted", "remove", "removed")):
        return "delete"
    # fallbacks
    if "push" in s or "commit" in s:
        return "push"
    if "pull_request" in s or "merge_request" in s or s in {"pr", "mr"}:
        return "pull_request"
    return None


def _extract_tags_from_nodes(nodes: Any) -> List[str]:
    """Generic DFS over dict/list (and BaseModel via model_dump) to find TagNode.content."""
    results: List[str] = []

    def walk(obj: Any) -> None:
        # Accept Pydantic models too
        if isinstance(obj, BaseModel):
            # dump by_alias to catch PascalCase keys if present
            walk(obj.model_dump(exclude_none=True, by_alias=True))
            return

        if isinstance(obj, dict):
            # Direct TagNode match - check both "TagNode" and nested structures
            if "TagNode" in obj and isinstance(obj["TagNode"], dict):
                content = obj["TagNode"].get("content")
                if isinstance(content, str):
                    results.append(content)

            # Also check Node.TagNode pattern from webhook
            if "Node" in obj and isinstance(obj["Node"], dict):
                node_data = obj["Node"]
                if "TagNode" in node_data and isinstance(node_data["TagNode"], dict):
                    content = node_data["TagNode"].get("content")
                    if isinstance(content, str):
                        results.append(content)

            # Recurse into all values
            for v in obj.values():
                walk(v)
            return

        if isinstance(obj, list):
            for item in obj:
                walk(item)

    walk(nodes)
    return results


def _gather_raw_paths(raw: Dict[str, Any], *paths: Tuple[str, ...]) -> Optional[Any]:
    """Attempt common envelope shapes without KeyError explosions."""
    for p in paths:
        cur = raw
        ok = True
        for key in p.split("."):
            if isinstance(cur, dict) and key in cur:
                cur = cur[key]
            else:
                ok = False
                break
        if ok:
            return cur
    return None


def _cheap_prefilter(
    raw_data: Dict[str, Any],
    any_tags: Set[str],
    all_tags: Set[str],
    content_contains: Optional[str],
    content_regex: Optional[re.Pattern],
) -> bool:
    """
    Fast reject before full model construction.
    Only checks what the class declares; avoids deep work otherwise.
    """
    if not (any_tags or all_tags or content_contains or content_regex):
        return True  # nothing to prefilter

    # Extract a content candidate
    content = _gather_raw_paths(
        raw_data,
        "memo.content",
        "data.content",
        "after.content",
        "payload.content",
        "content",
    )
    if content_contains and (not isinstance(content, str) or content_contains.lower() not in content.lower()):
        return False
    if content_regex and (not isinstance(content, str) or not content_regex.search(content)):
        return False

    # Extract tags if needed
    if any_tags or all_tags:
        tags: Set[str] = set()

        # plain tags
        memo_obj = _gather_raw_paths(raw_data, "memo", "data", "after", "payload")
        if isinstance(memo_obj, dict):
            t = memo_obj.get("tags")
            if isinstance(t, list):
                tags.update([str(x).lstrip("#").strip().lower() for x in t if isinstance(x, str)])

            # nodes (generic)
            nodes = memo_obj.get("nodes")
            if nodes is not None:
                found = _extract_tags_from_nodes(nodes)
                tags.update([str(x).lstrip("#").strip().lower() for x in found])

        if any_tags and tags.isdisjoint(any_tags):
            return False
        if all_tags and not all(tag in tags for tag in all_tags):
            return False

    return True


# ---------- The event base ----------


class MemoWebhookEvent(WebhookEventBase):
    """
    Base class for Memos webhook events.

    Declarative matchers (class-level):
        - any_tags: Set[str]
        - all_tags: Set[str]
        - content_contains: str (case-insensitive)
        - content_regex: str/Pattern (compiled lazily, flags=re.I|re.S)

    Parsed fields (instance attributes):
        - memo: Memo                    (required)
        - previous_memo: Optional[Memo] (if present)
        - user: Optional[User]          (actor)
        - activity_hint: Optional[str]  (normalized)
    """

    # Parsed data
    memo: Memo
    previous_memo: Optional[Memo] = None
    user: Optional[User] = None
    activity_hint: Optional[str] = Field(default=None, repr=False)

    # Declarative matchers (customize in subclasses)
    any_tags: ClassVar[Set[str]] = set()
    all_tags: ClassVar[Set[str]] = set()
    content_contains: ClassVar[Optional[str]] = None
    content_regex_str: ClassVar[Optional[str]] = None

    # internal caches
    _compiled_regex: ClassVar[Optional[re.Pattern]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="allow")

    @classmethod
    def from_raw(
        cls,
        raw_data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
        source_info: Optional[Dict[str, Any]] = None,
    ) -> MemoWebhookEvent:
        """Create event instance from raw webhook data using proper validation."""
        # print(f"Creating {cls.__name__} from raw data...")
        validated_model = cls.model_validate(
            {
                **raw_data,
                "headers": headers or {},
                "source_info": source_info or {},
                "timestamp": datetime.now(),
            }
        )
        # print(f"Created {cls.__name__} instance: {validated_model}")
        return validated_model

    @model_validator(mode="before")
    @classmethod
    def _coerce_envelopes(cls, data: Any) -> Any:
        """Accept multiple envelope shapes and normalize fields."""
        if not isinstance(data, dict):
            return data

        raw = dict(data)  # shallow copy

        # CRITICAL: Preserve raw_data for WebhookEventBase parent class
        raw["raw_data"] = data

        # Heuristic: find memo-ish object - DON'T fallback to entire raw data
        memo_like = raw.get("memo") or raw.get("data") or raw.get("after") or raw.get("payload")
        if memo_like:
            # Keep original dict form for node TagNode scanning; Memo will parse timestamps
            raw["memo"] = memo_like
        else:
            # If no envelope, assume raw data IS the memo (direct memo object)
            raw["memo"] = raw

        # previous memo envelope
        prev = raw.get("previous") or raw.get("before") or raw.get("prev") or raw.get("old")
        if prev:
            raw["previous_memo"] = prev

        # user/actor - handle string refs like "users/1"
        user_like = raw.get("user") or raw.get("creator") or raw.get("author")
        if user_like:
            if isinstance(user_like, str):
                # Simple string reference like "users/1" - make it a minimal User object
                raw["user"] = {"username": user_like}
            else:
                raw["user"] = user_like

        # NOTE: headers are passed separately into matches(); we also accept inline fields here
        for k in ("activity", "action", "event", "type", "event_type", "operation", "activityType"):
            if k in raw and isinstance(raw[k], str):
                raw["activity_hint"] = _normalize_activity(raw[k])
                break

        return raw

    @property
    def tags(self) -> List[str]:
        tags = list(self.memo.tags or [])
        if self.memo.nodes is not None:
            tags.extend(_extract_tags_from_nodes(self.memo.nodes))
        return tags

    @computed_field
    @property
    def tags_normalized(self) -> Set[str]:
        return {t.lstrip("#").strip().lower() for t in self.tags if isinstance(t, str)}

    def get_activity(self, headers: Optional[Dict[str, Any]] = None) -> str:
        """
        Determine activity: header -> hint -> timestamp inference -> 'any'
        """
        # 1) headers
        if headers:
            for hk in (
                "x-memos-event",
                "x-event-type",
                "x-github-event",
                "x-webhook-event",
                "x-activity",
                "x-action",
            ):
                hv = headers.get(hk) or headers.get(hk.title())
                if isinstance(hv, str):
                    act = _normalize_activity(hv)
                    if act:
                        return act

        # 2) inline activity_hint
        if self.activity_hint:
            return self.activity_hint

        # 3) compare timestamps if available
        ct = self.memo.create_time
        ut = self.memo.update_time
        try:
            if ct and ut:
                if ut == ct:
                    return "create"
                if ut > ct:
                    return "update"
        except Exception:
            pass

        # 4) fallback
        return "any"

    @classmethod
    def _get_compiled_regex(cls) -> Optional[re.Pattern]:
        if cls.content_regex_str is None:
            return None
        if cls._compiled_regex is None:
            try:
                cls._compiled_regex = re.compile(cls.content_regex_str, re.I | re.S)
            except re.error as e:
                logger.error("Invalid content_regex for %s: %s", cls.__name__, e)
                cls._compiled_regex = None
        return cls._compiled_regex

    @classmethod
    def matches(cls, raw_data: Dict[str, Any], headers: Optional[Dict[str, Any]] = None) -> bool:
        """Cheap prefilter + full validation + declarative checks."""
        # Skip matching for the base class itself
        if cls is MemoWebhookEvent:
            return False

        # Lazily compile regex
        regex = cls._get_compiled_regex()

        # Prefilter to drop obviously non-matching events
        if not _cheap_prefilter(
            raw_data=raw_data,
            any_tags={t.lower() for t in getattr(cls, "any_tags", set())},
            all_tags={t.lower() for t in getattr(cls, "all_tags", set())},
            content_contains=(getattr(cls, "content_contains", None) or None),
            content_regex=regex,
        ):
            logger.debug(f"Prefilter rejected {cls.__name__}")
            print(f"Prefilter rejected {cls.__name__}")
            return False

        # Try building the model (leverages validators)
        try:
            candidate = cls.model_validate(raw_data)
        except Exception as e:
            logger.debug("Validation failed in matches() for %s: %s", cls.__name__, e)
            print(f"Validation failed in matches() for {cls.__name__}: {e}")
            return False

        # Declarative checks
        tags = candidate.tags_normalized
        any_tags = {t.lower() for t in getattr(cls, "any_tags", set())}
        all_tags = {t.lower() for t in getattr(cls, "all_tags", set())}
        contains = getattr(cls, "content_contains", None)
        regex = cls._get_compiled_regex()

        if any_tags and tags.isdisjoint(any_tags):
            logger.debug(f"Tags check failed for {cls.__name__}: {tags} vs {any_tags}")
            print(f"Tags check failed for {cls.__name__}: {tags} vs {any_tags}")
            return False
        if all_tags and not all(t in tags for t in all_tags):
            logger.debug(f"All-tags check failed for {cls.__name__}: {tags} vs {all_tags}")
            print(f"All-tags check failed for {cls.__name__}: {tags} vs {all_tags}")
            return False

        if contains:
            if contains.lower() not in candidate.memo.content.lower():
                logger.debug(f"Content check failed for {cls.__name__}: {contains!r} not in {candidate.memo.content!r}")
                print(f"Content check failed for {cls.__name__}: {contains!r} not in {candidate.memo.content!r}")
                return False
        if regex:
            if not regex.search(candidate.memo.content):
                logger.debug(f"Regex check failed for {cls.__name__}")
                print(f"Regex check failed for {cls.__name__}")
                return False

        logger.debug(f"All checks passed for {cls.__name__}")
        # print(f"All checks passed for {cls.__name__}")
        return True

    async def process_triggers(self) -> Tuple[List[str], List[str]]:
        """
        Delegate to base impl (scans decorated methods).
        Kept for symmetry and future hooks.
        """
        return await super().process_triggers()

    @classmethod
    def normalize_tags(cls, tags: Iterable[str]) -> set[str]:
        return {t.strip().lower() for t in tags if t and t.strip()}

    @classmethod
    def event_matches(cls, env: WebhookEnvelope) -> bool:
        memo = env.memo
        tags = cls.normalize_tags(memo.tags)
        print(f"    Event tags: {tags}")
        if cls.any_tags and not (tags & cls.normalize_tags(cls.any_tags)):
            return False
        if cls.all_tags and not cls.normalize_tags(cls.all_tags).issubset(tags):
            return False
        return True

    @classmethod
    def from_envelope(cls, env: WebhookEnvelope) -> "MemoWebhookEvent":
        return cls(memo=env.memo)

