#!/usr/bin/env python3
"""Initialize a new skill directory with required structure."""

import argparse
import re
import sys
from pathlib import Path

SKILL_TEMPLATE = '''---
name: {name}
description: {description}
---

# {title}

One-line summary of what this skill does.

## When to use this skill

Use this skill when:
- First trigger condition
- Second trigger condition

## Key directives

1. **First rule** - Description of requirement
2. **Second rule** - Description of requirement

## Process

### Step 1: First step

Instructions for the first step.

### Step 2: Second step

Instructions for the second step.

## Validation checklist

Before completing:
- [ ] First check
- [ ] Second check

## References

- [Additional guide](references/guide.md)
'''


def validate_name(name: str) -> tuple[bool, str]:
    """Validate skill name against spec requirements."""
    if len(name) > 64:
        return False, "Name exceeds 64 characters"
    if not re.match(r'^[a-z0-9]+(-[a-z0-9]+)*$', name):
        return False, "Name must be lowercase letters, numbers, and single hyphens"
    if name.startswith('-') or name.endswith('-'):
        return False, "Name cannot start or end with hyphen"
    if '--' in name:
        return False, "Name cannot contain consecutive hyphens"
    return True, ""


def init_skill(name: str, description: str, base_dir: Path) -> Path:
    """Create skill directory structure."""
    valid, error = validate_name(name)
    if not valid:
        raise ValueError(f"Invalid skill name: {error}")

    skill_dir = base_dir / name
    if skill_dir.exists():
        raise FileExistsError(f"Skill directory already exists: {skill_dir}")

    # Create directories
    skill_dir.mkdir(parents=True)
    (skill_dir / "references").mkdir()
    (skill_dir / "scripts").mkdir()

    # Create SKILL.md
    title = name.replace("-", " ").title()
    content = SKILL_TEMPLATE.format(
        name=name,
        description=description,
        title=title,
    )
    (skill_dir / "SKILL.md").write_text(content)

    # Create placeholder reference
    (skill_dir / "references" / "guide.md").write_text(
        f"# {title} guide\n\nDetailed guidance for this skill.\n"
    )

    return skill_dir


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="Skill name (lowercase, hyphens)")
    parser.add_argument(
        "-d", "--description",
        required=True,
        help="Skill description (max 1024 chars)"
    )
    parser.add_argument(
        "-o", "--output",
        default="skills",
        help="Base directory for skills (default: skills)"
    )
    args = parser.parse_args()

    if len(args.description) > 1024:
        print(f"Error: Description exceeds 1024 characters ({len(args.description)})")
        return 1

    try:
        skill_dir = init_skill(args.name, args.description, Path(args.output))
        print(f"Created skill: {skill_dir}")
        print(f"  SKILL.md")
        print(f"  references/guide.md")
        print(f"  scripts/")
        return 0
    except (ValueError, FileExistsError) as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
