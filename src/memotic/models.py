from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Visibility(str, Enum):
    PRIVATE = "PRIVATE"
    PROTECTED = "PROTECTED"
    PUBLIC = "PUBLIC"


class Role(str, Enum):
    HOST = "HOST"
    ADMIN = "ADMIN"
    USER = "USER"


class RowStatus(str, Enum):
    NORMAL = "NORMAL"
    ARCHIVED = "ARCHIVED"


class User(BaseModel):
    id: int
    name: str
    username: str
    role: Role
    email: str
    nickname: str
    avatar_url: str = Field(alias="avatarUrl")
    create_time: datetime = Field(alias="createTime")
    update_time: datetime = Field(alias="updateTime")
    
    class Config:
        allow_population_by_field_name = True


class Resource(BaseModel):
    id: int
    name: str
    uid: str
    create_time: datetime = Field(alias="createTime")
    filename: str
    type: str
    size: int
    linked_memos: List[str] = Field(alias="linkedMemos", default=[])
    
    class Config:
        allow_population_by_field_name = True


class Memo(BaseModel):
    id: int
    name: str
    uid: str
    row_status: RowStatus = Field(alias="rowStatus")
    creator: str
    create_time: datetime = Field(alias="createTime")
    update_time: datetime = Field(alias="updateTime")
    display_time: datetime = Field(alias="displayTime")
    content: str
    visibility: Visibility
    pinned: bool = False
    resources: List[Resource] = []
    relations: List[Dict[str, Any]] = []
    tags: List[str] = []
    
    class Config:
        allow_population_by_field_name = True


class Tag(BaseModel):
    name: str
    count: int


class CustomizedProfile(BaseModel):
    title: str
    description: str
    logo_url: str = Field(alias="logoUrl")
    locale: str
    
    class Config:
        allow_population_by_field_name = True


class SystemInfo(BaseModel):
    version: str
    mode: str
    allow_sign_up: bool = Field(alias="allowSignUp")
    disable_password_login: bool = Field(alias="disablePasswordLogin")
    additional_script: str = Field(alias="additionalScript")
    customized_profile: CustomizedProfile = Field(alias="customizedProfile")
    
    class Config:
        allow_population_by_field_name = True


class Webhook(BaseModel):
    id: Optional[int] = None
    name: str
    url: str
    events: List[str]


class ErrorDetail(BaseModel):
    field: str
    issue: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[List[ErrorDetail]] = None


class ApiError(BaseModel):
    error: ErrorResponse


class AuthStatus(BaseModel):
    user: User


class MemoListResponse(BaseModel):
    data: List[Memo]
    next_page_token: Optional[str] = Field(alias="nextPageToken", default=None)
    
    class Config:
        allow_population_by_field_name = True


class ResourceListResponse(BaseModel):
    data: List[Resource]
    next_page_token: Optional[str] = Field(alias="nextPageToken", default=None)
    
    class Config:
        allow_population_by_field_name = True


class TagListResponse(BaseModel):
    data: List[Tag]


class CreateMemoRequest(BaseModel):
    content: str
    visibility: Visibility = Visibility.PRIVATE


class UpdateMemoRequest(BaseModel):
    content: Optional[str] = None
    visibility: Optional[Visibility] = None
    pinned: Optional[bool] = None


class UpdateUserRequest(BaseModel):
    nickname: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = Field(alias="avatarUrl", default=None)
    
    class Config:
        allow_population_by_field_name = True


class CreateWebhookRequest(BaseModel):
    name: str
    url: str
    events: List[str]


class SearchResponse(BaseModel):
    data: List[Memo]