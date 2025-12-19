#!/usr/bin/env python3
"""Validate a skill against the Agent Skills specification."""

import argparse
import re
import sys
from pathlib import Path

import yaml


def validate_skill(skill_dir: Path) -> list[str]:
    """Validate skill directory and return list of errors."""
    errors = []

    # Check SKILL.md exists
    skill_file = skill_dir / "SKILL.md"
    if not skill_file.exists():
        errors.append("Missing SKILL.md")
        return errors

    content = skill_file.read_text()
    lines = content.split("\n")

    # Check frontmatter exists
    if not content.startswith("---"):
        errors.append("SKILL.md must start with YAML frontmatter (---)")
        return errors

    # Extract frontmatter
    try:
        end_idx = content.index("---", 3)
        frontmatter_text = content[3:end_idx].strip()
        frontmatter = yaml.safe_load(frontmatter_text)
    except (ValueError, yaml.YAMLError) as e:
        errors.append(f"Invalid YAML frontmatter: {e}")
        return errors

    # Validate name
    name = frontmatter.get("name")
    if not name:
        errors.append("Missing required field: name")
    else:
        if len(name) > 64:
            errors.append(f"Name exceeds 64 characters ({len(name)})")
        if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
            errors.append("Name must be lowercase letters, numbers, and single hyphens")
        if name != skill_dir.name:
            errors.append(f"Name '{name}' does not match directory '{skill_dir.name}'")

    # Validate description
    description = frontmatter.get("description")
    if not description:
        errors.append("Missing required field: description")
    elif len(description) > 1024:
        errors.append(f"Description exceeds 1024 characters ({len(description)})")

    # Check line count
    line_count = len(lines)
    if line_count > 500:
        errors.append(f"SKILL.md exceeds 500 lines ({line_count})")

    # Check for recommended sections
    content_lower = content.lower()
    if "## when to use" not in content_lower:
        errors.append("Missing recommended section: 'When to use'")

    # Check references use relative paths
    if "references/" in content:
        # Check that referenced files exist
        for match in re.finditer(r'\(references/([^)]+)\)', content):
            ref_path = skill_dir / "references" / match.group(1)
            if not ref_path.exists():
                errors.append(f"Referenced file does not exist: {ref_path}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", type=Path, help="Path to skill directory")
    parser.add_argument("-q", "--quiet", action="store_true", help="Only show errors")
    args = parser.parse_args()

    if not args.skill_dir.is_dir():
        print(f"Error: Not a directory: {args.skill_dir}")
        return 1

    errors = validate_skill(args.skill_dir)

    if errors:
        print(f"Validation failed for {args.skill_dir.name}:")
        for error in errors:
            print(f"  - {error}")
        return 1
    else:
        if not args.quiet:
            print(f"Validation passed: {args.skill_dir.name}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
