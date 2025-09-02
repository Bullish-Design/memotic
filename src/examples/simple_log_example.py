#!/usr/bin/env python3
"""
Example: WebHook Logger Library using WebHooky as core
Demonstrates integration patterns for building on WebHooky
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from webhooky import EventBus, WebhookEventBase, GenericWebhookEvent, WebHookyConfig, create_bus, on_create, on_push
from webhooky.fastapi import create_app
from webhooky.registry import event_registry

print("\n\nRegistered classes:", event_registry.get_registry_info().registered_classes)


# 1. EXTEND WEBHOOKY'S CONFIG SYSTEM
class WebhookLoggerConfig(WebHookyConfig):
    """Extended config for webhook logging"""

    # Logging-specific settings
    log_storage_path: Path = Field(default=Path("./webhook_logs"))
    max_log_retention_days: int = Field(default=30)
    structured_logging: bool = Field(default=True)
    include_headers: bool = Field(default=True)
    include_payload: bool = Field(default=True)

    # Storage options
    storage_backend: str = Field(default="file")  # file, database, s3
    database_url: Optional[str] = None
    s3_bucket: Optional[str] = None


# 2. DEFINE DOMAIN-SPECIFIC MODELS
class WebhookLogEntry(BaseModel):
    """Core webhook log entry model"""

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    source_ip: Optional[str] = None
    user_agent: Optional[str] = None

    # Event data
    event_type: str
    matched_patterns: List[str] = Field(default_factory=list)
    activity: Optional[str] = None

    # Webhook data (optional based on config)
    headers: Optional[Dict[str, str]] = None
    payload: Optional[Dict[str, Any]] = None

    # Processing results
    success: bool = True
    processing_time: float = 0.0
    handler_count: int = 0
    errors: List[str] = Field(default_factory=list)


# 3. DEFINE STORAGE INTERFACE
class WebhookStorage(Protocol):
    """Storage interface for webhook logs"""

    async def store_log(self, log_entry: WebhookLogEntry) -> None: ...

    async def get_logs(
        self, limit: int = 100, offset: int = 0, event_type: Optional[str] = None
    ) -> List[WebhookLogEntry]: ...

    async def cleanup_old_logs(self, retention_days: int) -> int: ...


class FileWebhookStorage:
    """Working file-based webhook log storage"""

    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self.storage_path.mkdir(exist_ok=True)

    async def store_log(self, log_entry: WebhookLogEntry) -> None:
        log_file = self.storage_path / f"webhooks_{datetime.now().strftime('%Y-%m-%d')}.jsonl"

        with open(log_file, "a") as f:
            f.write(log_entry.model_dump_json() + "\n")

    async def get_logs(
        self, limit: int = 100, offset: int = 0, event_type: Optional[str] = None
    ) -> List[WebhookLogEntry]:
        """Actually read and return logs from files"""
        logs = []

        # Get all log files, newest first
        log_files = sorted(self.storage_path.glob("webhooks_*.jsonl"), reverse=True)

        count = 0
        skipped = 0

        for log_file in log_files:
            if count >= limit:
                break

            try:
                with open(log_file, "r") as f:
                    for line in reversed(f.readlines()):  # Newest first
                        if count >= limit:
                            break
                        if skipped < offset:
                            skipped += 1
                            continue

                        try:
                            log_data = json.loads(line.strip())
                            log_entry = WebhookLogEntry.model_validate(log_data)

                            # Filter by event type if specified
                            if event_type and log_entry.event_type != event_type:
                                continue

                            logs.append(log_entry)
                            count += 1

                        except (json.JSONDecodeError, Exception):
                            continue  # Skip malformed entries

            except (FileNotFoundError, PermissionError):
                continue  # Skip inaccessible files

        return logs

    async def cleanup_old_logs(self, retention_days: int) -> int:
        """Remove log files older than retention period"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_count = 0

        for log_file in self.storage_path.glob("webhooks_*.jsonl"):
            try:
                # Extract date from filename: webhooks_2024-01-15.jsonl
                date_str = log_file.stem.split("_")[1]  # 2024-01-15
                file_date = datetime.strptime(date_str, "%Y-%m-%d")

                if file_date < cutoff_date:
                    log_file.unlink()
                    removed_count += 1

            except (ValueError, IndexError):
                continue  # Skip files with unexpected names

        return removed_count


class GitHubRepository(BaseModel):
    """GitHub repository information."""

    name: str
    full_name: str = ""
    private: bool = False
    owner: Dict[str, Any] = {}


