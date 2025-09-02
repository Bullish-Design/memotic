# WebHooky Memos Plugin

Memos webhook event processing plugin for WebHooky. Enables pattern-matching webhook workflows for the Memos note-taking app using Pydantic validation.

## Features

- **Pattern-Based Event Matching** - Events trigger only when memos match specific criteria
- **Tag-Based Filtering** - Process memos with specific tags or any tags
- **Content-Based Matching** - Match memos containing specific text or patterns  
- **File Saving** - Automatically save memos as organized Markdown files
- **Search Indexing** - Build searchable index of processed memos
- **Notifications** - Console, webhook, or email notifications for memo events
- **Built-in Event Types** - Research, project, idea, urgent memo handling

## Installation

```bash
uv add webhooky-memos
```

## Quick Start

```python
from webhooky import EventBus, create_dev_config
from webhooky_memos import ResearchMemoEvent, create_research_handler

# Setup WebHooky
config = create_dev_config(enable_plugins=True)
bus = EventBus(config=config)

# Create file handler
research_handler = create_research_handler("./research_notes")

# Register custom handler
@bus.on_pattern(ResearchMemoEvent)
async def save_research_memo(event: ResearchMemoEvent):
    path = await research_handler.save_memo(event.payload)
    print(f"Saved research memo: {path}")

# Process webhook (automatically matches research content)
await bus.dispatch_raw({
    "action": "create",
    "memo": {
        "content": "Research findings on AI developments",
        "tags": ["research", "ai"]
    }
})
```

## Built-in Event Types

### TaggedMemoEvent
Matches any memo with tags:

```python
@bus.on_pattern(TaggedMemoEvent)
async def handle_tagged_memo(event: TaggedMemoEvent):
    tags = ", ".join(event.payload.memo.tags)
    print(f"Tagged memo: {tags}")
```

### ResearchMemoEvent  
Matches memos containing research-related keywords:

```python
# Automatically matches content with: research, study, investigate, analyze
@bus.on_pattern(ResearchMemoEvent)
async def handle_research(event: ResearchMemoEvent):
    # Save to research directory
    await research_handler.save_memo(event.payload)
```

### ProjectMemoEvent
Matches memos with project-related tags:

```python
# Matches tags: project, todo, task, milestone
@bus.on_pattern(ProjectMemoEvent) 
async def handle_project_memo(event: ProjectMemoEvent):
    await project_handler.save_memo(event.payload)
```

### UrgentMemoEvent
Matches urgent memos by tags or content:

```python
@bus.on_pattern(UrgentMemoEvent)
async def handle_urgent(event: UrgentMemoEvent):
    # Sends notifications and saves with URGENT prefix
    print("🚨 URGENT MEMO RECEIVED")
```

## Custom Event Classes

Create your own pattern-matching events:

### Tag-Based Custom Events

```python
from webhooky_memos import SpecificTagMemoEvent

class MeetingMemoEvent(SpecificTagMemoEvent):
    REQUIRED_TAGS = ["meeting", "notes"]
    MATCH_MODE = "any"  # or "all"
    CASE_SENSITIVE = False

@bus.on_pattern(MeetingMemoEvent)
async def handle_meeting_notes(event: MeetingMemoEvent):
    # Only processes memos with "meeting" or "notes" tags
    pass
```

### Content-Based Custom Events

```python
from webhooky_memos import ContentMatchMemoEvent

class TodoMemoEvent(ContentMatchMemoEvent):
    TEXT_PATTERNS = [r"- \[ \]", r"\* \[ \]", "TODO:", "todo:"]
    USE_REGEX = True
    CASE_SENSITIVE = False

@bus.on_pattern(TodoMemoEvent)
async def handle_todo_memo(event: TodoMemoEvent):
    # Only matches memos with TODO items or checkboxes
    pass
```

### Advanced Custom Events

```python
from pydantic import field_validator
from webhooky_memos import BaseMemoEvent

class LongFormMemoEvent(BaseMemoEvent):
    @field_validator('payload')
    @classmethod
    def validate_long_form(cls, payload):
        if payload.memo.word_count < 500:
            raise ValueError("Memo must be at least 500 words")
        if not payload.memo.has_tags:
            raise ValueError("Long form memos must have tags")
        return payload

@bus.on_pattern(LongFormMemoEvent)
async def handle_long_form(event: LongFormMemoEvent):
    # Only matches memos >500 words with tags
    pass
```

## File Handling

### Basic File Saving

```python
from webhooky_memos import MemoFileHandler

# Create handler with custom organization
handler = MemoFileHandler(
    base_path="./my_memos",
    organize_by="tags",  # "date", "tags", "content_type"
    filename_pattern="{timestamp}_{memo_name}.md",
    include_metadata=True
)

# Save memo
path = await handler.save_memo(event.payload)
```

