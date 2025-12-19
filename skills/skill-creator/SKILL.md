---
name: skill-creator
description: Create Agent Skills that comply with the agentskills.io specification. Use when the user asks to create a new skill, add agent capabilities, or build reusable instructions.
---

# Skill creator

Create Agent Skills following the agentskills.io specification.

## When to use this skill

Use this skill when:
- The user wants to create a new skill
- You need to package reusable instructions for agents
- Building capabilities that should be discoverable and shareable

## Design principles

### Context efficiency

The context window is a shared resource. Only include information the agent doesn't already have. Challenge every inclusion: does it justify its token cost?

**Include:**
- Domain-specific knowledge the agent lacks
- Exact formats or templates required
- Decision criteria for edge cases

**Exclude:**
- General programming knowledge
- Common patterns the agent knows
- Redundant explanations

### Appropriate specificity

Match constraint levels to task fragility:

| Task type | Approach |
|-----------|----------|
| Flexible (summaries, analysis) | Text instructions |
| Preferred patterns | Pseudocode or examples |
| Error-prone operations | Specific scripts |

### Progressive disclosure

Load content in phases to minimize token usage:

1. **Metadata** (~100 tokens) - Always loads
2. **SKILL.md** (<5000 tokens) - When skill activates
3. **References** - Only when explicitly needed

## Directory structure

```
skills/<skill-name>/
├── SKILL.md           # Required: main instructions
├── references/        # Detailed docs, loaded on demand
├── scripts/           # Executable code for deterministic tasks
└── assets/            # Templates, images, boilerplate
```

## Creation process

### Step 1: Understand

Start with concrete examples of the task. What inputs? What outputs? What decisions along the way?

### Step 2: Plan

Identify reusable components:
- Scripts for deterministic operations
- References for detailed guidance
- Assets for templates or boilerplate

### Step 3: Initialize

```bash
python scripts/init_skill.py my-skill -d "Description of what this skill does"
```

This creates the directory structure and a SKILL.md template.

### Step 4: Edit

Write the skill content:
1. Frontmatter (name, description)
2. When to use section
3. Key directives
4. Process steps
5. Validation checklist

### Step 5: Validate

```bash
python scripts/quick_validate.py skills/my-skill
```

Checks:
- Frontmatter completeness
- Name format and directory match
- Line count under 500
- Reference file existence

### Step 6: Package

```bash
python scripts/package_skill.py skills/my-skill -o dist
```

Creates a distributable bundle with manifest.

## Specification requirements

### Required frontmatter

```yaml
---
name: my-skill-name
description: What the skill does and when to use it.
---
```

**Name:** Max 64 chars, lowercase letters/numbers/hyphens, must match directory.

**Description:** Max 1024 chars, include trigger keywords.

### Optional frontmatter

```yaml
license: MIT
compatibility: Python 3.10+
metadata:
  author: your-name
  version: "1.0.0"
allowed-tools: Read Write Bash
```

## Writing effective content

### Descriptions

Structure: `[Action verb] [what] [when to use]`

Good: `Create API integrations with retry logic. Use when building tools that call external services.`

Bad: `A utility for API stuff.`

### Instructions

Be specific about:
- Trigger conditions (when to activate)
- Required outputs (what to produce)
- Constraints (what to avoid)

Avoid:
- Auxiliary files (README.md, CHANGELOG.md)
- General knowledge the agent has
- Redundant explanations

## Validation checklist

Before delivering a skill:
- [ ] Frontmatter has `name` and `description`
- [ ] Name matches directory name
- [ ] Name is lowercase with hyphens (no underscores)
- [ ] Description under 1024 characters
- [ ] SKILL.md under 500 lines
- [ ] Has "When to use" section
- [ ] Has clear process steps
- [ ] References use relative paths
- [ ] All referenced files exist

## References

- [Output patterns](references/output-patterns.md) - Templates and examples
- [Workflow patterns](references/workflows.md) - Sequential and conditional flows
- [Agent Skills specification](https://agentskills.io/specification.md)
