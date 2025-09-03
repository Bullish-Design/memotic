import os
import pytest
from memotic.cli.exec import run_cli_lines
import logging

logger = logging.getLogger(__name__)


SANDBOX_NAME = os.getenv("MEMOTIC_CLI_CONTAINER", "memotic-cli-sandbox")


def ensure_sandbox_running():
    # cheap check via `docker ps`; skip if unavailable
    import subprocess

    try:
        out = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
    except Exception:
        pytest.skip("Docker not available")
    if SANDBOX_NAME not in out.split():
        pytest.skip(f"Sandbox container '{SANDBOX_NAME}' is not running")


def test_stop_on_first_failure():
    logger.info(f"Testing stop on first failure behavior")
    ensure_sandbox_running()
    memo = """
    #cli echo first
    #cli false
    #cli echo never-reached
    """
    logger.info(f"  Memo content: \n{memo}")
    results = list(run_cli_lines(memo))
    logger.info(f"  Results: {results}")
    cmds = [c for c, *_ in results]
    logger.info(f"  Commands: {cmds}")
    assert cmds == ["echo first", "false"], "Should stop after the failing command"
    assert results[-1][1] != 0, "Second command should fail"


def test_bang_continues_on_error():
    logger.info(f"Testing !-suffixed commands continue on failure")
    ensure_sandbox_running()
    memo = """
    #cli echo first
    #cli! false
    #cli echo reached
    """
    logger.info(f"  Memo content:\n{memo}")
    results = list(run_cli_lines(memo))
    logger.info(f"  Results: {results}")
    cmds = [c for c, *_ in results]
    logger.info(f"  Commands: {cmds}")
    assert cmds == ["echo first", "false", "echo reached"], "Should continue despite failure due to #cli!"
    assert results[1][1] != 0 and results[2][1] == 0
