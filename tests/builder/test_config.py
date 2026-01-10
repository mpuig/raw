"""Tests for builder configuration loading and merging."""

import tempfile
from pathlib import Path

import pytest
import yaml

from raw.builder.config import (
    BuilderConfig,
    load_builder_config,
    merge_cli_overrides,
    save_example_builder_config,
)


def test_default_builder_config():
    """Test default configuration values."""
    config = BuilderConfig()

    assert config.budgets.max_iterations == 10
    assert config.budgets.max_minutes == 30
    assert config.budgets.doom_loop_threshold == 3

    assert config.gates.default == ["validate", "dry"]
    assert config.gates.optional == {}

    assert config.skills.auto_discover is True
    assert config.skills.fallback_to_builtin is False

    assert config.mode.plan_first is True
    assert config.mode.auto_execute is False


def test_load_builder_config_no_file():
    """Test loading config when no file exists."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = load_builder_config(Path(tmpdir))

        # Should return defaults
        assert config.budgets.max_iterations == 10
        assert config.gates.default == ["validate", "dry"]


def test_load_builder_config_with_file():
    """Test loading config from .raw/config.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        raw_dir = project_root / ".raw"
        raw_dir.mkdir()

        config_path = raw_dir / "config.yaml"
        config_data = {
            "builder": {
                "budgets": {
                    "max_iterations": 5,
                    "max_minutes": 15,
                },
                "gates": {
                    "default": ["validate"],
                    "optional": {
                        "pytest": {
                            "command": "pytest",
                            "timeout_seconds": 60,
                        }
                    },
                },
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_builder_config(project_root)

        assert config.budgets.max_iterations == 5
        assert config.budgets.max_minutes == 15
        assert config.budgets.doom_loop_threshold == 3  # Default

        assert config.gates.default == ["validate"]
        assert "pytest" in config.gates.optional
        assert config.gates.optional["pytest"].command == "pytest"
        assert config.gates.optional["pytest"].timeout_seconds == 60


def test_load_builder_config_empty_section():
    """Test loading config with empty builder section."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        raw_dir = project_root / ".raw"
        raw_dir.mkdir()

        config_path = raw_dir / "config.yaml"
        config_data = {"builder": {}}

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        config = load_builder_config(project_root)

        # Should use defaults
        assert config.budgets.max_iterations == 10
        assert config.gates.default == ["validate", "dry"]


def test_load_builder_config_invalid_yaml():
    """Test loading config with invalid YAML."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        raw_dir = project_root / ".raw"
        raw_dir.mkdir()

        config_path = raw_dir / "config.yaml"
        config_path.write_text("builder: [\ninvalid yaml")

        with pytest.raises(ValueError, match="Invalid YAML"):
            load_builder_config(project_root)


def test_load_builder_config_invalid_structure():
    """Test loading config with invalid structure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        raw_dir = project_root / ".raw"
        raw_dir.mkdir()

        config_path = raw_dir / "config.yaml"
        config_data = {
            "builder": {
                "budgets": {
                    "max_iterations": "not_an_int",  # Invalid type
                }
            }
        }

        with open(config_path, "w") as f:
            yaml.dump(config_data, f)

        with pytest.raises(ValueError, match="Invalid builder config"):
            load_builder_config(project_root)


def test_merge_cli_overrides():
    """Test merging CLI overrides into config."""
    config = BuilderConfig()

    # Override max_iterations
    updated = merge_cli_overrides(config, max_iterations=5)
    assert updated.budgets.max_iterations == 5
    assert updated.budgets.max_minutes == 30  # Unchanged

    # Override max_minutes
    updated = merge_cli_overrides(config, max_minutes=15)
    assert updated.budgets.max_iterations == 10  # Unchanged
    assert updated.budgets.max_minutes == 15

    # Override both
    updated = merge_cli_overrides(config, max_iterations=7, max_minutes=20)
    assert updated.budgets.max_iterations == 7
    assert updated.budgets.max_minutes == 20

    # Original config unchanged (deep copy)
    assert config.budgets.max_iterations == 10
    assert config.budgets.max_minutes == 30


def test_merge_cli_overrides_none_values():
    """Test merging with None values (no override)."""
    config = BuilderConfig()

    updated = merge_cli_overrides(config, max_iterations=None, max_minutes=None)

    # Should be unchanged
    assert updated.budgets.max_iterations == 10
    assert updated.budgets.max_minutes == 30


def test_save_example_builder_config():
    """Test saving example configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = Path(tmpdir) / "example.yaml"

        save_example_builder_config(output_path)

        assert output_path.exists()

        # Load and validate
        with open(output_path) as f:
            data = yaml.safe_load(f)

        assert "builder" in data
        assert "budgets" in data["builder"]
        assert "gates" in data["builder"]
        assert data["builder"]["budgets"]["max_iterations"] == 10
        assert data["builder"]["gates"]["default"] == ["validate", "dry"]


def test_builder_config_gate_command_validation():
    """Test GateCommand model validation."""
    config_data = {
        "budgets": {"max_iterations": 10},
        "gates": {
            "optional": {
                "pytest": {
                    "command": "pytest tests/",
                    "timeout_seconds": 120,
                }
            }
        },
    }

    config = BuilderConfig.model_validate(config_data)

    assert "pytest" in config.gates.optional
    assert config.gates.optional["pytest"].command == "pytest tests/"
    assert config.gates.optional["pytest"].timeout_seconds == 120
