"""
Activities tests
"""
from __future__ import annotations

import pytest


def test_list_activities_empty(client):
    """Test listing activities when none exist."""
    response = client.get("/api/v1/activities")
    
    assert response.status_code == 200
    data = response.json()
    assert "activities" in data
    assert data["activities"] == []


def test_list_activities_with_pagination(client):
    """Test listing activities with pagination parameters."""
    response = client.get("/api/v1/activities?pageSize=10&pageToken=test")
    
    assert response.status_code == 200
    data = response.json()
    assert "activities" in data