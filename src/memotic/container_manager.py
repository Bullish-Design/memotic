# src/memotic/container_manager.py
from __future__ import annotations

import logging
import subprocess
import time
from typing import Optional

from pydantic import BaseModel

from .config import MemoticConfig, get_config
from .dependencies import require_solitary

# Import solitary components with error handling
try:
    from solitary import SandboxConfig, Sandbox
    from solitary.exceptions import ContainerNotFoundError, SandboxError
except ImportError as e:
    raise ImportError(f"solitary is required: pip install solitary") from e

logger = logging.getLogger(__name__)


class ContainerStatus(BaseModel):
    """Container status information."""

    name: str
    exists: bool = False
    running: bool = False
    healthy: bool = False
    error: Optional[str] = None


class ContainerManager:
    """Manages Docker containers for CLI execution."""

    def __init__(self, config: Optional[MemoticConfig] = None):
        self.config = config or get_config()

    def _run_docker_cmd(self, cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Run docker command and return result."""
        try:
            result = subprocess.run(
                cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30
            )
            return result
        except subprocess.CalledProcessError as e:
            logger.error(f"Docker command failed: {' '.join(cmd)}: {e.stderr}")
            raise
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"Docker command timed out: {' '.join(cmd)}")
        except FileNotFoundError:
            raise RuntimeError("Docker not found. Please ensure Docker is installed and in PATH.")

    def is_docker_available(self) -> bool:
        """Check if Docker daemon is running."""
        try:
            self._run_docker_cmd(["docker", "version"], check=True)
            return True
        except Exception as e:
            logger.debug(f"Docker not available: {e}")
            return False

    def container_exists(self, name: str) -> bool:
        """Check if container exists."""
        try:
            result = self._run_docker_cmd(
                ["docker", "ps", "-a", "--format", "{{.Names}}", "--filter", f"name={name}"], check=False
            )
            return name in result.stdout.splitlines()
        except Exception:
            return False

    def container_running(self, name: str) -> bool:
        """Check if container is running."""
        try:
            result = self._run_docker_cmd(["docker", "inspect", "-f", "{{.State.Running}}", name], check=False)
            return result.stdout.strip() == "true"
        except Exception:
            return False

    def get_container_status(self, name: Optional[str] = None) -> ContainerStatus:
        """Get comprehensive container status."""
        container_name = name or self.config.default_container_name

        status = ContainerStatus(name=container_name)

        try:
            if not self.is_docker_available():
                status.error = "Docker daemon not available"
                return status

            status.exists = self.container_exists(container_name)
            status.running = self.container_running(container_name) if status.exists else False

            # Check health by trying to execute a simple command
            if status.running:
                status.healthy = self._test_container_health(container_name)

        except Exception as e:
            status.error = str(e)
            logger.error(f"Error checking container status: {e}")

        return status

    def _test_container_health(self, container_name: str) -> bool:
        """Test if container is healthy by executing a simple command."""
        try:
            print(f"    Testing health of container: {container_name}, workdir: {self.config.container_workdir}")
            sandbox_config = SandboxConfig(container=container_name, workdir=self.config.container_workdir, timeout=5)
            print(f"      Sandbox config: {sandbox_config}")
            with Sandbox(config=sandbox_config) as sandbox:
                result = sandbox.execute("echo 'health_check'")
                print(f"        Health check result: {result}")
                return result.success and "health_check" in result.stdout
        except Exception as e:
            logger.debug(f"Container health check failed: {e}")
            return False

    def ensure_container(self, name: Optional[str] = None) -> str:
        """Ensure container exists and is running."""
        if not self.is_docker_available():
            raise RuntimeError("Docker daemon not available. Please start Docker.")

        container_name = name or self.config.default_container_name

        # Check current status
        status = self.get_container_status(container_name)

        if status.error:
            raise RuntimeError(f"Container status check failed: {status.error}")

        if status.healthy:
            logger.debug(f"Container {container_name} is already healthy")
            return container_name

        # Try to start if exists but not running
        if status.exists and not status.running:
            logger.info(f"Starting existing container: {container_name}")
            try:
                self._run_docker_cmd(["docker", "start", container_name])

                # Wait for container to be ready
                time.sleep(2)

                # Verify it's now healthy
                if self._test_container_health(container_name):
                    logger.info(f"Container {container_name} started successfully")
                    return container_name
                else:
                    logger.warning(f"Container {container_name} started but not healthy, recreating...")
                    self.remove_container(container_name)
            except Exception as e:
                logger.warning(f"Failed to start container {container_name}: {e}")
                self.remove_container(container_name)

        # Create new container if needed
        if not self.get_container_status(container_name).healthy:
            logger.info(f"Creating new container: {container_name}")
            self._create_container(container_name)

        # Final health check
        final_status = self.get_container_status(container_name)
        if not final_status.healthy:
            raise RuntimeError(f"Failed to create healthy container: {container_name} (status: {final_status})")

        logger.info(f"Container {container_name} is ready")
        return container_name

    def _create_container(self, name: str) -> None:
        """Create and start a new container."""
        # Ensure old container is removed
        self.remove_container(name)

        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "--memory",
            "512m",  # Resource limits
            "--cpus",
            "1.0",
            "-w",
            self.config.container_workdir,
            "-v",
            f"{str(self.config.project_root)}:{self.config.container_workdir}",
            self.config.container_image,
            "bash",
            "-c",
            "sleep infinity",
        ]

        try:
            result = self._run_docker_cmd(cmd)
            logger.debug(f"Container created: {name} ({result.stdout.strip()[:12]})")

            # Wait for container to be ready
            time.sleep(2)

        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to create container {name}: {e.stderr}")

    def remove_container(self, name: Optional[str] = None) -> bool:
        """Remove container (stop and delete)."""
        container_name = name or self.config.default_container_name

        if not self.container_exists(container_name):
            return True

        try:
            self._run_docker_cmd(["docker", "rm", "-f", container_name])
            logger.info(f"Removed container: {container_name}")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to remove container {container_name}: {e.stderr}")
            return False

    def create_sandbox(self, container_name: Optional[str] = None) -> Sandbox:
        """Create a configured sandbox instance."""
        require_solitary()

        # Ensure container is ready
        actual_container_name = self.ensure_container(container_name)

        sandbox_config = SandboxConfig(
            container=actual_container_name,
            workdir=self.config.container_workdir,
            timeout=self.config.container_timeout,
            shell=self.config.container_shell,
        )

        return Sandbox(config=sandbox_config)


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

