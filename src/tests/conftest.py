"""
Pytest configuration and shared fixtures
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.memotic import MemosAPI


@pytest.fixture
def api():
    """Create API instance."""
    return MemosAPI()


@pytest.fixture
def client(api):
    """Create test client."""
    return TestClient(api.app)


@pytest.fixture
def auth_headers(client):
    """Get authenticated headers."""
    # Sign in to get auth token (mock)
    response = client.post("/api/v1/auth/signin", json={
        "passwordCredentials": {
            "username": "admin",
            "password": "password"
        }
    })
    assert response.status_code == 200
    return {"Authorization": "Bearer mock-token"}


@pytest.fixture
def sample_user():
    """Sample user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "displayName": "Test User",
        "role": "USER"
    }


@pytest.fixture
def sample_memo():
    """Sample memo data."""
    return {
        "content": "# Test Memo\nThis is a test memo with **markdown**",
        "visibility": "PUBLIC",
        "state": "NORMAL"
    }


@pytest.fixture
def created_user(client, sample_user):
    """Create a user for testing."""
    response = client.post("/api/v1/users", json={"user": sample_user})
    assert response.status_code == 200
    return response.json()


@pytest.fixture
def created_memo(client, sample_memo):
    """Create a memo for testing."""
    response = client.post("/api/v1/memos", json={"memo": sample_memo})
    assert response.status_code == 200
    return response.json()