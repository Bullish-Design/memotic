"""
Attachments router implementation
"""

from __future__ import annotations

from typing import Dict, Optional

from fastapi import APIRouter, HTTPException, Query, UploadFile
from pydantic import BaseModel

from ..models.base import PaginatedResponse
from ..models.memo import Attachment


class ListAttachmentsResponse(PaginatedResponse):
    """List attachments response."""

    attachments: list[Attachment] = []


class CreateAttachmentRequest(BaseModel):
    """Create attachment request."""

    attachment: Attachment


class AttachmentStorage:
    """In-memory attachment storage for MVP."""

    def __init__(self) -> None:
        self.attachments: Dict[str, Attachment] = {}
        self.counter = 0

    def create_attachment(self, attachment: Attachment) -> Attachment:
        """Create a new attachment."""
        self.counter += 1
        attachment_id = str(self.counter)
        attachment.name = f"attachments/{attachment_id}"
        self.attachments[attachment_id] = attachment
        return attachment

    def get_attachment(self, attachment_id: str) -> Optional[Attachment]:
        """Get attachment by ID."""
        return self.attachments.get(attachment_id)

    def list_attachments(self, filter: Optional[str] = None) -> list[Attachment]:
        """List all attachments with optional filtering."""
        attachments = list(self.attachments.values())
        if filter:
            # Simple filter by filename
            attachments = [a for a in attachments if filter.lower() in a.filename.lower()]
        return attachments

    def delete_attachment(self, attachment_id: str) -> bool:
        """Delete attachment by ID."""
        if attachment_id in self.attachments:
            del self.attachments[attachment_id]
            return True
        return False


class AttachmentRouter:
    """Attachment API router handler."""

    def __init__(self) -> None:
        self.router = APIRouter()
        self.storage = AttachmentStorage()
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Configure attachment routes."""

        @self.router.get("/attachments", response_model=ListAttachmentsResponse)
        async def list_attachments(
            page_size: Optional[int] = Query(None, ge=1, le=1000),
            page_token: Optional[str] = Query(None),
            filter: Optional[str] = Query(None),
        ) -> ListAttachmentsResponse:
            """List attachments."""
            attachments = self.storage.list_attachments(filter)
            return ListAttachmentsResponse(attachments=attachments)

        @self.router.post("/attachments", response_model=Attachment)
        async def create_attachment(request: CreateAttachmentRequest) -> Attachment:
            """Create a new attachment."""
            return self.storage.create_attachment(request.attachment)

        @self.router.post("/attachments/upload", response_model=Attachment)
        async def upload_attachment(file: UploadFile) -> Attachment:
            """Upload attachment file."""
            content = await file.read()
            attachment = Attachment(
                filename=file.filename or "unknown",
                type=file.content_type or "application/octet-stream",
                content=content,
                size=len(content),
            )
            return self.storage.create_attachment(attachment)

        @self.router.get("/attachments/{attachment_id}", response_model=Attachment)
        async def get_attachment(attachment_id: str) -> Attachment:
            """Get attachment by ID."""
            attachment = self.storage.get_attachment(attachment_id)
            if not attachment:
                raise HTTPException(status_code=404, detail="Attachment not found")
            return attachment

        @self.router.delete("/attachments/{attachment_id}")
        async def delete_attachment(attachment_id: str) -> Dict[str, str]:
            """Delete attachment by ID."""
            success = self.storage.delete_attachment(attachment_id)
            if not success:
                raise HTTPException(status_code=404, detail="Attachment not found")
            return {"message": "Attachment deleted successfully"}

