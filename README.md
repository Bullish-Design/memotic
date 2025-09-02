
# memos-webhooky

A small adapter to plug [Memos](https://usememos.com/) webhook payloads into the
`webhooky` event bus with Pydantic-based structural matching.

## Quick start

```python
from webhooky import EventBus
from memos_webhooky import MemoWebhookyBase, on_create, on_edit

class TaggedMemo(MemoWebhookyBase):
    any_tags = {"idea"}

    @on_create()
    def when_created(self):
        print("New idea:", self.memo.content)

class SaysHiMemo(MemoWebhookyBase):
    content_contains = "hi"

    @on_edit()
    def on_edit(self):
        print("Hi detected:", self.memo.content)

bus = EventBus()
bus.register(TaggedMemo)
bus.register(SaysHiMemo)
```

The adapter:
- Accepts either raw memo dicts (as in the examples) or common envelopes (`memo`, `data`, `after`).
- Normalizes activity from `X-Memos-Event` header if present, otherwise compares create/update seconds.
- Builds tags from `memo.tags` and scans node trees for `TagNode` contents.
