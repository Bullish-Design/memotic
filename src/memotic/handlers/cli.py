# src/memotic/cli_handler.py
from __future__ import annotations
import os, re, logging
from typing import List
from .base import MemoWebhookEvent, on_any

log = logging.getLogger(__name__)

# match lines that START with "#cli", then optional ":" or whitespace, then the command
CLI_LINE = re.compile(r"(?mi)^\s*#cli(?P<bang>!?)(?:[:\s]+)(?P<cmd>.+?)\s*$")


def extract_cli_oneliners(text: str):
    return [(m.group("cmd").strip(), bool(m.group("bang"))) for m in CLI_LINE.finditer(text) if m.group("cmd").strip()]


class CliTagged(MemoWebhookEvent):
    any_tags = {"cli"}  # still require the tag so handler doesn't run for every memo

    @on_any()
    def run_cli(self):
        cmds = extract_cli_oneliners(self.memo.content or "")
        if not cmds:
            log.info("[#cli] No one-line cli commands found.")
            return

        # lazy import: make solitary an optional extra
        try:
            from solitary import SandboxConfig, Sandbox
        except Exception:
            log.exception("solitary not available. Install memotic[cli].")
            return

        container = os.getenv("MEMOTIC_CLI_CONTAINER", "sandbox")
        workdir = os.getenv("MEMOTIC_CLI_WORKDIR", "/projects")
        timeout_s = int(os.getenv("MEMOTIC_CLI_TIMEOUT", "30"))
        shell = os.getenv("MEMOTIC_CLI_SHELL", "/bin/bash")

        cfg = SandboxConfig(container=container, workdir=workdir, timeout=timeout_s, shell=shell)
        results = []
        with Sandbox(config=cfg) as sb:
            for cmd, allow_fail in extract_cli_oneliners(self.memo.content or ""):
                res = sb.execute_shell(cmd)
                print(
                    f"[#cli:{'OK' if res.exit_code == 0 else f'ERR({res.exit_code})'}] $ {cmd}\n"
                    f"--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}"
                )
                if res.exit_code != 0 and not allow_fail:
                    break

        # simple logging/printing for now (you can post back to Memos later)
        for cmd, res in results:
            status = "OK" if res.exit_code == 0 else f"ERR({res.exit_code})"
            print(f"[#cli:{status}] $ {cmd}\n--- stdout ---\n{res.stdout}\n--- stderr ---\n{res.stderr}")
