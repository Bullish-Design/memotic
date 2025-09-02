# examples/basic_usage.py
import asyncio
from typing import List, Optional

from memotic.client import MemoticClient
from memotic.models import Memo, State, Visibility #, CreateMemoRequest 


async def _update_memo(
    client: MemoticClient,
    memo_id: int,
    *,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
) -> Memo:
    """
    Minimal helper until the client exposes update_memo().
    Adjust payload keys to match your server/model shape if needed.
    """
    payload = {}
    if content is not None:
        payload["content"] = content
    if tags is not None:
        payload["tags"] = tags

    resp = await client._client.patch(  # using underlying AsyncClient intentionally
        f"/memos/{memo_id}",
        headers=client._auth_headers,
        json=payload,
    )
    resp.raise_for_status()
    return Memo.model_validate(resp.json())


async def main():
    async with MemoticClient() as client:
        # 1) Create a memo
        created = await client.create_memo(Memo(content="Hello from example", visibility=Visibility.PRIVATE, state=State.NORMAL))
        print(f"Created: id={created.id}, content={created.content}")

        # 2) Get the same memo by id
        fetched = await client.get_memo(created.id)
        print(f"Fetched: id={fetched.id}, content={fetched.content}, tags={getattr(fetched, 'tags', None)}")

        # 3) Edit the contents
        edited = await _update_memo(client, fetched.id, content=fetched.content + " (edited)")
        print(f"Edited: id={edited.id}, content={edited.content}")

        # 4) Add a tag, then save
        current_tags = list(getattr(edited, "tags", []) or [])
        if "example" not in current_tags:
            current_tags.append("example")
        updated = await _update_memo(client, edited.id, tags=current_tags)
        print(f"Tagged: id={updated.id}, tags={getattr(updated, 'tags', None)}")


if __name__ == "__main__":
    asyncio.run(main())

