"""
Authentication router implementation
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..models.user import User


class PasswordCredentials(BaseModel):
    """Password authentication credentials."""

    username: str
    password: str


class SSOCredentials(BaseModel):
    """SSO authentication credentials."""

    idp_id: str
    code: str
    redirect_uri: str


class CreateSessionRequest(BaseModel):
    """Create session request."""

    password_credentials: Optional[PasswordCredentials] = None
    sso_credentials: Optional[SSOCredentials] = None


class CreateSessionResponse(BaseModel):
    """Create session response."""

    user: User
    last_accessed_at: datetime


class GetCurrentSessionResponse(BaseModel):
    """Get current session response."""

    user: User
    last_accessed_at: datetime


class AuthStorage:
    """In-memory auth storage for MVP."""

    def __init__(self) -> None:
        self.sessions: Dict[str, CreateSessionResponse] = {}
        # Mock user for testing
        self.mock_user = User(name="users/1", username="admin", email="admin@example.com", display_name="Admin User")

    def authenticate(self, credentials: PasswordCredentials) -> Optional[CreateSessionResponse]:
        """Authenticate user with password."""
        # Simple mock authentication for MVP
        if credentials.username == "admin" and credentials.password == "password":
            session = CreateSessionResponse(user=self.mock_user, last_accessed_at=datetime.now())
            self.sessions["mock-session"] = session
            return session
        return None

    def get_current_session(self) -> Optional[GetCurrentSessionResponse]:
        """Get current session."""
        # Return mock session for MVP
        if "mock-session" in self.sessions:
            session = self.sessions["mock-session"]
            return GetCurrentSessionResponse(user=session.user, last_accessed_at=session.last_accessed_at)
        return None


class AuthRouter:
    """Authentication API router handler."""

    def __init__(self) -> None:
        self.router = APIRouter()
        self.storage = AuthStorage()
        self._setup_routes()

    def _setup_routes(self) -> None:
        """Configure auth routes."""

        @self.router.post("/auth/signin", response_model=CreateSessionResponse)
        async def create_session(request: CreateSessionRequest) -> CreateSessionResponse:
            """Create authentication session."""
            if request.password_credentials:
                session = self.storage.authenticate(request.password_credentials)
                if session:
                    return session
                raise HTTPException(status_code=401, detail="Invalid credentials")

            if request.sso_credentials:
                # Mock SSO for MVP
                raise HTTPException(status_code=501, detail="SSO not implemented in MVP")

            raise HTTPException(status_code=400, detail="No credentials provided")

        @self.router.get("/auth/status", response_model=GetCurrentSessionResponse)
        async def get_auth_status() -> GetCurrentSessionResponse:
            """Get current authentication status."""
            session = self.storage.get_current_session()
            if not session:
                raise HTTPException(status_code=401, detail="Not authenticated")
            return session

        @self.router.post("/auth/signout")
        async def sign_out() -> Dict[str, str]:
            """Sign out current session."""
            # Clear mock session
            self.storage.sessions.clear()
            return {"message": "Signed out successfully"}

