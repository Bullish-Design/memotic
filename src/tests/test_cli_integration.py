# tests/test_cli_integration.py
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from io import StringIO
import sys

from memotic.cli.handler import CliTagged
from memotic.base import Memo


class TestCliIntegration:
    """Test CLI integration with proper async handling."""

    @pytest.mark.asyncio
    async def test_stop_on_first_failure(self, capsys):
        """Test that CLI execution stops on first failure (non-bang command)."""
        content = """
        Some memo content
        #cli: echo first
        #cli: false
        #cli: echo third
        """

        # Mock memo object
        memo = Memo(name="memos/123", content=content)
        evt = CliTagged(memo=memo)

        # Mock container execution
        with patch("memotic.cli.handler.run_cli_lines") as mock_run_cli:
            mock_run_cli.return_value = [
                ("echo first", 0, "first", "", 0.1),
                ("false", 1, "", "command failed", 0.1),
                # third command should not execute due to failure
            ]

            # Mock memos integration
            with patch("memotic.cli.handler.MemosIntegration") as mock_integration_class:
                mock_integration = AsyncMock()
                mock_integration_class.return_value.__aenter__.return_value = mock_integration

                await evt.run_cli()

        captured = capsys.readouterr()
        assert "echo first" in captured.out
        assert "[OK" in captured.out
        assert "false" in captured.out
        assert "[ERR(1)" in captured.out
        assert "echo third" not in captured.out  # Should not execute

    @pytest.mark.asyncio
    async def test_bang_continues_on_error(self, capsys):
        """Test that CLI execution continues on error with bang (!) commands."""
        content = """
        Some memo content
        #cli: echo first
        #cli!: false
        #cli: echo third
        """

        memo = Memo(name="memos/123", content=content)
        evt = CliTagged(memo=memo)

        with patch("memotic.cli.handler.run_cli_lines") as mock_run_cli:
            mock_run_cli.return_value = [
                ("echo first", 0, "first", "", 0.1),
                ("false", 1, "", "command failed", 0.1),
                ("echo third", 0, "third", "", 0.1),
            ]

            with patch("memotic.cli.handler.MemosIntegration") as mock_integration_class:
                mock_integration = AsyncMock()
                mock_integration_class.return_value.__aenter__.return_value = mock_integration

                await evt.run_cli()

        captured = capsys.readouterr()
        assert "echo first" in captured.out
        assert "false" in captured.out
        assert "echo third" in captured.out  # Should execute despite previous failure

    @pytest.mark.asyncio
    async def test_no_cli_commands(self, capsys):
        """Test memo with no CLI commands."""
        content = "Just a regular memo with no commands"

        memo = Memo(name="memos/123", content=content)
        evt = CliTagged(memo=memo)

        with patch("memotic.cli.handler.run_cli_lines") as mock_run_cli:
            mock_run_cli.return_value = []  # No commands found

            await evt.run_cli()

        captured = capsys.readouterr()
        assert "No CLI commands found" in captured.out

    @pytest.mark.asyncio
    async def test_memo_comment_creation(self):
        """Test that CLI results are posted as comments."""
        content = "#cli: echo hello"

        memo = Memo(name="memos/123", content=content)
        evt = CliTagged(memo=memo)

        with patch("memotic.cli.handler.run_cli_lines") as mock_run_cli:
            mock_run_cli.return_value = [
                ("echo hello", 0, "hello", "", 0.1),
            ]

            with patch("memotic.cli.handler.MemosIntegration") as mock_integration_class:
                mock_integration = AsyncMock()
                mock_memo_result = MagicMock()
                mock_memo_result.name = "memos/456"
                mock_integration.create_comment.return_value = mock_memo_result
                mock_integration_class.return_value.__aenter__.return_value = mock_integration

                await evt.run_cli()

        # Verify comment was created
        mock_integration.create_comment.assert_called_once()
        call_args = mock_integration.create_comment.call_args
        assert call_args[1]["parent_memo_name"] == "memos/123"
        assert "CLI Results" in call_args[1]["content"]
        assert "echo hello" in call_args[1]["content"]
        assert call_args[1]["visibility"] == "PRIVATE"

    @pytest.mark.asyncio
    async def test_missing_memo_name(self, capsys):
        """Test handling of memo without name."""
        content = "#cli: echo test"

        # Memo without name
        memo = Memo(content=content)
        evt = CliTagged(memo=memo)

        with patch("memotic.cli.handler.run_cli_lines") as mock_run_cli:
            mock_run_cli.return_value = [
                ("echo test", 0, "test", "", 0.1),
            ]

            await evt.run_cli()

        captured = capsys.readouterr()
        assert "cannot post a comment back" in captured.out

    @pytest.mark.asyncio
    async def test_api_config_missing(self, capsys):
        """Test handling when API config is missing."""
        content = "#cli: echo test"

        memo = Memo(name="memos/123", content=content)
        evt = CliTagged(memo=memo)

        with patch("memotic.cli.handler.run_cli_lines") as mock_run_cli:
            mock_run_cli.return_value = [
                ("echo test", 0, "test", "", 0.1),
            ]

            with patch("memotic.cli.handler.get_config") as mock_get_config:
                mock_config = MagicMock()
                mock_config.has_api_config.return_value = False
                mock_get_config.return_value = mock_config

                await evt.run_cli()

        captured = capsys.readouterr()
        assert "API configuration not available" in captured.out
