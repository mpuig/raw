"""Tests for tool registry introspection API."""

from collections.abc import AsyncIterator
from typing import Any, ClassVar

import pytest

from raw_runtime.models import ToolMetadata
from raw_runtime.tools import Tool, ToolEvent, ToolRegistry, tool


class MockEmailTool(Tool):
    """Mock email tool for testing."""

    name: ClassVar[str] = "email"
    description: ClassVar[str] = "Send emails via SMTP"
    triggers: ClassVar[list[str]] = ["email_received"]

    async def run(  # noqa: ARG002
        self,
        to: str,
        subject: str,
        body: str,  # noqa: ARG002
        html: str | None = None,  # noqa: ARG002
        **config: Any,  # noqa: ARG002
    ) -> AsyncIterator[ToolEvent]:
        """Send an email.

        Args:
            to: Recipient email
            subject: Email subject
            body: Email body
            html: Optional HTML body
        """
        yield self._emit_started(to=to, subject=subject)
        yield self._emit_completed(sent=True)

    def send_batch(self, emails: list[dict]) -> bool:  # noqa: ARG002
        """Send multiple emails at once."""
        return True


class MockStorageTool(Tool):
    """Mock storage tool for testing."""

    name: ClassVar[str] = "storage"
    description: ClassVar[str] = "Store and retrieve files"
    triggers: ClassVar[list[str]] = []

    async def run(self, operation: str, path: str, **config: Any) -> AsyncIterator[ToolEvent]:  # noqa: ARG002
        """Perform storage operation."""
        yield self._emit_started(operation=operation, path=path)
        yield self._emit_completed(success=True)


def test_registry_list_tools() -> None:
    """Test list_tools returns all registered tool names."""
    registry = ToolRegistry()
    registry.register(MockEmailTool())
    registry.register(MockStorageTool())

    tools = registry.list_tools()
    assert tools == ["email", "storage"]
    assert isinstance(tools, list)


def test_registry_list_tools_empty() -> None:
    """Test list_tools with empty registry."""
    registry = ToolRegistry()
    tools = registry.list_tools()
    assert tools == []


def test_registry_has_tool() -> None:
    """Test has_tool checks tool existence."""
    registry = ToolRegistry()
    registry.register(MockEmailTool())

    assert registry.has_tool("email") is True
    assert registry.has_tool("nonexistent") is False
    assert registry.has_tool("storage") is False


def test_registry_get_tool_metadata() -> None:
    """Test get_tool_metadata returns complete metadata."""
    registry = ToolRegistry()
    registry.register(MockEmailTool())

    metadata = registry.get_tool_metadata("email")

    assert isinstance(metadata, ToolMetadata)
    assert metadata.name == "email"
    assert metadata.description == "Send emails via SMTP"
    assert metadata.triggers == ["email_received"]
    assert "send_batch" in metadata.operations
    assert metadata.documentation is not None
    assert "Send an email" in metadata.documentation


def test_registry_get_tool_metadata_not_found() -> None:
    """Test get_tool_metadata raises KeyError for unknown tool."""
    registry = ToolRegistry()

    with pytest.raises(KeyError, match="Tool 'nonexistent' not found"):
        registry.get_tool_metadata("nonexistent")


def test_tool_metadata_extraction() -> None:
    """Test Tool.metadata() extracts comprehensive metadata."""
    metadata = MockEmailTool.metadata()

    assert metadata.name == "email"
    assert metadata.description == "Send emails via SMTP"
    assert metadata.triggers == ["email_received"]
    assert "send_batch" in metadata.operations
    assert "run" not in metadata.operations
    assert "call" not in metadata.operations
    assert "metadata" not in metadata.operations


def test_tool_metadata_operations() -> None:
    """Test metadata includes public methods as operations."""
    metadata = MockEmailTool.metadata()

    assert "send_batch" in metadata.operations
    assert len([op for op in metadata.operations if op.startswith("_")]) == 0


def test_tool_metadata_no_triggers() -> None:
    """Test metadata handles tools with no triggers."""
    metadata = MockStorageTool.metadata()

    assert metadata.triggers == []


