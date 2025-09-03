# src/memotic/container_manager.py
from __future__ import annotations

import logging
import os
import subprocess
import time
from typing import Optional

from pydantic import BaseModel

from .config import MemoticConfig, get_config
from .dependencies import require_solitary

try:
    from solitary import SandboxConfig, Sandbox
except ImportError as e:
    raise ImportError("solitary is required: pip install solitary") from e

logger = logging.getLogger(__name__)


class ContainerStatus(BaseModel):
    name: str
    exists: bool = False
    running: bool = False
    healthy: bool = False
    error: Optional[str] = None


class ContainerManager:
    """Manages the CLI sandbox via docker compose."""

    def __init__(self, config: Optional[MemoticConfig] = None):
        self.config = config or get_config()

    # -------- docker helpers --------
    def _run(self, cmd: list[str], check: bool = True, timeout: int = 30) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Command failed: {' '.join(cmd)}: {e.stderr.strip()}")
            raise
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Command timed out: {' '.join(cmd)}")
        except FileNotFoundError:
            raise RuntimeError(f"{cmd[0]} not found in PATH.")

    def is_docker_available(self) -> bool:
        try:
            self._run(["docker", "version"], check=True)
            return True
        except Exception as e:
            logger.debug(f"Docker not available: {e}")
            return False

    # ---- inspect helpers ----
    def _inspect_fmt(self, name: str, fmt: str) -> Optional[str]:
        cp = self._run(["docker", "inspect", "-f", fmt, name], check=False)
        if cp.returncode != 0:
            return None
        return cp.stdout.strip()

    def _exists(self, name: str) -> bool:
        return self._inspect_fmt(name, "{{.Id}}") is not None

    def _running(self, name: str) -> bool:
        return self._inspect_fmt(name, "{{.State.Running}}") == "true"

    def _health(self, name: str) -> Optional[str]:
        # returns "healthy" | "unhealthy" | "starting" | "none" | None
        out = self._inspect_fmt(name, "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}")
        return out

    def _docker_exec_ok(self, name: str, cmd: str) -> bool:
        # Use shell for parity with our runtime
        cp = self._run(["docker", "exec", name, "bash", "-lc", cmd], check=False)
        return cp.returncode == 0

    # -------- compose helpers --------
    def _compose_env(self) -> dict:
        env = os.environ.copy()
        env.update(self.config.environment_vars)
        return env

    def _compose_cmd(self, *args: str) -> list[str]:
        return ["docker", "compose", "-f", str(self.config.compose_file), *args]

    def _compose(self, *args: str, check: bool = True, timeout: int = 120) -> subprocess.CompletedProcess:
        return self._run(self._compose_cmd(*args), check=check, timeout=timeout)

    def _compose_ps_name(self) -> Optional[str]:
        cp = self._run(self._compose_cmd("ps", "-q", self.config.compose_service), check=False)
        cid = cp.stdout.strip()
        if not cid:
            return None
        name = self._run(["docker", "inspect", "-f", "{{.Name}}", cid], check=False).stdout.strip().lstrip("/")
        return name or None

    # -------- status & lifecycle --------
    def container_exists(self, name: Optional[str] = None) -> bool:
        cname = name or self.config.default_container_name
        return (self._compose_ps_name() is not None) or self._exists(cname)

    def container_running(self, name: Optional[str] = None) -> bool:
        cname = name or self.config.default_container_name
        compose_name = self._compose_ps_name() or cname
        return self._running(compose_name)

    def get_container_status(self, name: Optional[str] = None) -> ContainerStatus:
        cname = name or self.config.default_container_name
        status = ContainerStatus(name=cname)
        try:
            if not self.is_docker_available():
                status.error = "Docker daemon not available"
                return status
            status.exists = self.container_exists(cname)
            status.running = self.container_running(cname) if status.exists else False
            if status.running:
                # If there's a healthcheck, honor it; otherwise rely on exec probe
                h = self._health(cname)
                if h in ("healthy", "none"):
                    status.healthy = True
                elif h == "starting":
                    status.healthy = False
                else:
                    status.healthy = False
        except Exception as e:
            status.error = str(e)
        return status

    def _pre_up_cleanup(self) -> None:
        cname = self.config.default_container_name
        # Remove conflicting container name regardless of provenance
        self._run(["docker", "rm", "-f", cname], check=False)

    def _wait_ready(self, name: str, timeout_s: int = 45) -> bool:
        """Wait for Running + (healthy OR no healthcheck). Then exec quick probe."""
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            if not self._running(name):
                time.sleep(0.5)
                continue
            h = self._health(name)
            if h in ("healthy", "none"):
                # final exec probe
                if self._docker_exec_ok(name, "echo health_check"):
                    return True
            time.sleep(0.5)
        return False

    def ensure_container(self, name: Optional[str] = None) -> str:
        if not self.is_docker_available():
            raise RuntimeError("Docker daemon not available. Please start Docker.")

        cname = name or self.config.default_container_name

        # Cleanup any same-named legacy container before starting
        self._pre_up_cleanup()

        # Compose up
        logger.info(f"Starting compose service '{self.config.compose_service}' from {self.config.compose_file}")
        self._compose("up", "-d", "--build", "--remove-orphans", self.config.compose_service)

        # Wait for health + quick exec probe
        if not self._wait_ready(cname, timeout_s=45):
            raise RuntimeError(f"Failed to create healthy container: {cname}")

        return cname

    def remove_container(self, name: Optional[str] = None) -> bool:
        ok = True
        # Bring down compose project (ignore errors if not present)
        self._compose("down", "--remove-orphans", check=False)
        # Remove any same-named container regardless of source
        cname = name or self.config.default_container_name
        cp = self._run(["docker", "rm", "-f", cname], check=False)
        ok = ok and (cp.returncode in (0, 1))
        # Best-effort network cleanup
        self._run(["docker", "network", "rm", f"{self.config.compose_dir.name}_default"], check=False)
        return ok

    def create_sandbox(self, container_name: Optional[str] = None) -> Sandbox:
        """Return a Solitary sandbox for actual workload execution."""
        require_solitary()
        cname = self.ensure_container(container_name)
        return Sandbox(
            config=SandboxConfig(
                container=cname,
                workdir=self.config.container_workdir,
                timeout=self.config.container_timeout,
                shell=self.config.container_shell,
            )
        )


# Global container manager instance
_container_manager: Optional[ContainerManager] = None


def get_container_manager() -> ContainerManager:
    """Get global container manager instance."""
    global _container_manager
    if _container_manager is None:
        _container_manager = ContainerManager()
    return _container_manager


def set_container_manager(manager: ContainerManager) -> None:
    """Set global container manager instance."""
    global _container_manager
    _container_manager = manager


def reset_container_manager() -> None:
    """Reset global container manager for testing."""
    global _container_manager
    _container_manager = None

