"""
Storage implementations for Memotic
"""
from __future__ import annotations

from typing import Dict, Optional

from .models import (
    Attachment,
    Memo,
    User,
    UserAccessToken,
)


class MemoStorage:
    """In-memory memo storage."""
    
    def __init__(self) -> None:
        self.memos: Dict[str, Memo] = {}
        self.counter = 0
    
    def create(self, memo: Memo, memo_id: Optional[str] = None) -> Memo:
        """Create a new memo."""
        if memo_id is None:
            self.counter += 1
            memo_id = str(self.counter)
        
        memo.name = f"memos/{memo_id}"
        self.memos[memo_id] = memo
        return memo
    
    def get(self, memo_id: str) -> Optional[Memo]:
        """Get memo by ID."""
        return self.memos.get(memo_id)
    
    def list(self, filter_text: Optional[str] = None) -> list[Memo]:
        """List all memos with optional filtering."""
        memos = list(self.memos.values())
        if filter_text:
            memos = [
                m for m in memos
                if filter_text.lower() in m.content.lower()
            ]
        return memos
    
    def update(self, memo_id: str, memo: Memo) -> Optional[Memo]:
        """Update existing memo."""
        if memo_id not in self.memos:
            return None
        
        memo.name = f"memos/{memo_id}"
        self.memos[memo_id] = memo
        return memo
    
    def delete(self, memo_id: str) -> bool:
        """Delete memo by ID."""
        if memo_id in self.memos:
            del self.memos[memo_id]
            return True
        return False


class UserStorage:
    """In-memory user storage."""
    
    def __init__(self) -> None:
        self.users: Dict[str, User] = {}
        self.access_tokens: Dict[str, UserAccessToken] = {}
        self.counter = 0
    
    def create(self, user: User, user_id: Optional[str] = None) -> User:
        """Create a new user."""
        if user_id is None:
            self.counter += 1
            user_id = str(self.counter)
        
        user.name = f"users/{user_id}"
        self.users[user_id] = user
        return user
    
    def get(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)
    
    def list(self) -> list[User]:
        """List all users."""
        return list(self.users.values())
    
    def search(self, query: str) -> list[User]:
        """Search users by query."""
        query_lower = query.lower()
        return [
            user for user in self.users.values()
            if query_lower in user.username.lower()
            or (user.display_name and query_lower in user.display_name.lower())
            or (user.email and query_lower in user.email.lower())
        ]
    
    def update(self, user_id: str, user: User) -> Optional[User]:
        """Update existing user."""
        if user_id not in self.users:
            return None
        
        user.name = f"users/{user_id}"
        self.users[user_id] = user
        return user
    
    def delete(self, user_id: str) -> bool:
        """Delete user by ID."""
        if user_id in self.users:
            del self.users[user_id]
            return True
        return False


class AttachmentStorage:
    """In-memory attachment storage."""
    
    def __init__(self) -> None:
        self.attachments: Dict[str, Attachment] = {}
        self.counter = 0
    
    def create(self, attachment: Attachment) -> Attachment:
        """Create a new attachment."""
        self.counter += 1
        attachment_id = str(self.counter)
        attachment.name = f"attachments/{attachment_id}"
        self.attachments[attachment_id] = attachment
        return attachment
    
    def get(self, attachment_id: str) -> Optional[Attachment]:
        """Get attachment by ID."""
        return self.attachments.get(attachment_id)
    
    def list(self, filter_text: Optional[str] = None) -> list[Attachment]:
        """List all attachments with optional filtering."""
        attachments = list(self.attachments.values())
        if filter_text:
            attachments = [
                a for a in attachments
                if filter_text.lower() in a.filename.lower()
            ]
        return attachments
    
    def delete(self, attachment_id: str) -> bool:
        """Delete attachment by ID."""
        if attachment_id in self.attachments:
            del self.attachments[attachment_id]
            return True
        return False