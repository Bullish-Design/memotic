import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

from memotic import MemosClient, MemosAPIException
from memotic.models import *


@pytest.fixture
def mock_client():
    return MemosClient("https://memos.example.com", "test-token")


class TestMemosModels:
    """Test Pydantic models parsing"""

    def test_memo_model(self):
        memo_data = {
            "id": 123,
            "name": "memos/123",
            "uid": "1a2b3c4d",
            "rowStatus": "NORMAL",
            "creator": "users/1",
            "createTime": "2025-08-19T10:00:00Z",
            "updateTime": "2025-08-19T11:30:00Z",
            "displayTime": "2025-08-19T10:00:00Z",
            "content": "# Meeting Notes\n\nDiscussed project timeline.\n\n#work #meeting",
            "visibility": "PRIVATE",
            "pinned": False,
            "resources": [],
            "relations": [],
            "tags": ["work", "meeting"],
        }

        memo = Memo(**memo_data)
        assert memo.id == 123
        assert memo.visibility == Visibility.PRIVATE
        assert memo.tags == ["work", "meeting"]
        assert isinstance(memo.create_time, datetime)

    def test_user_model(self):
        user_data = {
            "id": 1,
            "name": "users/1",
            "username": "admin",
            "role": "HOST",
            "email": "admin@example.com",
            "nickname": "Administrator",
            "avatarUrl": "",
            "createTime": "2025-01-01T00:00:00Z",
            "updateTime": "2025-08-19T10:00:00Z",
        }

        user = User(**user_data)
        assert user.id == 1
        assert user.role == Role.HOST
        assert user.avatar_url == ""

    def test_resource_model(self):
        resource_data = {
            "id": 456,
            "name": "resources/456",
            "uid": "3c4d5e6f",
            "createTime": "2025-08-19T12:30:00Z",
            "filename": "screenshot.png",
            "type": "image/png",
            "size": 102400,
            "linkedMemos": [],
        }

        resource = Resource(**resource_data)
        assert resource.id == 456
        assert resource.type == "image/png"
        assert resource.linked_memos == []

    def test_system_info_model(self):
        system_data = {
            "version": "0.24.0",
            "mode": "prod",
            "allowSignUp": False,
            "disablePasswordLogin": False,
            "additionalScript": "",
            "customizedProfile": {
                "title": "Memos",
                "description": "A privacy-first, lightweight note-taking service",
                "logoUrl": "",
                "locale": "en",
            },
        }

        system_info = SystemInfo(**system_data)
        assert system_info.version == "0.24.0"
        assert system_info.allow_sign_up == False
        assert system_info.customized_profile.title == "Memos"


class TestMemosClient:
    """Test API client functionality"""

    @patch("httpx.Client")
    def test_client_initialization(self, mock_httpx):
        client = MemosClient("https://memos.example.com", "test-token")
        assert client.base_url == "https://memos.example.com"
        assert client.token == "test-token"

    @patch("httpx.Client")
    def test_get_auth_status(self, mock_httpx):
        # Mock successful response
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "user": {
                "id": 1,
                "name": "users/1",
                "username": "admin",
                "role": "HOST",
                "email": "admin@example.com",
                "nickname": "Administrator",
                "avatarUrl": "",
                "createTime": "2025-01-01T00:00:00Z",
                "updateTime": "2025-08-19T10:00:00Z",
            }
        }

        mock_httpx.return_value.request.return_value = mock_response

        client = MemosClient("https://memos.example.com", "test-token")
        auth_status = client.get_auth_status()

        assert isinstance(auth_status, AuthStatus)
        assert auth_status.user.username == "admin"
        assert auth_status.user.role == Role.HOST

    @patch("httpx.Client")
    def test_create_memo(self, mock_httpx):
        mock_response = Mock()
        mock_response.is_success = True
        mock_response.json.return_value = {
            "id": 124,
            "name": "memos/124",
            "uid": "2b3c4d5e",
            "rowStatus": "NORMAL",
            "creator": "users/1",
            "createTime": "2025-08-19T12:00:00Z",
            "updateTime": "2025-08-19T12:00:00Z",
            "displayTime": "2025-08-19T12:00:00Z",
            "content": "# Daily Standup\n\n- Completed: User authentication",
            "visibility": "PRIVATE",
            "pinned": False,
            "resources": [],
            "relations": [],
            "tags": ["daily", "work"],
        }

        mock_httpx.return_value.request.return_value = mock_response

        client = MemosClient("https://memos.example.com", "test-token")
        memo_request = CreateMemoRequest(
            content="# Daily Standup\n\n- Completed: User authentication",
            visibility=Visibility.PRIVATE,
        )

        memo = client.create_memo(memo_request)

        assert isinstance(memo, Memo)
        assert memo.id == 124
        assert memo.visibility == Visibility.PRIVATE
        assert memo.tags == ["daily", "work"]

    @patch("httpx.Client")
    def test_api_error_handling(self, mock_httpx):
        # Mock the error response
        error_response = {
            "error": {"code": "UNAUTHENTICATED", "message": "Invalid access token"}
        }

        mock_response = Mock()
        mock_response.is_success = False
        mock_response.status_code = 401
        mock_response.text = "Unauthorized"
        mock_response.json = Mock(return_value=error_response)

        mock_httpx.return_value.request.return_value = mock_response

        client = MemosClient("https://memos.example.com", "invalid-token")

        with pytest.raises(MemosAPIException) as exc_info:
            client.get_auth_status()

        assert exc_info.value.status_code == 401
        assert "Invalid access token" in str(exc_info.value)


class TestConnectionAndIntegration:
    """Integration tests - requires actual Memos instance"""

    @pytest.mark.integration
    def test_real_connection(self):
        """Test connection to real Memos instance - set environment variables"""
        base_url = os.getenv("MEMOS_URL", "http://localhost:5230")
        token = os.getenv("MEMOS_TOKEN")

        if not token:
            pytest.skip("MEMOS_TOKEN environment variable not set")

        client = MemosClient(base_url, token)

        try:
            # Test authentication
            auth_status = client.get_auth_status()
            assert isinstance(auth_status.user, User)

            # Test system info
            system_info = client.get_system_info()
            assert isinstance(system_info, SystemInfo)

            print(f"Connected to Memos v{system_info.version}")

        except MemosAPIException as e:
            # Skip test if server not available or wrong endpoint
            if e.status_code == 404:
                pytest.skip(
                    f"Memos server not available at {base_url} or wrong API version"
                )
            elif e.status_code in [401, 403]:
                pytest.skip(f"Authentication failed - check MEMOS_TOKEN")
            else:
                pytest.fail(f"Failed to connect to Memos: {e}")
        except Exception as e:
            pytest.skip(f"Connection failed - check MEMOS_URL: {e}")
        finally:
            client.close()


if __name__ == "__main__":
    # Run tests with: uv run pytest test_memos_api.py -v
    pytest.main(["-v", __file__])

