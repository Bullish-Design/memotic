# src/memotic/models/user.py
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
    
    model_config = {"populate_by_name": True}


class UserSetting(BaseModel):
    """User settings model."""
    name: Optional[str] = None
    locale: Optional[str] = None
    appearance: Optional[str] = None
    memo_visibility: Optional[str] = Field(None, alias="memoVisibility")
    theme: Optional[str] = None
    
    model_config = {"populate_by_name": True}


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
    
    model_config = {"populate_by_name": True}


class CreateUserRequest(BaseModel):
    """Create user request."""
    user: User
    user_id: Optional[str] = Field(None, alias="userId")
    validate_only: bool = Field(False, alias="validateOnly")
    request_id: Optional[str] = Field(None, alias="requestId")
    
    model_config = {"populate_by_name": True}


class ListUsersRequest(BaseModel):
    """List users request."""
    page_size: Optional[int] = Field(None, ge=1, le=1000, alias="pageSize")
    page_token: Optional[str] = Field(None, alias="pageToken")
    
    model_config = {"populate_by_name": True}


class ListUsersResponse(PaginatedResponse):
    """List users response."""
    users: list[User] = []