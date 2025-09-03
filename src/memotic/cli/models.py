# src/memotic/cli/models.py
from __future__ import annotations

import re
import shlex
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Dict, List, Optional, Type

from pydantic import BaseModel, Field, model_validator


class CliCommand(BaseModel, ABC):
    """Base class for CLI command parsing and validation."""

    # Command pattern matching
    command_pattern: ClassVar[Optional[str]] = None
    command_prefix: ClassVar[Optional[str]] = None

    # Parsed command components
    raw_command: str = Field(description="Original command string")
    allow_fail: bool = Field(default=False, description="Whether command can fail without stopping execution")
    args: List[str] = Field(default_factory=list, description="Parsed command arguments")
    flags: Dict[str, Any] = Field(default_factory=dict, description="Parsed command flags")

    @classmethod
    def matches(cls, command: str) -> bool:
        """Check if this command class can handle the given command string."""
        if cls.command_prefix:
            return command.strip().startswith(cls.command_prefix)

        if cls.command_pattern:
            return bool(re.match(cls.command_pattern, command.strip()))

        return True  # Base class accepts any command

    @classmethod
    def parse_command(cls, raw_command: str, allow_fail: bool = False) -> CliCommand:
        """Parse a raw command string into a command instance."""
        return cls(raw_command=raw_command, allow_fail=allow_fail)

    @model_validator(mode="after")
    def parse_args(self) -> CliCommand:
        """Parse command arguments and flags."""
        try:
            parts = shlex.split(self.raw_command)
            if parts:
                self.args = parts[1:] if len(parts) > 1 else []
                self.flags = self._parse_flags(self.args)
        except ValueError:
            parts = self.raw_command.split()
            self.args = parts[1:] if len(parts) > 1 else []
            self.flags = {}

        return self

    def _parse_flags(self, args: List[str]) -> Dict[str, Any]:
        """Parse command-line flags from arguments."""
        flags = {}
        i = 0
        while i < len(args):
            arg = args[i]
            if arg.startswith("--"):
                if "=" in arg:
                    key, value = arg[2:].split("=", 1)
                    flags[key] = value
                else:
                    key = arg[2:]
                    if i + 1 < len(args) and not args[i + 1].startswith("-"):
                        flags[key] = args[i + 1]
                        i += 1
                    else:
                        flags[key] = True
            elif arg.startswith("-") and len(arg) > 1:
                for char in arg[1:]:
                    flags[char] = True
            i += 1
        return flags

    @abstractmethod
    def validate_command(self) -> List[str]:
        """Validate the command and return list of validation errors."""
        pass

    @abstractmethod
    def is_safe(self) -> bool:
        """Check if the command is safe to execute."""
        pass

    def get_sanitized_command(self) -> str:
        """Get the command string, potentially sanitized."""
        return self.raw_command


class GenericCliCommand(CliCommand):
    """Generic command handler that accepts any command."""

    DANGEROUS_PATTERNS: ClassVar[List[str]] = [
        r"rm\s+-rf\s*/",
        r"format\s+[a-z]:",
        r":\(\)\{.*\|.*&",  # Fork bomb
        r"dd\s+if=/dev/zero",
        r"chmod\s+777",
        r"sudo\s+",
        r"su\s+",
    ]

    def validate_command(self) -> List[str]:
        """Basic validation for generic commands."""
        errors = []
        if not self.raw_command.strip():
            errors.append("Empty command")
        return errors

    def is_safe(self) -> bool:
        """Check for obviously dangerous command patterns."""
        cmd_lower = self.raw_command.lower()
        return not any(re.search(pattern, cmd_lower) for pattern in self.DANGEROUS_PATTERNS)


class EchoCommand(CliCommand):
    """Handler for echo commands."""

    command_prefix: ClassVar[str] = "echo"

    message: Optional[str] = None

    @model_validator(mode="after")
    def extract_message(self) -> EchoCommand:
        """Extract the message from echo command."""
        if self.args:
            self.message = " ".join(self.args)
        return self

    def validate_command(self) -> List[str]:
        """Validate echo command."""
        return ["Echo command has no message"] if not self.message else []

    def is_safe(self) -> bool:
        """Echo commands are generally safe."""
        return True


class GitCommand(CliCommand):
    """Handler for git commands."""

    command_prefix: ClassVar[str] = "git"

    subcommand: Optional[str] = None

    @model_validator(mode="after")
    def extract_subcommand(self) -> GitCommand:
        """Extract git subcommand."""
        if self.args:
            self.subcommand = self.args[0]
        return self

    def validate_command(self) -> List[str]:
        """Validate git command."""
        return ["Git command missing subcommand"] if not self.subcommand else []

    def is_safe(self) -> bool:
        """Check if git command is safe."""
        dangerous_subcommands = ["rm", "clean", "reset --hard"]

        if self.subcommand in dangerous_subcommands:
            return False

        if "--force" in self.flags or "-f" in self.flags:
            return False

        return True


# Registry of command handlers
COMMAND_HANDLERS: List[Type[CliCommand]] = [
    EchoCommand,
    GitCommand,
    GenericCliCommand,  # Always last as fallback
]


def parse_cli_command(raw_command: str, allow_fail: bool = False) -> CliCommand:
    """Parse a raw CLI command string into the appropriate command model."""

    for handler_class in COMMAND_HANDLERS:
        if handler_class.matches(raw_command):
            try:
                command = handler_class.parse_command(raw_command, allow_fail)

                errors = command.validate_command()
                if errors:
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(f"Command validation errors: {errors}")

                return command

            except Exception as e:
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Handler {handler_class.__name__} failed to parse '{raw_command}': {e}")
                continue

    return GenericCliCommand.parse_command(raw_command, allow_fail)


def get_safe_commands(commands: List[tuple[str, bool]]) -> List[CliCommand]:
    """Parse and filter commands, returning only safe ones."""
    safe_commands = []

    for raw_command, allow_fail in commands:
        cmd = parse_cli_command(raw_command, allow_fail)

        if cmd.is_safe():
            safe_commands.append(cmd)
        else:
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"Blocked unsafe command: {raw_command}")

    return safe_commands

