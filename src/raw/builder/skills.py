"""Builder skill discovery and management.

Discovers repo-local skills from builder/skills/**/SKILL.md
Skills use Agent Skills-style frontmatter for metadata.
"""

import logging
from pathlib import Path
from typing import NamedTuple

import yaml

logger = logging.getLogger(__name__)


class Skill(NamedTuple):
    """A discovered builder skill.

    Attributes:
        name: Unique skill name (from frontmatter)
        description: Brief description of what the skill does
        path: Path to SKILL.md file
    """

    name: str
    description: str
    path: Path

    @property
    def content(self) -> str:
        """Load full SKILL.md content on demand.

        Returns:
            Complete skill content including frontmatter
        """
        return self.path.read_text()

    @property
    def instructions(self) -> str:
        """Get skill instructions without frontmatter.

        Returns:
            Skill content with frontmatter stripped
        """
        content = self.content

        # Skip frontmatter
        if content.startswith("---\n"):
            parts = content.split("---\n", 2)
            if len(parts) >= 3:
                return parts[2].strip()

        return content


def discover_skills(skills_dir: Path | None = None) -> list[Skill]:
    """Discover skills from builder/skills/**/SKILL.md.

    Recursively searches for SKILL.md files and parses their frontmatter.
    Validates that each skill has required name and description fields.

    Args:
        skills_dir: Directory to search (defaults to builder/skills)

    Returns:
        List of discovered skills

    Example:
        skills = discover_skills()
        for skill in skills:
            print(f"{skill.name}: {skill.description}")
    """
    if skills_dir is None:
        skills_dir = Path.cwd() / "builder" / "skills"

    if not skills_dir.exists():
        return []

    skills: list[Skill] = []

    for skill_file in skills_dir.rglob("SKILL.md"):
        try:
            content = skill_file.read_text()

            # Parse frontmatter
            if not content.startswith("---\n"):
                logger.warning("%s missing frontmatter (---)", skill_file)
                continue

            parts = content.split("---\n", 2)
            if len(parts) < 3:
                logger.warning("%s invalid frontmatter format", skill_file)
                continue

            frontmatter = yaml.safe_load(parts[1])

            # Validate required fields
            if "name" not in frontmatter:
                logger.warning("%s missing 'name' in frontmatter", skill_file)
                continue

            if "description" not in frontmatter:
                logger.warning("%s missing 'description' in frontmatter", skill_file)
                continue

            # Create skill
            skills.append(
                Skill(
                    name=frontmatter["name"],
                    description=frontmatter["description"],
                    path=skill_file,
                )
            )

        except yaml.YAMLError as e:
            logger.warning("%s has invalid YAML frontmatter: %s", skill_file, e)
            continue
        except Exception as e:
            logger.warning("Failed to parse %s: %s", skill_file, e)
            continue

    return skills


def find_skill_by_name(name: str, skills: list[Skill]) -> Skill | None:
    """Find a skill by name.

    Args:
        name: Skill name to search for
        skills: List of skills to search

    Returns:
        Matching skill or None if not found
    """
    for skill in skills:
        if skill.name == name:
            return skill
    return None


def inject_skills_into_prompt(skills: list[Skill], base_prompt: str) -> str:
    """Inject <available_skills> section into system prompt.

    Args:
        skills: List of discovered skills
        base_prompt: Base system prompt

    Returns:
        Prompt with skills section injected

    Example:
        skills = discover_skills()
        prompt = inject_skills_into_prompt(skills, "You are a builder agent...")
    """
    if not skills:
        return base_prompt

    skills_section = "\n<available_skills>\n"
    skills_section += "The following skills are available to guide your work:\n\n"

    for skill in skills:
        skills_section += f"- **{skill.name}**: {skill.description}\n"

    skills_section += "\nTo use a skill, mention its name (e.g., '@plan-mode') and I will load "
    skills_section += "the full instructions for you.\n"
    skills_section += "</available_skills>\n\n"

    return base_prompt + skills_section


def format_skill_for_injection(skill: Skill) -> str:
    """Format skill content for injection into agent context.

    Args:
        skill: Skill to format

    Returns:
        Formatted skill content ready for injection

    Example:
        skill = find_skill_by_name("plan-mode", skills)
        formatted = format_skill_for_injection(skill)
        # Inject into agent messages
    """
    return f"""
<skill name="{skill.name}">
{skill.instructions}
</skill>
"""
