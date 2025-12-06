"""Template rendering utilities for code scaffolds."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"


def _get_environment() -> Environment:
    """Get Jinja2 environment configured for code templates."""
    return Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        keep_trailing_newline=True,
        trim_blocks=False,
        lstrip_blocks=False,
    )


def render_workflow_template(template_name: str, **context: Any) -> str:
    """Render a workflow template.

    Args:
        template_name: Template filename (e.g., "run.py.j2")
        **context: Template variables

    Returns:
        Rendered template content
    """
    env = _get_environment()
    template = env.get_template(f"workflow/{template_name}")
    return template.render(**context)  # type: ignore[no-any-return]


def render_tool_template(template_name: str, **context: Any) -> str:
    """Render a tool template.

    Args:
        template_name: Template filename (e.g., "tool.py.j2")
        **context: Template variables

    Returns:
        Rendered template content
    """
    env = _get_environment()
    template = env.get_template(f"tool/{template_name}")
    return template.render(**context)  # type: ignore[no-any-return]
