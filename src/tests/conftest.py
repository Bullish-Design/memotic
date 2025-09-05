# src/tests/conftest.py
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

from memotic.config import MemoticConfig, reset_config
from memotic.base import Memo


@pytest.fixture(autouse=True)
def reset_global_config():
    """Reset global config before each test."""
    reset_config()
    yield
    reset_config()


@pytest.fixture
def mock_config():
    """Mock memotic configuration with test values."""
    config = MemoticConfig()
    config.memos_api_host = "localhost"
    config.memos_api_port = 5232
    config.memos_token = "test-token-123"
    config.container_name = "test-container"
    config.container_timeout = 10
    config.max_comment_chars = 1000
    return config


@pytest.fixture
def sample_memo():
    """Sample memo for testing."""
    return Memo(name="memos/123", content="Test memo content", visibility="PRIVATE", tags=["test", "cli"])


@pytest.fixture
def cli_memo():
    """Memo with CLI commands for testing."""
    content = """
    # Test CLI Commands
    
    #cli: echo "Hello World"
    #cli: ls -la
    #cli!: false  # This should not stop execution
    #cli: echo "Final command"
    """
    return Memo(name="memos/456", content=content, tags=["cli"])


@pytest.fixture
def mock_container_manager():
    """Mock container manager."""
    manager = MagicMock()
    manager.is_docker_available.return_value = True
    manager.container_exists.return_value = True
    manager.container_running.return_value = True
    manager.ensure_container.return_value = "test-container"

    # Mock sandbox creation
    mock_sandbox = MagicMock()
    mock_sandbox.__enter__.return_value = mock_sandbox
    mock_sandbox.__exit__.return_value = None
    manager.create_sandbox.return_value = mock_sandbox

    return manager


@pytest.fixture
def mock_memos_integration():
    """Mock memos integration."""
    integration = AsyncMock()

    # Mock successful comment creation
    mock_comment = MagicMock()
    mock_comment.name = "memos/789"
    integration.create_comment.return_value = mock_comment

    # Mock successful memo creation
    mock_memo = MagicMock()
    mock_memo.name = "memos/999"
    integration.create_memo.return_value = mock_memo

    integration.health_check.return_value = True

    return integration


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory structure."""
    project_root = tmp_path / "test_project"
    project_root.mkdir()

    # Create compose directory structure
    compose_dir = project_root / "src" / "examples" / "cli-sandbox"
    compose_dir.mkdir(parents=True)

    # Create mock files
    (compose_dir / "docker-compose.yaml").write_text("services:\n  cli:\n    image: test")
    (compose_dir / "Dockerfile").write_text("FROM python:3.11")

    return project_root


@pytest.fixture
def mock_subprocess_run():
    """Mock subprocess.run for container operations."""

    def _mock_run(cmd, **kwargs):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "mock output"
        result.stderr = ""
        return result

    return _mock_run
