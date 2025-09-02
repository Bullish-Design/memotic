from __future__ import annotations

from memotic import MemoWebhookyBase, on_create, on_edit, on_any


class TaggedMemo(MemoWebhookyBase):
    """Triggers on any memo that has the tag #idea."""

    any_tags = {"idea"}

    @on_create()
    def on_create(self):
        print(f"[TaggedMemo] New #idea memo: {self.memo.content!r}")

    @on_any()
    def log_any(self):
        # helpful for debugging: see all matching activities
        print(f"[TaggedMemo] activity={self.get_activity()} tags={self.tags}")


class SaysHiMemo(MemoWebhookyBase):
    """Triggers on any memo whose content contains 'hi' (case-insensitive)."""

    content_contains = "hi"

    @on_edit()
    def on_edit(self):
        print(f"[SaysHiMemo] Edited memo containing 'hi': {self.memo.content!r}")
