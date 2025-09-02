"""
Memotic API application
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings

from .routers.activities import ActivityRouter
from .routers.attachments import AttachmentRouter
from .routers.auth import AuthRouter
from .routers.memos import MemoRouter
from .routers.users import UserRouter


class AppSettings(BaseSettings):
    """Application settings configuration."""

    host: str = "tower"
    port: int = 5232
    debug: bool = True
    api_prefix: str = "/api/v1"
    cors_origins: list[str] = ["http://tower:3000", "http://tower:8080"]

    class Config:
        env_file = ".env"
        extra = "ignore"


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager."""
    # Startup logic here if needed
    yield
    # Shutdown logic here if needed


class MemosAPI:
    """Main Memos API application class."""

    def __init__(self) -> None:
        self.settings = AppSettings()
        self.app = self._create_app()
        self._setup_middleware()
        self._setup_routers()

    def _create_app(self) -> FastAPI:
        """Create FastAPI application instance."""
        return FastAPI(
            title="Memos API",
            description="FastAPI implementation of Memos API",
            version="0.1.0",
            debug=self.settings.debug,
            lifespan=lifespan,
        )

    def _setup_middleware(self) -> None:
        """Configure application middleware."""
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=self.settings.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _setup_routers(self) -> None:
        """Register API route handlers."""
        prefix = self.settings.api_prefix

        # Create router instances
        activity_router = ActivityRouter()
        attachment_router = AttachmentRouter()
        auth_router = AuthRouter()
        memo_router = MemoRouter()
        user_router = UserRouter()

        # Register routers
        self.app.include_router(activity_router.router, prefix=prefix, tags=["activities"])
        self.app.include_router(attachment_router.router, prefix=prefix, tags=["attachments"])
        self.app.include_router(auth_router.router, prefix=prefix, tags=["auth"])
        self.app.include_router(memo_router.router, prefix=prefix, tags=["memos"])
        self.app.include_router(user_router.router, prefix=prefix, tags=["users"])

