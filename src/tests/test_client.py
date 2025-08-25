import pytest
from memotic.client import MemoticClient
from memotic.models import CreateMemo, Visibility, Memo

pytestmark = pytest.mark.asyncio


async def test_client_initialization(memos_credentials):
    """Test that the client initializes correctly."""
    client = MemoticClient(**memos_credentials)
    assert client.host == memos_credentials["host"]
    assert client.memo_service is not None


async def test_create_and_get_memo(client: MemoticClient):
    """Test creating a memo and then retrieving it."""
    # 1. Create a new memo
    memo_to_create = CreateMemo(
        content="Hello from memotic pytest!", visibility=Visibility.PRIVATE
    )
    created_memo = await client.create_memo(memo_to_create)

    assert isinstance(created_memo, Memo)
    assert "memos/" in created_memo.name
    assert created_memo.content == memo_to_create.content
    assert created_memo.visibility == memo_to_create.visibility

    # 2. Get the memo back using its name
    retrieved_memo = await client.get_memo(name=created_memo.name)
    assert retrieved_memo.id == created_memo.id
    assert retrieved_memo.content == "Hello from memotic pytest!"


async def test_list_memos(client: MemoticClient):
    """Test listing memos."""
    memos = await client.list_memos(page_size=5)
    assert isinstance(memos, list)
    if memos:
        assert isinstance(memos[0], Memo)
        assert len(memos) <= 5
