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

## Specification overview

Agent Skills use a `SKILL.md` file with YAML frontmatter and markdown content.

### Required frontmatter

```yaml
---
name: my-skill-name
description: What the skill does and when to use it.
---
```

**Name requirements:**
- Max 64 characters
- Lowercase letters, numbers, and hyphens only
- Cannot start or end with hyphens
- No consecutive hyphens
- Must match the parent directory name

**Description requirements:**
- Max 1024 characters
- Non-empty
- Should include keywords that help agents identify relevant tasks

### Optional frontmatter

```yaml
---
name: my-skill
description: What it does.
license: MIT
compatibility: Python 3.10+, macOS/Linux
metadata:
  author: your-name
  version: "1.0.0"
allowed-tools: Read Write Bash
---
```

## Directory structure

```
skills/<skill-name>/
├── SKILL.md           # Required: main instructions
├── references/        # Optional: detailed docs
│   ├── guide.md
│   └── examples.md
├── templates/         # Optional: code templates
└── assets/            # Optional: images, data
```

## Creation process

### Step 1: Create directory

```bash
mkdir -p skills/<skill-name>/references
```

The directory name must match the `name` in frontmatter.

### Step 2: Write SKILL.md

Create the main skill file with:

1. **Frontmatter** - name and description (required)
2. **When to use** - Clear trigger conditions
3. **Key directives** - Non-negotiable rules
4. **Process steps** - Step-by-step instructions
5. **Examples** - Concrete usage examples
6. **Validation checklist** - Pre-delivery checks

### Step 3: Keep under 500 lines

The spec recommends keeping `SKILL.md` under 500 lines. Move detailed content to `references/`:

- Long examples → `references/examples.md`
- Error catalogs → `references/troubleshooting.md`
- Advanced patterns → `references/patterns.md`

### Step 4: Validate

Check your skill:
- [ ] Name is lowercase with hyphens
- [ ] Name matches directory
- [ ] Description under 1024 chars
- [ ] SKILL.md under 500 lines
- [ ] Frontmatter has `---` delimiters
- [ ] References use relative paths

## Progressive disclosure

Skills load content in phases:

1. **Metadata** (~100 tokens) - Always loads
2. **Full instructions** (<5000 tokens recommended) - When activated
3. **Reference files** - Only when needed

Structure your skill so basic usage works with just the main file.

## Writing effective descriptions

Descriptions are indexed for search. Structure them as:

`[Action verb] [what] [when to use]`

Good:
```
Create API integrations with error handling and retry logic. Use when building tools that call external services.
```

Bad:
```
A utility for API stuff.
```

## Template

```markdown
---
name: example-skill
description: Brief description of what this skill does and when to use it.
---

# Example skill

One-line summary.

## When to use this skill

- Bullet points of trigger conditions
- Be specific about scenarios

## Key directives

1. **Rule one** - Non-negotiable requirement
2. **Rule two** - Another requirement

## Process

### Step 1: First step

Instructions for step 1.

### Step 2: Second step

Instructions for step 2.

## Validation checklist

Before reporting success:
- [ ] Check one
- [ ] Check two

## References

- [Detailed guide](references/guide.md)
```

## Validation checklist

Before delivering a skill:
- [ ] Frontmatter has `name` and `description`
- [ ] Name matches directory name
- [ ] Name is lowercase, hyphens only (no underscores)
- [ ] Description is under 1024 characters
- [ ] SKILL.md is under 500 lines
- [ ] Has "When to use" section
- [ ] Has clear process steps
- [ ] References use relative paths

## References

- [Agent Skills specification](https://agentskills.io/specification.md)
