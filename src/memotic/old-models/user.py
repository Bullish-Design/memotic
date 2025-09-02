"""
User-related models
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .base import PaginatedResponse, State, TimestampMixin, UserRole


class UserAccessToken(BaseModel):
    """User access token model."""
    name: Optional[str] = None
    access_token: str = Field(alias="accessToken")
    description: Optional[str] = None
    issued_at: Optional[datetime] = Field(None, alias="issuedAt")
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")
    
    class Config:
        populate_by_name = True


class UserSetting(BaseModel):
    """User settings model."""
    name: Optional[str] = None
    locale: Optional[str] = None
    appearance: Optional[str] = None
    memo_visibility: Optional[str] = Field(None, alias="memoVisibility")
    theme: Optional[str] = None
    
    class Config:
        populate_by_name = True


class UserStatsMemoTypeStats(BaseModel):
    """User statistics memo type stats."""
    link_count: int = Field(default=0, alias="linkCount")
    code_count: int = Field(default=0, alias="codeCount")
    todo_count: int = Field(default=0, alias="todoCount")
    undo_count: int = Field(default=0, alias="undoCount")
    
    class Config:
        populate_by_name = True


class UserStats(BaseModel):
    """User statistics model."""
    name: Optional[str] = None
    memo_type_stats: Optional[UserStatsMemoTypeStats] = Field(
        None,
        alias="memoTypeStats"
    )
    
    class Config:
        populate_by_name = True


class User(TimestampMixin):
    """Main user model."""
    name: Optional[str] = None
    role: UserRole = UserRole.USER
    username: str
    email: Optional[str] = None
    display_name: Optional[str] = Field(None, alias="displayName")
    avatar_url: Optional[str] = Field(None, alias="avatarUrl")
    description: Optional[str] = None
    password: Optional[str] = None  # Input only
    state: State = State.NORMAL
    
    class Config:
        populate_by_name = True


class CreateUserRequest(BaseModel):
    """Create user request."""
    user: User
    user_id: Optional[str] = Field(None, alias="userId")
    validate_only: bool = Field(False, alias="validateOnly")
    request_id: Optional[str] = Field(None, alias="requestId")
    
    class Config:
        populate_by_name = True


class ListUsersRequest(BaseModel):
    """List users request."""
    page_size: Optional[int] = Field(None, ge=1, le=1000, alias="pageSize")
    page_token: Optional[str] = Field(None, alias="pageToken")
    
    class Config:
        populate_by_name = True


class ListUsersResponse(PaginatedResponse):
    """List users response."""
    users: list[User] = []


class SearchUsersRequest(BaseModel):
    """Search users request."""
    query: str
    page_size: Optional[int] = Field(None, ge=1, le=1000, alias="pageSize")
    page_token: Optional[str] = Field(None, alias="pageToken")
    
    class Config:
        populate_by_name = True


class SearchUsersResponse(PaginatedResponse):
    """Search users response."""
    users: list[User] = []


class GetUserRequest(BaseModel):
    """Get user request."""
    name: str


class UpdateUserRequest(BaseModel):
    """Update user request."""
    user: User
    update_mask: Optional[str] = Field(None, alias="updateMask")
    
    class Config:
        populate_by_name = True


class DeleteUserRequest(BaseModel):
    """Delete user request."""
    name: str


class ListUserAccessTokensRequest(BaseModel):
    """List user access tokens request."""
    parent: str
    page_size: Optional[int] = Field(None, ge=1, le=1000, alias="pageSize")
    page_token: Optional[str] = Field(None, alias="pageToken")
    
    class Config:
        populate_by_name = True


class ListUserAccessTokensResponse(PaginatedResponse):
    """List user access tokens response."""
    access_tokens: list[UserAccessToken] = Field([], alias="accessTokens")
    
    class Config:
        populate_by_name = True


class CreateUserAccessTokenRequest(BaseModel):
    """Create user access token request."""
    parent: str
    access_token: UserAccessToken = Field(alias="accessToken")
    access_token_id: Optional[str] = Field(None, alias="accessTokenId")
    
    class Config:
        populate_by_name = True


class DeleteUserAccessTokenRequest(BaseModel):
    """Delete user access token request."""
    name: str


class ListAllUserStatsResponse(PaginatedResponse):
    """List all user stats response."""
    stats: list[UserStats] = []