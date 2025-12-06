"""Markdown generation utilities for RAW.

This module provides structured content generation with:
- Escape utilities for safe content embedding
- Builder classes for tables, code blocks, sections
- Pydantic models for content structure
- Jinja2 templates for document rendering
"""

from raw.scaffold.markdown.builders import (
    CodeBlock,
    Document,
    List,
    Section,
    Table,
)
from raw.scaffold.markdown.escape import (
    escape_backtick,
    escape_inline_code,
    escape_pipe,
    escape_table_cell,
    normalize_whitespace,
    slugify,
    truncate,
)
from raw.scaffold.markdown.models import (
    CodeExample,
    CommandInfo,
    PrimeContext,
    ToolSummary,
    WorkflowSummary,
)
from raw.scaffold.markdown.render import (
    render_onboard,
    render_prime,
)

__all__ = [
    # Builders
    "Table",
    "CodeBlock",
    "Section",
    "List",
    "Document",
    # Models
    "WorkflowSummary",
    "ToolSummary",
    "CommandInfo",
    "CodeExample",
    "PrimeContext",
    # Render functions
    "render_prime",
    "render_onboard",
    # Escape utilities
    "escape_pipe",
    "escape_backtick",
    "escape_table_cell",
    "escape_inline_code",
    "truncate",
    "slugify",
    "normalize_whitespace",
]
