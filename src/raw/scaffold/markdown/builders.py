"""Markdown builder classes for structured content generation."""

from __future__ import annotations

from raw.scaffold.markdown.escape import escape_table_cell


class Table:
    """Builder for markdown tables.

    Example:
        table = Table(["Command", "Description"])
        table.add_row("raw init", "Initialize RAW")
        table.add_row("raw run", "Execute workflow")
        print(table.render())
    """

    def __init__(self, headers: list[str]) -> None:
        self.headers = headers
        self.rows: list[list[str]] = []

    def add_row(self, *values: str) -> Table:
        """Add a row to the table."""
        if len(values) != len(self.headers):
            raise ValueError(f"Row has {len(values)} values, expected {len(self.headers)}")
        self.rows.append([escape_table_cell(str(v)) for v in values])
        return self

    def render(self) -> str:
        """Render the table to markdown."""
        if not self.headers:
            return ""

        lines = []

        # Header row
        header_row = "| " + " | ".join(self.headers) + " |"
        lines.append(header_row)

        # Separator row
        separator = "| " + " | ".join("-" * len(h) for h in self.headers) + " |"
        lines.append(separator)

        # Data rows
        for row in self.rows:
            data_row = "| " + " | ".join(row) + " |"
            lines.append(data_row)

        return "\n".join(lines)


class CodeBlock:
    """Builder for fenced code blocks.

    Example:
        code = CodeBlock("python")
        code.add_line("def hello():")
        code.add_line("    print('Hello')")
        print(code.render())
    """

    def __init__(self, language: str = "") -> None:
        self.language = language
        self.lines: list[str] = []

    def add_line(self, line: str) -> CodeBlock:
        """Add a line of code."""
        self.lines.append(line)
        return self

    def add_lines(self, *lines: str) -> CodeBlock:
        """Add multiple lines of code."""
        self.lines.extend(lines)
        return self

    def set_content(self, content: str) -> CodeBlock:
        """Set the entire code block content."""
        self.lines = content.split("\n")
        return self

    def render(self) -> str:
        """Render the code block to markdown."""
        content = "\n".join(self.lines)
        return f"```{self.language}\n{content}\n```"


class List:
    """Builder for markdown lists.

    Example:
        ul = List()
        ul.add_item("First item")
        ul.add_item("Second item")
        print(ul.render())
    """

    def __init__(self, ordered: bool = False) -> None:
        self.ordered = ordered
        self.items: list[str] = []

    def add_item(self, text: str) -> List:
        """Add an item to the list."""
        self.items.append(text)
        return self

    def render(self) -> str:
        """Render the list to markdown."""
        lines = []
        for i, item in enumerate(self.items):
            if self.ordered:
                lines.append(f"{i + 1}. {item}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)


class Section:
    """Builder for markdown sections with heading and content.

    Example:
        section = Section("Getting Started", level=2)
        section.add_paragraph("This is the intro.")
        section.add_code_block("bash", "raw init")
        print(section.render())
    """

    def __init__(self, title: str, level: int = 2) -> None:
        if level < 1 or level > 6:
            raise ValueError("Heading level must be between 1 and 6")
        self.title = title
        self.level = level
        self.content: list[str] = []

    def add_paragraph(self, text: str) -> Section:
        """Add a paragraph."""
        self.content.append(text)
        self.content.append("")  # Blank line after paragraph
        return self

    def add_code_block(self, language: str, code: str) -> Section:
        """Add a code block."""
        block = CodeBlock(language)
        block.set_content(code)
        self.content.append(block.render())
        self.content.append("")
        return self

    def add_table(self, table: Table) -> Section:
        """Add a table."""
        self.content.append(table.render())
        self.content.append("")
        return self

    def add_list(self, items: list[str], ordered: bool = False) -> Section:
        """Add a list."""
        md_list = List(ordered=ordered)
        for item in items:
            md_list.add_item(item)
        self.content.append(md_list.render())
        self.content.append("")
        return self

    def add_raw(self, content: str) -> Section:
        """Add raw markdown content."""
        self.content.append(content)
        return self

    def render(self) -> str:
        """Render the section to markdown."""
        heading = "#" * self.level + " " + self.title
        body = "\n".join(self.content)
        return f"{heading}\n\n{body}"


class Document:
    """Builder for complete markdown documents.

    Example:
        doc = Document()
        doc.add_heading("My Document", level=1)
        doc.add_paragraph("Introduction paragraph.")
        doc.add_section(some_section)
        print(doc.render())
    """

    def __init__(self) -> None:
        self.parts: list[str] = []

    def add_heading(self, title: str, level: int = 1) -> Document:
        """Add a heading."""
        self.parts.append("#" * level + " " + title)
        self.parts.append("")
        return self

    def add_paragraph(self, text: str) -> Document:
        """Add a paragraph."""
        self.parts.append(text)
        self.parts.append("")
        return self

    def add_section(self, section: Section) -> Document:
        """Add a section."""
        self.parts.append(section.render())
        return self

    def add_code_block(self, language: str, code: str) -> Document:
        """Add a code block."""
        block = CodeBlock(language)
        block.set_content(code)
        self.parts.append(block.render())
        self.parts.append("")
        return self

    def add_table(self, table: Table) -> Document:
        """Add a table."""
        self.parts.append(table.render())
        self.parts.append("")
        return self

    def add_list(self, items: list[str], ordered: bool = False) -> Document:
        """Add a list."""
        md_list = List(ordered=ordered)
        for item in items:
            md_list.add_item(item)
        self.parts.append(md_list.render())
        self.parts.append("")
        return self

    def add_blockquote(self, text: str) -> Document:
        """Add a blockquote."""
        lines = text.split("\n")
        quoted = "\n".join(f"> {line}" for line in lines)
        self.parts.append(quoted)
        self.parts.append("")
        return self

    def add_horizontal_rule(self) -> Document:
        """Add a horizontal rule."""
        self.parts.append("---")
        self.parts.append("")
        return self

    def add_raw(self, content: str) -> Document:
        """Add raw markdown content."""
        self.parts.append(content)
        return self

    def render(self) -> str:
        """Render the document to markdown."""
        return "\n".join(self.parts).rstrip() + "\n"
