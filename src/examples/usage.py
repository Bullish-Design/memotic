"""
Example usage of the Memos API wrapper

Run with:
    uv run memos-example
    uv run memos-example webhook
"""

import asyncio
import json
import os
from memotic import (
    MemosClient,
    CreateMemoRequest,
    Visibility,
    register_webhook_handler,
)
from dotenv import load_dotenv

load_dotenv()


def example_api_usage():
    """Basic API usage example"""
    base_url = os.getenv("MEMOS_URL", "http://localhost:5232")
    token = os.getenv("MEMOS_TOKEN")

    if not token:
        print("Error: MEMOS_TOKEN environment variable not set")
        return

    # Initialize client
    client = MemosClient(base_url, token)
    print(f"\n\nUSAGE.PY\n\n")
    print(f"Connecting to Memos API at {client.base_url}\n\n")

    try:
        # Get auth status
        # auth = client.get_auth_status()
        # print(f"Logged in as: {auth.user.nickname}")

        # Create a memo
        memo_request = CreateMemoRequest(
            content="# API Test\n\nTesting the Python API wrapper!\n\n#test #api",
            visibility=Visibility.PRIVATE,
        )
        print(
            f"Creating memo with content:\n{json.dumps(memo_request.model_dump(), indent=4)}\n\n"
        )
        memo = client.create_memo(memo_request)
        print(f"Created memo: {memo}\n")

        # List memos
        memos = client.list_memos(tag="api")
        print(f"Found {len(memos.memos)} memos\n")

        # Search memos
        search_results = client.search_memos("Test")
        print(f"Search found {len(search_results.memos)} memos\n")

        # Get system info
        system_info = client.get_system_info()
        print(f"Connected to Memos v{system_info.version}\n")

    except Exception as e:
        print(f"\n\nError: {e}\n\n")
    finally:
        client.close()


# Example webhook handlers
@register_webhook_handler("memo.created")
async def handle_new_memo(data):
    print(f"New memo created with ID: {data.get('id')}")
    # You could trigger notifications, sync to other services, etc.


@register_webhook_handler("memo.updated")
async def handle_memo_update(data):
    print(f"Memo {data.get('id')} was updated")


@register_webhook_handler("memo.deleted")
async def handle_memo_deleted(data):
    print(f"Memo {data.get('id')} was deleted")


def run_webhook_server():
    """Run the FastAPI webhook server"""
    import uvicorn
    from memotic.server import app

    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8000"))

    print(f"Starting webhook server on {host}:{port}")
    uvicorn.run(app, host=host, port=port)


def main():
    """Main entry point for the example script"""
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "webhook":
        # Run webhook server
        run_webhook_server()
    else:
        # Run API examples
        print("Running API usage examples...")
        print("Set MEMOS_URL and MEMOS_TOKEN environment variables")
        print("Use 'memos-example webhook' to run webhook server")
        print()
        example_api_usage()


if __name__ == "__main__":
    main()
