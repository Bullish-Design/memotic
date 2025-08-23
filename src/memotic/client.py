import httpx
from typing import Optional, List
from .models import *


class MemosAPIException(Exception):
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class MemosClient:
    def __init__(self, base_url: str, token: str):
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0,
        )
        self._user_id = None

    def _handle_response(self, response: httpx.Response) -> httpx.Response:
        # print(f"\n\nResponse: {response.status_code} {response.text}\n\n")
        if not response.is_success:
            try:
                error_data = response.json()
                if "error" in error_data:
                    raise MemosAPIException(
                        error_data["error"]["message"], response.status_code
                    )
            except:
                pass
            raise MemosAPIException(
                f"HTTP {response.status_code}: {response.text}", response.status_code
            )
        return response

    def get_user_id(self) -> str:
        """Get the user ID of the authenticated user"""
        if self._user_id:
            return self._user_id

        response = self._handle_response(self.client.post("auth/status"))
        user_data = response.json()
        user_id = user_data.get("user", {}).get("name")
        if not user_id:
            raise MemosAPIException("Could not retrieve user ID from auth status")
        self._user_id = user_id
        print(f"User ID: {user_id}")
        return user_id

    # Auth
    def get_auth_status(self) -> AuthStatus:
        response = self._handle_response(self.client.post("auth/status"))
        return AuthStatus(**response.json())

    # Memos
    def list_memos(
        self,
        page: int = 1,
        page_size: int = 20,
        tag: Optional[str] = None,
        visibility: Optional[str] = None,
        order_by: str = "create_time",
        order: str = "desc",
    ) -> MemoListResponse:
        user_id = 1  # self.get_user_id()
        params = {}  # {"pageSize": page_size}  # , "orderBy": order_by, "order": order}

        # Build filter if needed
        filters = []
        if tag:
            filters.append(f'content.contains("{tag}")')
        if visibility:
            filters.append(f'visibility == "{visibility}"')
        if filters:
            params["filter"] = " && ".join(filters)

        request = self.client.get(f"{user_id}/memos", params=params)
        print(f"\n    Request URL: {request.url}")
        print(f"    Request Params: {params}")
        print(f"    Request Headers: {request.headers}")
        # print(f"    Request Method: {request.method}")
        print(f"    Request Body: {request.content}")
        print(f"    Request Cookies: {request.cookies}")
        # print(f"    Request Timeout: {request.timeout}")

        response = self._handle_response(
            self.client.get(f"{user_id}/memos", params=params)
        )
        response.raise_for_status()
        print(f"    Request Response: {response}\n\n")

        return MemoListResponse(**response.json())

    def create_memo(self, memo_data: CreateMemoRequest) -> Memo:
        response = self._handle_response(
            self.client.post("memos", json=memo_data.model_dump())
        )
        return Memo(**response.json())

    def get_memo(self, memo_id: int) -> Memo:
        response = self._handle_response(self.client.get(f"memos/{memo_id}"))
        return Memo(**response.json())

    def update_memo(self, memo_id: int, memo_data: UpdateMemoRequest) -> Memo:
        response = self._handle_response(
            self.client.patch(
                f"memos/{memo_id}", json=memo_data.model_dump(exclude_none=True)
            )
        )
        return Memo(**response.json())

    def delete_memo(self, memo_id: int) -> bool:
        response = self._handle_response(self.client.delete(f"memos/{memo_id}"))
        return response.status_code == 200

    # Resources
    def upload_resource(self, file_path: str) -> Resource:
        with open(file_path, "rb") as f:
            response = self._handle_response(
                self.client.post("resources", files={"file": f})
            )
        return Resource(**response.json())

    def list_resources(
        self, page: int = 1, page_size: int = 20
    ) -> ResourceListResponse:
        params = {"pageSize": page_size}
        response = self._handle_response(self.client.get("resources", params=params))
        return ResourceListResponse(**response.json())

    def get_resource(self, resource_id: int) -> bytes:
        response = self._handle_response(self.client.get(f"resources/{resource_id}"))
        return response.content

    def delete_resource(self, resource_id: int) -> bool:
        response = self._handle_response(self.client.delete(f"resources/{resource_id}"))
        return response.status_code == 200

    # Tags
    def list_tags(self) -> TagListResponse:
        response = self._handle_response(self.client.get("tags"))
        return TagListResponse(**response.json())

    def get_tag_stats(self) -> TagListResponse:
        response = self._handle_response(self.client.get("tags/stats"))
        return TagListResponse(**response.json())

    # Search
    def search_memos(
        self, query: str, page_size: Optional[int] = None, tag: Optional[str] = None
    ) -> SearchResponse:
        user_id = self.get_user_id()
        params = {"filter": f'content.contains("{query}")'}
        if page_size:
            params["pageSize"] = page_size
        else:
            params["pageSize"] = 20

        response = self._handle_response(
            self.client.get(f"{user_id}/memos", params=params)
        )
        return SearchResponse(**response.json())

    # System
    def get_system_info(self) -> SystemInfo:
        response = self._handle_response(self.client.get("system/info"))
        return SystemInfo(**response.json())

    # Webhooks
    def list_webhooks(self) -> List[Webhook]:
        response = self._handle_response(self.client.get("webhooks"))
        return [Webhook(**webhook) for webhook in response.json()]

    def create_webhook(self, webhook_data: CreateWebhookRequest) -> Webhook:
        response = self._handle_response(
            self.client.post("webhooks", json=webhook_data.model_dump())
        )
        return Webhook(**response.json())

    def close(self):
        self.client.close()
