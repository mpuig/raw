# RAW Skills

Claude Code Agent Skills for creating RAW workflows and tools.

## Directory Structure

```
skills/
├── raw-workflow-creator/   # Skill for creating workflows
│   ├── SKILL.md            # Main skill file (required)
│   ├── references/         # Reference documentation
│   └── templates/          # Code templates
├── raw-tool-creator/       # Skill for creating tools
│   ├── SKILL.md
│   └── ...
└── README.md               # This file
```

## Installation

Skills are installed to user projects via:

```bash
raw hooks install
```

This copies skills to `.claude/skills/` in the target project.

## Creating New Skills

1. Create a directory: `skills/<skill-name>/`
2. Add `SKILL.md` with YAML frontmatter:
   ```yaml
   ---
   name: skill-name
   description: Brief description. Include when to use it.
   ---

   # Skill Title

   ## Instructions
   ...
   ```
3. Register in `src/raw/commands/hooks.py`:
   ```python
   RAW_SKILLS = ["raw-workflow-creator", "raw-tool-creator", "new-skill"]
   ```

## Documentation

See [docs/CLAUDE_INTEGRATION.md](../docs/CLAUDE_INTEGRATION.md) for:
- How skills integrate with Claude Code
- Skill storage locations
- How Claude invokes skills

See [Claude Code Skills documentation](https://code.claude.com/docs/en/skills) for the full Skills API.
