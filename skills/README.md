# RAW skills

Agent Skills for RAW platform, following the [agentskills.io](https://agentskills.io) specification.

## Available skills

| Skill | Description |
|-------|-------------|
| `raw-workflow-creator` | Create and run RAW workflows |
| `raw-tool-creator` | Create reusable RAW tools |
| `skill-creator` | Create new Agent Skills |

## Directory structure

```
skills/
├── raw-workflow-creator/
│   ├── SKILL.md
│   ├── references/
│   └── templates/
├── raw-tool-creator/
│   ├── SKILL.md
│   ├── references/
│   └── templates/
├── skill-creator/
│   ├── SKILL.md
│   ├── references/
│   └── scripts/
└── README.md
```

## Installation

Skills are installed to user projects via:

```bash
raw hooks install
```

This copies skills to `.claude/skills/` in the target project.

## Creating new skills

Use the `skill-creator` skill or the init script:

```bash
python skills/skill-creator/scripts/init_skill.py my-skill -d "Description"
```

Validate your skill:

```bash
python skills/skill-creator/scripts/quick_validate.py skills/my-skill
```

## Skill format

Each skill requires a `SKILL.md` with YAML frontmatter:

```yaml
---
name: skill-name
description: What it does and when to use it.
---

# Skill title

Instructions...
```

Requirements:
- Name: lowercase, hyphens, max 64 chars, matches directory
- Description: max 1024 chars
- SKILL.md: under 500 lines

See [agentskills.io/specification.md](https://agentskills.io/specification.md) for full spec.
