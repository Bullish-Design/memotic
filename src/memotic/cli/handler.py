# src/memotic/cli/handler.py
from __future__ import annotations
import logging
import os
from typing import List

from memotic.base import MemoWebhookEvent, on_any  # webhooky base & decorator
from memotic.memos_client import MemosClient, format_cli_comment
from memotic.old_models.base import Visibility
from .exec import run_cli_lines

log = logging.getLogger(__name__)

# prevent oversized comments; can be tuned via env
MAX_COMMENT_CHARS = int(os.getenv("MEMOTIC_CLI_COMMENT_MAX", "15000"))


def _summarize_results(chunks: List[str]) -> List[str]:
    """
    Combine text chunks into <= MAX_COMMENT_CHARS pieces to stay under server limits.
    """
    if not chunks:
        return []
    combined: List[str] = []
    buf = ""
    for piece in chunks:
        if len(buf) + len(piece) + 1 > MAX_COMMENT_CHARS and buf:
            combined.append(buf.rstrip())
            buf = ""
        buf += piece if not buf else "\n" + piece
    if buf:
        combined.append(buf.rstrip())
    return combined


class CliTagged(MemoWebhookEvent):
    """
    Execute `#cli` one-liners inside a Docker container via solitary.
    Default: stop on first failure unless the line uses `#cli!`.
    Then, post the results as a comment under the source memo.
    """

    any_tags = {"cli"}

    @on_any()
    def run_cli(self):
        content = self.memo.content or ""
        parent_name = getattr(self.memo, "name", None)

        # Run commands and accumulate results
        rendered_chunks: List[str] = []
        for cmd, code, out, err, secs in run_cli_lines(content):
            status = "OK" if code == 0 else f"ERR({code})"
            took = f" in {secs:.2f}s" if secs is not None else ""
            rendered = (
                f"$ {cmd}\n[{status}{took}]\n--- stdout ---\n{out.rstrip()}\n--- stderr ---\n{err.rstrip()}\n"
            ).rstrip()
            rendered_chunks.append(rendered)

            # still print to logs/console as before
            print(f"[#cli:{status}] $ {cmd}{took}\n--- stdout ---\n{out}\n--- stderr ---\n{err}\n")

        if not rendered_chunks:
            log.info("[#cli] Nothing to execute or extract.")
            return

        # Post back as a comment if we have the memo name and API creds
        if not parent_name:
            log.warning("[#cli] No memo.name on event; cannot post a comment back.")
            return

        api_base = os.getenv("MEMOTIC_API_BASE", "")
        api_token = os.getenv("MEMOTIC_API_TOKEN", "")
        if not api_base or not api_token:
            log.warning("[#cli] MEMOTIC_API_BASE or MEMOTIC_API_TOKEN not set; skipping reply comment.")
            return

        # Chunk if needed, then post one (or several) comments
        body_chunks = _summarize_results(rendered_chunks)
        title = "CLI result"

        try:
            client = MemosClient(base_url=api_base, token=api_token)
            created_names: List[str] = []
            for i, body in enumerate(body_chunks, start=1):
                label = f"{title} ({i}/{len(body_chunks)})" if len(body_chunks) > 1 else title
                comment_md = format_cli_comment(label, body)
                created = client.create_comment(
                    parent_memo_name=parent_name,
                    content=comment_md,
                    visibility=Visibility.PRIVATE,
                )
                created_names.append(created or "<unknown>")
            client.close()
            log.info("[#cli] Posted %d comment(s) back to %s: %s", len(created_names), parent_name, created_names)
        except Exception as e:
            log.exception("[#cli] Failed to post comment back to %s: %s", parent_name, e)
