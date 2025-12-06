"""Pydantic models for structured markdown content."""

from pydantic import BaseModel, Field


class WorkflowSummary(BaseModel):
    """Summary of a workflow for rendering in prime output."""

    id: str
    name: str
    status: str = "draft"
    intent: str = ""

    @property
    def status_icon(self) -> str:
        """Get status icon for display."""
        return "✅" if self.status == "published" else "📝"

    @property
    def truncated_intent(self) -> str:
        """Get intent truncated to 60 chars."""
        if len(self.intent) <= 60:
            return self.intent
        return self.intent[:57] + "..."


class ToolSummary(BaseModel):
    """Summary of a tool for rendering in prime output."""

    name: str
    version: str = "1.0.0"
    status: str = "draft"
    description: str = ""

    @property
    def truncated_description(self) -> str:
        """Get description truncated to 50 chars."""
        if len(self.description) <= 50:
            return self.description
        return self.description[:47] + "..."


class CommandInfo(BaseModel):
    """CLI command documentation."""

    command: str
    description: str


class CodeExample(BaseModel):
    """Code example with optional language."""

    code: str
    language: str = "bash"


class PrimeContext(BaseModel):
    """Full context for rendering prime output."""

    workflows: list[WorkflowSummary] = Field(default_factory=list)
    tools: list[ToolSummary] = Field(default_factory=list)

    @property
    def workflow_count(self) -> int:
        return len(self.workflows)

    @property
    def tool_count(self) -> int:
        return len(self.tools)

    @property
    def published_count(self) -> int:
        return sum(1 for w in self.workflows if w.status == "published")

    @property
    def draft_count(self) -> int:
        return sum(1 for w in self.workflows if w.status == "draft")

    @property
    def has_workflows(self) -> bool:
        return len(self.workflows) > 0

    @property
    def has_tools(self) -> bool:
        return len(self.tools) > 0