class GitHubCommit(BaseModel):
    """GitHub commit information."""

    message: str
    id: str = ""
    author: Dict[str, Any] = {}


class GitHubPushPayload(BaseModel):
    """GitHub push webhook payload."""

    action: str = "push"  # Default to push for backward compatibility
    repository: GitHubRepository
    commits: List[GitHubCommit] = []
    ref: str = "refs/heads/main"  # Default branch

    @field_validator("action")
    @classmethod
    def validate_push_action(cls, v: str) -> str:
        # Accept various push-related actions
        valid_actions = {"push", "create", "synchronize"}
        if v not in valid_actions:
            # Don't raise error - let this pattern not match instead
            pass
        return v


class GitHubPushEvent(WebhookEventBase[GitHubPushPayload]):
    """GitHub push event with automatic activity detection."""

    @classmethod
    def _transform_raw_data(cls, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform GitHub webhook data to match our payload structure."""
        # Handle cases where repository is just a dict with name
        if isinstance(raw_data.get("repository"), dict):
            repo_data = raw_data["repository"]
            if "name" in repo_data and "full_name" not in repo_data:
                repo_data["full_name"] = repo_data["name"]

        # Handle commits that might just be dicts with message
        if "commits" in raw_data:
            commits = []
            for commit in raw_data["commits"]:
                if isinstance(commit, dict):
                    commit_data = {"message": commit.get("message", "")}
                    if "id" in commit:
                        commit_data["id"] = commit["id"]
                    commits.append(commit_data)
            raw_data = {**raw_data, "commits": commits}

        return raw_data

    @on_push()
    async def handle_push(self):
        """Handle push events."""
        print(f"Push to repository: {self.payload.repository.name}")
        print(f"Commits: {len(self.payload.commits)}")


# More specific GitHub events
class GitHubIssuePayload(BaseModel):
    """GitHub issue webhook payload."""

    action: str
    issue: Dict[str, Any]
    repository: GitHubRepository

    @field_validator("action")
    @classmethod
    def validate_issue_action(cls, v: str) -> str:
        valid_actions = {"opened", "closed", "edited", "reopened", "assigned"}
        if v not in valid_actions:
            raise ValueError(f"Invalid issue action: {v}")
        return v


class GitHubIssueEvent(WebhookEventBase[GitHubIssuePayload]):
    """GitHub issue event."""

    @on_create()
    async def handle_issue_created(self):
        """Handle new issues."""
        if self.payload.action == "opened":
            print(f"New issue in {self.payload.repository.name}")


# Generic GitHub webhook for any GitHub event
class GitHubWebhookPayload(BaseModel):
    """Generic GitHub webhook payload."""

    repository: GitHubRepository
    action: str = ""
    sender: Dict[str, Any] = {}


class GitHubWebhookEvent(WebhookEventBase[GitHubWebhookPayload]):
    """Generic GitHub webhook event."""

    @classmethod
    def matches(cls, raw_data: Dict[str, Any], headers=None) -> bool:
        """Match any data with a GitHub repository structure."""
        try:
            # Check for GitHub-style repository structure
            repo = raw_data.get("repository", {})
            return isinstance(repo, dict) and "name" in repo
        except Exception:
            return False

    def get_activity(self) -> str:
        """Extract activity from GitHub webhook action."""
        action = self.payload.action
        if action in ["opened", "created"]:
            return "create"
        elif action in ["closed", "deleted"]:
            return "delete"
        elif action in ["edited", "updated", "synchronize"]:
            return "update"
        return action or "github"


# 5. MAIN LOGGER CLASS THAT EXTENDS WEBHOOKY
class WebhookLogger:
    """
    Webhook event logger built on WebHooky
    Demonstrates composition over inheritance
    """

    def __init__(self, config: Optional[WebhookLoggerConfig] = None):
        self.config = config or WebhookLoggerConfig()

        # Create WebHooky bus with extended config
        self.bus = create_bus(self.config)

        # Setup storage backend
        self.storage = self._create_storage()

        # Register our logging handlers
        self._register_handlers()

    def _create_storage(self) -> WebhookStorage:
        """Factory method for storage backends"""
        if self.config.storage_backend == "file":
            return FileWebhookStorage(self.config.log_storage_path)
        # Could add database, S3, etc.
        raise ValueError(f"Unknown storage backend: {self.config.storage_backend}")

    def _register_handlers(self) -> None:
        """Register logging handlers with WebHooky bus"""

        # Catch-all handler to log every webhook
        @self.bus.on_any()
        async def log_all_webhooks(event: WebhookEventBase):
            await self._log_webhook_event(event)

        # Activity-specific handlers for structured logging
        @self.bus.on_activity("create", "push", "deploy")
        async def log_creation_events(event: WebhookEventBase):
            # Additional processing for creation events
            await self._log_structured_event(event, category="creation")

        @self.bus.on_activity("delete", "remove")
        async def log_deletion_events(event: WebhookEventBase):
            await self._log_structured_event(event, category="deletion")

    async def _log_webhook_event(self, event: WebhookEventBase) -> None:
        """Core logging logic"""
        log_entry = WebhookLogEntry(
            event_type=event.event_type,
            activity=event.get_activity(),
            headers=event.headers if self.config.include_headers else None,
            payload=event.payload.model_dump() if self.config.include_payload else None,
        )

        await self.storage.store_log(log_entry)

    async def _log_structured_event(self, event: WebhookEventBase, category: str) -> None:
        """Enhanced logging for specific categories"""
        # Additional structured logging logic
        pass

    # 6. PROVIDE HIGH-LEVEL API
    async def process_webhook(
        self, raw_data: Dict[str, Any], headers: Dict[str, str] = None, source_info: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Process webhook and return results"""
        result = await self.bus.dispatch_raw(raw_data, headers, source_info)

        return {
            "logged": True,
            "matched_patterns": result.matched_patterns,
            "processing_time": result.processing_time,
            "success": result.success,
        }

    async def get_recent_logs(self, limit: int = 100) -> List[WebhookLogEntry]:
        """Get recent webhook logs"""
        return await self.storage.get_logs(limit=limit)

    def create_fastapi_app(self, **kwargs):
        """Create FastAPI app with WebHooky + logging endpoints"""
        app = create_app(self.bus, self.config, **kwargs)

        # Add logging-specific endpoints
        @app.get("/logs")
        async def get_logs(limit: int = 100, offset: int = 0):
            logs = await self.storage.get_logs(limit, offset)
            return {"logs": [log.model_dump() for log in logs]}

        @app.post("/webhook")
        async def webhook_endpoint(request):
            # Override default webhook endpoint to include our logging
            # Implementation would extract data and call process_webhook()
            pass

        return app


# 7. PLUGIN FOR EXTENDING WEBHOOKY ECOSYSTEM
class WebhookLoggerPlugin:
    """
    Plugin to integrate webhook logging into existing WebHooky installations
    """

    def __init__(self, storage_path: Path = Path("./webhook_logs")):
        self.storage = FileWebhookStorage(storage_path)

    def get_handlers(self):
        """Return handlers for WebHooky plugin system"""

        async def log_handler(event: WebhookEventBase):
            log_entry = WebhookLogEntry(
                event_type=event.event_type,
                activity=event.get_activity(),
                headers=event.headers,
                payload=event.payload.model_dump(),
            )
            await self.storage.store_log(log_entry)

        return [log_handler]


# 8. CONVENIENCE FACTORY FUNCTIONS
def create_webhook_logger(storage_path: Path = Path("./webhook_logs"), **config_kwargs) -> WebhookLogger:
    """Factory function for easy setup"""
    config = WebhookLoggerConfig(log_storage_path=storage_path, **config_kwargs)
    return WebhookLogger(config)


def create_logging_app(storage_path: Path = Path("./webhook_logs")):
    """Create ready-to-run FastAPI app with webhook logging"""
    logger = create_webhook_logger(storage_path)
    return logger.create_fastapi_app()


# 9. EXAMPLE USAGE
if __name__ == "__main__":

    async def main():
        # Create logger instance
        # print("\n\nPre Registered classes:", event_registry.get_registry_info().registered_classes)

        logger = create_webhook_logger()
        # print("\n\nPost Registered classes:", event_registry.get_registry_info().registered_classes)

        # Process sample webhook
        sample_webhook = {
            "action": "push",
            "repository": {"name": "test-repo"},
            "commits": [{"message": "test commit"}],
        }

        sample_data = {"action": "push", "repository": {"name": "test-repo"}, "commits": [{"message": "test commit"}]}

        print("\n\nTesting GitHub event matching:")
        print(f"GitHubPushEvent matches: {GitHubPushEvent.matches(sample_data)}")
        print(f"GitHubWebhookEvent matches: {GitHubWebhookEvent.matches(sample_data)}")

        result = await logger.process_webhook(sample_data)
        print(f"Processed webhook: {result}")

        # Get logs
        recent_logs = await logger.get_recent_logs(10)
        print(f"Recent logs: {len(recent_logs)}")

    asyncio.run(main())
