"""
Creator agent for RAW Platform self-extension.

The CreatorAgent orchestrates the creation of tools and workflows through
a multi-phase process: design, generate, validate, and refine.

Design Philosophy:
- Progressive disclosure: Skills load on-demand, not eagerly
- Simulation-based refinement: Use dry-runs to identify issues before real execution
- Clear separation: Each phase (design, generate, validate, refine) is a distinct skill
- Type-safe parameters: Use Pydantic models for validation
"""

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class CreatorType(str, Enum):
    """Type of artifact to create."""

    TOOL = "tool"
    WORKFLOW = "workflow"


class CreatorPhase(str, Enum):
    """Phases in the creation process."""

    DESIGN = "design"
    GENERATE = "generate"
    VALIDATE = "validate"
    REFINE = "refine"


class DesignSpec(BaseModel):
    """Design specification for a tool or workflow."""

    name: str = Field(..., description="Name of the tool or workflow")
    description: str = Field(..., description="What it does")
    type: CreatorType = Field(..., description="Tool or workflow")
    inputs: list[dict[str, Any]] = Field(
        default_factory=list, description="Input parameters"
    )
    outputs: list[dict[str, Any]] = Field(
        default_factory=list, description="Output structure"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Required Python packages"
    )
    steps: list[str] | None = Field(
        default=None, description="Workflow steps (workflows only)"
    )


class ValidationResult(BaseModel):
    """Result of validation phase."""

    passed: bool = Field(..., description="Whether validation passed")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class RefinementSuggestion(BaseModel):
    """Suggestion for improving implementation."""

    issue: str = Field(..., description="Issue identified")
    suggestion: str = Field(..., description="How to fix it")
    severity: Literal["error", "warning", "info"] = Field(
        ..., description="Issue severity"
    )


