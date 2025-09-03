# src/memotic/memos_client.py
from __future__ import annotations

import logging
import textwrap
import time
from typing import Optional

import httpx
from pydantic import BaseModel

from .config import get_config
from .models.memo import Memo as APIMemo, CreateMemoRequest
from .models.base import Visibility

logger = logging.getLogger(__name__)


class MemosClientConfig(BaseModel):
    """Configuration for Memos API client."""
    base_url: str
    token: str
    timeout: float = 15.0


class MemosClient:
    """Minimal client for the Memos API."""

    def __init__(
        self, 
        base_url: Optional[str] = None, 
        token: Optional[str] = None, 
        timeout: float = 15.0,
        config: Optional[MemosClientConfig] = None
    ):
        if config:
            self.config = config
        else:
            if not base_url or not token:
                global_config = get_config()
                base_url = base_url or global_config.api_base
                token = token or global_config.api_token
            
            if not base_url:
                raise ValueError("MEMOTIC_API_BASE not set and no base_url provided")
            if not token:
                raise ValueError("MEMOTIC_API_TOKEN not set and no token provided")
            
            self.config = MemosClientConfig(
                base_url=base_url.rstrip("/"),
                token=token,
                timeout=timeout
            )

        self._client = httpx.Client(
            base_url=self.config.base_url,
            headers={
                "Authorization": f"Bearer {self.config.token}",
                "Content-Type": "application/json",
                "User-Agent": "memotic/0.5.1"
            },
            timeout=self.config.timeout,
        )
        
        logger.debug(f"Initialized Memos client for {self.config.base_url}")

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()

    def __enter__(self) -> MemosClient:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def test_connection(self) -> bool:
        """Test if the API connection is working."""
        try:
            response = self._client.get("/v1/user")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def create_comment(
        self, 
        parent_memo_name: str, 
        content: str, 
        visibility: Visibility = Visibility.PRIVATE,
        max_retries: int = 2
    ) -> str:
        """Create a memo as a comment (child) of parent_memo_name."""
        body = CreateMemoRequest(
            memo=APIMemo(
                content=content,
                parent=parent_memo_name,
                visibility=visibility,
            )
        )
        
        logger.debug(f"Creating comment for {parent_memo_name}")
        logger.debug(f"Comment content length: {len(content)} chars")
        
        for attempt in range(max_retries + 1):
            try:
                response = self._client.post(
                    "/v1/memos", 
                    json=body.model_dump(by_alias=True, exclude_unset=True)
                )
                
                logger.debug(f"API response status: {response.status_code}")
                if response.status_code >= 400:
                    logger.error(f"API error response: {response.text}")
                
                response.raise_for_status()
                
                data = response.json()
                created = data.get("memo", data)
                memo_name = created.get("name", "")
                
                if memo_name:
                    logger.info(f"Created comment memo: {memo_name}")
                    return memo_name
                else:
                    logger.warning(f"No memo name in response: {created}")
                    return ""
                    
            except (httpx.RequestError, httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < max_retries:
                    wait_time = 1.0 * (attempt + 1)
                    logger.warning(f"API request failed (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"API request failed after {max_retries + 1} attempts: {e}")
                    raise
            except httpx.HTTPStatusError as e:
                if 400 <= e.response.status_code < 500:
                    logger.error(f"Client error creating comment: {e.response.status_code} {e.response.text}")
                    raise
                if attempt < max_retries:
                    wait_time = 1.0 * (attempt + 1)
                    logger.warning(f"Server error (attempt {attempt + 1}), retrying in {wait_time}s: {e}")
                    time.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Server error after {max_retries + 1} attempts: {e}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error creating comment: {e}")
                raise
        
        return ""

    def get_memo(self, memo_name: str) -> Optional[APIMemo]:
        """Get a memo by its name/resource ID."""
        try:
            response = self._client.get(f"/v1/{memo_name}")
            response.raise_for_status()
            
            data = response.json()
            return APIMemo.model_validate(data.get("memo", data))
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            logger.error(f"HTTP error getting memo: {e.response.status_code} {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error getting memo {memo_name}: {e}")
            raise


def format_cli_comment(title: str, combined_text: str, fence: str = "```") -> str:
    """Format CLI results as a markdown comment body."""
    return textwrap.dedent(f"""\
    **{title}**

    {fence}
    {combined_text.rstrip()}
    {fence}
    """)


def create_client(
    base_url: Optional[str] = None,
    token: Optional[str] = None,
    timeout: float = 15.0
) -> MemosClient:
    """Create a configured Memos client."""
    return MemosClient(base_url=base_url, token=token, timeout=timeout)