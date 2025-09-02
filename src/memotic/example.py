#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "webhooky @ git+https://github.com/Bullish-Design/webhooky.git",
#   "memotic @ git+https://github.com/Bullish-Design/memotic.git",
# ]
# ///

"""Example usage of WebHooky Memos plugin."""

from __future__ import annotations

import asyncio
from pathlib import Path

from webhooky import EventBus, create_dev_config
from webhooky_memos import (
    ResearchMemoEvent,
    ProjectMemoEvent,
    UrgentMemoEvent,
    create_research_handler,
    create_project_handler,
    MemoNotificationHandler,
)


async def main():
    """Demonstrate memos plugin usage."""
    print("🚀 WebHooky Memos Plugin Example")

    # Setup WebHooky with plugin support
    config = create_dev_config(enable_plugins=True)
    bus = EventBus(
        timeout_seconds=config.timeout_seconds,
        max_concurrent_handlers=config.max_concurrent_handlers,
        swallow_exceptions=config.swallow_exceptions,
        enable_metrics=config.enable_metrics,
        activity_groups={k: set(v) for k, v in config.activity_groups.items()},
    )

    # Create handlers
    research_handler = create_research_handler("./example_output/research")
    project_handler = create_project_handler("./example_output/projects")
    notification_handler = MemoNotificationHandler(["console"])

    # Register pattern-based handlers
    @bus.on_pattern(ResearchMemoEvent)
    async def handle_research_memo(event: ResearchMemoEvent):
        print(f"📚 Research memo detected!")
        path = await research_handler.save_memo(event.payload)
        await notification_handler.notify(
            "Research Memo", f"Saved research memo: {event.payload.memo.name or 'Untitled'}", event.payload
        )
        print(f"   Saved to: {path}")

    @bus.on_pattern(ProjectMemoEvent)
    async def handle_project_memo(event: ProjectMemoEvent):
        print(f"📋 Project memo detected!")
        path = await project_handler.save_memo(event.payload)
        tags = ", ".join(event.payload.memo.tags or [])
        print(f"   Tags: {tags}")
        print(f"   Saved to: {path}")

    @bus.on_pattern(UrgentMemoEvent)
    async def handle_urgent_memo(event: UrgentMemoEvent):
        print(f"🚨 URGENT memo detected!")
        content_preview = (event.payload.memo.content or "")[:100]
        print(f"   Preview: {content_preview}...")

        await notification_handler.notify(
            "🚨 URGENT MEMO", f"Urgent attention required: {event.payload.memo.name or 'Untitled'}", event.payload
        )

    # Test data - simulating different memo webhook payloads
    test_payloads = [
        {
            "action": "create",
            "memo": {
                "name": "AI Research Findings",
                "content": "Research shows that large language models can be effectively fine-tuned for specific tasks...",
                "tags": ["research", "ai", "machine-learning"],
                "visibility": "PRIVATE",
                "creator": "researcher@example.com",
            },
        },
        {
            "action": "create",
            "memo": {
                "name": "Project Alpha Milestone",
                "content": "Completed initial prototype development. Next steps: user testing and feedback collection.",
                "tags": ["project", "alpha", "milestone"],
                "visibility": "PROTECTED",
                "creator": "pm@example.com",
            },
        },
        {
            "action": "update",
            "memo": {
                "name": "URGENT: Server Issues",
                "content": "URGENT: Production servers experiencing high load. Immediate investigation needed!!",
                "tags": ["urgent", "infrastructure"],
                "visibility": "PUBLIC",
                "creator": "devops@example.com",
            },
        },
        {
            "action": "create",
            "memo": {
                "name": "Meeting Notes",
                "content": "Discussed quarterly goals and resource allocation. Action items: hire 2 engineers, upgrade infrastructure.",
                "tags": ["meeting", "notes"],
                "visibility": "PRIVATE",
                "creator": "manager@example.com",
            },
        },
        {
            "action": "create",
            "memo": {
                "name": "Study on User Behavior",
                "content": "Analysis of user behavior patterns reveals interesting insights about engagement...",
                "tags": ["study", "analytics"],
                "visibility": "PRIVATE",
                "creator": "analyst@example.com",
            },
        },
    ]

    print(f"\n📡 Processing {len(test_payloads)} test webhook payloads...\n")

    # Process each test payload
    for i, payload in enumerate(test_payloads, 1):
        print(f"--- Processing Webhook {i} ---")
        print(f"Action: {payload['action']}")
        print(f"Memo: {payload['memo']['name']}")
        print(f"Tags: {', '.join(payload['memo'].get('tags', []))}")

        result = await bus.dispatch_raw(payload)

        print(f"✅ Processed: {result.success}")
        print(f"   Patterns matched: {result.matched_patterns}")
        print(f"   Handlers executed: {result.handler_count}")
        print(f"   Processing time: {result.processing_time:.3f}s")

        if result.errors:
            print(f"❌ Errors: {result.errors}")

        print()

    # Show metrics
    metrics = bus.get_metrics()
    print(f"📊 Final Metrics:")
    print(f"   Total events: {metrics.total_events}")
    print(f"   Success rate: {metrics.success_rate:.1%}")
    print(f"   Avg processing time: {metrics.average_processing_time:.3f}s")

    # Show saved files
    output_dir = Path("./example_output")
    if output_dir.exists():
        print(f"\n📁 Saved files:")
        for file_path in output_dir.rglob("*.md"):
            print(f"   {file_path}")


if __name__ == "__main__":
    asyncio.run(main())
