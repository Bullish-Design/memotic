# src/memotic/cli/handler.py
# src/memotic/cli/handler.py
from __future__ import annotations

import logging
import textwrap
from typing import List

from ..base import MemoWebhookEvent, on_any, on_create
from ..config import get_config
from ..integrations import MemosIntegration, MemosIntegrationError, MemosAuthError, MemosNotFoundError
from .exec import run_cli_lines

logger = logging.getLogger(__name__)


def _summarize_results(chunks: List[str]) -> List[str]:
    """Combine text chunks into <= MAX_COMMENT_CHARS pieces."""
    if not chunks:
        return []

    config = get_config()
    max_chars = config.max_comment_chars

    combined: List[str] = []
    buf = ""

    for piece in chunks:
        if len(buf) + len(piece) + 1 > max_chars and buf:
            combined.append(buf.rstrip())
            buf = ""
        buf += piece if not buf else "\n" + piece

    if buf:
        combined.append(buf.rstrip())

    return combined


def _format_cli_comment(title: str, combined_text: str, fence: str = "```") -> str:
    """Format CLI results as a markdown comment body."""
    return textwrap.dedent(f"""\
    **{title}**

    {fence}
    {combined_text.rstrip()}
    {fence}
    """)


class CliTagged(MemoWebhookEvent):
    """Execute #cli commands and post results back to Memos using memos-api."""

    any_tags = {"cli"}

    @on_create()
    async def run_cli(self):
        """Execute CLI commands and post results back to Memos."""
        content = self.memo.content or ""
        parent_name = getattr(self.memo, "name", None)

        logger.info(f"Processing CLI commands for memo: {parent_name or 'unnamed'}")

        # Run commands and accumulate results
        rendered_chunks: List[str] = []

        try:
            commands_executed = 0
            for cmd, code, out, err, secs in run_cli_lines(content):
                commands_executed += 1
                status = "OK" if code == 0 else f"ERR({code})"
                took = f" in {secs:.2f}s" if secs is not None else ""

                rendered = (
                    f"$ {cmd}\n[{status}{took}]\n--- stdout ---\n{out.rstrip()}\n--- stderr ---\n{err.rstrip()}\n"
                ).rstrip()
                print(rendered + "\n")

                rendered_chunks.append(rendered)

                logger.info(f"CLI command '{cmd}' completed with exit code {code}")
                print(f"    CLI command '{cmd}' completed with exit code {code}")
                if code != 0 and err:
                    logger.warning(f"Command stderr: {err[:100]}...")

            if commands_executed == 0:
                logger.info("No CLI commands found in memo content")
                print(f"No CLI commands found in memo content")
                return

            logger.info(f"Executed {commands_executed} CLI commands")

        except Exception as e:
            logger.error(f"Failed to execute CLI commands: {e}")
            print(f"Failed to execute CLI commands: {e}")
            rendered_chunks.append(f"Execution failed: {e}")

        if not rendered_chunks:
            logger.info("No CLI command output to post back")
            return

        # Post back as comment if we have memo name and API config
        if not parent_name:
            logger.warning("No memo.name on event; cannot post a comment back")
            print(f"No memo.name on event; cannot post a comment back")
            return

        config = get_config()
        if not config.has_api_config():
            logger.warning("API configuration not available; skipping reply comment")
            print(f"API configuration not available; skipping reply comment")
            return

        # Create and post comments using memos integration
        try:
            async with MemosIntegration() as memos:
                body_chunks = _summarize_results(rendered_chunks)
                print(f"\nPosting {len(body_chunks)} comment(s) back to {parent_name}...")
                title = "CLI Results"

                created_names: List[str] = []

                for i, body in enumerate(body_chunks, start=1):
                    label = f"{title} ({i}/{len(body_chunks)})" if len(body_chunks) > 1 else title
                    comment_md = _format_cli_comment(label, body)
                    print(f"Prepared comment chunk {i}:\n{comment_md}\n")

                    try:
                        memo = await memos.create_comment(
                            parent_memo_name=parent_name, content=comment_md, visibility="PRIVATE"
                        )

                        created_name = memo.name or f"memo-{i}"
                        print(f"Posted comment chunk {i}: {created_name}")
                        created_names.append(created_name)
                        logger.debug(f"Posted comment chunk {i}: {created_name}")

                    except MemosAuthError as e:
                        logger.error(f"Authentication failed posting comment chunk {i}: {e}")
                        created_names.append(f"<auth failed: {e}>")
                    except MemosNotFoundError as e:
                        logger.error(f"Parent memo not found for chunk {i}: {e}")
                        created_names.append(f"<parent not found: {e}>")
                    except MemosIntegrationError as e:
                        logger.error(f"Failed to post comment chunk {i}: {e}")
                        created_names.append(f"<failed: {e}>")

                logger.info(f"Posted {len(body_chunks)} comment(s) to {parent_name}")

                if any("failed" in name or "auth failed" in name for name in created_names):
                    logger.warning(f"Some comments failed to post: {created_names}")

        except Exception as e:
            logger.exception(f"Failed to post comments back to {parent_name}: {e}")
