"""
Authentication tests
"""
from __future__ import annotations

import pytest


def test_signin_success(client):
    """Test successful authentication."""
    response = client.post("/api/v1/auth/signin", json={
        "passwordCredentials": {
            "username": "admin",
            "password": "password"
        }
    })
    
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert "lastAccessedAt" in data
    assert data["user"]["username"] == "admin"


def test_signin_invalid_credentials(client):
    """Test authentication with invalid credentials."""
    response = client.post("/api/v1/auth/signin", json={
        "passwordCredentials": {
            "username": "invalid",
            "password": "wrong"
        }
    })
    
    assert response.status_code == 401


def test_signin_no_credentials(client):
    """Test authentication without credentials."""
    response = client.post("/api/v1/auth/signin", json={})
    assert response.status_code == 400


def test_auth_status_authenticated(client, auth_headers):
    """Test auth status when authenticated."""
    response = client.get("/api/v1/auth/status")
    
    assert response.status_code == 200
    data = response.json()
    assert "user" in data
    assert "lastAccessedAt" in data


def test_signout(client, auth_headers):
    """Test signout functionality."""
    response = client.post("/api/v1/auth/signout")
    
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Signed out successfully"


def test_sso_not_implemented(client):
    """Test SSO authentication returns not implemented."""
    response = client.post("/api/v1/auth/signin", json={
        "ssoCredentials": {
            "idpId": "test",
            "code": "test",
            "redirectUri": "http://test.com"
        }
    })
    
    assert response.status_code == 501