"""
Activities router implementation
"""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

from ..models.base import PaginatedResponse, TimestampMixin


class ActivityMemoCommentPayload(BaseModel):
    """Activity memo comment payload."""

    memo: str
    related_memo: str


class ActivityPayload(BaseModel):
    """Activity payload union."""

    memo_comment: Optional[ActivityMemoCommentPayload] = None


class Activity(TimestampMixin):
    """Activity model."""

    name: Optional[str] = None
    creator: str
    type: str
    level: str
    payload: Optional[ActivityPayload] = None


class ListActivitiesResponse(PaginatedResponse):
    """List activities response."""

    activities: list[Activity] = []


class ActivityStorage:
    """In-memory activity storage for MVP."""

    def __init__(self) -> None:
        self.activities: Dict[str, Activity] = {}
        self.counter = 0

    def list_activities(self) -> list[Activity]:
        """List all activities."""
        return list(self.activities.values())

    def create_activity(self, activity: Activity) -> Activity:
        """Create a new activity."""
        self.counter += 1
        activity_id = str(self.counter)
        activity.name = f"activities/{activity_id}"
        self.activities[activity_id] = activity
        return activity


class ActivityRouter:
    """Activity API router handler."""

    def __init__(self) -> None:
        self.router = APIRouter()
        self.storage = ActivityStorage()
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Configure activity routes."""

        @self.router.get("/activities", response_model=ListActivitiesResponse)
        async def list_activities(
            page_size: Optional[int] = Query(None, ge=1, le=1000),
            page_token: Optional[str] = Query(None),
        ) -> ListActivitiesResponse:
            """List activities."""
            activities = self.storage.list_activities()
            return ListActivitiesResponse(activities=activities)