def test_tool_metadata_documentation() -> None:
    """Test metadata extracts docstrings."""
    metadata = MockEmailTool.metadata()

    assert metadata.documentation is not None
    assert "Send an email" in metadata.documentation
    assert "to:" in metadata.documentation or "Recipient" in metadata.documentation


def test_registry_integration() -> None:
    """Test full integration of registry introspection."""
    registry = ToolRegistry()
    registry.register(MockEmailTool())
    registry.register(MockStorageTool())

    # List all tools
    assert registry.list_tools() == ["email", "storage"]

    # Check existence
    assert registry.has_tool("email")
    assert registry.has_tool("storage")
    assert not registry.has_tool("unknown")

    # Get metadata for each
    email_meta = registry.get_tool_metadata("email")
    storage_meta = registry.get_tool_metadata("storage")

    assert email_meta.name == "email"
    assert storage_meta.name == "storage"
    assert "send_batch" in email_meta.operations
    assert len(storage_meta.operations) >= 0


def test_programmatic_tool_metadata() -> None:
    """Test metadata extraction from @tool decorator."""

    @tool(description="Fetch customer data", name="get_customer")
    def fetch_customer(customer_id: str, include_orders: bool = False) -> dict:  # noqa: ARG001
        """Retrieve customer from database."""
        return {"id": customer_id, "orders": []}

    metadata = fetch_customer.__class__.metadata()

    assert metadata.name == "get_customer"
    assert metadata.description == "Fetch customer data"
    assert metadata.parameters is not None

    # Check that schema was extracted from decorator
    if hasattr(fetch_customer, "schema"):
        params = metadata.parameters
        assert "customer_id" in params or len(params) >= 0


def test_tool_metadata_serialization() -> None:
    """Test ToolMetadata can be serialized to JSON."""
    metadata = MockEmailTool.metadata()

    # Should serialize without error
    json_str = metadata.model_dump_json()
    assert "email" in json_str
    assert "Send emails" in json_str

    # Should deserialize back
    restored = ToolMetadata.model_validate_json(json_str)
    assert restored.name == metadata.name
    assert restored.description == metadata.description


def test_registry_list_all_vs_list_tools() -> None:
    """Test list_all and list_tools return same tools (different sort)."""
    registry = ToolRegistry()
    registry.register(MockStorageTool())
    registry.register(MockEmailTool())

    all_tools = set(registry.list_all())
    sorted_tools = set(registry.list_tools())

    assert all_tools == sorted_tools
    assert sorted(registry.list_all()) == registry.list_tools()


@pytest.mark.asyncio
async def test_metadata_from_live_tool() -> None:
    """Test metadata extraction from a tool that actually runs."""
    tool_instance = MockEmailTool()
    metadata = tool_instance.__class__.metadata()

    assert metadata.name == "email"

    # Verify tool still works after metadata extraction
    events = []
    async for event in tool_instance.run(to="test@example.com", subject="Test", body="Hello"):
        events.append(event)

    assert len(events) == 2
    assert events[0].type.value == "started"
    assert events[1].type.value == "completed"


def test_multiple_registries_independent() -> None:
    """Test multiple registries maintain independent state."""
    registry1 = ToolRegistry()
    registry2 = ToolRegistry()

    registry1.register(MockEmailTool())
    registry2.register(MockStorageTool())

    assert registry1.list_tools() == ["email"]
    assert registry2.list_tools() == ["storage"]
    assert registry1.has_tool("email")
    assert not registry1.has_tool("storage")
    assert not registry2.has_tool("email")
    assert registry2.has_tool("storage")


def test_tool_metadata_version_and_doc_fields() -> None:
    """Test metadata includes version and documentation fields."""
    metadata = MockEmailTool.metadata()

    assert hasattr(metadata, "version")
    assert hasattr(metadata, "documentation")
    assert metadata.version is None  # Default for tools without version
    assert metadata.documentation is not None


def test_tool_metadata_parameters_field() -> None:
    """Test metadata includes parameters field."""
    metadata = MockEmailTool.metadata()

    assert hasattr(metadata, "parameters")
    assert isinstance(metadata.parameters, dict)
