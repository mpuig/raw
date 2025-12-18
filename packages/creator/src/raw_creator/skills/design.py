"""
Design skill for creator agent.

This skill analyzes user intent and creates design specifications for tools
and workflows. It extracts requirements, identifies dependencies, and
structures the design before generation.

Key responsibilities:
- Parse user intent into structured requirements
- Search for existing tools/workflows to avoid duplication
- Identify required inputs, outputs, and dependencies
- Create actionable design specifications
"""

from typing import Any

from raw_creator.agent import CreatorType, DesignSpec


def design_tool(
    intent: str,
    name: str,
    search_existing: bool = True,
) -> DesignSpec:
    """
    Design a tool from user intent.

    This function analyzes the intent and creates a structured design
    specification that can be used for code generation.

    Args:
        intent: User description of what the tool should do
        name: Proposed name for the tool (will be sanitized)
        search_existing: Whether to search for existing tools first

    Returns:
        Design specification with inputs, outputs, and dependencies

    Example:
        >>> spec = design_tool(
        ...     intent="Fetch stock prices from Yahoo Finance API",
        ...     name="fetch_stock"
        ... )
        >>> spec.name
        'fetch_stock'
        >>> spec.type
        CreatorType.TOOL
    """
    # TODO: Implement actual design logic
    # For now, return a basic spec based on intent

    # Sanitize name: replace hyphens with underscores
    sanitized_name = name.replace("-", "_").lower()

    # Parse intent to extract requirements
    # In a full implementation, this would use NLP or LLM to analyze intent
    inputs = _extract_inputs_from_intent(intent)
    outputs = _extract_outputs_from_intent(intent)
    dependencies = _extract_dependencies_from_intent(intent)

    return DesignSpec(
        name=sanitized_name,
        description=intent,
        type=CreatorType.TOOL,
        inputs=inputs,
        outputs=outputs,
        dependencies=dependencies,
    )


def design_workflow(
    intent: str,
    name: str,
    search_existing: bool = True,
) -> DesignSpec:
    """
    Design a workflow from user intent.

    This function analyzes the intent and creates a structured design
    specification including workflow steps and required tools.

    Args:
        intent: User description of what the workflow should do
        name: Proposed name for the workflow
        search_existing: Whether to search for existing workflows first

    Returns:
        Design specification with steps, inputs, and required tools

    Example:
        >>> spec = design_workflow(
        ...     intent="Fetch TSLA stock data, calculate RSI, save report",
        ...     name="stock_analysis"
        ... )
        >>> spec.name
        'stock_analysis'
        >>> spec.type
        CreatorType.WORKFLOW
        >>> len(spec.steps) > 0
        True
    """
    # TODO: Implement actual design logic
    # For now, return a basic spec based on intent

    # Sanitize name
    sanitized_name = name.replace("-", "_").lower()

    # Parse intent to extract workflow structure
    steps = _extract_steps_from_intent(intent)
    inputs = _extract_inputs_from_intent(intent)
    outputs = _extract_outputs_from_intent(intent)
    dependencies = _extract_dependencies_from_intent(intent)

    return DesignSpec(
        name=sanitized_name,
        description=intent,
        type=CreatorType.WORKFLOW,
        inputs=inputs,
        outputs=outputs,
        dependencies=dependencies,
        steps=steps,
    )


def _extract_inputs_from_intent(intent: str) -> list[dict[str, Any]]:
    """Extract input parameters from intent description.

    This is a simplified implementation. A full version would use
    NLP or LLM to identify parameters from natural language.

    Args:
        intent: User intent description

    Returns:
        List of input parameter specifications
    """
    # Basic keyword detection
    inputs = []

    # Look for common parameter indicators
    if "ticker" in intent.lower() or "symbol" in intent.lower():
        inputs.append(
            {
                "name": "ticker",
                "type": "str",
                "required": True,
                "description": "Stock ticker symbol",
            }
        )

    if "file" in intent.lower():
        inputs.append(
            {
                "name": "input_file",
                "type": "str",
                "required": True,
                "description": "Input file path",
            }
        )

    if "limit" in intent.lower() or "count" in intent.lower():
        inputs.append(
            {
                "name": "limit",
                "type": "int",
                "required": False,
                "default": 10,
                "description": "Number of items to fetch",
            }
        )

    # Default: generic data parameter if nothing else found
    if not inputs:
        inputs.append(
            {
                "name": "data",
                "type": "str",
                "required": True,
                "description": "Input data",
            }
        )

    return inputs


def _extract_outputs_from_intent(intent: str) -> list[dict[str, Any]]:
    """Extract output structure from intent description.

    Args:
        intent: User intent description

    Returns:
        List of output specifications
    """
    # Basic output detection
    outputs = []

    if "price" in intent.lower():
        outputs.append({"name": "prices", "type": "list[float]", "description": "Price data"})

    if "report" in intent.lower():
        outputs.append({"name": "report", "type": "str", "description": "Generated report"})

    # Default: generic result
    if not outputs:
        outputs.append({"name": "result", "type": "dict", "description": "Operation result"})

    return outputs


def _extract_dependencies_from_intent(intent: str) -> list[str]:
    """Extract required dependencies from intent description.

    Args:
        intent: User intent description

    Returns:
        List of Python package names
    """
    dependencies = []

    # Map keywords to packages
    if "http" in intent.lower() or "api" in intent.lower() or "fetch" in intent.lower():
        dependencies.append("httpx>=0.24")

    if "yahoo" in intent.lower() or "stock" in intent.lower():
        dependencies.append("yfinance>=0.2")

    if "csv" in intent.lower() or "excel" in intent.lower():
        dependencies.append("pandas>=2.0")

    if "pdf" in intent.lower():
        dependencies.append("reportlab>=4.0")

    if "json" in intent.lower() and "schema" in intent.lower():
        dependencies.append("jsonschema>=4.0")

    return dependencies


def _extract_steps_from_intent(intent: str) -> list[str]:
    """Extract workflow steps from intent description.

    Args:
        intent: User intent description

    Returns:
        List of step names
    """
    steps = []

    # Look for action verbs that indicate steps
    intent_lower = intent.lower()

    if "fetch" in intent_lower or "get" in intent_lower or "download" in intent_lower:
        steps.append("fetch")

    if "process" in intent_lower or "calculate" in intent_lower or "transform" in intent_lower:
        steps.append("process")

    if "analyze" in intent_lower or "compute" in intent_lower:
        steps.append("analyze")

    if "save" in intent_lower or "export" in intent_lower or "write" in intent_lower:
        steps.append("save")

    if "send" in intent_lower or "notify" in intent_lower or "post" in intent_lower:
        steps.append("notify")

    # Default workflow: fetch -> process -> save
    if not steps:
        steps = ["fetch", "process", "save"]

    return steps
