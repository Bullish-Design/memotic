"""
Memotic - FastAPI Memos Library
"""
from __future__ import annotations

from .api import MemosAPI
from .models import Memo, User
from .storage import MemoStorage, UserStorage

__version__ = "0.1.0"
__all__ = ["MemosAPI", "Memo", "User", "MemoStorage", "UserStorage"]