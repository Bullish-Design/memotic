# src/tests/test_container_management.py
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import subprocess

from memotic.container_manager import ContainerManager, ContainerStatus, get_container_manager
from memotic.config import MemoticConfig


class TestContainerManager:
    """Test container management functionality."""

    @pytest.fixture
    def mock_config(self):
        """Mock memotic config."""
        config = MemoticConfig()
        config.container_name = "test-container"
        config.compose_service = "test-service"
        return config

    @pytest.fixture
    def container_manager(self, mock_config):
        """Container manager instance."""
        return ContainerManager(mock_config)

    def test_docker_available(self, container_manager):
        """Test Docker availability check."""
        with patch.object(container_manager, "_run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert container_manager.is_docker_available() is True

            mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
            assert container_manager.is_docker_available() is False

    def test_container_exists(self, container_manager):
        """Test container existence check."""
        with patch.object(container_manager, "_compose_ps_name") as mock_ps:
            with patch.object(container_manager, "_exists") as mock_exists:
                # Container exists via compose
                mock_ps.return_value = "test-container"
                assert container_manager.container_exists() is True

                # Container exists via direct check
                mock_ps.return_value = None
                mock_exists.return_value = True
                assert container_manager.container_exists() is True

                # Container doesn't exist
                mock_exists.return_value = False
                assert container_manager.container_exists() is False

    def test_container_status(self, container_manager):
        """Test container status reporting."""
        with patch.object(container_manager, "is_docker_available") as mock_docker:
            with patch.object(container_manager, "container_exists") as mock_exists:
                with patch.object(container_manager, "container_running") as mock_running:
                    # Docker not available
                    mock_docker.return_value = False
                    status = container_manager.get_container_status()
                    assert not status.exists
                    assert not status.running
                    assert status.error == "Docker daemon not available"

                    # Container exists and running
                    mock_docker.return_value = True
                    mock_exists.return_value = True
                    mock_running.return_value = True

                    with patch.object(container_manager, "_health") as mock_health:
                        mock_health.return_value = "healthy"
                        status = container_manager.get_container_status()
                        assert status.exists
                        assert status.running
                        assert status.healthy

    def test_ensure_container_success(self, container_manager):
        """Test successful container creation."""
        with patch.object(container_manager, "is_docker_available", return_value=True):
            with patch.object(container_manager, "_pre_up_cleanup"):
                with patch.object(container_manager, "_compose") as mock_compose:
                    with patch.object(container_manager, "_wait_ready", return_value=True):
                        result = container_manager.ensure_container()
                        assert result == "test-container"
                        mock_compose.assert_called_once()

    def test_ensure_container_docker_unavailable(self, container_manager):
        """Test container creation when Docker unavailable."""
        with patch.object(container_manager, "is_docker_available", return_value=False):
            with pytest.raises(RuntimeError, match="Docker daemon not available"):
                container_manager.ensure_container()

    def test_ensure_container_health_timeout(self, container_manager):
        """Test container creation health timeout."""
        with patch.object(container_manager, "is_docker_available", return_value=True):
            with patch.object(container_manager, "_pre_up_cleanup"):
                with patch.object(container_manager, "_compose"):
                    with patch.object(container_manager, "_wait_ready", return_value=False):
                        with pytest.raises(RuntimeError, match="Failed to create healthy container"):
                            container_manager.ensure_container()

    def test_remove_container(self, container_manager):
        """Test container removal."""
        with patch.object(container_manager, "_compose") as mock_compose:
            with patch.object(container_manager, "_run") as mock_run:
                mock_compose.return_value = MagicMock(returncode=0)
                mock_run.return_value = MagicMock(returncode=0)

                result = container_manager.remove_container()
                assert result is True

    def test_create_sandbox(self, container_manager):
        """Test sandbox creation."""
        with patch.object(container_manager, "ensure_container", return_value="test-container"):
            with patch("memotic.container_manager.Sandbox") as mock_sandbox_class:
                mock_sandbox = MagicMock()
                mock_sandbox_class.return_value = mock_sandbox

                sandbox = container_manager.create_sandbox()
                assert sandbox == mock_sandbox

                # Verify sandbox config
                call_args = mock_sandbox_class.call_args[1]["config"]
                assert call_args.container == "test-container"

    def test_global_container_manager(self):
        """Test global container manager singleton."""
        from memotic.container_manager import reset_container_manager

        reset_container_manager()

        manager1 = get_container_manager()
        manager2 = get_container_manager()
        assert manager1 is manager2
