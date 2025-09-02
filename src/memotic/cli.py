#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "typer[all]>=0.12.0",
#     "rich>=13.0.0",
#     "httpx>=0.27.0",
#     "fastapi>=0.110.0",
#     "uvicorn[standard]>=0.27.0",
# ]
# ///
"""
Memotic CLI - Command line interface for Memos API
"""

from __future__ import annotations

import asyncio
import os
import sys
import json
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

import httpx
import typer
import uvicorn
from rich.console import Console
from rich.table import Table

from .api import MemosAPI

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

app = typer.Typer(name="memotic", help="Memotic - FastAPI Memos CLI", no_args_is_help=True)
console = Console()


memo_app = typer.Typer(help="Memo management commands.", no_args_is_help=True)
user_app = typer.Typer(help="User management commands.", no_args_is_help=True)
app.add_typer(memo_app, name="memo")
app.add_typer(user_app, name="user")


def get_auth_settings() -> tuple[str, Optional[str]]:
    """Get API URL and token from environment."""
    api_url = os.getenv("MEMOS_URL") or os.getenv("memos_url") or "http://localhost:5232"
    token = os.getenv("MEMOS_TOKEN") or os.getenv("memos_token")
    return api_url, token


class APIClient:
    """HTTP client for API operations."""

    def __init__(self, base_url: str = "http://localhost:5232", token: Optional[str] = None) -> None:
        self.base_url = base_url
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        self.client = httpx.AsyncClient(base_url=base_url, headers=headers)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()


@app.command()
def serve(
    host: str = typer.Option("localhost", help="Host to bind to"),
    port: int = typer.Option(5232, help="Port to bind to"),
    reload: bool = typer.Option(True, help="Enable auto-reload"),
) -> None:
    """Start the Memos API server."""
    console.print(f"[green]Starting Memos API server on {host}:{port}[/green]")

    api = MemosAPI()
    uvicorn.run(
        api.app,
        host=host,
        port=port,
        # reload=reload,
    )


@memo_app.command("create")
def memo_create(
    content: str = typer.Argument(..., help="Memo content"),
    visibility: str = typer.Option("PRIVATE", help="Memo visibility"),
    api_url: Optional[str] = typer.Option(None, help="API URL override"),
) -> None:
    """Create a new memo."""

    async def _create():
        url, token = get_auth_settings()
        if api_url:
            url = api_url

        console.print(f"\nCreating memo at {url}...\n")

        async with APIClient(url, token) as client:
            response = await client.client.post(
                "/api/v1/memos", json={"content": content, "visibility": visibility, "state": "NORMAL"}
            )
            if response.status_code == 200:
                data = response.json()
                console.print(f"[green]✓[/green] Created memo: \n\n{json.dumps(data, indent=2)}\n")
            else:
                console.print(f"[red]✗[/red] Error: {response.text}")

    try:
        asyncio.run(_create())
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create memo: {e}")


@memo_app.command("list")
def memo_list(
    filter_text: Optional[str] = typer.Option(None, "--filter", help="Filter text"),
    api_url: Optional[str] = typer.Option(None, help="API URL override"),
) -> None:
    """List all memos."""

    async def _list():
        url, token = get_auth_settings()
        # console.print(f"Using API URL: {url}")
        # console.print(f"Using Token: {token if token else 'No'}")
        if api_url:
            url = api_url

        async with APIClient(url, token) as client:
            params = {}
            if filter_text:
                params["filter"] = filter_text

            response = await client.client.get("/api/v1/memos", params=params)
            if response.status_code == 200:
                data = response.json()
                memos = data.get("memos", [])

                if not memos:
                    console.print("[yellow]No memos found[/yellow]")
                    return

                table = Table()
                table.add_column("ID")
                table.add_column("Content")
                table.add_column("Visibility")
                table.add_column("Pinned")

                for memo in memos:
                    memo_id = memo["name"].split("/")[-1]
                    content = memo["content"][:50] + "..." if len(memo["content"]) > 50 else memo["content"]
                    visibility = memo["visibility"]
                    pinned = "📌" if memo.get("pinned") else ""

                    table.add_row(memo_id, content, visibility, pinned)

                console.print(table)
            else:
                console.print(f"[red]✗[/red] Error: {response.text}")

    try:
        asyncio.run(_list())
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list memos: {e}")


