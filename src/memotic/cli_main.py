# src/memotic/cli_main.py
from __future__ import annotations

import hashlib
import importlib
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import typer

app = typer.Typer(add_completion=False, help="memotic control CLI", no_args_is_help=True)

# ---------- helpers ----------

PROJECT_MARKERS = ("pyproject.toml", ".git")


def find_project_root(start: Path | str = ".") -> Path:
    """Walk up to locate a project root (pyproject.toml or .git)."""
    p = Path(start).resolve()
    for parent in [p, *p.parents]:
        for marker in PROJECT_MARKERS:
            if (parent / marker).exists():
                return parent
    return p  # fallback to CWD if no markers found


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")


def default_container_name(project_root: Path) -> str:
    base = slugify(project_root.name)
    h = hashlib.sha1(str(project_root).encode()).hexdigest()[:7]
    return f"memotic-cli-{base}-{h}"


def run(cmd: List[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def docker_is_running() -> bool:
    try:
        run(["docker", "ps"], check=True)
        return True
    except Exception:
        return False


def container_running(name: str) -> bool:
    try:
        out = run(["docker", "inspect", "-f", "{{.State.Running}}", name], check=False).stdout.strip()
        return out == "true"
    except Exception:
        return False


def container_exists(name: str) -> bool:
    try:
        out = run(["docker", "ps", "-a", "--format", "{{.Names}}"]).stdout.splitlines()
        return name in out
    except Exception:
        return False


def ensure_sandbox(project_root: Path, name: Optional[str] = None, image: str = "debian:bookworm-slim") -> str:
    """Create or start a simple long-lived container mounted to project_root:/workspace."""
    if not docker_is_running():
        typer.secho("Docker daemon not available. Install/start Docker or skip --ensure-sandbox.", fg="red", err=True)
        raise typer.Exit(2)

    name = name or default_container_name(project_root)
    if container_exists(name):
        if not container_running(name):
            run(["docker", "start", name])
        return name

    # Create the container
    run(
        [
            "docker",
            "run",
            "-d",
            "--name",
            name,
            "-w",
            "/workspace",
            "-v",
            f"{str(project_root)}:/workspace",
            image,
            "bash",
            "-lc",
            "sleep infinity",
        ]
    )
    return name


def load_pyproject_imports(project_root: Path) -> List[str]:
    """Read [tool.memotic].imports from pyproject.toml if present."""
    pt = project_root / "pyproject.toml"
    if not pt.exists():
        return []
    try:
        import tomllib  # 3.11+

        data = tomllib.loads(pt.read_text())
    except Exception:
        return []
    imports = data.get("tool", {}).get("memotic", {}).get("imports", [])
    return [i for i in imports if isinstance(i, str)]


def import_module_dotted(path: str) -> None:
    importlib.import_module(path)


def import_file(path: Path, module_name: str = "_memotic_handlers") -> None:
    """Allow dropping a `memotic_handlers.py` into the project root."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec and spec.loader:
        m = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = m
        spec.loader.exec_module(m)


def import_handlers(project_root: Path, extra_imports: Optional[Iterable[str]] = None):
    """
    Load handler modules so memotic's subclass discovery sees them.
    Precedence:
      1) CLI --import values
      2) MEMOTIC_IMPORTS env (comma-separated)
      3) [tool.memotic].imports in pyproject.toml
      4) memotic_handlers.py in project root (if present)
    """
    seen: set[str] = set()

    # Normalize possibly-None input into a list
    extra_list = [s for s in (extra_imports or []) if s]

    env_imps = os.getenv("MEMOTIC_IMPORTS", "")
    env_list = [s.strip() for s in env_imps.split(",") if s.strip()] if env_imps else []

    pyproject_list = load_pyproject_imports(project_root)

    # dotted imports
    for mod in [*extra_list, *env_list, *pyproject_list]:
        if mod and mod not in seen:
            try:
                import_module_dotted(mod)
                seen.add(mod)
            except Exception as e:
                typer.secho(f"[memotic] Warning: failed to import '{mod}': {e}", fg="yellow", err=True)

    # file-based fallback
    hf = project_root / "memotic_handlers.py"
    if hf.exists():
        try:
            import_file(hf)
            seen.add(str(hf))
        except Exception as e:
            typer.secho(f"[memotic] Warning: failed to import handlers file '{hf}': {e}", fg="yellow", err=True)


# ---------- CLI commands ----------


@app.command(no_args_is_help=True)
def serve(
    imports: Optional[List[str]] = typer.Option(
        None, "--import", "-I", help="Extra dotted modules to import for handler discovery (repeatable)."
    ),
    ensure_sandbox_flag: bool = typer.Option(
        False, "--ensure-sandbox", help="Create/start a per-project Docker sandbox and mount the project root."
    ),
    container: Optional[str] = typer.Option(None, "--container", help="Sandbox container name (default is derived)."),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    port: int = typer.Option(8000, "--port", "-p", help="Port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload on code changes"),
):
    """
    Start the memotic FastAPI webhook app, loading handlers from the current project.
    """
    root = find_project_root()
    typer.echo(f"Project root: {root}")

    # Prepare sandbox
    cname = container or default_container_name(root)
    if ensure_sandbox_flag:
        cname = ensure_sandbox(root, name=cname)
        typer.echo(f"Sandbox: {cname} (mounted {root} -> /workspace)")

    # Set env for the #cli executor
    os.environ.setdefault("MEMOTIC_CLI_CONTAINER", cname)
    os.environ.setdefault("MEMOTIC_CLI_WORKDIR", "/workspace")
    os.environ.setdefault("MEMOTIC_CLI_SHELL", "/bin/bash")
    os.environ.setdefault("MEMOTIC_CLI_TIMEOUT", "30")

    # Load handlers: built-ins + project-provided
    import memotic.cli  # ensure the #cli handler class is present

    import_handlers(root, extra_imports=imports)

    # Finally run the app
    import uvicorn

    uvicorn.run("memotic.app:app", host=host, port=port, reload=reload, factory=False)


@app.command()
def up(
    name: Optional[str] = typer.Option(None, "--name", help="Container name (defaults to per-project name)"),
    image: str = typer.Option("debian:bookworm-slim", "--image", help="Base image"),
):
    """Create/start the per-project Docker sandbox."""
    root = find_project_root()
    cname = ensure_sandbox(root, name=name or default_container_name(root), image=image)
    typer.echo(f"Sandbox up: {cname}")


@app.command()
def down(name: Optional[str] = typer.Option(None, "--name", help="Container name")):
    """Stop and remove the per-project sandbox."""
    root = find_project_root()
    cname = name or default_container_name(root)
    if container_exists(cname):
        run(["docker", "rm", "-f", cname], check=False)
        typer.echo(f"Sandbox removed: {cname}")
    else:
        typer.echo(f"No such sandbox: {cname}")


@app.command()
def doctor():
    """Print diagnostics for the current working directory."""
    root = find_project_root()
    cname = default_container_name(root)
    typer.echo(f"Project root: {root}")
    typer.echo(f"Default sandbox name: {cname}")
    typer.echo(f"Docker available: {docker_is_running()}")
    typer.echo(f"Sandbox exists: {container_exists(cname)} running={container_running(cname)}")


def main():
    app()
