# src/tests/test_config_validation.py
from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from memotic.config import MemoticConfig, get_config, set_config, reset_config


class TestMemoticConfig:
    """Test configuration management."""

    def test_default_config(self):
        """Test default configuration values."""
        # Clear environment to test actual defaults
        with patch.dict("os.environ", {}, clear=True):
            config = MemoticConfig()

            assert config.host == "127.0.0.1"
            assert config.port == 8000
            assert config.container_image == "debian:bookworm-slim"
            assert config.container_timeout == 30
            assert config.max_comment_chars == 15000

    def test_environment_override(self):
        """Test environment variable overrides."""
        with patch.dict(
            "os.environ",
            {
                "MEMOTIC_HOST": "0.0.0.0",
                "MEMOTIC_PORT": "9000",
                "MEMOS_HOST": "memos-server",
                "MEMOS_PORT": "3232",
                "MEMOS_TOKEN": "secret-token",
                "MEMOTIC_CLI_TIMEOUT": "60",
            },
            clear=True,
        ):
            # Create config with empty defaults to test environment override
            config = MemoticConfig(
                host="", port=0, memos_api_host="", memos_api_port=0, memos_token="", container_timeout=0
            )

            assert config.host == "0.0.0.0"
            assert config.port == 9000
            assert config.memos_api_host == "memos-server"
            assert config.memos_api_port == 3232
            assert config.memos_token == "secret-token"
            assert config.container_timeout == 60

    def test_computed_properties(self):
        """Test computed configuration properties."""
        config = MemoticConfig()
        config.memos_api_host = "localhost"
        config.memos_api_port = 5232

        assert config.memos_api_url == "http://localhost:5232"
        assert "memotic-cli-" in config.default_container_name

    def test_has_api_config(self):
        """Test API configuration detection."""
        config = MemoticConfig()

        # No API config
        config.memos_api_host = ""
        config.memos_api_port = 0
        assert not config.has_api_config()

        # Has API config
        config.memos_api_host = "localhost"
        config.memos_api_port = 5232
        assert config.has_api_config()

    def test_validate_setup(self):
        """Test configuration validation."""
        config = MemoticConfig()

        # Mock project root to not exist
        with patch.object(config, "project_root", Path("/nonexistent")):
            issues = config.validate_setup()
            assert any("Project root does not exist" in issue for issue in issues)

    def test_environment_vars_property(self):
        """Test environment variables generation."""
        config = MemoticConfig()
        config.memos_api_host = "test-host"
        config.memos_api_port = 1234
        config.memos_token = "test-token"

        env_vars = config.environment_vars

        assert env_vars["MEMOS_HOST"] == "test-host"
        assert env_vars["MEMOS_PORT"] == "1234"
        assert env_vars["MEMOS_TOKEN"] == "test-token"
        assert env_vars["MEMOS_URL"] == "http://test-host:1234"

    def test_global_config_management(self):
        """Test global configuration singleton."""
        # Reset to clean state
        reset_config()

        # Get default config
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2  # Same instance

        # Set custom config
        custom_config = MemoticConfig(host="custom-host")
        set_config(custom_config)

        config3 = get_config()
        assert config3 is custom_config
        assert config3.host == "custom-host"

        # Reset again
        reset_config()
        config4 = get_config()
        assert config4 is not custom_config
