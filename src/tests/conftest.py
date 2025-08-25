import os
import pytest
import pytest_asyncio
from dotenv import load_dotenv
from memotic.client import MemoticClient

load_dotenv()


@pytest.fixture(scope="session")
def memos_credentials():
    host = os.getenv("MEMOS_HOST")
    port = os.getenv("MEMOS_PORT")
    token = os.getenv("MEMOS_TOKEN")
    if not all([host, port, token]):
        pytest.skip(
            "MEMOS_HOST, MEMOS_PORT, and MEMOS_TOKEN environment variables must be set for integration tests."
        )
    return {"host": host, "port": int(port), "token": token}


@pytest_asyncio.fixture(scope="session")
async def client(memos_credentials):
    """Provides an authenticated MemoticClient for tests."""
    return MemoticClient(**memos_credentials)
