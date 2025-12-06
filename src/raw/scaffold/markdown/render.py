"""Template rendering for markdown generation."""

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from raw.scaffold.markdown.models import PrimeContext

# Template directory
TEMPLATES_DIR = Path(__file__).parent / "templates"


def get_jinja_env() -> Environment:
    """Get configured Jinja2 environment."""
    return Environment(
        loader=FileSystemLoader(TEMPLATES_DIR),
        autoescape=select_autoescape(default=False),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_prime(ctx: PrimeContext) -> str:
    """Render the prime output using Jinja2 template.

    Args:
        ctx: PrimeContext with workflows and tools data

    Returns:
        Rendered markdown string
    """
    env = get_jinja_env()
    template = env.get_template("prime.md.j2")
    return template.render(ctx=ctx)  # type: ignore[no-any-return]


def render_onboard() -> str:
    """Render the onboard output using Jinja2 template.

    Returns:
        Rendered markdown string (with trailing newline for POSIX compliance)
    """
    env = get_jinja_env()
    template = env.get_template("onboard.md.j2")
    result: str = template.render()
    # Ensure trailing newline for POSIX compliance
    if not result.endswith("\n"):
        result += "\n"
    return result
