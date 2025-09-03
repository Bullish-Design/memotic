# src/memotic/memos_client.py
from __future__ import annotations

import os
import textwrap
from typing import Optional

import httpx

# Uses your vendored Memos API models
from memotic.old_models.memo import Memo as APIMemo, CreateMemoRequest
from memotic.old_models.base import Visibility


class MemosClient:
    """
    Minimal client for the Memos API we need:
      - create a child memo (comment) under a parent memo
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None, timeout: float = 15.0):
        self.base_url = (base_url or os.getenv("MEMOTIC_API_BASE", "")).rstrip("/")
        self.token = token or os.getenv("MEMOTIC_API_TOKEN")
        self.timeout = timeout
        if not self.base_url:
            raise ValueError("MEMOTIC_API_BASE not set")
        if not self.token:
            raise ValueError("MEMOTIC_API_TOKEN not set")

        self._client = httpx.Client(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
            },
            timeout=self.timeout,
        )

    def close(self) -> None:
        self._client.close()

    def create_comment(self, parent_memo_name: str, content: str, visibility: Visibility = Visibility.PRIVATE) -> str:
        """
        Create a memo as a **comment** (child) of `parent_memo_name`.
        Returns the created memo's `name` (resource id).
        """
        body = CreateMemoRequest(
            memo=APIMemo(
                content=content,
                parent=parent_memo_name,
                visibility=visibility,
            )
        )
        resp = self._client.post("/v1/memos", json=body.model_dump(by_alias=True, exclude_unset=True))
        resp.raise_for_status()
        data = resp.json()
        created = data.get("memo", data)  # support either shape
        return created.get("name", "")


def format_cli_comment(title: str, combined_text: str, fence: str = "```") -> str:
    """
    Nicely format CLI results as a single markdown comment body.
    """
    return textwrap.dedent(f"""\
    **{title}**

    {fence}
    {combined_text.rstrip()}
    {fence}
    """)
