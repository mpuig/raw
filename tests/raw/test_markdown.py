"""Tests for markdown generation module."""

from pathlib import Path

import pytest

from raw.scaffold.markdown import (
    CodeBlock,
    Document,
    List,
    PrimeContext,
    Section,
    Table,
    ToolSummary,
    WorkflowSummary,
    escape_inline_code,
    escape_pipe,
    escape_table_cell,
    render_onboard,
    render_prime,
    slugify,
    truncate,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "markdown"


class TestEscapeUtilities:
    """Tests for escape functions."""

    def test_escape_pipe(self) -> None:
        assert escape_pipe("foo|bar") == "foo\\|bar"
        assert escape_pipe("no pipes") == "no pipes"

    def test_escape_table_cell(self) -> None:
        assert escape_table_cell("foo|bar") == "foo\\|bar"
        assert escape_table_cell("  spaces  ") == "spaces"
        assert escape_table_cell("line\nbreak") == "line break"

    def test_escape_inline_code(self) -> None:
        assert escape_inline_code("simple") == "`simple`"
        assert escape_inline_code("with`backtick") == "`` with`backtick ``"

    def test_truncate(self) -> None:
        assert truncate("short", 10) == "short"
        assert truncate("this is a long string", 10) == "this is..."
        assert truncate("exactly10!", 10) == "exactly10!"

    def test_slugify(self) -> None:
        assert slugify("Hello World") == "hello-world"
        assert slugify("  Spaces  ") == "spaces"
        assert slugify("Special!@#Chars") == "specialchars"
        assert slugify("Multiple---Dashes") == "multiple-dashes"


class TestTable:
    """Tests for Table builder."""

    def test_basic_table(self) -> None:
        table = Table(["Name", "Value"])
        table.add_row("foo", "bar")
        table.add_row("baz", "qux")

        result = table.render()
        assert "| Name | Value |" in result
        assert "| foo | bar |" in result
        assert "| baz | qux |" in result

    def test_table_escapes_pipes(self) -> None:
        table = Table(["Command", "Description"])
        table.add_row("foo|bar", "test")

        result = table.render()
        assert "foo\\|bar" in result

    def test_table_wrong_column_count(self) -> None:
        table = Table(["A", "B"])
        with pytest.raises(ValueError, match="expected 2"):
            table.add_row("only one")

    def test_empty_table(self) -> None:
        table = Table([])
        assert table.render() == ""


class TestCodeBlock:
    """Tests for CodeBlock builder."""

    def test_basic_code_block(self) -> None:
        code = CodeBlock("python")
        code.add_line("def hello():")
        code.add_line("    print('hi')")

        result = code.render()
        assert result.startswith("```python\n")
        assert result.endswith("\n```")
        assert "def hello():" in result

    def test_code_block_no_language(self) -> None:
        code = CodeBlock()
        code.set_content("plain text")

        result = code.render()
        assert result.startswith("```\n")

    def test_set_content(self) -> None:
        code = CodeBlock("bash")
        code.set_content("line1\nline2\nline3")

        result = code.render()
        assert "line1" in result
        assert "line2" in result
        assert "line3" in result


class TestList:
    """Tests for List builder."""

    def test_unordered_list(self) -> None:
        md_list = List()
        md_list.add_item("First")
        md_list.add_item("Second")

        result = md_list.render()
        assert "- First" in result
        assert "- Second" in result

    def test_ordered_list(self) -> None:
        md_list = List(ordered=True)
        md_list.add_item("First")
        md_list.add_item("Second")

        result = md_list.render()
        assert "1. First" in result
        assert "2. Second" in result


class TestSection:
    """Tests for Section builder."""

    def test_basic_section(self) -> None:
        section = Section("My Section", level=2)
        section.add_paragraph("Intro text.")

        result = section.render()
        assert result.startswith("## My Section\n")
        assert "Intro text." in result

    def test_section_with_code(self) -> None:
        section = Section("Example", level=3)
        section.add_code_block("bash", "echo hello")

        result = section.render()
        assert "### Example" in result
        assert "```bash" in result
        assert "echo hello" in result

    def test_invalid_heading_level(self) -> None:
        with pytest.raises(ValueError, match="between 1 and 6"):
            Section("Test", level=7)


class TestDocument:
    """Tests for Document builder."""

    def test_basic_document(self) -> None:
        doc = Document()
        doc.add_heading("Title", level=1)
        doc.add_paragraph("Introduction.")

        result = doc.render()
        assert "# Title" in result
        assert "Introduction." in result

    def test_document_with_multiple_elements(self) -> None:
        doc = Document()
        doc.add_heading("Doc", level=1)
        doc.add_paragraph("Intro")
        doc.add_code_block("python", "x = 1")
        doc.add_horizontal_rule()
        doc.add_blockquote("A quote")

        result = doc.render()
        assert "# Doc" in result
        assert "Intro" in result
        assert "```python" in result
        assert "---" in result
        assert "> A quote" in result


class TestModels:
    """Tests for Pydantic content models."""

    def test_workflow_summary(self) -> None:
        wf = WorkflowSummary(
            id="test-123",
            name="test-workflow",
            status="published",
            intent="Do something important",
        )
        assert wf.status_icon == "✅"
        assert wf.truncated_intent == "Do something important"

    def test_workflow_summary_draft(self) -> None:
        wf = WorkflowSummary(id="test", name="test", status="draft")
        assert wf.status_icon == "📝"

    def test_workflow_summary_truncates_intent(self) -> None:
        long_intent = "A" * 100
        wf = WorkflowSummary(id="test", name="test", intent=long_intent)
        assert len(wf.truncated_intent) == 60
        assert wf.truncated_intent.endswith("...")

    def test_tool_summary_truncates_description(self) -> None:
        long_desc = "B" * 100
        tool = ToolSummary(name="test", description=long_desc)
        assert len(tool.truncated_description) == 50
        assert tool.truncated_description.endswith("...")

    def test_prime_context_counts(self) -> None:
        ctx = PrimeContext(
            workflows=[
                WorkflowSummary(id="1", name="a", status="published"),
                WorkflowSummary(id="2", name="b", status="draft"),
                WorkflowSummary(id="3", name="c", status="draft"),
            ],
            tools=[ToolSummary(name="t1"), ToolSummary(name="t2")],
        )
        assert ctx.workflow_count == 3
        assert ctx.published_count == 1
        assert ctx.draft_count == 2
        assert ctx.tool_count == 2
        assert ctx.has_workflows is True
        assert ctx.has_tools is True


class TestGoldenFiles:
    """Golden file tests for rendered markdown output."""

    def test_render_onboard_matches_golden(self) -> None:
        """Test that render_onboard output matches golden file."""
        result = render_onboard()
        golden_path = FIXTURES_DIR / "onboard.md"

        if not golden_path.exists():
            pytest.skip("Golden file not found - run tests to generate")

        expected = golden_path.read_text()
        assert result == expected, "Output differs from golden file"

    def test_render_prime_empty_matches_golden(self) -> None:
        """Test that render_prime with empty context matches golden file."""
        ctx = PrimeContext()
        result = render_prime(ctx)
        golden_path = FIXTURES_DIR / "prime_empty.md"

        if not golden_path.exists():
            pytest.skip("Golden file not found - run tests to generate")

        expected = golden_path.read_text()
        assert result == expected, "Output differs from golden file"

    def test_render_prime_with_content_matches_golden(self) -> None:
        """Test that render_prime with content matches golden file."""
        ctx = PrimeContext(
            workflows=[
                WorkflowSummary(
                    id="20251206-stock-abc",
                    name="stock-analysis",
                    status="published",
                    intent="Analyze TSLA stock data and generate charts",
                ),
                WorkflowSummary(
                    id="20251206-report-xyz",
                    name="daily-report",
                    status="draft",
                    intent="Generate daily sales report from database",
                ),
            ],
            tools=[
                ToolSummary(
                    name="fetch_stock",
                    version="1.0.0",
                    status="stable",
                    description="Fetch stock data from yfinance",
                ),
                ToolSummary(
                    name="generate-pdf",
                    version="1.0.0",
                    status="draft",
                    description="Generate PDF reports",
                ),
            ],
        )
        result = render_prime(ctx)
        golden_path = FIXTURES_DIR / "prime_with_content.md"

        if not golden_path.exists():
            pytest.skip("Golden file not found - run tests to generate")

        expected = golden_path.read_text()
        assert result == expected, "Output differs from golden file"
