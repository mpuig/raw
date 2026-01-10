"""Tests for SDK workflow functions."""

from pathlib import Path

import pytest
import yaml

from raw.core.schemas import WorkflowStatus
from raw.sdk import (
    Workflow,
    WorkflowNotFoundError,
    add_step,
    create_workflow,
    delete_workflow,
    get_workflow,
    list_workflows,
    update_workflow,
)


@pytest.fixture
def temp_raw_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a temporary RAW project."""
    raw_dir = tmp_path / ".raw"
    raw_dir.mkdir()
    workflows_dir = raw_dir / "workflows"
    workflows_dir.mkdir()

    # Mock get_workflows_dir in all modules that use it
    import raw.discovery.workflow
    import raw.scaffold.init

    monkeypatch.setattr(raw.scaffold.init, "get_workflows_dir", lambda: workflows_dir)
    monkeypatch.setattr(raw.discovery.workflow, "get_workflows_dir", lambda: workflows_dir)

    return workflows_dir


class TestCreateWorkflow:
    """Tests for create_workflow function."""

    def test_create_workflow_with_intent(self, temp_raw_project: Path) -> None:
        """Test creating workflow with intent."""
        workflow = create_workflow(
            name="test-workflow",
            intent="Fetch stock data and generate report",
        )

        assert workflow.name == "test-workflow"
        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.description.intent == "Fetch stock data and generate report"
        assert "test-workflow" in workflow.id
        assert workflow.path.exists()

        # Verify config.yaml was created
        config_path = workflow.path / "config.yaml"
        assert config_path.exists()

        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["name"] == "test-workflow"
        assert config_data["status"] == "draft"

    def test_create_workflow_with_description(self, temp_raw_project: Path) -> None:
        """Test creating workflow with explicit description."""
        workflow = create_workflow(
            name="my-workflow",
            intent="Do something",
            description="Custom description",
        )

        assert workflow.name == "my-workflow"
        assert workflow.description.intent == "Do something"

    def test_create_workflow_minimal(self, temp_raw_project: Path) -> None:
        """Test creating workflow with minimal parameters."""
        workflow = create_workflow(name="minimal")

        assert workflow.name == "minimal"
        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.description.intent.startswith("Scaffold workflow:")

    def test_create_workflow_sanitizes_name(self, temp_raw_project: Path) -> None:
        """Test that workflow name is sanitized."""
        workflow = create_workflow(name="Test Workflow 123")

        assert "test-workflow-123" in workflow.id


class TestListWorkflows:
    """Tests for list_workflows function."""

    def test_list_empty_workflows(self, temp_raw_project: Path) -> None:
        """Test listing workflows when none exist."""
        workflows = list_workflows()
        assert workflows == []

    def test_list_workflows(self, temp_raw_project: Path) -> None:
        """Test listing multiple workflows."""
        workflow1 = create_workflow(name="workflow-1", intent="First workflow")
        workflow2 = create_workflow(name="workflow-2", intent="Second workflow")

        workflows = list_workflows()

        assert len(workflows) == 2
        workflow_ids = {w.id for w in workflows}
        assert workflow1.id in workflow_ids
        assert workflow2.id in workflow_ids

    def test_list_workflows_filters_non_dirs(self, temp_raw_project: Path) -> None:
        """Test that list_workflows ignores non-directory entries."""
        create_workflow(name="real-workflow", intent="Real workflow")

        # Create a file in workflows directory
        (temp_raw_project / "not-a-workflow.txt").write_text("test")

        workflows = list_workflows()
        assert len(workflows) == 1
        assert workflows[0].name == "real-workflow"


class TestGetWorkflow:
    """Tests for get_workflow function."""

    def test_get_workflow_by_full_id(self, temp_raw_project: Path) -> None:
        """Test getting workflow by full ID."""
        created = create_workflow(name="test", intent="Test workflow")

        workflow = get_workflow(created.id)

        assert workflow is not None
        assert workflow.id == created.id
        assert workflow.name == "test"

    def test_get_workflow_by_partial_id(self, temp_raw_project: Path) -> None:
        """Test getting workflow by partial ID match."""
        created = create_workflow(name="unique-name", intent="Test")

        workflow = get_workflow("unique-name")

        assert workflow is not None
        assert workflow.id == created.id

    def test_get_workflow_not_found(self, temp_raw_project: Path) -> None:
        """Test getting non-existent workflow returns None."""
        workflow = get_workflow("nonexistent-id")
        assert workflow is None


class TestUpdateWorkflow:
    """Tests for update_workflow function."""

    def test_update_workflow_name(self, temp_raw_project: Path) -> None:
        """Test updating workflow name."""
        workflow = create_workflow(name="original", intent="Test")

        updated = update_workflow(workflow, name="updated-name")

        assert updated.name == "updated-name"

        # Verify config file was updated
        config_path = workflow.path / "config.yaml"
        config_data = yaml.safe_load(config_path.read_text())
        assert config_data["name"] == "updated-name"

    def test_update_workflow_intent(self, temp_raw_project: Path) -> None:
        """Test updating workflow intent."""
        workflow = create_workflow(name="test", intent="Original intent")

        updated = update_workflow(workflow, intent="New intent")

        assert updated.description.intent == "New intent"

    def test_update_workflow_status(self, temp_raw_project: Path) -> None:
        """Test updating workflow status."""
        workflow = create_workflow(name="test", intent="Test")

        updated = update_workflow(workflow, status=WorkflowStatus.GENERATED)

        assert updated.status == WorkflowStatus.GENERATED

    def test_update_workflow_multiple_fields(self, temp_raw_project: Path) -> None:
        """Test updating multiple fields at once."""
        workflow = create_workflow(name="test", intent="Test")

        updated = update_workflow(
            workflow,
            name="new-name",
            intent="New intent",
            status=WorkflowStatus.TESTED,
        )

        assert updated.name == "new-name"
        assert updated.description.intent == "New intent"
        assert updated.status == WorkflowStatus.TESTED


class TestDeleteWorkflow:
    """Tests for delete_workflow function."""

    def test_delete_workflow(self, temp_raw_project: Path) -> None:
        """Test deleting a workflow."""
        workflow = create_workflow(name="to-delete", intent="Test")
        workflow_path = workflow.path

        assert workflow_path.exists()

        delete_workflow(workflow)

        assert not workflow_path.exists()

    def test_delete_workflow_not_found(self, temp_raw_project: Path) -> None:
        """Test deleting non-existent workflow raises error."""
        workflow = Workflow(
            id="nonexistent",
            name="test",
            path=temp_raw_project / "nonexistent",
            status=WorkflowStatus.DRAFT,
            description={"intent": "test"},
            steps=[],
        )

        with pytest.raises(WorkflowNotFoundError):
            delete_workflow(workflow)


class TestAddStep:
    """Tests for add_step function."""

    def test_add_step_with_tool(self, temp_raw_project: Path) -> None:
        """Test adding a step with tool reference."""
        workflow = create_workflow(name="test", intent="Test")

        step = add_step(
            workflow,
            name="fetch-data",
            tool="stock_fetcher",
            config={"ticker": "TSLA"},
        )

        assert step.name == "fetch-data"
        assert step.tool == "stock_fetcher"
        assert step.inputs == {"ticker": "TSLA"}

        # Verify workflow was updated
        updated_workflow = get_workflow(workflow.id)
        assert updated_workflow is not None
        assert len(updated_workflow.steps) == 1
        assert updated_workflow.steps[0].name == "fetch-data"

    def test_add_step_with_code(self, temp_raw_project: Path) -> None:
        """Test adding a step with inline code."""
        workflow = create_workflow(name="test", intent="Test")

        code = "def process():\n    return 'result'"
        step = add_step(workflow, name="process", code=code)

        assert step.name == "process"
        assert step.description.startswith("Custom code:")

    def test_add_step_requires_tool_or_code(self, temp_raw_project: Path) -> None:
        """Test that add_step requires either tool or code."""
        workflow = create_workflow(name="test", intent="Test")

        with pytest.raises(ValueError, match="Either tool or code must be provided"):
            add_step(workflow, name="invalid-step")

    def test_add_step_cannot_have_both_tool_and_code(self, temp_raw_project: Path) -> None:
        """Test that add_step cannot have both tool and code."""
        workflow = create_workflow(name="test", intent="Test")

        with pytest.raises(ValueError, match="Cannot specify both tool and code"):
            add_step(
                workflow,
                name="invalid-step",
                tool="my_tool",
                code="print('hello')",
            )

    def test_add_multiple_steps(self, temp_raw_project: Path) -> None:
        """Test adding multiple steps to a workflow."""
        workflow = create_workflow(name="test", intent="Test")

        step1 = add_step(workflow, name="step-1", tool="tool1")
        step2 = add_step(workflow, name="step-2", tool="tool2")

        updated_workflow = get_workflow(workflow.id)
        assert updated_workflow is not None
        assert len(updated_workflow.steps) == 2
        assert updated_workflow.steps[0].id == step1.id
        assert updated_workflow.steps[1].id == step2.id


class TestWorkflowModel:
    """Tests for Workflow model."""

    def test_workflow_from_config(self, temp_raw_project: Path) -> None:
        """Test creating Workflow model from config."""
        created = create_workflow(name="test", intent="Test workflow")

        # Get it back
        workflow = get_workflow(created.id)

        assert workflow is not None
        assert workflow.id == created.id
        assert workflow.name == "test"
        assert workflow.status == WorkflowStatus.DRAFT
        assert workflow.path == created.path

    def test_workflow_steps_empty_by_default(self, temp_raw_project: Path) -> None:
        """Test that new workflows have no steps."""
        workflow = create_workflow(name="test", intent="Test")
        assert workflow.steps == []
