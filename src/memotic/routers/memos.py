"""
Memo router implementation
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ..models.memo import (
    CreateMemoRequest,
    DeleteMemoRequest,
    GetMemoRequest,
    ListMemosRequest,
    ListMemosResponse,
    Memo,
    RenameMemoTagBody,
    SetMemoAttachmentsBody,
    SetMemoRelationsBody,
    UpdateMemoRequest,
    UpsertMemoReactionBody,
)
from ..storage import MemoStorage


class MemoRouter:
    """Memo API router handler."""
    
    def __init__(self) -> None:
        self.router = APIRouter()
        self.storage = MemoStorage()
        self._setup_routes()
    
    def _setup_routes(self) -> None:
        """Configure memo routes."""
        
        @self.router.get("/memos", response_model=ListMemosResponse)
        async def list_memos(
            page_size: Optional[int] = Query(None, ge=1, le=1000),
            page_token: Optional[str] = Query(None),
            filter: Optional[str] = Query(None),
        ) -> ListMemosResponse:
            """List memos."""
            memos = self.storage.list(filter)
            return ListMemosResponse(memos=memos)
        
        @self.router.post("/memos", response_model=Memo)
        async def create_memo(request: CreateMemoRequest) -> Memo:
            """Create a new memo."""
            return self.storage.create(request.memo, request.memo_id)
        
        @self.router.get("/memos/{memo_id}", response_model=Memo)
        async def get_memo(memo_id: str) -> Memo:
            """Get memo by ID."""
            memo = self.storage.get(memo_id)
            if not memo:
                raise HTTPException(status_code=404, detail="Memo not found")
            return memo
        
        @self.router.patch("/memos/{memo_id}", response_model=Memo)
        async def update_memo(
            memo_id: str,
            request: UpdateMemoRequest
        ) -> Memo:
            """Update existing memo."""
            memo = self.storage.update(memo_id, request.memo)
            if not memo:
                raise HTTPException(status_code=404, detail="Memo not found")
            return memo
        
        @self.router.delete("/memos/{memo_id}")
        async def delete_memo(memo_id: str) -> Dict[str, str]:
            """Delete memo by ID."""
            success = self.storage.delete(memo_id)
            if not success:
                raise HTTPException(status_code=404, detail="Memo not found")
            return {"message": "Memo deleted successfully"}
        
        @self.router.patch("/memos/{memo_id}/attachments")
        async def set_memo_attachments(
            memo_id: str,
            body: SetMemoAttachmentsBody
        ) -> Dict[str, str]:
            """Set memo attachments."""
            memo = self.storage.get(memo_id)
            if not memo:
                raise HTTPException(status_code=404, detail="Memo not found")
            
            memo.attachments = body.attachments
            return {"message": "Attachments updated successfully"}
        
        @self.router.patch("/memos/{memo_id}/relations")
        async def set_memo_relations(
            memo_id: str,
            body: SetMemoRelationsBody
        ) -> Dict[str, str]:
            """Set memo relations."""
            memo = self.storage.get(memo_id)
            if not memo:
                raise HTTPException(status_code=404, detail="Memo not found")
            
            memo.relations = body.relations
            return {"message": "Relations updated successfully"}
        
        @self.router.patch("/memos/{memo_id}/reactions")
        async def upsert_memo_reaction(
            memo_id: str,
            body: UpsertMemoReactionBody
        ) -> Dict[str, str]:
            """Upsert memo reaction."""
            memo = self.storage.get(memo_id)
            if not memo:
                raise HTTPException(status_code=404, detail="Memo not found")
            
            if not memo.reactions:
                memo.reactions = []
            
            existing = next(
                (r for r in memo.reactions if r.creator == body.reaction.creator),
                None
            )
            if existing:
                existing.content = body.reaction.content
                existing.content_type = body.reaction.content_type
            else:
                memo.reactions.append(body.reaction)
            
            return {"message": "Reaction updated successfully"}
        
        @self.router.patch("/memos/-/tags:rename")
        async def rename_memo_tag(
            body: RenameMemoTagBody
        ) -> Dict[str, str]:
            """Rename memo tags across all memos."""
            for memo in self.storage.memos.values():
                if memo.tags:
                    memo.tags = [
                        body.new_tag if tag == body.old_tag else tag
                        for tag in memo.tags
                    ]
            return {"message": "Tags renamed successfully"}
        
        @self.router.delete("/memos/-/tags/{tag}")
        async def delete_memo_tag(
            tag: str,
            delete_related_memos: bool = Query(False)
        ) -> Dict[str, str]:
            """Delete memo tag across all memos."""
            memos_to_delete = []
            
            for memo_id, memo in self.storage.memos.items():
                if memo.tags and tag in memo.tags:
                    if delete_related_memos:
                        memos_to_delete.append(memo_id)
                    else:
                        memo.tags = [t for t in memo.tags if t != tag]
            
            for memo_id in memos_to_delete:
                self.storage.delete(memo_id)
            
            return {"message": f"Tag '{tag}' deleted successfully"}