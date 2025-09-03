# src/memotic/cli_main.py
from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path
from typing import Iterable, List, Optional

import typer

from .dependencies import get_console
from .config import get_config, set_config, MemoticConfig
from .container_manager import get_container_manager

console = get_console()
app = typer.Typer(add_completion=False, help="Memotic control CLI", no_args_is_help=True)


def load_pyproject_imports(project_root: Path) -> List[str]:
    """Read [tool.memotic].imports from pyproject.toml if present."""
    pt = project_root / "pyproject.toml"
    if not pt.exists():
        return []
    
    try:
        import tomllib  # 3.11+
        data = tomllib.loads(pt.read_text())
    except ImportError:
        console.print("Warning: tomllib not available, skipping pyproject.toml imports")
        return []
    except Exception as e:
        console.print(f"Warning: failed to parse pyproject.toml: {e}")
        return []
    
    imports = data.get("tool", {}).get("memotic", {}).get("imports", [])
    return [i for i in imports if isinstance(i, str)]


def import_module_dotted(path: str) -> None:
    """Import a module by dotted path."""
    importlib.import_module(path)


def import_file(path: Path, module_name: str = "_memotic_handlers") -> None:
    """Import a Python file as a module."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec and spec.loader:
        m = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = m
        spec.loader.exec_module(m)


def import_handlers(project_root: Path, extra_imports: Optional[Iterable[str]] = None, verbose: bool = False):
    """Load handler modules for subclass discovery."""
    seen: set[str] = set()

    extra_list = [s for s in (extra_imports or []) if s]
    
    env_imps = os.getenv("MEMOTIC_IMPORTS", "")
    env_list = [s.strip() for s in env_imps.split(",") if s.strip()] if env_imps else []

    pyproject_list = load_pyproject_imports(project_root)

    # Import dotted modules
    for mod in [*extra_list, *env_list, *pyproject_list]:
        if mod and mod not in seen:
            try:
                import_module_dotted(mod)
                seen.add(mod)
                if verbose:
                    console.print(f"✓ Imported: {mod}")
            except Exception as e:
                console.print(f"⚠ Failed to import '{mod}': {e}")

    # Import file-based handlers
    hf = project_root / "memotic_handlers.py"
    if hf.exists():
        try:
            import_file(hf)
            seen.add(str(hf))
            if verbose:
                console.print(f"✓ Imported: {hf}")
        except Exception as e:
            console.print(f"⚠ Failed to import handlers file '{hf}': {e}")

    return len(seen)


@app.command(no_args_is_help=True)
def serve(
    imports: Optional[List[str]] = typer.Option(
        None, "--import", "-I", help="Extra dotted modules to import"
    ),
    ensure_sandbox_flag: bool = typer.Option(
        False, "--ensure-sandbox", help="Create/start Docker sandbox"
    ),
    container: Optional[str] = typer.Option(None, "--container", help="Container name"),
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address"),
    port: int = typer.Option(8000, "--port", "-p", help="Port"),
    reload: bool = typer.Option(False, "--reload", help="Auto-reload"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Start the memotic FastAPI webhook app."""
    
    config = MemoticConfig(
        host=host,
        port=port,
        container_name=container,
    )
    set_config(config)
    
    console.print(f"Project root: {config.project_root}")
    console.print(f"Container name: {config.default_container_name}")

    # Validate configuration
    issues = config.validate_setup()
    if issues:
        console.print("Configuration issues:")
        for issue in issues:
            console.print(f"  ⚠ {issue}")

    # Prepare container if requested
    if ensure_sandbox_flag:
        console.print("Preparing container...")
        container_manager = get_container_manager()
        try:
            container_name = container_manager.ensure_container()
            console.print(f"✓ Container ready: {container_name}")
        except Exception as e:
            console.print(f"✗ Container setup failed: {e}")
            console.print("Continuing without container - CLI commands may fail")

    # Load built-in CLI handler
    try:
        import memotic.cli
        if verbose:
            console.print("✓ Built-in CLI handler loaded")
    except ImportError as e:
        console.print(f"✗ Failed to load built-in CLI handler: {e}")

    # Load project handlers
    console.print("Loading handlers...")
    imported_count = import_handlers(config.project_root, extra_imports=imports, verbose=verbose)
    
    if imported_count == 0:
        console.print("⚠ No additional handlers imported")
    else:
        console.print(f"✓ Loaded {imported_count} handler modules")

    # Create and run app
    from .app import create_app
    
    app_instance = create_app(config)
    console.print(f"Starting server on {host}:{port}")
    
    import uvicorn
    uvicorn.run(app_instance, host=host, port=port, reload=reload, factory=False)


