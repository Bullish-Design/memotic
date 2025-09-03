# src/memotic/cli/__init__.py
from __future__ import annotations

from .exec import extract_cli_oneliners, extract_cli_commands, run_cli_lines
from .handler import CliTagged
from .models import (
    CliCommand,
    GenericCliCommand,
    EchoCommand,
    GitCommand,
    parse_cli_command,
    get_safe_commands,
    COMMAND_HANDLERS
)

__all__ = [
    # Execution functions
    "extract_cli_oneliners",
    "extract_cli_commands", 
    "run_cli_lines",
    
    # Handler class
    "CliTagged",
    
    # Command models
    "CliCommand",
    "GenericCliCommand",
    "EchoCommand",
    "GitCommand",
    
    # Utility functions
    "parse_cli_command",
    "get_safe_commands",
    
    # Registry
    "COMMAND_HANDLERS"
]