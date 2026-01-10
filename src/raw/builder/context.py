"""Context injection for builder LLM - provides available tools, workflows, and skills."""

from pathlib import Path

from raw.builder.skills import Skill, discover_skills
from raw.discovery.tool import list_tools
from raw.discovery.workflow import list_workflows


class BuilderContext:
    """Builds context for LLM prompts.

    Discovers and formats:
    - Available tools (searchable capabilities)
    - Existing workflows
    - Builder skills (architecture patterns)
    - Previous failures (from journal)
    """

    def __init__(
        self,
        workflow_id: str,
        intent: str | None = None,
        last_failures: list[str] | None = None,
    ) -> None:
        """Initialize context builder.

        Args:
            workflow_id: Target workflow ID
            intent: User's original intent/requirements
            last_failures: Previous iteration failures (for retry)
        """
        self.workflow_id = workflow_id
        self.intent = intent
        self.last_failures = last_failures or []

        # Discover resources
        self.tools = list_tools()
        self.workflows = list_workflows()
        self.skills = discover_skills()

    def build_system_prompt(self, mode: str) -> str:
        """Build system prompt for plan or execute mode.

        Args:
            mode: "plan" or "execute"

        Returns:
            System prompt with injected context
        """
        if mode == "plan":
            return self._build_plan_prompt()
        elif mode == "execute":
            return self._build_execute_prompt()
        else:
            raise ValueError(f"Unknown mode: {mode}")

    def _build_plan_prompt(self) -> str:
        """Build system prompt for plan mode."""
        prompt = """You are a builder agent helping design workflows and systems.

## Your Role

You analyze requirements and create a numbered implementation plan. You may design:
- Single RAW workflows (for data processing, API integrations)
- Multi-system architectures (FastAPI + RAW + Temporal + K8s)

## Available Tools

You can search for existing tools before creating new ones:

"""
        # Add tool listing
        if self.tools:
            prompt += "**Discovered Tools:**\n"
            for tool in self.tools[:20]:  # Show first 20
                prompt += f"- `{tool['name']}`: {tool.get('description', 'No description')}\n"
            if len(self.tools) > 20:
                prompt += f"\n...and {len(self.tools) - 20} more. Use search to find specific capabilities.\n"
        else:
            prompt += "No tools discovered yet.\n"

        prompt += "\n"

        # Add workflow context
        if self.workflows:
            prompt += f"\n**Existing Workflows:** {len(self.workflows)} workflows available\n"

        # Add skills
        if self.skills:
            prompt += "\n## Builder Skills\n\nYou have access to these architecture patterns:\n\n"
            for skill in self.skills:
                prompt += f"- **{skill.name}**: {skill.description}\n"
            prompt += "\n"

        # Add target workflow context
        prompt += f"\n## Target Workflow\n\n"
        prompt += f"**Workflow ID:** `{self.workflow_id}`\n"

        if self.intent:
            prompt += f"**User Intent:** {self.intent}\n"

        # Add failure context if retrying
        if self.last_failures:
            prompt += "\n## Previous Failures\n\n"
            prompt += "The last iteration failed with these gate errors:\n\n"
            for failure in self.last_failures[-3:]:  # Last 3 failures
                prompt += f"- {failure}\n"
            prompt += "\nYour plan must address these failures.\n"

        # Add output format
        prompt += """

## Output Format

Generate a plan with these sections:

### Analysis
- What does this workflow/system need to do?
- What components are required?
- What existing tools can be reused?

### Architecture
- For simple workflows: Single RAW workflow
- For complex systems: RAW + FastAPI + Temporal + deployment configs

### Steps
1. Numbered implementation steps
2. Each step should be clear and testable
3. Reference specific files to create/modify

### Quality Gates
- validate: Always include structural validation
- dry: Include if RAW workflow is generated
- Custom gates as needed (pytest, ruff, etc.)
"""

        return prompt

    def _build_execute_prompt(self) -> str:
        """Build system prompt for execute mode."""
        prompt = """You are a builder agent implementing a plan.

## Your Role

You have a numbered plan. Execute it by:
1. Reading existing files to understand structure
2. Creating new files or modifying existing ones
3. Using proper templates and patterns
4. Testing as you go

## Available Tools

You can use these tools:
- Read: Read file contents
- Write: Create new files
- Edit: Modify existing files
- Bash: Run shell commands (git, mkdir, etc.)
- Search: Find existing tools or code

"""

        # Add tool context
        if self.tools:
            prompt += f"**Available Tools:** {len(self.tools)} tools discovered\n"

        # Add workflow context
        prompt += f"\n## Target Workflow\n\n"
        prompt += f"**Workflow ID:** `{self.workflow_id}`\n"
        prompt += f"**Directory:** `.raw/workflows/{self.workflow_id}/`\n\n"

        # Add RAW workflow template reference
        prompt += """## RAW Workflow Template

When creating RAW workflows, use this structure:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "rich>=13.0"]
# ///

from pydantic import BaseModel, Field
from raw_runtime import BaseWorkflow, step

class MyParams(BaseModel):
    \"\"\"CLI parameters.\"\"\"
    arg: str = Field(..., description="Description")

class MyWorkflow(BaseWorkflow[MyParams]):
    @step("step-name")
    def my_step(self) -> dict:
        # Implementation
        return {"result": "data"}

    def run(self) -> int:
        result = self.my_step()
        self.save("output.json", result)
        return 0

if __name__ == "__main__":
    MyWorkflow.main()
```

## Execution Guidelines

1. **Read before writing**: Always read existing files first
2. **Use templates**: Follow RAW workflow patterns
3. **Import tools**: Use existing tools when possible
4. **Save results**: Always use self.save() for outputs
5. **Return 0**: Success = return 0, failure = return non-zero

Work systematically through the plan steps.
"""

        return prompt

    def format_skills_for_injection(self, skill_names: list[str]) -> str:
        """Format specific skills for injection into context.

        Args:
            skill_names: List of skill names to inject

        Returns:
            Formatted skill content
        """
        output = ""
        for skill in self.skills:
            if skill.name in skill_names:
                output += f"\n## Skill: {skill.name}\n\n"
                output += skill.instructions
                output += "\n"

        return output
