"""Convert RAW tools to PydanticAI tools."""

import inspect
from collections.abc import Callable
from typing import Any, get_type_hints


def to_ai_tool(func: Callable) -> dict[str, Any]:
    """Convert a RAW tool function to a PydanticAI tool definition.

    Takes a Python function and generates a tool schema that PydanticAI
    can use to let an LLM call the function.

    Args:
        func: A RAW tool function with type hints

    Returns:
        Tool definition dict compatible with PydanticAI

    Example:
        from tools.weather import get_weather
        from raw_ai import to_ai_tool

        tool_def = to_ai_tool(get_weather)
        # Use with @agent(tools=[tool_def])
    """
    sig = inspect.signature(func)
    hints = get_type_hints(func) if hasattr(func, "__annotations__") else {}
    doc = inspect.getdoc(func) or f"Call {func.__name__}"

    # Build parameters schema
    parameters = {
        "type": "object",
        "properties": {},
        "required": [],
    }

    for name, param in sig.parameters.items():
        if name == "self":
            continue

        param_type = hints.get(name, str)
        param_schema = _type_to_json_schema(param_type)

        # Extract description from docstring if available
        param_schema["description"] = _extract_param_description(doc, name)

        parameters["properties"][name] = param_schema

        if param.default is inspect.Parameter.empty:
            parameters["required"].append(name)

    return {
        "name": func.__name__,
        "description": _extract_function_description(doc),
        "parameters": parameters,
        "function": func,
    }


def _type_to_json_schema(python_type: type) -> dict[str, Any]:
    """Convert Python type to JSON schema."""
    origin = getattr(python_type, "__origin__", None)

    if python_type is str:
        return {"type": "string"}
    elif python_type is int:
        return {"type": "integer"}
    elif python_type is float:
        return {"type": "number"}
    elif python_type is bool:
        return {"type": "boolean"}
    elif origin is list:
        args = getattr(python_type, "__args__", (str,))
        return {"type": "array", "items": _type_to_json_schema(args[0])}
    elif origin is dict:
        return {"type": "object"}
    else:
        return {"type": "string"}


def _extract_function_description(docstring: str) -> str:
    """Extract the main description from a docstring."""
    if not docstring:
        return ""
    lines = docstring.strip().split("\n")
    desc_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith(("args:", "returns:", "raises:", "example:")):
            break
        desc_lines.append(stripped)
    return " ".join(desc_lines).strip()


def _extract_param_description(docstring: str, param_name: str) -> str:
    """Extract parameter description from docstring."""
    if not docstring:
        return f"Parameter {param_name}"

    lines = docstring.split("\n")
    in_args = False
    for line in lines:
        stripped = line.strip()
        if stripped.lower().startswith("args:"):
            in_args = True
            continue
        if in_args:
            if stripped.lower().startswith(("returns:", "raises:", "example:")):
                break
            if stripped.startswith(f"{param_name}:"):
                return stripped[len(param_name) + 1:].strip()

    return f"Parameter {param_name}"


def create_pydantic_ai_tool(func: Callable):
    """Create a PydanticAI-compatible tool from a function.

    This wraps the function for use with PydanticAI's tool system.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function compatible with PydanticAI tools
    """
    from pydantic_ai import Tool

    tool_def = to_ai_tool(func)

    return Tool(
        name=tool_def["name"],
        description=tool_def["description"],
        function=func,
    )