### Pre-configured Handlers

```python
from webhooky_memos import (
    create_research_handler,
    create_project_handler, 
    create_idea_handler
)

research_handler = create_research_handler("./research")
project_handler = create_project_handler("./projects") 
idea_handler = create_idea_handler("./ideas")
```

### File Organization Options

- **By Date**: `./memos/2024/01/memo.md`
- **By Tags**: `./memos/by_tag/research/memo.md`  
- **By Content Type**: `./memos/todo_lists/memo.md`

## Configuration

### Plugin Configuration

```python
from webhooky_memos import init_plugin

config = {
    "enable_file_saving": True,
    "enable_notifications": True,
    "enable_search_indexing": True,
    "base_save_path": "./saved_memos",
    "research_save_path": "./research_memos",
    "project_save_path": "./project_memos",
    "idea_save_path": "./ideas",
}

init_plugin(config)
```

### Environment Variables

```bash
export WEBHOOKY_MEMOS_SAVE_PATH="./my_memos"
export WEBHOOKY_MEMOS_ENABLE_SEARCH="true"
export WEBHOOKY_MEMOS_NOTIFICATION_WEBHOOK="https://hooks.slack.com/..."
```

## FastAPI Integration

```python
from webhooky.fastapi import create_app
from webhooky import create_dev_config

# Create app with memos plugin
config = create_dev_config(enable_plugins=True)
app = create_app(config=config)

# Configure memos webhook endpoint to point to: 
# http://your-server/webhooks/webhook
```

## Search and Indexing

```python
from webhooky_memos import get_search_indexer, search_saved_memos

# Search memos
results = await search_saved_memos(
    query="research findings",
    tags=["ai", "machine-learning"]
)

for result in results:
    print(f"Found: {result['id']} - {result['content'][:100]}")
```

## Notification Setup

```python
from webhooky_memos import MemoNotificationHandler

# Console notifications
handler = MemoNotificationHandler(["console"])

# Webhook notifications  
handler = MemoNotificationHandler(
    ["webhook"], 
    webhook_url="https://hooks.slack.com/your-webhook"
)

# Custom notification
await handler.notify(
    "Custom Event",
    "Something happened with a memo",
    event.payload
)
```

## Example Workflows

### Research Paper Pipeline

```python
class ResearchPaperEvent(ContentMatchMemoEvent):
    TEXT_PATTERNS = ["research", "paper", "study", "findings"]
    
@bus.on_pattern(ResearchPaperEvent)
async def research_pipeline(event: ResearchPaperEvent):
    # Save to research directory
    await research_handler.save_memo(event.payload)
    
    # Index for search
    await search_indexer.index_memo(event.payload)
    
    # Notify team
    await notification_handler.notify(
        "Research Paper", 
        f"New research: {event.payload.memo.name}",
        event.payload
    )
```

### Project Management

```python
class ProjectTaskEvent(SpecificTagMemoEvent):
    REQUIRED_TAGS = ["project", "task"]
    
@bus.on_pattern(ProjectTaskEvent)
async def project_task_handler(event: ProjectTaskEvent):
    # Save to project-specific directory
    project_name = event.payload.memo.tags[0] if event.payload.memo.tags else "general"
    
    handler = MemoFileHandler(
        base_path=f"./projects/{project_name}",
        organize_by="date"
    )
    
    await handler.save_memo(event.payload)
```

## API Reference

### Event Classes
- `BaseMemoEvent` - Base for all memo events
- `TaggedMemoEvent` - Any memo with tags
- `SpecificTagMemoEvent` - Base for specific tag matching
- `ContentMatchMemoEvent` - Base for content pattern matching
- `ResearchMemoEvent` - Research-related content
- `ProjectMemoEvent` - Project-related tags
- `IdeaMemoEvent` - Idea-related tags
- `UrgentMemoEvent` - Urgent memos (tags/content)
- `PrivateMemoEvent` - Private visibility only
- `PublicMemoEvent` - Public visibility only
- `AttachmentMemoEvent` - Memos with attachments
- `LongMemoEvent` - Long-form content

### Handler Classes
- `MemoFileHandler` - File saving with organization
- `MemoNotificationHandler` - Multi-channel notifications
- `MemoSearchIndexer` - Search index management

### Utility Functions
- `create_research_handler()` - Pre-configured research handler
- `create_project_handler()` - Pre-configured project handler
- `create_idea_handler()` - Pre-configured idea handler
- `search_saved_memos()` - Search indexed memos

## Contributing

1. Fork the repository
2. Create feature branch: `git checkout -b feature/my-feature`
3. Commit changes: `git commit -am 'Add feature'`
4. Push branch: `git push origin feature/my-feature`
5. Submit pull request

## License

MIT License - see LICENSE file for details.
