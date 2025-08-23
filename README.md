# Memos Python API Wrapper
A comprehensive Pydantic API wrapper for [Memos](https://www.usememos.com/) with FastAPI webhook support. Provides basic pydantic models of the core datastructures, a simple FastAPI server that can snag a webhook url, and an API for CRUD interactions. 

## Features

- **Full API Coverage**: Complete Pydantic models and client methods for all Memos REST API endpoints
- **Type Safety**: Full type hints and validation using Pydantic v2
- **Webhook Support**: FastAPI-based webhook server with decorator-based event handlers
- **Docker Ready**: Script entrypoints configured for container deployment
- **Test Suite**: Comprehensive pytest coverage with integration test support

## Quick Start

### Installation

This project uses [UV](https://github.com/astral-sh/uv) for dependency management:

```bash
# Install UV if you haven't already
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup the project
git clone <your-repo>
cd memotic
uv sync
```

### Basic Usage

```python
from memotic import MemosClient, CreateMemoRequest, Visibility

# Initialize client
client = MemosClient("http://localhost:5230", "your-access-token")

# Create a memo
memo = client.create_memo(CreateMemoRequest(
    content="# Hello World\n\nMy first memo via API!",
    visibility=Visibility.PRIVATE
))

print(f"Created memo: {memo.id}")
```

### Webhook Server

```python
from memotic import register_webhook_handler

@register_webhook_handler("memo.created")
async def handle_new_memo(data):
    print(f"New memo created: {data.get('id')}")

# Run server
uv run memos-webhook-server
```

## Environment Variables

```bash
# Required for API client
MEMOS_URL=http://localhost:5230
MEMOS_TOKEN=your-access-token

# Optional for webhook server
HOST=0.0.0.0
PORT=8000
LOG_LEVEL=info
```

## Commands

### Run Examples
```bash
# API usage examples
uv run memos-example

# Start webhook server via example
uv run memos-example webhook
```

### Start Webhook Server
```bash
uv run memos-webhook-server
```

### Development

```bash
# Install with dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Run specific test with integration
MEMOS_URL=http://localhost:5230 MEMOS_TOKEN=your-token uv run pytest -m integration

# Code formatting
uv run black .
uv run isort .
uv run ruff check .
```

## Docker Usage

```dockerfile
FROM python:3.11-slim

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app
COPY . .

# Install dependencies
RUN uv sync --frozen

# Run webhook server
CMD ["uv", "run", "memos-webhook-server"]
```

Or use with environment variables:

```bash
docker run -e MEMOS_URL=http://memos:5230 -e MEMOS_TOKEN=token -p 8000:8000 memos-api
```

## API Reference

### Client Methods

- `get_auth_status()` - Get current user info
- `list_memos()` - List memos with filtering
- `create_memo()` - Create new memo  
- `get_memo()` - Get specific memo
- `update_memo()` - Update existing memo
- `delete_memo()` - Delete memo
- `upload_resource()` - Upload file attachment
- `list_resources()` - List uploaded resources
- `search_memos()` - Search memos by content
- `get_system_info()` - Get system information

### Webhook Events

- `memo.created` - New memo created
- `memo.updated` - Memo updated  
- `memo.deleted` - Memo deleted

### Models

All API objects are represented as Pydantic models:

- `Memo` - Memo object with content, tags, visibility
- `User` - User account information
- `Resource` - File attachments  
- `Tag` - Tag with usage count
- `SystemInfo` - System configuration
- `Webhook` - Webhook configuration

## Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=memotic

# Integration tests (requires running Memos instance)
MEMOS_URL=http://localhost:5230 MEMOS_TOKEN=token uv run pytest -m integration
```

## Development

This project uses modern Python tooling:

- **UV**: Fast Python package installer and resolver
- **Pydantic v2**: Type validation and serialization
- **FastAPI**: Modern web framework for webhooks
- **pytest**: Testing framework
- **black/isort/ruff**: Code formatting and linting

## License

MIT License