class CreatorAgent:
    """
    Agent that orchestrates tool and workflow creation.

    The creator agent uses a skills-based architecture where each capability
    (design, generate, validate, refine) is implemented as a separate skill.

    Usage:
        agent = CreatorAgent()

        # Create a tool
        spec = agent.design_tool(
            intent="Fetch stock prices from Yahoo Finance API",
            name="fetch_stock"
        )
        artifact = agent.generate_tool(spec)
        validation = agent.validate(artifact)

        if not validation.passed:
            artifact = agent.refine(artifact, validation)

    Architecture:
        - Skills are loaded on-demand from src/raw_creator/skills/
        - Each skill is a separate module with clear responsibilities
        - Skills can be swapped or extended without changing the agent
    """

    def __init__(self, skills_dir: Path | None = None) -> None:
        """Initialize creator agent.

        Args:
            skills_dir: Directory containing skill implementations.
                       Defaults to src/raw_creator/skills/
        """
        if skills_dir is None:
            skills_dir = Path(__file__).parent / "skills"
        self.skills_dir = skills_dir
        self._loaded_skills: dict[str, Any] = {}

    def _load_skill(self, phase: CreatorPhase) -> Any:
        """Load a skill module on-demand.

        Args:
            phase: The creation phase (design, generate, validate, refine)

        Returns:
            The loaded skill module
        """
        if phase.value not in self._loaded_skills:
            # Dynamic import - skills are loaded only when needed
            skill_module = __import__(
                f"raw_creator.skills.{phase.value}", fromlist=[phase.value]
            )
            self._loaded_skills[phase.value] = skill_module
        return self._loaded_skills[phase.value]

    def design_tool(
        self,
        intent: str,
        name: str,
        search_existing: bool = True,
    ) -> DesignSpec:
        """Design a new tool from user intent.

        This phase analyzes the intent and creates a design specification
        including inputs, outputs, and dependencies.

        Args:
            intent: User description of what the tool should do
            name: Proposed name for the tool
            search_existing: Whether to search for existing tools first

        Returns:
            Design specification for the tool
        """
        design_skill = self._load_skill(CreatorPhase.DESIGN)
        return design_skill.design_tool(
            intent=intent, name=name, search_existing=search_existing
        )

    def design_workflow(
        self,
        intent: str,
        name: str,
        search_existing: bool = True,
    ) -> DesignSpec:
        """Design a new workflow from user intent.

        This phase analyzes the intent and creates a design specification
        including workflow steps, required tools, and parameters.

        Args:
            intent: User description of what the workflow should do
            name: Proposed name for the workflow
            search_existing: Whether to search for existing workflows first

        Returns:
            Design specification for the workflow
        """
        design_skill = self._load_skill(CreatorPhase.DESIGN)
        return design_skill.design_workflow(
            intent=intent, name=name, search_existing=search_existing
        )

    def generate_tool(self, spec: DesignSpec) -> Path:
        """Generate tool implementation from design spec.

        This phase creates the actual tool files:
        - tool.py: Main implementation
        - __init__.py: Package exports
        - test.py: Unit tests
        - config.yaml: Metadata

        Args:
            spec: Design specification

        Returns:
            Path to generated tool directory
        """
        generate_skill = self._load_skill(CreatorPhase.GENERATE)
        return generate_skill.generate_tool(spec)

    def generate_workflow(self, spec: DesignSpec) -> Path:
        """Generate workflow implementation from design spec.

        This phase creates the workflow files:
        - run.py: Main workflow implementation
        - dry_run.py: Mock data for testing
        - mocks/: Mock response files

        Args:
            spec: Design specification

        Returns:
            Path to generated workflow directory
        """
        generate_skill = self._load_skill(CreatorPhase.GENERATE)
        return generate_skill.generate_workflow(spec)

    def validate(
        self,
        artifact_path: Path,
        artifact_type: CreatorType,
    ) -> ValidationResult:
        """Validate a generated tool or workflow.

        This phase runs:
        - Syntax validation (Python parsing)
        - Import validation (can it be imported?)
        - Tests (for tools: pytest, for workflows: dry-run)
        - Style checks (naming conventions, docstrings)

        Args:
            artifact_path: Path to tool or workflow directory
            artifact_type: Tool or workflow

        Returns:
            Validation result with errors and warnings
        """
        validate_skill = self._load_skill(CreatorPhase.VALIDATE)
        return validate_skill.validate(artifact_path, artifact_type)

    def refine(
        self,
        artifact_path: Path,
        validation: ValidationResult,
        artifact_type: CreatorType,
    ) -> Path:
        """Refine implementation based on validation feedback.

        This phase uses simulation-based improvement:
        1. Analyze validation errors/warnings
        2. Generate refinement suggestions
        3. Apply fixes to the implementation
        4. Re-validate to ensure improvements

        Args:
            artifact_path: Path to artifact to refine
            validation: Validation results identifying issues
            artifact_type: Tool or workflow

        Returns:
            Path to refined artifact (same as input, modified in-place)
        """
        refine_skill = self._load_skill(CreatorPhase.REFINE)
        return refine_skill.refine(artifact_path, validation, artifact_type)

    def create_tool(
        self,
        intent: str,
        name: str,
        search_existing: bool = True,
        auto_refine: bool = True,
        max_refinements: int = 3,
    ) -> tuple[Path, ValidationResult]:
        """
        End-to-end tool creation with automatic refinement.

        This orchestrates all phases:
        1. Design: Create specification from intent
        2. Generate: Create implementation files
        3. Validate: Run tests and checks
        4. Refine: Fix issues (if auto_refine=True)

        Args:
            intent: User description of what the tool should do
            name: Tool name (will be sanitized to use underscores)
            search_existing: Search for existing tools before creating
            auto_refine: Automatically refine based on validation feedback
            max_refinements: Maximum refinement iterations

        Returns:
            Tuple of (tool_path, final_validation_result)
        """
        # Phase 1: Design
        spec = self.design_tool(intent, name, search_existing)

        # Phase 2: Generate
        tool_path = self.generate_tool(spec)

        # Phase 3: Validate
        validation = self.validate(tool_path, CreatorType.TOOL)

        # Phase 4: Refine (iterative)
        refinements = 0
        while auto_refine and not validation.passed and refinements < max_refinements:
            tool_path = self.refine(tool_path, validation, CreatorType.TOOL)
            validation = self.validate(tool_path, CreatorType.TOOL)
            refinements += 1

        return tool_path, validation

    def create_workflow(
        self,
        intent: str,
        name: str,
        search_existing: bool = True,
        auto_refine: bool = True,
        max_refinements: int = 3,
    ) -> tuple[Path, ValidationResult]:
        """
        End-to-end workflow creation with automatic refinement.

        This orchestrates all phases:
        1. Design: Create specification from intent
        2. Generate: Create implementation files
        3. Validate: Run dry-run tests
        4. Refine: Fix issues (if auto_refine=True)

        Args:
            intent: User description of what the workflow should do
            name: Workflow name
            search_existing: Search for existing workflows before creating
            auto_refine: Automatically refine based on validation feedback
            max_refinements: Maximum refinement iterations

        Returns:
            Tuple of (workflow_path, final_validation_result)
        """
        # Phase 1: Design
        spec = self.design_workflow(intent, name, search_existing)

        # Phase 2: Generate
        workflow_path = self.generate_workflow(spec)

        # Phase 3: Validate
        validation = self.validate(workflow_path, CreatorType.WORKFLOW)

        # Phase 4: Refine (iterative)
        refinements = 0
        while (
            auto_refine and not validation.passed and refinements < max_refinements
        ):
            workflow_path = self.refine(workflow_path, validation, CreatorType.WORKFLOW)
            validation = self.validate(workflow_path, CreatorType.WORKFLOW)
            refinements += 1

        return workflow_path, validation
