
# memotic

A small, uv-managed Python client for the self-hosted **Memos** API:

- Typed **Pydantic v2** models and settings
- Async **REST** client on **httpx** 
- One-command **codegen** from upstream OpenAPI (fail-fast if missing)
- Thin, ergonomic wrappers (create/get/list/search memos; tags)
- Optional, separately-composable **attachments** helpers
- Pagination & async iterators by default

> **Non-goal:** This package does **not** include an MCP server. A separate repo can depend on `memotic` for MCP.

## Quick Start

```python
import asyncio
from memotic import Settings, MemosClient, Visibility

async def main():
    # Configure via .env or environment
    # MEMOS_BASE_URL=https://memos.example.com
    # MEMOS_TOKEN=... (personal access token)
    settings = Settings()

    async with MemosClient.from_settings(settings) as client:
        # Create memo
        memo = await client.create_memo(
            content="Hello, memos!", 
            visibility=Visibility.PRIVATE
        )
        
        # Get memo
        retrieved = await client.get_memo(memo.id)
        print(retrieved.content)  # "Hello, memos!"
        
        # Iterate all memos with pagination
        async for m in client.list_memos(page_size=100):
            print(m.id, m.created_ts)

asyncio.run(main())
```

## Installation

```bash
uv add memotic
```

## Development Setup

```bash
git clone https://github.com/you/memotic.git
cd memotic
uv sync

# Generate OpenAPI client (required before tests)
uv run memotic.codegen --clean

# Run tests
uv run pytest -q
```

## Configuration

Required environment variables:
- `MEMOS_BASE_URL` - Your Memos instance URL
- `MEMOS_TOKEN` - Personal access token

Optional timeouts (seconds):
- `MEMOTIC_CONNECT_TIMEOUT` (default: 10.0)
- `MEMOTIC_READ_TIMEOUT` (default: 30.0) 
- `MEMOTIC_WRITE_TIMEOUT` (default: 30.0)

