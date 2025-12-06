# Claude Code Skills Architecture

This document describes the design, implementation, and extension of RAW's AI skills. These skills enable Claude Code to autonomously build, test, and run workflows using RAW's architecture.

## Overview

Skills are located in `skills/` and installed into the user's project via `raw hooks install`. They provide Claude with specialized knowledge and procedural guidance.

### Available Skills

| Skill | Directory | Purpose |
|-------|-----------|---------|
| **Workflow Creator** | `raw-workflow-creator` | Guides creation of new workflows, emphasizing "Unified Tools" and "No API calls in run.py". |
| **Tool Creator** | `raw-tool-creator` | Guides creation of reusable tools, enforcing testing and proper `__init__.py` exports. |

---

## Skill Structure

Each skill follows a common directory structure:

```
skills/<skill-name>/
├── SKILL.md          # The brain: Definition, triggers, and knowledge base
├── README.md         # Human-readable documentation for the skill
├── references/       # Supporting context files (best practices, patterns, detailed examples)
└── templates/        # Code templates (optional, for code generation)
```

### 1. SKILL.md (The Definition)

This is the file Claude actually reads. It must contain:

*   **Frontmatter:** YAML block defining `name` and `description` (triggers).
*   **Key Directives:** High-priority rules (e.g., "ALWAYS search before creating").
*   **Prerequisites:** What must exist before starting.
*   **Process Flow:** Step-by-step instructions (Search -> Create -> Implement -> Test).
*   **Error Catalog:** "If you see Error X, do Y."
*   **Patterns:** Reusable architectural patterns (e.g., Webhook, Cron).

**Example Frontmatter:**
```markdown
---
name: raw-workflow-creator
description: Create and run RAW workflows. Use when the user asks to create a workflow, automate a task, or asks "How do I build X?".
---
```

### 2. References (The Context)

Keep `SKILL.md` concise by offloading heavy documentation to `references/`.
*   `references/workflow_patterns.md`: Detailed code examples.
*   `references/testing_guide.md`: How to use `pytest` with RAW.

---

## Best Practices for Skill Design

### 1. Modular Responsibilities
Don't create one giant "Super Skill." Split responsibilities:
*   **Tool Creator:** Only cares about `tools/` structure, `pip` deps, and unit tests.
*   **Workflow Creator:** Only cares about `run.py`, orchestration, and importing tools.

### 2. The "Validation Loop"
Teach the agent to expect failure and fix it.
*   *Bad:* "Run the test."
*   *Good:* "Run `raw run --dry`. If it fails with `ModuleNotFoundError`, add the dependency to the header. If it fails with `401`, check `.env`."

### 3. Trigger Engineering
Write descriptions that capture intent, not just keywords.
*   *Weak:* "Create tools."
*   *Strong:* "Use this skill when the user asks to create a tool, extract reusable functionality, or build a new capability."

### 4. Error Catalogs
Include a specific table of common errors and fixes. Agents are great at matching error strings to solutions if you provide the map.

### 5. Control Tool Access (`allowed-tools`)
For skills using sensitive or specific CLI tools, use the `allowed-tools` field in your `SKILL.md` frontmatter. This explicitly grants the skill permission to run certain commands, enhancing security and guiding Claude's behavior.

```markdown
---
name: raw-sensitive-tool-skill
description: Manages production deployments.
allowed-tools:
  - Bash(uv run deploy-script:*)
  - Files(write:production_logs/*)
---
```

---

## How to Add a New Skill

### Step 1: Create Directory
```bash
mkdir -p skills/raw-new-skill/references
```

### Step 2: Write SKILL.md
Create `skills/raw-new-skill/SKILL.md`. Start with the frontmatter and the "Key Directives" section.

### Step 3: Register in CLI
Update `src/raw/commands/hooks.py` to include the new skill in `RAW_SKILLS`.

```python
RAW_SKILLS = ["raw-workflow-creator", "raw-tool-creator", "raw-new-skill"]
```

### Step 4: Test Installation
Run `raw hooks install` in a test project. Verify the skill appears in `.claude/skills/`.

---

## Debugging Skills

If Claude isn't using your skill correctly:

1.  **Check Triggers:** Is the description in `SKILL.md` broad enough?
2.  **Check Context Window:** Is `SKILL.md` too long? Move details to `references/`.
3.  **Check Instructions:** Are the directives contradictory? Use **bold** for mandatory rules.
4.  **Verify Permissions:** Ensure `raw hooks install` added the skill to `permissions.allow` in `settings.local.json`.
