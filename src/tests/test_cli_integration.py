# tests/test_cli_integration.py
import os
import subprocess
import pytest

from memotic.cli.handler import CliTagged
from memotic.base import MemoWebhookEvent

SANDBOX_NAME = os.getenv("MEMOTIC_CLI_CONTAINER", "memotic-cli-sandbox")


def ensure_sandbox_running():
    try:
        out = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
    except Exception:
        pytest.skip("Docker not available")
    if SANDBOX_NAME not in out.split():
        pytest.skip(f"Sandbox container '{SANDBOX_NAME}' is not running")


def mk_envelope(content: str, tags=("cli",)):
    # Your base class accepts multiple envelope shapes; this is the simplest.
    return {"memo": {"id": 1, "content": content, "tags": list(tags)}}


def test_stop_on_first_failure(capsys):
    ensure_sandbox_running()
    env = mk_envelope("""
#cli echo first
#cli false
#cli echo never-reached
""")
    evt = CliTagged.model_validate(env)  # base model normalization
    evt.run_cli()
    captured = capsys.readouterr().out
    assert "echo first" in captured
    assert "false" in captured
    assert "never-reached" not in captured


def test_bang_continues_on_error(capsys):
    ensure_sandbox_running()
    env = mk_envelope("""
#cli echo first
#cli! false
#cli echo reached
""")
    evt = CliTagged.model_validate(env)
    evt.run_cli()
    captured = capsys.readouterr().out
    assert "echo first" in captured
    assert "false" in captured
    assert "echo reached" in captured
