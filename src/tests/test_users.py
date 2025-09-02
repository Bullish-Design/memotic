"""
User tests
"""
from __future__ import annotations

import pytest


def test_create_user(client, sample_user):
    """Test user creation."""
    response = client.post("/api/v1/users", json={"user": sample_user})
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["username"] == sample_user["username"]
    assert data["email"] == sample_user["email"]


def test_create_user_with_id(client, sample_user):
    """Test user creation with specific ID."""
    response = client.post("/api/v1/users", json={
        "user": sample_user,
        "userId": "custom-user-id"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "users/custom-user-id"


def test_list_users_empty(client):
    """Test listing users when none exist."""
    response = client.get("/api/v1/users")
    
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert isinstance(data["users"], list)


def test_list_users(client, created_user):
    """Test listing users."""
    response = client.get("/api/v1/users")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["users"]) >= 1


def test_get_user(client, created_user):
    """Test getting specific user."""
    user_id = created_user["name"].split("/")[-1]
    response = client.get(f"/api/v1/users/{user_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == created_user["name"]


def test_get_user_not_found(client):
    """Test getting non-existent user."""
    response = client.get("/api/v1/users/nonexistent")
    assert response.status_code == 404


def test_update_user(client, created_user):
    """Test updating user."""
    user_id = created_user["name"].split("/")[-1]
    update_data = {
        "user": {
            "username": "updated_user",
            "email": "updated@example.com",
            "displayName": "Updated User"
        }
    }
    
    response = client.patch(f"/api/v1/users/{user_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == update_data["user"]["username"]
    assert data["email"] == update_data["user"]["email"]


def test_update_user_not_found(client):
    """Test updating non-existent user."""
    response = client.patch("/api/v1/users/nonexistent", json={
        "user": {"username": "test"}
    })
    assert response.status_code == 404


def test_delete_user(client, created_user):
    """Test deleting user."""
    user_id = created_user["name"].split("/")[-1]
    response = client.delete(f"/api/v1/users/{user_id}")
    
    assert response.status_code == 200
    assert "message" in response.json()


def test_delete_user_not_found(client):
    """Test deleting non-existent user."""
    response = client.delete("/api/v1/users/nonexistent")
    assert response.status_code == 404


def test_search_users(client, created_user):
    """Test searching users."""
    response = client.get("/api/v1/users:search?query=testuser")
    
    assert response.status_code == 200
    data = response.json()
    assert "users" in data


def test_search_users_no_results(client):
    """Test searching users with no results."""
    response = client.get("/api/v1/users:search?query=nonexistent")
    
    assert response.status_code == 200
    data = response.json()
    assert data["users"] == []


def test_list_user_stats(client):
    """Test listing user statistics."""
    response = client.get("/api/v1/users:stats")
    
    assert response.status_code == 200
    data = response.json()
    assert "stats" in data


def test_list_user_access_tokens(client, created_user):
    """Test listing user access tokens."""
    user_id = created_user["name"].split("/")[-1]
    response = client.get(f"/api/v1/users/{user_id}/accessTokens")
    
    assert response.status_code == 200
    data = response.json()
    assert "accessTokens" in data


def test_create_user_access_token(client, created_user):
    """Test creating user access token."""
    user_id = created_user["name"].split("/")[-1]
    token_data = {
        "accessToken": {
            "accessToken": "test-token",
            "description": "Test token"
        }
    }
    
    response = client.post(
        f"/api/v1/users/{user_id}/accessTokens",
        json=token_data
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["accessToken"] == "test-token"


def test_create_user_access_token_user_not_found(client):
    """Test creating access token for non-existent user."""
    response = client.post("/api/v1/users/nonexistent/accessTokens", json={
        "accessToken": {"accessToken": "test-token"}
    })
    assert response.status_code == 404


def test_delete_user_access_token(client, created_user):
    """Test deleting user access token."""
    user_id = created_user["name"].split("/")[-1]
    
    # Create token first
    token_data = {
        "accessToken": {
            "accessToken": "delete-me-token",
            "description": "Token to delete"
        }
    }
    create_response = client.post(
        f"/api/v1/users/{user_id}/accessTokens",
        json=token_data
    )
    assert create_response.status_code == 200
    
    # Delete token
    response = client.delete(f"/api/v1/users/{user_id}/accessTokens/1")
    
    assert response.status_code == 200
    assert "message" in response.json()