"""
Node models for markdown parsing
"""
from __future__ import annotations

from typing import Optional, Union

from pydantic import BaseModel

from .base import ListNodeKind, NodeType


class LineBreakNode(BaseModel):
    """Line break node."""
    pass


class ParagraphNode(BaseModel):
    """Paragraph node."""
    children: Optional[list[Node]] = None


class TextNode(BaseModel):
    """Text node."""
    content: str


class CodeBlockNode(BaseModel):
    """Code block node."""
    language: Optional[str] = None
    content: str


class HeadingNode(BaseModel):
    """Heading node."""
    level: int
    children: Optional[list[Node]] = None


class HorizontalRuleNode(BaseModel):
    """Horizontal rule node."""
    symbol: str


class BlockquoteNode(BaseModel):
    """Blockquote node."""
    children: Optional[list[Node]] = None


class ListNode(BaseModel):
    """List node."""
    kind: ListNodeKind
    children: Optional[list[Node]] = None


class OrderedListItemNode(BaseModel):
    """Ordered list item node."""
    number: int
    indent: int
    children: Optional[list[Node]] = None


class UnorderedListItemNode(BaseModel):
    """Unordered list item node."""
    symbol: str
    indent: int
    children: Optional[list[Node]] = None


class TaskListItemNode(BaseModel):
    """Task list item node."""
    symbol: str
    indent: int
    complete: bool
    children: Optional[list[Node]] = None


class MathBlockNode(BaseModel):
    """Math block node."""
    content: str


class TableNodeRow(BaseModel):
    """Table node row."""
    cells: Optional[list[Node]] = None


class TableNode(BaseModel):
    """Table node."""
    header: Optional[list[Node]] = None
    delimiter: Optional[list[str]] = None
    rows: Optional[list[TableNodeRow]] = None


class EmbeddedContentNode(BaseModel):
    """Embedded content node."""
    resource_name: str
    params: Optional[str] = None


class BoldNode(BaseModel):
    """Bold node."""
    symbol: str
    children: Optional[list[Node]] = None


class ItalicNode(BaseModel):
    """Italic node."""
    symbol: str
    content: str


class BoldItalicNode(BaseModel):
    """Bold italic node."""
    symbol: str
    content: str


class CodeNode(BaseModel):
    """Inline code node."""
    content: str


class ImageNode(BaseModel):
    """Image node."""
    alt_text: str
    url: str


class LinkNode(BaseModel):
    """Link node."""
    text: str
    url: str


class AutoLinkNode(BaseModel):
    """Auto link node."""
    url: str
    is_raw_text: bool


class TagNode(BaseModel):
    """Tag node."""
    content: str


class StrikethroughNode(BaseModel):
    """Strikethrough node."""
    content: str


class EscapingCharacterNode(BaseModel):
    """Escaping character node."""
    symbol: str


class MathNode(BaseModel):
    """Math node."""
    content: str


class HighlightNode(BaseModel):
    """Highlight node."""
    content: str


class SubscriptNode(BaseModel):
    """Subscript node."""
    content: str


class SuperscriptNode(BaseModel):
    """Superscript node."""
    content: str


class SpoilerNode(BaseModel):
    """Spoiler node."""
    content: str


# Union of all node types for the main Node model
NodeUnion = Union[
    LineBreakNode,
    ParagraphNode,
    TextNode,
    CodeBlockNode,
    HeadingNode,
    HorizontalRuleNode,
    BlockquoteNode,
    ListNode,
    OrderedListItemNode,
    UnorderedListItemNode,
    TaskListItemNode,
    MathBlockNode,
    TableNode,
    EmbeddedContentNode,
    BoldNode,
    ItalicNode,
    BoldItalicNode,
    CodeNode,
    ImageNode,
    LinkNode,
    AutoLinkNode,
    TagNode,
    StrikethroughNode,
    EscapingCharacterNode,
    MathNode,
    HighlightNode,
    SubscriptNode,
    SuperscriptNode,
    SpoilerNode,
]


class Node(BaseModel):
    """Main node model."""
    type: NodeType
    line_break_node: Optional[LineBreakNode] = None
    paragraph_node: Optional[ParagraphNode] = None
    text_node: Optional[TextNode] = None
    code_block_node: Optional[CodeBlockNode] = None
    heading_node: Optional[HeadingNode] = None
    horizontal_rule_node: Optional[HorizontalRuleNode] = None
    blockquote_node: Optional[BlockquoteNode] = None
    list_node: Optional[ListNode] = None
    ordered_list_item_node: Optional[OrderedListItemNode] = None
    unordered_list_item_node: Optional[UnorderedListItemNode] = None
    task_list_item_node: Optional[TaskListItemNode] = None
    math_block_node: Optional[MathBlockNode] = None
    table_node: Optional[TableNode] = None
    embedded_content_node: Optional[EmbeddedContentNode] = None
    bold_node: Optional[BoldNode] = None
    italic_node: Optional[ItalicNode] = None
    bold_italic_node: Optional[BoldItalicNode] = None
    code_node: Optional[CodeNode] = None
    image_node: Optional[ImageNode] = None
    link_node: Optional[LinkNode] = None
    auto_link_node: Optional[AutoLinkNode] = None
    tag_node: Optional[TagNode] = None
    strikethrough_node: Optional[StrikethroughNode] = None
    escaping_character_node: Optional[EscapingCharacterNode] = None
    math_node: Optional[MathNode] = None
    highlight_node: Optional[HighlightNode] = None
    subscript_node: Optional[SubscriptNode] = None
    superscript_node: Optional[SuperscriptNode] = None
    spoiler_node: Optional[SpoilerNode] = None


# Fix forward references
ParagraphNode.model_rebuild()
BlockquoteNode.model_rebuild()
ListNode.model_rebuild()
OrderedListItemNode.model_rebuild()
UnorderedListItemNode.model_rebuild()
TaskListItemNode.model_rebuild()
BoldNode.model_rebuild()
TableNodeRow.model_rebuild()
TableNode.model_rebuild()