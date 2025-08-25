from __future__ import annotations
from enum import Enum
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class Visibility(str, Enum):
    """Enumeration for memo visibility."""

    PUBLIC = "PUBLIC"
    PROTECTED = "PROTECTED"
    PRIVATE = "PRIVATE"


class RowStatus(str, Enum):
    """Enumeration for row status."""

    ACTIVE = "ACTIVE"
    ARCHIVED = "ARCHIVED"


class MemoProperty(BaseModel):
    """Calculated properties from memo content."""

    tags: List[str] = Field(default_factory=list)
    has_link: bool = False
    has_task_list: bool = False
    has_code: bool = False
    has_incomplete_tasks: bool = False


class Resource(BaseModel):
    """Represents a resource attached to a memo."""

    name: str
    id: int
    creator: str
    created_ts: datetime
    updated_ts: datetime
    filename: str
    internal_path: str
    external_link: str
    type: str
    size: int
    public_id: str
    linked_memo_id: Optional[int] = None


class Reaction(BaseModel):
    """Represents a reaction to a memo."""

    id: int
    creator: str
    content_id: str
    reaction_type: str


class Memo(BaseModel):
    """Represents a memo object."""

    name: str
    id: int
    row_status: RowStatus
    creator: str
    created_ts: datetime
    updated_ts: datetime
    content: str
    visibility: Visibility
    pinned: bool
    display_ts: datetime
    property: MemoProperty = Field(default_factory=MemoProperty)
    # The following fields are not in the provided proto but are good to have
    # resources: List[Resource] = Field(default_factory=list)
    # relations: List[MemoRelation] = Field(default_factory=list)
    # reactions: List[Reaction] = Field(default_factory=list)


class CreateMemo(BaseModel):
    """Model for creating a new memo."""

    content: str = Field(..., min_length=1, description="The content of the memo.")
    visibility: Visibility = Field(
        default=Visibility.PRIVATE, description="The visibility of the memo."
    )
