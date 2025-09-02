"""
Attachments tests
"""
from __future__ import annotations

import io

import pytest


def test_list_attachments_empty(client):
    """Test listing attachments when none exist."""
    response = client.get("/api/v1/attachments")
    
    assert response.status_code == 200
    data = response.json()
    assert "attachments" in data
    assert data["attachments"] == []


def test_list_attachments_with_filter(client):
    """Test listing attachments with filter."""
    response = client.get("/api/v1/attachments?filter=test")
    
    assert response.status_code == 200
    data = response.json()
    assert "attachments" in data


def test_create_attachment(client):
    """Test creating attachment."""
    attachment_data = {
        "attachment": {
            "filename": "test.txt",
            "type": "text/plain",
            "content": b"test content"
        }
    }
    
    response = client.post("/api/v1/attachments", json=attachment_data)
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["filename"] == "test.txt"


def test_upload_attachment(client):
    """Test uploading attachment file."""
    files = {"file": ("test.txt", io.BytesIO(b"test content"), "text/plain")}
    response = client.post("/api/v1/attachments/upload", files=files)
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "test.txt"
    assert data["type"] == "text/plain"


def test_get_attachment(client):
    """Test getting specific attachment."""
    # Create attachment first
    attachment_data = {
        "attachment": {
            "filename": "get_test.txt",
            "type": "text/plain",
            "content": b"content"
        }
    }
    create_response = client.post("/api/v1/attachments", json=attachment_data)
    assert create_response.status_code == 200
    
    attachment_id = create_response.json()["name"].split("/")[-1]
    response = client.get(f"/api/v1/attachments/{attachment_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "get_test.txt"


def test_get_attachment_not_found(client):
    """Test getting non-existent attachment."""
    response = client.get("/api/v1/attachments/nonexistent")
    assert response.status_code == 404


def test_delete_attachment(client):
    """Test deleting attachment."""
    # Create attachment first
    attachment_data = {
        "attachment": {
            "filename": "delete_test.txt",
            "type": "text/plain",
            "content": b"content"
        }
    }
    create_response = client.post("/api/v1/attachments", json=attachment_data)
    assert create_response.status_code == 200
    
    attachment_id = create_response.json()["name"].split("/")[-1]
    response = client.delete(f"/api/v1/attachments/{attachment_id}")
    
    assert response.status_code == 200
    assert "message" in response.json()


def test_delete_attachment_not_found(client):
    """Test deleting non-existent attachment."""
    response = client.delete("/api/v1/attachments/nonexistent")
    assert response.status_code == 404