"""Tests for builder skill discovery and management."""

import tempfile
from pathlib import Path

import pytest

from raw.builder.skills import (
    discover_skills,
    find_skill_by_name,
    format_skill_for_injection,
    inject_skills_into_prompt,
)


def create_test_skill(skills_dir: Path, skill_name: str, content: str) -> Path:
    """Helper to create a test SKILL.md file."""
    skill_dir = skills_dir / skill_name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    skill_file.write_text(content)
    return skill_file


def test_discover_skills_basic():
    """Test basic skill discovery."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        # Create test skills
        create_test_skill(
            skills_dir,
            "test-skill",
            """---
name: test-skill
description: A test skill
---
This is the skill content.
""",
        )

        create_test_skill(
            skills_dir,
            "another-skill",
            """---
name: another-skill
description: Another test skill
---
More skill content here.
""",
        )

        # Discover skills
        skills = discover_skills(skills_dir)

        assert len(skills) == 2
        names = [s.name for s in skills]
        assert "test-skill" in names
        assert "another-skill" in names


def test_discover_skills_nested():
    """Test discovering skills in nested directories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        # Create nested skill
        nested_dir = skills_dir / "category" / "subcategory"
        nested_dir.mkdir(parents=True)
        (nested_dir / "SKILL.md").write_text(
            """---
name: nested-skill
description: A nested skill
---
Nested content.
"""
        )

        skills = discover_skills(skills_dir)

        assert len(skills) == 1
        assert skills[0].name == "nested-skill"


def test_discover_skills_missing_frontmatter():
    """Test skill without frontmatter is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        create_test_skill(skills_dir, "invalid", "Just content, no frontmatter")

        skills = discover_skills(skills_dir)

        assert len(skills) == 0


def test_discover_skills_invalid_frontmatter():
    """Test skill with invalid YAML frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        create_test_skill(
            skills_dir,
            "invalid-yaml",
            """---
name: [
invalid yaml
---
Content.
""",
        )

        skills = discover_skills(skills_dir)

        assert len(skills) == 0


def test_discover_skills_missing_name():
    """Test skill without name field is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        create_test_skill(
            skills_dir,
            "no-name",
            """---
description: Missing name
---
Content.
""",
        )

        skills = discover_skills(skills_dir)

        assert len(skills) == 0


def test_discover_skills_missing_description():
    """Test skill without description field is skipped."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        create_test_skill(
            skills_dir,
            "no-desc",
            """---
name: no-desc
---
Content.
""",
        )

        skills = discover_skills(skills_dir)

        assert len(skills) == 0


def test_discover_skills_empty_directory():
    """Test discovering skills from empty directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir) / "empty"
        skills_dir.mkdir()

        skills = discover_skills(skills_dir)

        assert skills == []


def test_discover_skills_nonexistent_directory():
    """Test discovering skills when directory doesn't exist."""
    skills_dir = Path("/nonexistent/path")
    skills = discover_skills(skills_dir)
    assert skills == []


def test_skill_content_property():
    """Test Skill.content property."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        content = """---
name: test
description: Test skill
---
This is the full content.
Including multiple lines.
"""

        create_test_skill(skills_dir, "test", content)

        skills = discover_skills(skills_dir)
        skill = skills[0]

        assert skill.content == content


def test_skill_instructions_property():
    """Test Skill.instructions property strips frontmatter."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        create_test_skill(
            skills_dir,
            "test",
            """---
name: test
description: Test skill
---
This is the instructions.
Without frontmatter.
""",
        )

        skills = discover_skills(skills_dir)
        skill = skills[0]

        instructions = skill.instructions
        assert "---" not in instructions
        assert "name:" not in instructions
        assert "This is the instructions." in instructions


def test_find_skill_by_name():
    """Test finding skill by name."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        create_test_skill(
            skills_dir,
            "skill-one",
            """---
name: skill-one
description: First skill
---
Content.
""",
        )

        create_test_skill(
            skills_dir,
            "skill-two",
            """---
name: skill-two
description: Second skill
---
Content.
""",
        )

        skills = discover_skills(skills_dir)

        found = find_skill_by_name("skill-two", skills)
        assert found is not None
        assert found.name == "skill-two"

        not_found = find_skill_by_name("nonexistent", skills)
        assert not_found is None


def test_inject_skills_into_prompt():
    """Test injecting skills section into prompt."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        create_test_skill(
            skills_dir,
            "skill-a",
            """---
name: skill-a
description: Skill A description
---
Content.
""",
        )

        create_test_skill(
            skills_dir,
            "skill-b",
            """---
name: skill-b
description: Skill B description
---
Content.
""",
        )

        skills = discover_skills(skills_dir)

        base_prompt = "You are a builder agent."
        enhanced_prompt = inject_skills_into_prompt(skills, base_prompt)

        assert "You are a builder agent." in enhanced_prompt
        assert "<available_skills>" in enhanced_prompt
        assert "skill-a" in enhanced_prompt
        assert "Skill A description" in enhanced_prompt
        assert "skill-b" in enhanced_prompt
        assert "Skill B description" in enhanced_prompt


def test_inject_skills_empty_list():
    """Test injecting skills with empty list."""
    base_prompt = "You are a builder agent."
    enhanced_prompt = inject_skills_into_prompt([], base_prompt)

    # Should return unchanged
    assert enhanced_prompt == base_prompt


def test_format_skill_for_injection():
    """Test formatting skill for injection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        skills_dir = Path(tmpdir)

        create_test_skill(
            skills_dir,
            "test-skill",
            """---
name: test-skill
description: Test
---
These are the instructions.
Line 1.
Line 2.
""",
        )

        skills = discover_skills(skills_dir)
        skill = skills[0]

        formatted = format_skill_for_injection(skill)

        assert '<skill name="test-skill">' in formatted
        assert "</skill>" in formatted
        assert "These are the instructions." in formatted
        assert "Line 1." in formatted
        assert "Line 2." in formatted
        assert "---" not in formatted  # Frontmatter should be stripped
