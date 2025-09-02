"""
User router implementation
"""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query

from ..models.user import (
    CreateUserAccessTokenRequest,
    CreateUserRequest,
    DeleteUserAccessTokenRequest,
    DeleteUserRequest,
    GetUserRequest,
    ListAllUserStatsResponse,
    ListUserAccessTokensRequest,
    ListUserAccessTokensResponse,
    ListUsersRequest,
    ListUsersResponse,
    SearchUsersRequest,
    SearchUsersResponse,
    UpdateUserRequest,
    User,
    UserAccessToken,
    UserStats,
)


class UserStorage:
    """In-memory user storage for MVP."""

    def __init__(self) -> None:
        self.users: Dict[str, User] = {}
        self.access_tokens: Dict[str, UserAccessToken] = {}
        self.counter = 0

    def create_user(self, user: User, user_id: Optional[str] = None) -> User:
        """Create a new user."""
        if user_id is None:
            self.counter += 1
            user_id = str(self.counter)

        user.name = f"users/{user_id}"
        self.users[user_id] = user
        return user

    def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    def list_users(self) -> list[User]:
        """List all users."""
        return list(self.users.values())

    def search_users(self, query: str) -> list[User]:
        """Search users by query."""
        query_lower = query.lower()
        return [
            user
            for user in self.users.values()
            if query_lower in user.username.lower()
            or (user.display_name and query_lower in user.display_name.lower())
            or (user.email and query_lower in user.email.lower())
        ]

    def update_user(self, user_id: str, user: User) -> Optional[User]:
        """Update existing user."""
        if user_id not in self.users:
            return None

        user.name = f"users/{user_id}"
        self.users[user_id] = user
        return user

    def delete_user(self, user_id: str) -> bool:
        """Delete user by ID."""
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False


class UserRouter:
    """User API router handler."""

    def __init__(self) -> None:
        self.router = APIRouter()
        self.storage = UserStorage()
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Configure user routes."""

        @self.router.get("/users", response_model=ListUsersResponse)
        async def list_users(
            page_size: Optional[int] = Query(None, ge=1, le=1000),
            page_token: Optional[str] = Query(None),
        ) -> ListUsersResponse:
            """List users."""
            users = self.storage.list_users()
            return ListUsersResponse(users=users)

        @self.router.post("/users", response_model=User)
        async def create_user(request: CreateUserRequest) -> User:
            """Create a new user."""
            return self.storage.create_user(request.user, request.user_id)

        @self.router.get("/users/{user_id}", response_model=User)
        async def get_user(user_id: str) -> User:
            """Get user by ID."""
            user = self.storage.get_user(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return user

        @self.router.patch("/users/{user_id}", response_model=User)
        async def update_user(user_id: str, request: UpdateUserRequest) -> User:
            """Update existing user."""
            user = self.storage.update_user(user_id, request.user)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            return user

        @self.router.delete("/users/{user_id}")
        async def delete_user(user_id: str) -> Dict[str, str]:
            """Delete user by ID."""
            success = self.storage.delete_user(user_id)
            if not success:
                raise HTTPException(status_code=404, detail="User not found")
            return {"message": "User deleted successfully"}

        @self.router.get("/users:search", response_model=SearchUsersResponse)
        async def search_users(
            query: str = Query(..., description="Search query"),
            page_size: Optional[int] = Query(None, ge=1, le=1000),
            page_token: Optional[str] = Query(None),
        ) -> SearchUsersResponse:
            """Search users."""
            users = self.storage.search_users(query)
            return SearchUsersResponse(users=users)

        @self.router.get("/users:stats", response_model=ListAllUserStatsResponse)
        async def list_all_user_stats(
            page_size: Optional[int] = Query(None, ge=1, le=1000),
            page_token: Optional[str] = Query(None),
        ) -> ListAllUserStatsResponse:
            """List all user statistics."""
            # Mock stats for MVP
            stats = [UserStats(name=f"users/{user_id}") for user_id in self.storage.users.keys()]
            return ListAllUserStatsResponse(stats=stats)

        @self.router.get("/users/{user_id}/accessTokens", response_model=ListUserAccessTokensResponse)
        async def list_user_access_tokens(
            user_id: str,
            page_size: Optional[int] = Query(None, ge=1, le=1000),
            page_token: Optional[str] = Query(None),
        ) -> ListUserAccessTokensResponse:
            """List user access tokens."""
            # Simple implementation for MVP
            tokens = [
                token
                for token in self.storage.access_tokens.values()
                if token.name and f"users/{user_id}" in token.name
            ]
            return ListUserAccessTokensResponse(access_tokens=tokens)

        @self.router.post("/users/{user_id}/accessTokens", response_model=UserAccessToken)
        async def create_user_access_token(user_id: str, request: CreateUserAccessTokenRequest) -> UserAccessToken:
            """Create user access token."""
            if user_id not in self.storage.users:
                raise HTTPException(status_code=404, detail="User not found")

            token_id = request.access_token_id or str(len(self.storage.access_tokens) + 1)
            token = request.access_token
            token.name = f"users/{user_id}/accessTokens/{token_id}"
            self.storage.access_tokens[token_id] = token
            return token

        @self.router.delete("/users/{user_id}/accessTokens/{token_id}")
        async def delete_user_access_token(user_id: str, token_id: str) -> Dict[str, str]:
            """Delete user access token."""
            if token_id in self.storage.access_tokens:
                del self.storage.access_tokens[token_id]
                return {"message": "Access token deleted successfully"}
            raise HTTPException(status_code=404, detail="Access token not found")

