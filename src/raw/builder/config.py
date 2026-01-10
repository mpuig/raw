"""Builder configuration schema and loading."""

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class BudgetConfig(BaseModel):
    """Budget limits for builder execution."""

    max_iterations: int = Field(
        default=10, description="Maximum plan-execute cycles before stopping"
    )
    max_minutes: int = Field(default=30, description="Maximum wall time in minutes")
    doom_loop_threshold: int = Field(
        default=3, description="Break on N consecutive identical tool calls"
    )


class GateCommand(BaseModel):
    """Configuration for an optional gate command."""

    command: str = Field(..., description="Shell command to execute")
    timeout_seconds: int = Field(default=300, description="Command timeout in seconds")


class GatesConfig(BaseModel):
    """Quality gates configuration."""

    default: list[str] = Field(
        default_factory=lambda: ["validate", "dry"],
        description="Gates that always run (validate, dry)",
    )
    optional: dict[str, GateCommand] = Field(
        default_factory=dict, description="Optional project-specific gates (pytest, ruff, etc.)"
    )


class SkillsConfig(BaseModel):
    """Skills discovery configuration."""

    auto_discover: bool = Field(
        default=True, description="Automatically discover skills from builder/skills/"
    )
    fallback_to_builtin: bool = Field(
        default=False, description="Use built-in skills if no repo skills found"
    )


class ModeConfig(BaseModel):
    """Builder mode configuration."""

    plan_first: bool = Field(default=True, description="Always start with plan mode")
    auto_execute: bool = Field(
        default=False, description="Automatically execute without confirmation"
    )


class BuilderConfig(BaseModel):
    """Complete builder configuration.

    Loaded from .raw/config.yaml under 'builder:' section.
    CLI flags override config values with precedence:
    1. CLI flags (highest)
    2. .raw/config.yaml
    3. Defaults (lowest)
    """

    budgets: BudgetConfig = Field(default_factory=BudgetConfig)
    gates: GatesConfig = Field(default_factory=GatesConfig)
    skills: SkillsConfig = Field(default_factory=SkillsConfig)
    mode: ModeConfig = Field(default_factory=ModeConfig)


def load_builder_config(project_root: Path | None = None) -> BuilderConfig:
    """Load builder configuration from .raw/config.yaml.

    Args:
        project_root: Project root directory (contains .raw/). Defaults to cwd.

    Returns:
        BuilderConfig with values from file or defaults

    Example:
        config = load_builder_config()
        print(f"Max iterations: {config.budgets.max_iterations}")
    """
    if project_root is None:
        project_root = Path.cwd()

    config_path = project_root / ".raw" / "config.yaml"

    # Return defaults if no config file
    if not config_path.exists():
        return BuilderConfig()

    # Load YAML
    try:
        with open(config_path) as f:
            raw_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ValueError(f"Invalid YAML in {config_path}: {e}") from e

    # Extract builder section
    builder_section = raw_config.get("builder", {})

    # Parse with Pydantic (validates structure)
    try:
        return BuilderConfig.model_validate(builder_section)
    except Exception as e:
        raise ValueError(f"Invalid builder config in {config_path}: {e}") from e


def merge_cli_overrides(
    config: BuilderConfig,
    max_iterations: int | None = None,
    max_minutes: int | None = None,
) -> BuilderConfig:
    """Merge CLI flag overrides into config.

    Args:
        config: Base configuration from file
        max_iterations: CLI override for max iterations
        max_minutes: CLI override for max minutes

    Returns:
        New BuilderConfig with overrides applied

    Example:
        config = load_builder_config()
        config = merge_cli_overrides(config, max_iterations=5)
    """
    # Create a copy to avoid mutating original
    updated = config.model_copy(deep=True)

    # Apply overrides
    if max_iterations is not None:
        updated.budgets.max_iterations = max_iterations

    if max_minutes is not None:
        updated.budgets.max_minutes = max_minutes

    return updated


def save_example_builder_config(output_path: Path) -> None:
    """Save example builder configuration to file.

    Useful for documentation or initialization.

    Args:
        output_path: Path to write example config.yaml
    """
    example = {
        "builder": {
            "budgets": {
                "max_iterations": 10,
                "max_minutes": 30,
                "doom_loop_threshold": 3,
            },
            "gates": {
                "default": ["validate", "dry"],
                "optional": {
                    "pytest": {
                        "command": "pytest tests/ -v",
                        "timeout_seconds": 300,
                    },
                    "ruff": {
                        "command": "ruff check . && ruff format . --check",
                        "timeout_seconds": 60,
                    },
                    "typecheck": {
                        "command": "mypy src/",
                        "timeout_seconds": 120,
                    },
                },
            },
            "skills": {
                "auto_discover": True,
                "fallback_to_builtin": False,
            },
            "mode": {
                "plan_first": True,
                "auto_execute": False,
            },
        }
    }

    with open(output_path, "w") as f:
        yaml.dump(example, f, default_flow_style=False, sort_keys=False)
