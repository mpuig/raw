"""Hooks command implementation."""

import json
import shutil
from importlib.resources import files
from pathlib import Path

from raw.discovery.display import console, print_info, print_success

RAW_HOOK_COMMAND = "raw prime"
RAW_SKILLS = ["raw-workflow-creator", "raw-tool-creator"]


def _get_project_settings_path() -> Path:
    """Get path to project-level Claude settings."""
    return Path.cwd() / ".claude" / "settings.local.json"


def _load_claude_settings() -> dict:
    """Load project-level Claude Code settings."""
    settings_path = _get_project_settings_path()
    if not settings_path.exists():
        return {}
    try:
        return json.loads(settings_path.read_text())
    except (json.JSONDecodeError, OSError):
        return {}


def _save_claude_settings(settings: dict) -> None:
    """Save project-level Claude Code settings."""
    settings_path = _get_project_settings_path()
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")


def _has_raw_hook(hooks_list: list) -> bool:
    """Check if RAW hook exists in a hooks list."""
    for entry in hooks_list:
        for hook in entry.get("hooks", []):
            if hook.get("command") == RAW_HOOK_COMMAND:
                return True
    return False


def _add_raw_hook(hooks_list: list) -> list:
    """Add RAW hook to a hooks list if not present."""
    if _has_raw_hook(hooks_list):
        return hooks_list

    hooks_list.append(
        {
            "matcher": "",
            "hooks": [{"type": "command", "command": RAW_HOOK_COMMAND}],
        }
    )
    return hooks_list


def _remove_raw_hook(hooks_list: list) -> list:
    """Remove RAW hook from a hooks list."""
    result = []
    for entry in hooks_list:
        filtered_hooks = [h for h in entry.get("hooks", []) if h.get("command") != RAW_HOOK_COMMAND]
        if filtered_hooks:
            entry["hooks"] = filtered_hooks
            result.append(entry)
    return result


def _get_skills_source_dir() -> Path | None:
    """Get the path to RAW's bundled skills directory."""
    try:
        package_root = files("raw").joinpath("..").joinpath("..").joinpath("skills")
        if hasattr(package_root, "_path"):
            skills_path = Path(package_root._path)
            if skills_path.exists():
                return skills_path
    except Exception:
        pass

    this_file = Path(__file__)
    # src/raw/commands/hooks.py -> go up to repo root -> skills/
    repo_root = this_file.parent.parent.parent.parent
    skills_path = repo_root / "skills"
    if skills_path.exists():
        return skills_path

    return None


def _get_project_skills_dir() -> Path:
    """Get path to project-level Claude skills directory."""
    return Path.cwd() / ".claude" / "skills"


def _install_skills() -> list[str]:
    """Copy RAW skills to project's .claude/skills/ directory.

    Returns list of installed skill names.
    """
    source_dir = _get_skills_source_dir()
    if not source_dir:
        return []

    target_dir = _get_project_skills_dir()
    target_dir.mkdir(parents=True, exist_ok=True)

    installed = []
    for skill_name in RAW_SKILLS:
        source_skill = source_dir / skill_name
        target_skill = target_dir / skill_name

        if not source_skill.exists():
            continue

        if target_skill.exists():
            shutil.rmtree(target_skill)

        shutil.copytree(source_skill, target_skill)
        installed.append(skill_name)

    return installed


def _remove_skills() -> list[str]:
    """Remove RAW skills from project's .claude/skills/ directory.

    Returns list of removed skill names.
    """
    target_dir = _get_project_skills_dir()
    if not target_dir.exists():
        return []

    removed = []
    for skill_name in RAW_SKILLS:
        skill_path = target_dir / skill_name
        if skill_path.exists():
            shutil.rmtree(skill_path)
            removed.append(skill_name)

    if target_dir.exists() and not any(target_dir.iterdir()):
        target_dir.rmdir()

    return removed


def _add_skill_permission(settings: dict, skill_name: str) -> None:
    """Add skill permission to settings."""
    if "permissions" not in settings:
        settings["permissions"] = {}
    
    if "allow" not in settings["permissions"]:
        settings["permissions"]["allow"] = []
    
    permission = f"Skill({skill_name})"
    if permission not in settings["permissions"]["allow"]:
        settings["permissions"]["allow"].append(permission)


def hooks_install_command() -> None:
    """Install RAW hooks and skills into Claude Code (project-level).

    This function contains the business logic for the hooks install command.
    """
    settings = _load_claude_settings()

    if "hooks" not in settings:
        settings["hooks"] = {}

    hooks_config = settings["hooks"]

    for event in ["SessionStart", "PreCompact"]:
        if event not in hooks_config:
            hooks_config[event] = []
        hooks_config[event] = _add_raw_hook(hooks_config[event])

    installed_skills = _install_skills()
    
    # Auto-allow installed skills
    for skill in installed_skills:
        _add_skill_permission(settings, skill)

    _save_claude_settings(settings)

    print_success("RAW hooks installed")
    console.print(f"  Hooks: {_get_project_settings_path()}")
    console.print("  Events: SessionStart, PreCompact")
    if installed_skills:
        console.print(f"  Skills: {_get_project_skills_dir()}")
        for skill in installed_skills:
            console.print(f"    - {skill}")
    console.print("\n  Hooks run [cyan]raw prime[/] on session start.")
    if installed_skills:
        console.print("  Skills are auto-invoked by Claude when creating workflows/tools.")


def hooks_uninstall_command() -> None:
    """Remove RAW hooks and skills from Claude Code.

    This function contains the business logic for the hooks uninstall command.
    """
    settings = _load_claude_settings()

    hooks_removed = False
    if "hooks" in settings:
        hooks_config = settings["hooks"]

        for event in ["SessionStart", "PreCompact"]:
            if event in hooks_config:
                original_len = len(hooks_config[event])
                hooks_config[event] = _remove_raw_hook(hooks_config[event])
                if len(hooks_config[event]) < original_len:
                    hooks_removed = True
                if not hooks_config[event]:
                    del hooks_config[event]

        if hooks_removed:
            _save_claude_settings(settings)

    # Remove skills
    removed_skills = _remove_skills()

    if hooks_removed or removed_skills:
        print_success("RAW integration removed")
        if hooks_removed:
            console.print("  Hooks: removed from settings")
        if removed_skills:
            console.print(f"  Skills: removed {len(removed_skills)} skill(s)")
    else:
        print_info("No RAW hooks or skills found to remove")
