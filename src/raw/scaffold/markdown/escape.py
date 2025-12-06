"""Markdown escaping and sanitization utilities."""

import re


def escape_pipe(text: str) -> str:
    """Escape pipe characters for table cells."""
    return text.replace("|", "\\|")


def escape_backtick(text: str) -> str:
    """Escape backticks to prevent code block injection."""
    return text.replace("`", "\\`")


def escape_table_cell(text: str) -> str:
    """Escape content for safe use in markdown table cells.

    Handles:
    - Pipe characters (|)
    - Newlines (replaced with space)
    - Leading/trailing whitespace
    """
    text = re.sub(r"\s+", " ", text)
    text = escape_pipe(text)
    return text.strip()


def escape_inline_code(text: str) -> str:
    """Escape content for use in inline code spans.

    If text contains backticks, uses double backticks with spacing.
    """
    if "`" not in text:
        return f"`{text}`"
    # Use double backticks with space padding
    return f"`` {text} ``"


def truncate(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to max_length, adding suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug.

    Used for generating anchor links from headings.
    """
    slug = text.lower()
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace in text (collapse multiple spaces/newlines)."""
    return re.sub(r"\s+", " ", text).strip()
