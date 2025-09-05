# src/memotic/integrations/memos.py
from __future__ import annotations

import logging
from typing import Optional

from memos_api import MemosClient, MemosClientConfig
from memos_api.exceptions import (
    MemosAPIError,
    MemosAuthenticationError as MemosAPIAuthError,
    MemosNotFoundError as MemosAPINotFoundError,
    MemosConnectionError,
    MemosValidationError,
)
from memos_api.models import Memo, Visibility

from ..config import MemoticConfig, get_config

logger = logging.getLogger(__name__)


class MemosIntegrationError(Exception):
    """Base exception for Memos integration errors."""

    pass


class MemosAuthError(MemosIntegrationError):
    """Authentication error with Memos API."""

    pass


class MemosNotFoundError(MemosIntegrationError):
    """Resource not found in Memos API."""

    pass


class MemosConnectionError(MemosIntegrationError):
    """Connection error with Memos API."""

    pass


class MemosIntegration:
    """
    High-level integration wrapper for Memos API client.

    Provides memotic-specific convenience methods and integrates with
    memotic configuration system.
    """

    def __init__(self, config: Optional[MemoticConfig] = None) -> None:
        self.config = config or get_config()
        self._client: Optional[MemosClient] = None

    async def __aenter__(self) -> MemosIntegration:
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._client:
            await self._client.disconnect()
            self._client = None

    async def _ensure_client(self) -> MemosClient:
        """Ensure memos client is initialized and connected."""
        if self._client is None:
            if not self.config.has_api_config():
                raise MemosConnectionError("Memos API not configured. Set MEMOS_HOST, MEMOS_PORT, and MEMOS_TOKEN")

            client_config = MemosClientConfig(
                base_url=self.config.memos_api_url,
                token=self.config.memos_token,
                timeout=30.0,
                retries=3,
            )

            self._client = MemosClient(client_config)

            try:
                await self._client.connect()
                logger.debug(f"Connected to Memos API at {self.config.memos_api_url}")
            except MemosAPIAuthError as e:
                raise MemosAuthError("Failed to authenticate with Memos API") from e
            except MemosConnectionError as e:
                raise MemosConnectionError(f"Failed to connect to Memos API: {e}") from e
            except Exception as e:
                raise MemosConnectionError(f"Unexpected error connecting to Memos API: {e}") from e

        return self._client

    async def create_memo(
        self, content: str, visibility: str = "PRIVATE", parent: Optional[str] = None, **kwargs
    ) -> Memo:
        """
        Create a new memo.

        Args:
            content: Memo content
            visibility: Memo visibility (PRIVATE, PROTECTED, PUBLIC)
            parent: Parent memo name for creating child memos/comments
            **kwargs: Additional memo attributes

        Returns:
            Created memo object
        """
        client = await self._ensure_client()

        try:
            logger.debug(f"Creating memo with {len(content)} characters")
            if parent:
                logger.debug(f"Creating as child of {parent}")

            memo = await client.create_memo(content=content, visibility=visibility, parent=parent, **kwargs)

            logger.info(f"Created memo: {memo.name}")
            return memo

        except MemosAPIAuthError as e:
            raise MemosAuthError("Authentication failed when creating memo") from e
        except MemosAPINotFoundError as e:
            raise MemosNotFoundError(f"Parent memo not found: {parent}") from e
        except MemosValidationError as e:
            raise MemosIntegrationError(f"Validation error: {e}") from e
        except MemosAPIError as e:
            raise MemosIntegrationError(f"API error creating memo: {e}") from e

    async def create_comment(self, parent_memo_name: str, content: str, visibility: str = "PRIVATE", **kwargs) -> Memo:
        """
        Create a comment (child memo) on an existing memo.

        Args:
            parent_memo_name: Name/ID of parent memo
            content: Comment content
            visibility: Comment visibility
            **kwargs: Additional memo attributes

        Returns:
            Created comment memo
        """
        return await self.create_memo(content=content, visibility=visibility, parent=parent_memo_name, **kwargs)

    async def get_memo(self, memo_name: str) -> Memo:
        """
        Get memo by name/ID.

        Args:
            memo_name: Memo name or ID

        Returns:
            Memo object
        """
        client = await self._ensure_client()

        try:
            memo = await client.get_memo(memo_name)
            logger.debug(f"Retrieved memo: {memo.name}")
            return memo

        except MemosAPINotFoundError as e:
            raise MemosNotFoundError(f"Memo not found: {memo_name}") from e
        except MemosAPIError as e:
            raise MemosIntegrationError(f"API error getting memo: {e}") from e

    async def list_memos(self, filter_text: Optional[str] = None, page_size: Optional[int] = None) -> list[Memo]:
        """
        List memos with optional filtering.

        Args:
            filter_text: Filter text to search for
            page_size: Maximum number of memos to return

        Returns:
            List of memo objects
        """
        client = await self._ensure_client()

        try:
            memos = await client.list_memos(filter_text=filter_text, page_size=page_size)
            logger.debug(f"Listed {len(memos)} memos")
            return memos

        except MemosAPIError as e:
            raise MemosIntegrationError(f"API error listing memos: {e}") from e

    async def health_check(self) -> bool:
        """
        Check if Memos API is healthy and accessible.

        Returns:
            True if healthy, False otherwise
        """
        try:
            client = await self._ensure_client()
            return await client.health_check()
        except Exception as e:
            logger.warning(f"Memos API health check failed: {e}")
            return False


def create_memos_integration(config: Optional[MemoticConfig] = None) -> MemosIntegration:
    """Create a new Memos integration instance."""
    return MemosIntegration(config)
