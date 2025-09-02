"""
Memo tests
"""
from __future__ import annotations

import pytest


def test_create_memo(client, sample_memo):
    """Test memo creation."""
    response = client.post("/api/v1/memos", json={"memo": sample_memo})
    
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert data["content"] == sample_memo["content"]
    assert data["visibility"] == sample_memo["visibility"]


def test_create_memo_with_id(client, sample_memo):
    """Test memo creation with specific ID."""
    response = client.post("/api/v1/memos", json={
        "memo": sample_memo,
        "memoId": "custom-id"
    })
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "memos/custom-id"


def test_list_memos_empty(client):
    """Test listing memos when none exist."""
    response = client.get("/api/v1/memos")
    
    assert response.status_code == 200
    data = response.json()
    assert "memos" in data
    assert data["memos"] == []


def test_list_memos(client, created_memo):
    """Test listing memos."""
    response = client.get("/api/v1/memos")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["memos"]) >= 1
    assert data["memos"][0]["name"] == created_memo["name"]


def test_list_memos_with_filter(client, created_memo):
    """Test listing memos with filter."""
    response = client.get("/api/v1/memos?filter=markdown")
    
    assert response.status_code == 200
    data = response.json()
    assert len(data["memos"]) >= 1


def test_get_memo(client, created_memo):
    """Test getting specific memo."""
    memo_id = created_memo["name"].split("/")[-1]
    response = client.get(f"/api/v1/memos/{memo_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == created_memo["name"]


def test_get_memo_not_found(client):
    """Test getting non-existent memo."""
    response = client.get("/api/v1/memos/nonexistent")
    assert response.status_code == 404


def test_update_memo(client, created_memo):
    """Test updating memo."""
    memo_id = created_memo["name"].split("/")[-1]
    update_data = {
        "memo": {
            "content": "# Updated Memo\nThis has been updated",
            "pinned": True
        }
    }
    
    response = client.patch(f"/api/v1/memos/{memo_id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    assert data["content"] == update_data["memo"]["content"]
    assert data["pinned"] is True


def test_update_memo_not_found(client):
    """Test updating non-existent memo."""
    response = client.patch("/api/v1/memos/nonexistent", json={
        "memo": {"content": "test"}
    })
    assert response.status_code == 404


def test_delete_memo(client, created_memo):
    """Test deleting memo."""
    memo_id = created_memo["name"].split("/")[-1]
    response = client.delete(f"/api/v1/memos/{memo_id}")
    
    assert response.status_code == 200
    assert "message" in response.json()


def test_delete_memo_not_found(client):
    """Test deleting non-existent memo."""
    response = client.delete("/api/v1/memos/nonexistent")
    assert response.status_code == 404


def test_set_memo_attachments(client, created_memo):
    """Test setting memo attachments."""
    memo_id = created_memo["name"].split("/")[-1]
    attachments_data = {
        "attachments": [{
            "filename": "test.txt",
            "type": "text/plain",
            "content": "dGVzdA=="
        }]
    }
    
    response = client.patch(
        f"/api/v1/memos/{memo_id}/attachments",
        json=attachments_data
    )
    
    assert response.status_code == 200


def test_set_memo_relations(client, created_memo):
    """Test setting memo relations."""
    memo_id = created_memo["name"].split("/")[-1]
    relations_data = {
        "relations": [{
            "memo": {"name": created_memo["name"]},
            "relatedMemo": {"name": created_memo["name"]},
            "type": "REFERENCE"
        }]
    }
    
    response = client.patch(
        f"/api/v1/memos/{memo_id}/relations",
        json=relations_data
    )
    
    assert response.status_code == 200


def test_upsert_memo_reaction(client, created_memo):
    """Test upserting memo reaction."""
    memo_id = created_memo["name"].split("/")[-1]
    reaction_data = {
        "reaction": {
            "creator": "users/1",
            "contentType": "emoji",
            "content": "👍"
        }
    }
    
    response = client.patch(
        f"/api/v1/memos/{memo_id}/reactions",
        json=reaction_data
    )
    
    assert response.status_code == 200


def test_rename_memo_tag(client, created_memo):
    """Test renaming memo tags."""
    tag_data = {
        "oldTag": "oldtag",
        "newTag": "newtag"
    }
    
    response = client.patch("/api/v1/memos/-/tags:rename", json=tag_data)
    
    assert response.status_code == 200


def test_delete_memo_tag(client):
    """Test deleting memo tag."""
    response = client.delete("/api/v1/memos/-/tags/testtag")
    
    assert response.status_code == 200
    assert "message" in response.json()