# src/memotic/cli/exec.py
from __future__ import annotations
import os
import re
import logging
from typing import Iterator, List, Tuple
from rich.console import Console

console = Console()

log = logging.getLogger(__name__)

# Lines that START with "#cli" or "#cli!" then ":" or whitespace then the command.
# Examples:
#   #cli echo "hi"
#   #cli: uname -a
#   #cli! false   -> continue past this failure
CLI_LINE = re.compile(r"(?mi)^\s*#cli(?P<bang>!?)(?:[:\s]+)(?P<cmd>.+?)\s*$")


def extract_cli_oneliners(text: str) -> List[Tuple[str, bool]]:
    """Return (command, allow_fail) tuples parsed from memo content."""
    console.print(f"[#cli] Found command(s): {text}")
    return [
        (m.group("cmd").strip(), bool(m.group("bang")))
        for m in CLI_LINE.finditer(text or "")
        if m.group("cmd") and m.group("cmd").strip()
    ]


def run_cli_lines(
    text: str,
    *,
    container: str | None = None,
    workdir: str | None = None,
    shell: str | None = None,
    timeout_s: int | None = None,
) -> Iterator[tuple[str, int, str, str, float | None]]:
    """
    Execute #cli one-liners inside a configured Docker container using solitary.

    Yields (cmd, exit_code, stdout, stderr, execution_time).
    Stops on first failure unless that line used #cli! (allow_fail=True).

    Note: solitary is imported lazily so the dependency stays optional.
    """
    try:
        from solitary import SandboxConfig, Sandbox
    except Exception as e:
        raise RuntimeError("solitary not available. Install memotic[cli] or `pip install solitary`.") from e

    commands = extract_cli_oneliners(text)

    if not commands:
        log.info("[#cli] No commands found in content.")
        return iter(())

    container = container or os.getenv("MEMOTIC_CLI_CONTAINER", "memotic-cli-sandbox")
    workdir = workdir or os.getenv("MEMOTIC_CLI_WORKDIR", "/workspace")
    timeout_s = int(timeout_s or os.getenv("MEMOTIC_CLI_TIMEOUT", "30"))
    shell = shell or os.getenv("MEMOTIC_CLI_SHELL", "/bin/bash")

    cfg = SandboxConfig(container=container, workdir=workdir, timeout=timeout_s, shell=shell)

    with Sandbox(config=cfg) as sb:
        for cmd, allow_fail in commands:
            res = sb.execute_shell(cmd)
            yield (cmd, res.exit_code, res.stdout, res.stderr, getattr(res, "execution_time", None))
            if res.exit_code != 0 and not allow_fail:
                break
