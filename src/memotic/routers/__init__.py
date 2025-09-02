"""
Memotic API routers
"""
from __future__ import annotations

from .activities import ActivityRouter
from .attachments import AttachmentRouter
from .auth import AuthRouter
from .memos import MemoRouter
from .users import UserRouter

__all__ = [
    "ActivityRouter",
    "AttachmentRouter", 
    "AuthRouter",
    "MemoRouter",
    "UserRouter",
]