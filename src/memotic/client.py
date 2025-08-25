import os
from typing import Optional

from dotenv import load_dotenv
from grpclib.client import Channel

from .models import CreateMemo, Memo, Visibility
from .proto_gen.memos.api import v1 as memos_api

# Load environment variables from .env file
load_dotenv()


class MemoticClient:
    """
    An asynchronous client for interacting with the Memos API.

    This client provides a high-level, Pydantic-based interface over the
    gRPC API stubs generated from the Memos protobuf definitions.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        token: Optional[str] = None,
    ):
        """
        Initializes the MemoticClient.

        Args:
            host: The hostname of the Memos server. Defaults to MEMOS_HOST env var.
            port: The port of the Memos server. Defaults to MEMOS_PORT env var.
            token: The access token for authentication. Defaults to MEMOS_TOKEN env var.

        Raises:
            ValueError: If host, port, or token are not provided and not found in env vars.
        """
        self.host = host or os.getenv("MEMOS_HOST")
        self.port = port or (int(p) if (p := os.getenv("MEMOS_PORT")) else None)
        self.token = token or os.getenv("MEMOS_TOKEN")

        if not all([self.host, self.port, self.token]):
            raise ValueError(
                "Memos host, port, and token must be provided either as arguments "
                "or as MEMOS_HOST, MEMOS_PORT, and MEMOS_TOKEN environment variables."
            )

        metadata = {"authorization": f"Bearer {self.token}"}
        channel = Channel(self.host, self.port)

        self.memo_service = memos_api.MemoServiceStub(channel, metadata=metadata)
        # Add other service stubs here as needed
        # self.user_service = memos_api.UserServiceStub(channel, metadata=metadata)

    async def create_memo(self, memo_data: CreateMemo) -> Memo:
        """
        Creates a new memo.

        Args:
            memo_data: A CreateMemo Pydantic model with the content and visibility.

        Returns:
            The created Memo object.
        """
        request = memos_api.CreateMemoRequest(
            memo=memo_data.content,
            visibility=memos_api.Visibility.from_string(memo_data.visibility.value),
        )
        created_memo_proto = await self.memo_service.create_memo(
            create_memo_request=request
        )
        return Memo.model_validate(created_memo_proto)

    async def list_memos(
        self,
        page_size: int = 50,
        page_token: str = "",
        filter_str: str = "row_status == 'NORMAL'",
    ) -> list[Memo]:
        """
        Lists memos with optional filtering and pagination.

        Args:
            page_size: The number of memos to retrieve.
            page_token: The token for the next page of results.
            filter_str: A filter string to apply to the query.

        Returns:
            A list of Memo objects.
        """
        request = memos_api.ListMemosRequest(
            page_size=page_size, page_token=page_token, filter=filter_str
        )
        response = await self.memo_service.list_memos(list_memos_request=request)
        return [Memo.model_validate(memo_proto) for memo_proto in response.memos]

    async def get_memo(self, name: str) -> Memo:
        """
        Retrieves a single memo by its name (ID).

        Args:
            name: The name of the memo, e.g., "memos/101".

        Returns:
            The requested Memo object.
        """
        request = memos_api.GetMemoRequest(name=name)
        memo_proto = await self.memo_service.get_memo(get_memo_request=request)
        return Memo.model_validate(memo_proto)
