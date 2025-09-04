# src/memotic/config.py
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Dict, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field, computed_field

load_dotenv()


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

    # Compose settings
    compose_service: str = Field(default="cli", description="Compose service name for the sandbox")

    # Memos API settings - Simplified for memos-api integration
    memos_api_host: str = Field(default="localhost", description="Memos API host")
    memos_api_port: int = Field(default=5232, description="Memos API port")
    memos_token: Optional[str] = Field(default=None, description="Memos API token")

    # CLI settings
    max_comment_chars: int = Field(default=15000, description="Maximum comment size")

    # Project settings
    project_root: Path = Field(default_factory=lambda: find_project_root())

    model_config = {"arbitrary_types_allowed": True}

    def model_post_init(self, __context) -> None:
        """Load configuration from environment after initialization."""
        self.host = self.host or os.getenv("MEMOTIC_HOST", "127.0.0.1")
        self.port = self.port or int(os.getenv("MEMOTIC_PORT", "8000"))

        # Container settings
        self.container_name = os.getenv("MEMOTIC_CLI_CONTAINER", self.container_name)
        self.container_image = os.getenv("MEMOTIC_CLI_IMAGE", self.container_image)
        self.container_workdir = os.getenv("MEMOTIC_CLI_WORKDIR", self.container_workdir)
        self.container_shell = os.getenv("MEMOTIC_CLI_SHELL", self.container_shell)
        self.container_timeout = int(os.getenv("MEMOTIC_CLI_TIMEOUT", str(self.container_timeout)))

        # Compose overrides
        self.compose_service = os.getenv("MEMOTIC_COMPOSE_SERVICE", self.compose_service)

        # Memos API settings - Simplified
        self.memos_api_host = os.getenv("MEMOS_HOST", self.memos_api_host)
        self.memos_api_port = int(os.getenv("MEMOS_PORT", str(self.memos_api_port)))

        self.max_comment_chars = int(os.getenv("MEMOTIC_CLI_COMMENT_MAX", str(self.max_comment_chars)))
        self.memos_token = os.getenv("MEMOS_TOKEN", self.memos_token or "")

    @computed_field
    @property
    def default_container_name(self) -> str:
        """Generate default container name from project root, unless overridden."""
        if self.container_name:
            return self.container_name
        base = slugify(self.project_root.name)
        h = hashlib.sha1(str(self.project_root).encode()).hexdigest()[:7]
        return f"memotic-cli-{base}-{h}"

    @computed_field
    @property
    def memos_api_url(self) -> str:
        """Generate Memos API URL from host and port."""
        return f"http://{self.memos_api_host}:{self.memos_api_port}"

    # --- Compose-aware paths (derived from project_root) ---
    @computed_field
    @property
    def compose_dir(self) -> Path:
        """Directory containing Dockerfile and docker-compose.yaml for the CLI sandbox."""
        return self.project_root / "src" / "examples" / "cli-sandbox"

    @computed_field
    @property
    def compose_file(self) -> Path:
        return self.compose_dir / "docker-compose.yaml"

    @computed_field
    @property
    def dockerfile_path(self) -> Path:
        return self.compose_dir / "Dockerfile"

    @computed_field
    @property
    def environment_vars(self) -> Dict[str, str]:
        """Environment variables for container/compose execution."""
        return {
            "MEMOTIC_CLI_CONTAINER": self.default_container_name,
            "MEMOTIC_CLI_WORKDIR": self.container_workdir,
            "MEMOTIC_CLI_SHELL": self.container_shell,
            "MEMOTIC_CLI_TIMEOUT": str(self.container_timeout),
            "MEMOTIC_CLI_COMMENT_MAX": str(self.max_comment_chars),
            # compose file uses these:
            "PROJECT_ROOT": str(self.project_root),
            "WORKDIR": self.container_workdir,
            # Memos API settings
            "MEMOS_HOST": self.memos_api_host,
            "MEMOS_PORT": str(self.memos_api_port),
            "MEMOS_URL": self.memos_api_url,
            "MEMOS_TOKEN": self.memos_token,
        }

    def has_api_config(self) -> bool:
        """Check if Memos API configuration is available."""
        return bool(self.memos_api_host and self.memos_api_port)

    def validate_setup(self) -> list[str]:
        """Validate configuration and return list of issues."""
        issues = []

        if not self.project_root.exists():
            issues.append(f"Project root does not exist: {self.project_root}")

        if not self.compose_file.exists():
            issues.append(f"Compose file not found: {self.compose_file}")
        if not self.dockerfile_path.exists():
            issues.append(f"Dockerfile not found: {self.dockerfile_path}")

        if not self.has_api_config():
            issues.append("Memos API not configured (missing MEMOS_HOST or MEMOS_PORT)")

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
