#!/usr/bin/env python3
"""Package a skill for distribution, validating and creating a bundle."""

import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from quick_validate import validate_skill


def count_tokens_estimate(text: str) -> int:
    """Rough token estimate (words * 1.3)."""
    words = len(text.split())
    return int(words * 1.3)


def package_skill(skill_dir: Path, output_dir: Path) -> dict:
    """Package skill and return metadata."""
    # Validate first
    errors = validate_skill(skill_dir)
    if errors:
        raise ValueError(f"Validation failed: {errors}")

    skill_name = skill_dir.name
    package_dir = output_dir / skill_name

    # Clean existing package
    if package_dir.exists():
        shutil.rmtree(package_dir)

    # Copy skill directory
    shutil.copytree(skill_dir, package_dir)

    # Calculate stats
    skill_md = (package_dir / "SKILL.md").read_text()
    line_count = len(skill_md.split("\n"))
    token_estimate = count_tokens_estimate(skill_md)

    # Count reference files
    references_dir = package_dir / "references"
    ref_count = 0
    ref_tokens = 0
    if references_dir.exists():
        for ref_file in references_dir.glob("*.md"):
            ref_count += 1
            ref_tokens += count_tokens_estimate(ref_file.read_text())

    # Count scripts
    scripts_dir = package_dir / "scripts"
    script_count = 0
    if scripts_dir.exists():
        script_count = len(list(scripts_dir.glob("*.py")))

    # Generate manifest
    manifest = {
        "name": skill_name,
        "packaged_at": datetime.now().isoformat(),
        "stats": {
            "skill_md_lines": line_count,
            "skill_md_tokens_estimate": token_estimate,
            "reference_files": ref_count,
            "reference_tokens_estimate": ref_tokens,
            "scripts": script_count,
        },
    }

    # Write manifest
    (package_dir / "MANIFEST.json").write_text(
        json.dumps(manifest, indent=2)
    )

    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("skill_dir", type=Path, help="Path to skill directory")
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=Path("dist"),
        help="Output directory (default: dist)"
    )
    args = parser.parse_args()

    if not args.skill_dir.is_dir():
        print(f"Error: Not a directory: {args.skill_dir}")
        return 1

    args.output.mkdir(parents=True, exist_ok=True)

    try:
        manifest = package_skill(args.skill_dir, args.output)
        print(f"Packaged: {manifest['name']}")
        print(f"  Lines: {manifest['stats']['skill_md_lines']}")
        print(f"  Tokens (est): {manifest['stats']['skill_md_tokens_estimate']}")
        print(f"  References: {manifest['stats']['reference_files']}")
        print(f"  Scripts: {manifest['stats']['scripts']}")
        print(f"  Output: {args.output / manifest['name']}")
        return 0
    except ValueError as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
