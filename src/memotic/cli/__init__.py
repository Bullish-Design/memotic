# src/memotic/cli/__init__.py
from .exec import extract_cli_oneliners, run_cli_lines
from .handler import CliTagged

__all__ = ["extract_cli_oneliners", "run_cli_lines", "CliTagged"]