@memo_app.command("get")
def memo_get(
    memo_id: str = typer.Argument(..., help="Memo ID"),
    api_url: Optional[str] = typer.Option(None, help="API URL override"),
) -> None:
    """Get a specific memo."""

    async def _get():
        url, token = get_auth_settings()
        if api_url:
            url = api_url

        async with APIClient(url, token) as client:
            response = await client.client.get(f"/api/v1/memos/{memo_id}")
            if response.status_code == 200:
                data = response.json()
                console.print(f"[bold]Memo: {data['name']}[/bold]")
                console.print(f"Visibility: {data['visibility']}")
                console.print(f"Pinned: {'Yes' if data.get('pinned') else 'No'}")
                console.print(f"\n[bold]Content:[/bold]")
                console.print(data["content"])
            else:
                console.print(f"[red]✗[/red] Memo not found: {memo_id}")

    try:
        asyncio.run(_get())
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to get memo: {e}")


@user_app.command("create")
def user_create(
    username: str = typer.Argument(..., help="Username"),
    email: Optional[str] = typer.Option(None, help="Email"),
    api_url: Optional[str] = typer.Option(None, help="API URL override"),
) -> None:
    """Create a new user."""

    async def _create():
        user_data = {"username": username, "role": "USER"}
        if email:
            user_data["email"] = email
            user_data["displayName"] = username.title()

        url, token = get_auth_settings()
        if api_url:
            url = api_url

        async with APIClient(url, token) as client:
            response = await client.client.post("/api/v1/users", json={"user": user_data})
            if response.status_code == 200:
                data = response.json()
                console.print(f"[green]✓[/green] Created user: {data['name']}")
            else:
                console.print(f"[red]✗[/red] Error: {response.text}")

    try:
        asyncio.run(_create())
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to create user: {e}")


@user_app.command("list")
def user_list(
    api_url: Optional[str] = typer.Option(None, help="API URL override"),
) -> None:
    """List all users."""

    async def _list():
        url, token = get_auth_settings()
        if api_url:
            url = api_url

        async with APIClient(url, token) as client:
            response = await client.client.get("/api/v1/users")
            if response.status_code == 200:
                data = response.json()
                users = data.get("users", [])

                if not users:
                    console.print("[yellow]No users found[/yellow]")
                    return

                table = Table()
                table.add_column("ID")
                table.add_column("Username")
                table.add_column("Email")
                table.add_column("Role")

                for user in users:
                    user_id = user["name"].split("/")[-1] if user.get("name") else "N/A"
                    username = user.get("username", "N/A")
                    email = user.get("email", "N/A")
                    role = user.get("role", "N/A")

                    table.add_row(user_id, username, email, role)

                console.print(table)
            else:
                console.print(f"[red]✗[/red] Error: {response.text}")

    try:
        asyncio.run(_list())
    except Exception as e:
        console.print(f"[red]✗[/red] Failed to list users: {e}")


@app.command()
def status(
    api_url: Optional[str] = typer.Option(None, help="API URL override"),
) -> None:
    """Check API server status."""

    async def _check():
        url, token = get_auth_settings()
        if api_url:
            url = api_url

        try:
            async with APIClient(url, token) as client:
                response = await client.client.get("/docs")
                if response.status_code == 200:
                    console.print(f"[green]✓[/green] API server is running at {url}")
                else:
                    console.print(f"[red]✗[/red] API server returned {response.status_code}")
        except Exception:
            console.print(f"[red]✗[/red] Cannot connect to API server at {url}")

    try:
        asyncio.run(_check())
    except Exception as e:
        console.print(f"[red]✗[/red] Status check failed: {e}")


@app.command()
def version() -> None:
    """Show version information."""
    console.print("Memotic CLI v0.1.0")
    console.print("FastAPI Memos implementation")


def main() -> None:
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()