@app.command()
def up(
    name: Optional[str] = typer.Option(None, "--name", help="Container name"),
    image: str = typer.Option("debian:bookworm-slim", "--image", help="Base image"),
):
    """Create/start the Docker container."""
    config = get_config()
    if name:
        config = MemoticConfig(container_name=name, container_image=image)
        set_config(config)
    
    container_manager = get_container_manager()
    try:
        container_name = container_manager.ensure_container()
        console.print(f"✓ Container ready: {container_name}")
    except Exception as e:
        console.print(f"✗ Failed to create container: {e}")
        raise typer.Exit(1)


@app.command()
def down(name: Optional[str] = typer.Option(None, "--name", help="Container name")):
    """Stop and remove the container."""
    container_manager = get_container_manager()
    success = container_manager.remove_container(name)
    if success:
        console.print("✓ Container removed")
    else:
        console.print("✗ Failed to remove container")
        raise typer.Exit(1)


@app.command()
def status():
    """Show container and configuration status."""
    config = get_config()
    container_manager = get_container_manager()
    
    console.print("Configuration")
    console.print(f"  Project root: {config.project_root}")
    console.print(f"  Container name: {config.default_container_name}")
    console.print(f"  API configured: {config.has_api_config()}")
    
    console.print("\nDocker & Container")
    try:
        docker_available = container_manager.is_docker_available()
        console.print(f"  Docker available: {'✓' if docker_available else '✗'}")
        
        if docker_available:
            status = container_manager.get_container_status()
            console.print(f"  Container exists: {'✓' if status.exists else '✗'}")
            console.print(f"  Container running: {'✓' if status.running else '✗'}")
            console.print(f"  Container healthy: {'✓' if status.healthy else '✗'}")
            
            if status.error:
                console.print(f"  Error: {status.error}")
        
    except Exception as e:
        console.print(f"  Status check failed: {e}")


@app.command()
def doctor():
    """Run diagnostics and show troubleshooting information."""
    config = get_config()
    container_manager = get_container_manager()
    
    console.print("=== Memotic Doctor ===")
    
    # Configuration
    console.print("\nConfiguration")
    console.print(f"✓ Project root: {config.project_root}")
    console.print(f"✓ Container name: {config.default_container_name}")
    
    if config.has_api_config():
        console.print("✓ Memos API configured")
    else:
        console.print("⚠ Memos API not configured")
        console.print("  Set MEMOTIC_API_BASE and MEMOTIC_API_TOKEN")
    
    # Validate configuration
    issues = config.validate_setup()
    if issues:
        console.print("\nConfiguration Issues:")
        for issue in issues:
            console.print(f"  ⚠ {issue}")
    
    # Docker
    console.print("\nDocker")
    try:
        if container_manager.is_docker_available():
            console.print("✓ Docker daemon available")
        else:
            console.print("✗ Docker daemon not available")
            console.print("  Install Docker and ensure it's running")
    except Exception as e:
        console.print(f"✗ Docker check failed: {e}")
    
    # Container status
    console.print("\nContainer")
    try:
        status = container_manager.get_container_status()
        if status.healthy:
            console.print(f"✓ Container healthy: {status.name}")
        elif status.running:
            console.print(f"⚠ Container running but not healthy: {status.name}")
            console.print("  Container may have issues - try: memotic down && memotic up")
        elif status.exists:
            console.print(f"⚠ Container exists but not running: {status.name}")
            console.print("  Start with: memotic up")
        else:
            console.print(f"⚠ Container does not exist: {status.name}")
            console.print("  Create with: memotic up")
        
        if status.error:
            console.print(f"  Error: {status.error}")
    
    except Exception as e:
        console.print(f"✗ Container status check failed: {e}")

    # Handler check
    console.print("\nHandlers")
    try:
        import memotic.cli
        from memotic.base import MemoWebhookEvent
        
        handlers = MemoWebhookEvent.__subclasses__()
        if handlers:
            console.print(f"✓ Found {len(handlers)} handlers:")
            for handler in handlers:
                console.print(f"    - {handler.__name__}")
        else:
            console.print("⚠ No handlers found")
            console.print("  Handlers may not be imported yet - this is normal")
            
    except Exception as e:
        console.print(f"✗ Handler check failed: {e}")

    console.print("\nRecommendations")
    if not config.has_api_config():
        console.print("  1. Configure Memos API access")
    try:
        if not container_manager.is_docker_available():
            console.print("  2. Install and start Docker")
        elif not container_manager.get_container_status().healthy:
            console.print("  2. Set up container: memotic up")
    except Exception:
        pass
    console.print("  3. Test setup: memotic serve --verbose")


def main():
    """Main CLI entry point."""
    app()


if __name__ == "__main__":
    main()