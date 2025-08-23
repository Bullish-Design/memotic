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
        self.base_url = base_url.rstrip('/')
        self.token = token
        self.client = httpx.Client(
            base_url=f"{self.base_url}/api/v1",
            headers={"Authorization": f"Bearer {token}"},
            timeout=30.0
        )
    
    def _request(self, method: str, endpoint: str, **kwargs) -> httpx.Response:
        response = self.client.request(method, endpoint, **kwargs)
        
        if not response.is_success:
            try:
                error_data = response.json()
                if "error" in error_data:
                    raise MemosAPIException(error_data["error"]["message"], response.status_code)
            except:
                pass
            raise MemosAPIException(f"HTTP {response.status_code}: {response.text}", response.status_code)
        
        return response
    
    # Auth
    def get_auth_status(self) -> AuthStatus:
        response = self._request("GET", "/auth/status")
        return AuthStatus(**response.json())
    
    # Memos
    def list_memos(
        self, 
        page: int = 1, 
        limit: int = 20, 
        tag: Optional[str] = None,
        visibility: Optional[str] = None,
        order_by: str = "created_ts",
        order: str = "desc"
    ) -> MemoListResponse:
        params = {
            "page": page,
            "limit": limit,
            "orderBy": order_by,
            "order": order
        }
        if tag:
            params["tag"] = tag
        if visibility:
            params["visibility"] = visibility
            
        response = self._request("GET", "/memos", params=params)
        return MemoListResponse(**response.json())
    
    def create_memo(self, memo_data: CreateMemoRequest) -> Memo:
        response = self._request("POST", "/memos", json=memo_data.dict())
        return Memo(**response.json())
    
    def get_memo(self, memo_id: int) -> Memo:
        response = self._request("GET", f"/memos/{memo_id}")
        return Memo(**response.json())
    
    def update_memo(self, memo_id: int, memo_data: UpdateMemoRequest) -> Memo:
        response = self._request("PATCH", f"/memos/{memo_id}", json=memo_data.dict(exclude_none=True))
        return Memo(**response.json())
    
    def delete_memo(self, memo_id: int) -> bool:
        response = self._request("DELETE", f"/memos/{memo_id}")
        return response.status_code == 200
    
    # Resources
    def upload_resource(self, file_path: str) -> Resource:
        with open(file_path, "rb") as f:
            files = {"file": f}
            response = self._request("POST", "/resources", files=files)
        return Resource(**response.json())
    
    def list_resources(self, page: int = 1, limit: int = 20) -> ResourceListResponse:
        params = {"page": page, "limit": limit}
        response = self._request("GET", "/resources", params=params)
        return ResourceListResponse(**response.json())
    
    def get_resource(self, resource_id: int) -> bytes:
        response = self._request("GET", f"/resources/{resource_id}")
        return response.content
    
    def delete_resource(self, resource_id: int) -> bool:
        response = self._request("DELETE", f"/resources/{resource_id}")
        return response.status_code == 200
    
    # Tags
    def list_tags(self) -> TagListResponse:
        response = self._request("GET", "/tags")
        return TagListResponse(**response.json())
    
    def get_tag_stats(self) -> TagListResponse:
        response = self._request("GET", "/tags/stats")
        return TagListResponse(**response.json())
    
    # Search
    def search_memos(self, query: str, limit: Optional[int] = None, tag: Optional[str] = None) -> SearchResponse:
        params = {"q": query}
        if limit:
            params["limit"] = limit
        if tag:
            params["tag"] = tag
        
        response = self._request("GET", "/search", params=params)
        return SearchResponse(**response.json())
    
    # System
    def get_system_info(self) -> SystemInfo:
        response = self._request("GET", "/system/info")
        return SystemInfo(**response.json())
    
    # Webhooks
    def list_webhooks(self) -> List[Webhook]:
        response = self._request("GET", "/webhooks")
        return [Webhook(**webhook) for webhook in response.json()]
    
    def create_webhook(self, webhook_data: CreateWebhookRequest) -> Webhook:
        response = self._request("POST", "/webhooks", json=webhook_data.dict())
        return Webhook(**response.json())
    
    def close(self):
        self.client.close()