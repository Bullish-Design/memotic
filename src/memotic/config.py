# src/memotic/config.py
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, Optional
from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel, Field, computed_field


def find_project_root(start: Path | str = ".") -> Path:
    """Walk up to locate a project root (pyproject.toml or .git)."""
    p = Path(start).resolve()
    for parent in [p, *p.parents]:
        for marker in ("pyproject.toml", ".git"):
            if (parent / marker).exists():
                return parent
    return p


def slugify(name: str) -> str:
    """Convert string to slug format."""
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")


class MemoticConfig(BaseModel):
    """Centralized configuration for all Memotic components."""

    # Server settings
    host: str = Field(default="127.0.0.1", description="Server host")
    port: int = Field(default=8000, description="Server port")

    # Container settings
    container_name: Optional[str] = Field(default=None, description="Container name override")
    container_image: str = Field(default="debian:bookworm-slim", description="Base container image")
    container_workdir: str = Field(default="/workspace", description="Container working directory")
    container_shell: str = Field(default="/bin/bash", description="Container shell")
    container_timeout: int = Field(default=30, description="Command timeout in seconds")

    # Memos API settings
    api_base: Optional[str] = Field(default=None, description="Memos API base URL")
    api_token: Optional[str] = Field(default=None, description="Memos API token")

    # CLI settings
    max_comment_chars: int = Field(default=15000, description="Maximum comment size")

    # Project settings
    project_root: Path = Field(default_factory=lambda: find_project_root())

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context) -> None:
        """Load configuration from environment after initialization."""
        self.host = self.host or os.getenv("MEMOTIC_HOST", "127.0.0.1")
        self.port = self.port or int(os.getenv("MEMOTIC_PORT", "8000"))

        # if not self.container_name:
        #    self.container_name = os.getenv("MEMOTIC_CLI_CONTAINER")

        self.container_image = os.getenv("MEMOTIC_CLI_IMAGE", self.container_image)
        self.container_workdir = os.getenv("MEMOTIC_CLI_WORKDIR", self.container_workdir)
        self.container_shell = os.getenv("MEMOTIC_CLI_SHELL", self.container_shell)
        self.container_timeout = int(os.getenv("MEMOTIC_CLI_TIMEOUT", str(self.container_timeout)))

        if not self.api_base:
            # print(f"\nWarning: MEMOTIC_API_BASE not set, using environment variable if available.")
            self.api_base = os.getenv("MEMOTIC_API_BASE")
            # print(f"    Current MEMOTIC_API_BASE: {self.api_base}\n")
        if not self.api_token:
            # print(f"\nWarning: MEMOTIC_API_TOKEN not set, using environment variable if available.")
            self.api_token = os.getenv("MEMOTIC_API_TOKEN")
            # print(f"    Current MEMOTIC_API_TOKEN: {'*' * len(self.api_token) if self.api_token else None}\n")

        self.max_comment_chars = int(os.getenv("MEMOTIC_CLI_COMMENT_MAX", str(self.max_comment_chars)))

    @computed_field
    @property
    def default_container_name(self) -> str:
        """Generate default container name from project root."""
        if self.container_name:
            return self.container_name

        base = slugify(self.project_root.name)
        h = hashlib.sha1(str(self.project_root).encode()).hexdigest()[:7]
        return f"memotic-cli-{base}-{h}"

    @computed_field
    @property
    def environment_vars(self) -> Dict[str, str]:
        """Environment variables for container execution."""
        return {
            "MEMOTIC_CLI_CONTAINER": self.default_container_name,
            "MEMOTIC_CLI_WORKDIR": self.container_workdir,
            "MEMOTIC_CLI_SHELL": self.container_shell,
            "MEMOTIC_CLI_TIMEOUT": str(self.container_timeout),
            "MEMOTIC_API_BASE": self.api_base or "",
            "MEMOTIC_API_TOKEN": self.api_token or "",
            "MEMOTIC_CLI_COMMENT_MAX": str(self.max_comment_chars),
        }

    def has_api_config(self) -> bool:
        """Check if API configuration is available."""
        return bool(self.api_base and self.api_token)

    def validate_setup(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if not self.project_root.exists():
            issues.append(f"Project root does not exist: {self.project_root}")

        if not self.has_api_config():
            issues.append("Memos API not configured (missing MEMOTIC_API_BASE or MEMOTIC_API_TOKEN)")

        if self.container_timeout <= 0:
            issues.append(f"Invalid container timeout: {self.container_timeout}")

        return issues


# Global configuration instance
_config: Optional[MemoticConfig] = None


def get_config() -> MemoticConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = MemoticConfig()
    return _config


def set_config(config: MemoticConfig) -> None:
    """Set global configuration instance."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset global configuration for testing."""
    global _config
    _config = None

