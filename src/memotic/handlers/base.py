# src/memotic/handlers.py
"""
Example handlers; replace with your own.
"""

from __future__ import annotations

from ..base import MemoWebhookEvent, on_create, on_update, on_any


class IdeaTagged(MemoWebhookEvent):
    any_tags = {"idea"}

    @on_create()
    def announce(self):
        print(f"[IdeaTagged] New idea: {self.memo.content!r}")


class MentionsHello(MemoWebhookEvent):
    content_contains = "hello"

    @on_update()
    def on_hello_edit(self):
        print(f"[MentionsHello] Edited memo mentioning hello: {self.memo.content!r}")


class RegexMatch(MemoWebhookEvent):
    content_regex_str = r"\bETA\s*:\s*(\d{4}-\d{2}-\d{2})\b"

    @on_any()
    def log_eta(self):
        print(f"[RegexMatch] content={self.memo.content!r}")
