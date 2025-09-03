# src/memotic/cli/exec.py
from __future__ import annotations

import logging
import re
from typing import Iterator, List, Tuple

from .models import parse_cli_command, get_safe_commands, CliCommand
from ..config import get_config
from ..container_manager import get_container_manager

logger = logging.getLogger(__name__)

CLI_LINE = re.compile(r"(?mi)^\s*#cli(?P<bang>!?)(?:[:\s]+)(?P<cmd>.+?)\s*$")


def extract_cli_oneliners(text: str) -> List[Tuple[str, bool]]:
    """Return (command, allow_fail) tuples parsed from memo content."""
    commands = []
    
    for m in CLI_LINE.finditer(text or ""):
        cmd = m.group("cmd").strip()
        if not cmd:
            continue
            
        allow_fail = bool(m.group("bang"))
        commands.append((cmd, allow_fail))
    
    if commands:
        logger.info(f"Found {len(commands)} CLI command(s) in memo content")
        for cmd, allow_fail in commands:
            fail_indicator = "!" if allow_fail else ""
            logger.debug(f"  #cli{fail_indicator}: {cmd}")
    
    return commands


def extract_cli_commands(text: str) -> List[CliCommand]:
    """Extract and parse CLI commands into CliCommand objects."""
    raw_commands = extract_cli_oneliners(text)
    safe_commands = get_safe_commands(raw_commands)
    
    if len(safe_commands) < len(raw_commands):
        blocked_count = len(raw_commands) - len(safe_commands)
        logger.warning(f"Blocked {blocked_count} unsafe commands")
    
    return safe_commands


def run_cli_lines(text: str) -> Iterator[Tuple[str, int, str, str, float | None]]:
    """
    Execute #cli one-liners using the container manager.
    Yields (cmd, exit_code, stdout, stderr, execution_time).
    """
    commands = extract_cli_commands(text)

    if not commands:
        logger.debug("No CLI commands found in content")
        return iter(())

    config = get_config()
    container_manager = get_container_manager()

    try:
        logger.info(f"Executing {len(commands)} CLI commands in container {config.default_container_name}")
        
        with container_manager.create_sandbox() as sandbox:
            for i, cmd_obj in enumerate(commands, 1):
                cmd = cmd_obj.get_sanitized_command()
                allow_fail = cmd_obj.allow_fail
                
                logger.debug(f"Executing command {i}/{len(commands)}: {cmd} (allow_fail={allow_fail})")
                logger.debug(f"Command type: {cmd_obj.__class__.__name__}")
                
                try:
                    result = sandbox.execute_shell(cmd)
                    execution_time = result.execution_time
                    
                    status = "OK" if result.exit_code == 0 else f"ERR({result.exit_code})"
                    logger.info(f"Command {i} completed: {status} in {execution_time:.2f}s")
                    
                    if result.exit_code != 0:
                        logger.warning(f"Command failed: {cmd}")
                        if result.stderr:
                            logger.debug(f"stderr: {result.stderr[:200]}...")
                    
                    yield (cmd, result.exit_code, result.stdout, result.stderr, execution_time)
                    
                    if result.exit_code != 0 and not allow_fail:
                        logger.warning(f"Stopping execution due to command failure (exit code {result.exit_code})")
                        break
                        
                except Exception as e:
                    logger.error(f"Exception executing command '{cmd}': {e}")
                    yield (cmd, -1, "", str(e), None)
                    if not allow_fail:
                        logger.warning("Stopping execution due to exception")
                        break

    except Exception as e:
        logger.error(f"Failed to create sandbox for CLI execution: {e}")
        if commands:
            first_cmd = commands[0].get_sanitized_command()
            yield (first_cmd, -1, "", f"Container setup failed: {e}", None)