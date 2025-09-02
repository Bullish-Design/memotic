#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27.0",
# ]
# ///
"""
Memos API Usage Examples

To start the server:
    uv run main.py
    # or
    uv run serve

To run examples:
    uv run usage_examples.py
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

import httpx


class MemosAPIClient:
    """Simple client for Memos API."""

    def __init__(self, base_url: str = "http://tower:5232") -> None:
        self.base_url = base_url
        self.client = httpx.AsyncClient(base_url=base_url)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def create_user(self, username: str, email: str) -> Dict[str, Any]:
        """Create a new user."""
        response = await self.client.post(
            "/api/v1/users",
            json={"user": {"username": username, "email": email, "displayName": username.title(), "role": "USER"}},
        )
        response.raise_for_status()
        return response.json()

    async def list_users(self) -> Dict[str, Any]:
        """List all users."""
        response = await self.client.get("/api/v1/users")
        response.raise_for_status()
        return response.json()

    async def create_memo(self, content: str, visibility: str = "PRIVATE") -> Dict[str, Any]:
        """Create a new memo."""
        response = await self.client.post(
            "/api/v1/memos", json={"memo": {"content": content, "visibility": visibility, "state": "NORMAL"}}
        )
        response.raise_for_status()
        return response.json()

    async def list_memos(self, filter: str = None) -> Dict[str, Any]:
        """List memos with optional filter."""
        params = {}
        if filter:
            params["filter"] = filter

        response = await self.client.get("/api/v1/memos", params=params)
        response.raise_for_status()
        return response.json()

    async def get_memo(self, memo_id: str) -> Dict[str, Any]:
        """Get memo by ID."""
        response = await self.client.get(f"/api/v1/memos/{memo_id}")
        response.raise_for_status()
        return response.json()

    async def update_memo(
        self, memo_id: str, content: str = None, visibility: str = None, pinned: bool = None
    ) -> Dict[str, Any]:
        """Update existing memo."""
        memo_data = {}
        if content is not None:
            memo_data["content"] = content
        if visibility is not None:
            memo_data["visibility"] = visibility
        if pinned is not None:
            memo_data["pinned"] = pinned

        response = await self.client.patch(f"/api/v1/memos/{memo_id}", json={"memo": memo_data})
        response.raise_for_status()
        return response.json()

    async def signin(self, username: str, password: str) -> Dict[str, Any]:
        """Sign in with credentials."""
        response = await self.client.post(
            "/api/v1/auth/signin", json={"passwordCredentials": {"username": username, "password": password}}
        )
        response.raise_for_status()
        return response.json()


async def run_examples() -> None:
    """Run API usage examples."""
    print("🚀 Running Memos API Examples")
    print("=" * 50)

    async with MemosAPIClient() as client:
        try:
            # Test authentication
            print("1. Testing Authentication...")
            auth_result = await client.signin("user", "user123")
            print(f"✓ Signed in: {auth_result['user']['displayName']}")

            # Create a user
            print("\n2. Creating User...")
            user = await client.create_user("john_doe", "john@example.com")
            print(f"✓ Created user: {user['username']}")

            # List users
            print("\n3. Listing Users...")
            users = await client.list_users()
            print(f"✓ Found {len(users.get('users', []))} users")

            # Create memos
            print("\n4. Creating Memos...")
            memo1 = await client.create_memo("# My First Memo\nThis is my first memo with **markdown**!", "PUBLIC")
            memo2 = await client.create_memo("Private memo with #tag and a todo:\n- [ ] Task to complete")
            print(f"✓ Created memo 1: {memo1['name']}")
            print(f"✓ Created memo 2: {memo2['name']}")

            # List memos
            print("\n5. Listing Memos...")
            memos = await client.list_memos()
            print(f"✓ Found {len(memos.get('memos', []))} memos")

            # Search memos
            print("\n6. Searching Memos...")
            search_results = await client.list_memos(filter="markdown")
            print(f"✓ Found {len(search_results.get('memos', []))} memos with 'markdown'")

            # Update memo
            print("\n7. Updating Memo...")
            memo1_id = memo1["name"].split("/")[-1]
            updated_memo = await client.update_memo(
                memo1_id, content="# Updated Memo\nThis memo has been **updated**!", pinned=True
            )
            print(f"✓ Updated memo: {updated_memo['name']}")

            # Get specific memo
            print("\n8. Getting Specific Memo...")
            retrieved_memo = await client.get_memo(memo1_id)
            print(f"✓ Retrieved memo: {retrieved_memo['content'][:50]}...")

        except httpx.HTTPStatusError as e:
            print(f"❌ HTTP Error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 50)
    print("🎉 Examples completed!")


def print_curl_examples() -> None:
    """Print curl command examples."""
    print("\n📝 Curl Examples:")
    print("-" * 30)

    examples = [
        {
            "name": "Sign In",
            "curl": """curl -X POST http://tower:5232/api/v1/auth/signin \\
  -H "Content-Type: application/json" \\
  -d '{"passwordCredentials": {"username": "admin", "password": "password"}}'""",
        },
        {
            "name": "Create User",
            "curl": """curl -X POST http://tower:5232/api/v1/users \\
  -H "Content-Type: application/json" \\
  -d '{"user": {"username": "alice", "email": "alice@example.com", "role": "USER"}}'""",
        },
        {
            "name": "Create Memo",
            "curl": """curl -X POST http://tower:5232/api/v1/memos \\
  -H "Content-Type: application/json" \\
  -d '{"memo": {"content": "Hello **World**!", "visibility": "PUBLIC", "state": "NORMAL"}}'""",
        },
        {"name": "List Memos", "curl": "curl http://tower:5232/api/v1/memos"},
        {"name": "Get Memo", "curl": "curl http://tower:5232/api/v1/memos/1"},
        {
            "name": "Update Memo",
            "curl": """curl -X PATCH http://tower:5232/api/v1/memos/1 \\
  -H "Content-Type: application/json" \\
  -d '{"memo": {"content": "Updated content", "pinned": true}}'""",
        },
    ]

    for example in examples:
        print(f"\n• {example['name']}:")
        print(f"  {example['curl']}")


if __name__ == "__main__":
    print("Starting Memos API Usage Examples...")
    print("Make sure the server is running on http://tower:5232")

    print_curl_examples()

    try:
        asyncio.run(run_examples())
    except KeyboardInterrupt:
        print("\n👋 Examples interrupted by user")
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        print("Is the server running? Start it with: uv run main.py")

