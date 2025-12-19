"""Decorator for creating programmatic tools.

Allows Claude Code to define simple tools as decorated functions
that automatically get wrapped in the Tool interface.

Usage:
    @tool(description="Get account balance")
    def get_balance(account_id: str) -> float:
        return db.query("SELECT balance FROM accounts WHERE id = ?", account_id)

    # Can then be used in workflows:
    async for event in self.tool("get_balance").run(account_id="123"):
        if event.type == "completed":
            balance = event.data["result"]
"""

import asyncio
import inspect
from collections.abc import AsyncIterator, Callable
from typing import Any, get_type_hints

from raw_runtime.tools.base import Tool, ToolEvent


def tool(
    description: str = "",
    name: str | None = None,
    triggers: list[str] | None = None,
) -> Callable[[Callable[..., Any]], Tool]:
    """Decorator to create a tool from a simple function.

    The decorated function is wrapped in the Tool interface, with
    automatic event emission for started/completed/failed.

    Args:
        description: Human-readable description of what the tool does.
                    Used by LLMs to understand when to call the tool.
        name: Tool name. Defaults to the function name.
        triggers: List of event types this tool can handle.

    Returns:
        A Tool instance wrapping the function.

    Usage:
        @tool(description="Fetch customer data from CRM")
        def get_customer(customer_id: str) -> dict:
            return crm.get(customer_id)

        @tool(description="Send notification")
        async def send_notification(user_id: str, message: str) -> bool:
            await notifications.send(user_id, message)
            return True
    """

    def decorator(func: Callable[..., Any]) -> Tool:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or ""
        tool_triggers = triggers or []

        # Extract parameter info for schema
        sig = inspect.signature(func)
        try:
            hints = get_type_hints(func)
        except Exception:
            hints = {}

        parameters: dict[str, Any] = {}
        for param_name, param in sig.parameters.items():
            param_type = hints.get(param_name, Any)
            param_info: dict[str, Any] = {"type": _type_to_json_schema(param_type)}
            if param.default is not inspect.Parameter.empty:
                param_info["default"] = param.default
            parameters[param_name] = param_info

        is_async = asyncio.iscoroutinefunction(func)

        class ProgrammaticTool(Tool):
            name = tool_name
            description = tool_description
            triggers = tool_triggers
            schema = {"parameters": parameters}

            async def run(self, **config: Any) -> AsyncIterator[ToolEvent]:
                yield self._emit_started(**config)
                try:
                    if is_async:
                        result = await func(**config)
                    else:
                        result = func(**config)
                    yield self._emit_completed(result=result)
                except Exception as e:
                    yield self._emit_failed(str(e))

        # Preserve function metadata
        ProgrammaticTool.__doc__ = func.__doc__
        ProgrammaticTool.__module__ = func.__module__

        return ProgrammaticTool()

    return decorator


def _type_to_json_schema(type_hint: Any) -> str:
    """Convert Python type hint to JSON schema type."""
    if type_hint is None or type_hint is type(None):
        return "null"

    type_name = getattr(type_hint, "__name__", str(type_hint))

    type_map = {
        "str": "string",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "list": "array",
        "dict": "object",
        "List": "array",
        "Dict": "object",
    }

    return type_map.get(type_name, "string")
