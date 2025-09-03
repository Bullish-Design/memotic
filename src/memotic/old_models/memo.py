# src/memotic/models/memo.py
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from .base import (
    MemoRelationType,
    PaginatedResponse,
    State,
    TimestampMixin,
    Visibility,
)
from .nodes import Node


class Location(BaseModel):
    """Geographic location model."""
    placeholder: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class MemoProperty(BaseModel):
    """Computed memo properties."""
    has_link: bool = Field(default=False, alias="hasLink")
    has_task_list: bool = Field(default=False, alias="hasTaskList")
    has_code: bool = Field(default=False, alias="hasCode")
    has_incomplete_tasks: bool = Field(default=False, alias="hasIncompleteTasks")
    
    model_config = {"populate_by_name": True}


class MemoRelationMemo(BaseModel):
    """Memo reference in relations."""
    name: str
    snippet: Optional[str] = None


class MemoRelation(BaseModel):
    """Memo relation model."""
    memo: MemoRelationMemo
    related_memo: MemoRelationMemo = Field(alias="relatedMemo")
    type: MemoRelationType
    
    model_config = {"populate_by_name": True}


class Reaction(BaseModel):
    """Memo reaction model."""
    id: Optional[int] = None
    creator: str
    content_type: str = Field(alias="contentType")
    content: str
    
    model_config = {"populate_by_name": True}


class Attachment(BaseModel):
    """Memo attachment model."""
    name: Optional[str] = None
    filename: str
    content: Optional[bytes] = None
    external_link: Optional[str] = Field(None, alias="externalLink")
    type: str
    size: Optional[int] = None
    memo: Optional[str] = None
    
    model_config = {"populate_by_name": True}


class Memo(TimestampMixin):
    """Main memo model."""
    name: Optional[str] = None
    state: State = State.NORMAL
    creator: Optional[str] = None
    display_time: Optional[str] = Field(None, alias="displayTime")
    content: str
    nodes: Optional[list[Node]] = None
    visibility: Visibility = Visibility.PRIVATE
    tags: Optional[list[str]] = None
    pinned: bool = False
    attachments: Optional[list[Attachment]] = None
    relations: Optional[list[MemoRelation]] = None
    reactions: Optional[list[Reaction]] = None
    property: Optional[MemoProperty] = None
    parent: Optional[str] = None
    snippet: Optional[str] = None
    location: Optional[Location] = None
    
    model_config = {"populate_by_name": True}


class CreateMemoRequest(BaseModel):
    """Create memo request."""
    memo: Memo
    memo_id: Optional[str] = Field(None, alias="memoId")
    request_id: Optional[str] = Field(None, alias="requestId")
    
    model_config = {"populate_by_name": True}


class ListMemosRequest(BaseModel):
    """List memos request."""
    page_size: Optional[int] = Field(None, ge=1, le=1000, alias="pageSize")
    page_token: Optional[str] = Field(None, alias="pageToken")
    filter: Optional[str] = None
    
    model_config = {"populate_by_name": True}


class ListMemosResponse(PaginatedResponse):
    """List memos response."""
    memos: list[Memo] = []


class GetMemoRequest(BaseModel):
    """Get memo request."""
    name: str


class UpdateMemoRequest(BaseModel):
    """Update memo request."""
    memo: Memo
    update_mask: Optional[str] = Field(None, alias="updateMask")
    
    model_config = {"populate_by_name": True}


class DeleteMemoRequest(BaseModel):
    """Delete memo request."""
    name: str