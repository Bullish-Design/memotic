# src/memotic/models/base.py
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class State(str, Enum):
    """Resource state enumeration."""
    STATE_UNSPECIFIED = "STATE_UNSPECIFIED"
    NORMAL = "NORMAL"
    ARCHIVED = "ARCHIVED"


class Visibility(str, Enum):
    """Memo visibility enumeration."""
    VISIBILITY_UNSPECIFIED = "VISIBILITY_UNSPECIFIED" 
    PRIVATE = "PRIVATE"
    PROTECTED = "PROTECTED"
    PUBLIC = "PUBLIC"


class UserRole(str, Enum):
    """User role enumeration."""
    ROLE_UNSPECIFIED = "ROLE_UNSPECIFIED"
    HOST = "HOST"
    ADMIN = "ADMIN"
    USER = "USER"


class MemoRelationType(str, Enum):
    """Memo relation type enumeration."""
    TYPE_UNSPECIFIED = "TYPE_UNSPECIFIED"
    REFERENCE = "REFERENCE" 
    COMMENT = "COMMENT"


class ListNodeKind(str, Enum):
    """List node kind enumeration."""
    KIND_UNSPECIFIED = "KIND_UNSPECIFIED"
    ORDERED = "ORDERED"
    UNORDERED = "UNORDERED"
    DESCRIPTION = "DESCRIPTION"


class NodeType(str, Enum):
    """Node type enumeration for markdown parsing."""
    NODE_UNSPECIFIED = "NODE_UNSPECIFIED"
    LINE_BREAK = "LINE_BREAK"
    PARAGRAPH = "PARAGRAPH"
    CODE_BLOCK = "CODE_BLOCK"
    HEADING = "HEADING"
    HORIZONTAL_RULE = "HORIZONTAL_RULE"
    BLOCKQUOTE = "BLOCKQUOTE"
    LIST = "LIST"
    ORDERED_LIST_ITEM = "ORDERED_LIST_ITEM"
    UNORDERED_LIST_ITEM = "UNORDERED_LIST_ITEM"
    TASK_LIST_ITEM = "TASK_LIST_ITEM"
    MATH_BLOCK = "MATH_BLOCK"
    TABLE = "TABLE"
    EMBEDDED_CONTENT = "EMBEDDED_CONTENT"
    TEXT = "TEXT"
    BOLD = "BOLD"
    ITALIC = "ITALIC"
    BOLD_ITALIC = "BOLD_ITALIC"
    CODE = "CODE"
    IMAGE = "IMAGE"
    LINK = "LINK"
    AUTO_LINK = "AUTO_LINK"
    TAG = "TAG"
    STRIKETHROUGH = "STRIKETHROUGH"
    ESCAPING_CHARACTER = "ESCAPING_CHARACTER"
    MATH = "MATH"
    HIGHLIGHT = "HIGHLIGHT"
    SUBSCRIPT = "SUBSCRIPT"
    SUPERSCRIPT = "SUPERSCRIPT" 
    SPOILER = "SPOILER"


class BaseResponse(BaseModel):
    """Base response model."""
    pass


class PaginationMixin(BaseModel):
    """Pagination parameters mixin."""
    page_size: Optional[int] = Field(None, ge=1, le=1000)
    page_token: Optional[str] = None


class PaginatedResponse(BaseResponse):
    """Base paginated response model."""
    next_page_token: Optional[str] = None
    total_size: Optional[int] = None


class TimestampMixin(BaseModel):
    """Timestamp fields mixin."""
    create_time: Optional[datetime] = Field(None, alias="createTime")
    update_time: Optional[datetime] = Field(None, alias="updateTime")
    
    model_config = {"populate_by_name": True}


class ErrorDetail(BaseModel):
    """Error detail model."""
    type_url: str
    value: bytes


class GoogleRpcStatus(BaseModel):
    """Google RPC status error model."""
    code: int
    message: str
    details: list[ErrorDetail] = []