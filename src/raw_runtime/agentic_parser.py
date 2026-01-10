"""Response parsing for @agentic decorator with comprehensive type support.

This module provides robust parsing of LLM responses into Python types:
- Primitives: str, int, float, bool
- Literals: Literal["a", "b"]
- Structures: list, dict, Pydantic models
- Advanced: Union, Optional
- Handles markdown code blocks and natural language responses
"""

import json
import re
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel, ValidationError


class ResponseParsingError(Exception):
    """Raised when response cannot be parsed to expected type."""

    def __init__(
        self,
        response: str,
        expected_type: Any,
        error: str,
        suggestions: list[str] | None = None,
    ) -> None:
        self.response = response
        self.expected_type = expected_type
        self.error = error
        self.suggestions = suggestions or []

        type_name = _format_type_name(expected_type)
        msg = f"Failed to parse response to {type_name}: {error}\n\nResponse (truncated to 500 chars):\n{response[:500]}"

        if self.suggestions:
            msg += "\n\nSuggestions:\n" + "\n".join(f"  - {s}" for s in self.suggestions)

        super().__init__(msg)


def _format_type_name(type_hint: Any) -> str:
    """Format type hint into readable string."""
    if type_hint is None or type_hint is type(None):
        return "None"
    if hasattr(type_hint, "__name__"):
        return type_hint.__name__

    origin = get_origin(type_hint)
    if origin is None:
        return str(type_hint)

    # Handle Union[X, Y] and Optional[X]
    if origin is Union:
        args = get_args(type_hint)
        if len(args) == 2 and type(None) in args:
            # Optional[X]
            non_none = [a for a in args if a is not type(None)][0]
            return f"Optional[{_format_type_name(non_none)}]"
        else:
            # Union[X, Y, Z]
            arg_names = [_format_type_name(a) for a in args]
            return f"Union[{', '.join(arg_names)}]"

    # Handle generics like list[int], dict[str, int]
    args = get_args(type_hint)
    if args:
        arg_names = [_format_type_name(a) for a in args]
        return f"{origin.__name__}[{', '.join(arg_names)}]"

    return origin.__name__ if hasattr(origin, "__name__") else str(origin)


def extract_json(response: str) -> str:
    """Extract JSON from markdown code blocks or raw text.

    Handles:
    - ```json {...} ```
    - ``` {...} ```
    - Raw JSON: {...} or [...]

    Args:
        response: Raw LLM response that may contain JSON

    Returns:
        Extracted JSON string

    Raises:
        ResponseParsingError: If no valid JSON found
    """
    response = response.strip()

    # Try to extract from markdown code block
    json_block_patterns = [
        r"```json\s*\n(.*?)\n```",  # ```json ... ```
        r"```\s*\n(.*?)\n```",  # ``` ... ```
    ]

    for pattern in json_block_patterns:
        match = re.search(pattern, response, re.DOTALL)
        if match:
            return match.group(1).strip()

    # Try to find JSON object or array in text
    # Look for {...} or [...]
    brace_match = re.search(r"\{.*\}", response, re.DOTALL)
    if brace_match:
        return brace_match.group(0)

    bracket_match = re.search(r"\[.*\]", response, re.DOTALL)
    if bracket_match:
        return bracket_match.group(0)

    # No JSON found, return as-is
    return response


def parse_bool(response: str) -> bool:
    """Parse boolean from various representations.

    Accepts:
    - true/false (case insensitive)
    - yes/no
    - 1/0
    - y/n

    Args:
        response: String to parse as boolean

    Returns:
        Parsed boolean value

    Raises:
        ResponseParsingError: If value is ambiguous
    """
    normalized = response.strip().lower()

    # True values
    if normalized in ("true", "yes", "1", "y"):
        return True

    # False values
    if normalized in ("false", "no", "0", "n"):
        return False

    # Ambiguous values
    raise ResponseParsingError(
        response=response,
        expected_type=bool,
        error=f"Ambiguous boolean value: '{response}'",
        suggestions=[
            "Expected: true/false, yes/no, 1/0, or y/n (case insensitive)",
            "Try reformatting your prompt to request explicit true/false values",
        ],
    )


def parse_int(response: str) -> int:
    """Parse integer from response.

    Handles:
    - Plain numbers: "42"
    - Numbers in text: "The answer is 42"
    - Negative numbers: "-5"

    Args:
        response: String containing integer

    Returns:
        Parsed integer value

    Raises:
        ResponseParsingError: If no valid integer found
    """
    response = response.strip()

    # Try direct conversion first
    try:
        return int(response)
    except ValueError:
        pass

    # Try to extract number from text
    # Look for integers (including negative)
    match = re.search(r"-?\d+", response)
    if match:
        return int(match.group(0))

    raise ResponseParsingError(
        response=response,
        expected_type=int,
        error="No valid integer found in response",
        suggestions=[
            "Expected a numeric value like: 42, -5, or 100",
            "Try asking for 'just the number' in your prompt",
        ],
    )


def parse_float(response: str) -> float:
    """Parse float from response.

    Handles:
    - Plain numbers: "3.14"
    - Numbers in text: "The value is 3.14"
    - Scientific notation: "1.5e-10"
    - Negative numbers: "-2.5"

    Args:
        response: String containing float

    Returns:
        Parsed float value

    Raises:
        ResponseParsingError: If no valid float found
    """
    response = response.strip()

    # Try direct conversion first
    try:
        return float(response)
    except ValueError:
        pass

    # Try to extract number from text
    # Look for floats (including negative, scientific notation)
    match = re.search(r"-?\d+\.?\d*(?:[eE][+-]?\d+)?", response)
    if match:
        try:
            return float(match.group(0))
        except ValueError:
            pass

    raise ResponseParsingError(
        response=response,
        expected_type=float,
        error="No valid float found in response",
        suggestions=[
            "Expected a numeric value like: 3.14, -2.5, or 1.5e-10",
            "Try asking for 'just the number' in your prompt",
        ],
    )


def parse_literal(response: str, literal_type: Any) -> Any:
    """Parse and validate Literal type.

    Args:
        response: String to validate against literal values
        literal_type: Literal type with allowed values

    Returns:
        Validated literal value

    Raises:
        ResponseParsingError: If value not in allowed set
    """
    from typing import get_args

    response = response.strip()
    allowed_values = get_args(literal_type)

    # Direct match
    if response in allowed_values:
        return response

    # Case-insensitive match for strings
    for value in allowed_values:
        if isinstance(value, str) and response.lower() == value.lower():
            return value

    raise ResponseParsingError(
        response=response,
        expected_type=literal_type,
        error=f"Response '{response}' not in allowed values: {allowed_values}",
        suggestions=[
            f"Expected one of: {', '.join(repr(v) for v in allowed_values)}",
            "Try updating your prompt to specify allowed values explicitly",
        ],
    )


def parse_pydantic_model(response: str, model_class: type[BaseModel]) -> BaseModel:
    """Parse Pydantic model from JSON response.

    Args:
        response: JSON string or text containing JSON
        model_class: Pydantic model class to parse into

    Returns:
        Validated Pydantic model instance

    Raises:
        ResponseParsingError: If JSON invalid or validation fails
    """
    # Extract JSON from response
    json_str = extract_json(response)

    # Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ResponseParsingError(
            response=response,
            expected_type=model_class,
            error=f"Invalid JSON: {e}",
            suggestions=[
                "Expected valid JSON object",
                "Try asking Claude to return 'only valid JSON' in your prompt",
                "Use structured output mode for Pydantic models",
            ],
        ) from e

    # Validate against model
    try:
        return model_class.model_validate(data)
    except ValidationError as e:
        raise ResponseParsingError(
            response=response,
            expected_type=model_class,
            error=f"Validation failed: {e}",
            suggestions=[
                f"Expected fields: {', '.join(model_class.model_fields.keys())}",
                "Check that all required fields are present in the response",
            ],
        ) from e


def parse_list(response: str, list_type: Any) -> list[Any]:
    """Parse list from JSON response.

    Args:
        response: JSON string or text containing JSON array
        list_type: List type hint (e.g., list[int])

    Returns:
        Parsed list

    Raises:
        ResponseParsingError: If not valid JSON array
    """
    # Extract JSON from response
    json_str = extract_json(response)

    # Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ResponseParsingError(
            response=response,
            expected_type=list_type,
            error=f"Invalid JSON: {e}",
            suggestions=[
                "Expected valid JSON array like: [1, 2, 3]",
                "Try asking Claude to return 'only a JSON array' in your prompt",
            ],
        ) from e

    if not isinstance(data, list):
        raise ResponseParsingError(
            response=response,
            expected_type=list_type,
            error=f"Expected array but got {type(data).__name__}",
            suggestions=["Response must be a JSON array: [...]"],
        )

    return data


def parse_dict(response: str, dict_type: Any) -> dict[Any, Any]:
    """Parse dict from JSON response.

    Args:
        response: JSON string or text containing JSON object
        dict_type: Dict type hint (e.g., dict[str, int])

    Returns:
        Parsed dict

    Raises:
        ResponseParsingError: If not valid JSON object
    """
    # Extract JSON from response
    json_str = extract_json(response)

    # Parse JSON
    try:
        data = json.loads(json_str)
    except json.JSONDecodeError as e:
        raise ResponseParsingError(
            response=response,
            expected_type=dict_type,
            error=f"Invalid JSON: {e}",
            suggestions=[
                'Expected valid JSON object like: {"key": "value"}',
                "Try asking Claude to return 'only a JSON object' in your prompt",
            ],
        ) from e

    if not isinstance(data, dict):
        raise ResponseParsingError(
            response=response,
            expected_type=dict_type,
            error=f"Expected object but got {type(data).__name__}",
            suggestions=["Response must be a JSON object: {...}"],
        )

    return data


def parse_union(response: str, union_type: Any) -> Any:
    """Parse Union type by trying each option in order.

    Args:
        response: String to parse
        union_type: Union type hint (e.g., Union[int, str])

    Returns:
        Parsed value as first matching type

    Raises:
        ResponseParsingError: If no type in union matches
    """
    args = get_args(union_type)
    errors = []

    for arg_type in args:
        try:
            return parse_response(response, arg_type)
        except ResponseParsingError as e:
            errors.append(f"  - {_format_type_name(arg_type)}: {e.error}")
            continue

    # None of the types worked
    raise ResponseParsingError(
        response=response,
        expected_type=union_type,
        error="Could not parse as any union member",
        suggestions=[
            "Tried parsing as:",
            *errors,
            "Try making your prompt more specific about the expected format",
        ],
    )


def parse_optional(response: str, optional_type: Any) -> Any:
    """Parse Optional type (Union[X, None]).

    Args:
        response: String to parse
        optional_type: Optional type hint (e.g., Optional[int])

    Returns:
        Parsed value or None
    """
    response = response.strip()

    # Check for None-like values
    if response.lower() in ("none", "null", ""):
        return None

    # Parse as the non-None type
    args = get_args(optional_type)
    non_none_type = [a for a in args if a is not type(None)][0]
    return parse_response(response, non_none_type)


def parse_response(response: str, return_type: Any) -> Any:
    """Parse LLM response based on return type hint.

    Supports:
    - str: Return as-is (strip whitespace)
    - int: Parse integer, handle "42" or "The answer is 42"
    - float: Parse float
    - bool: Parse yes/no, true/false, 1/0
    - Literal: Validate against allowed values
    - Pydantic models: Parse JSON and validate
    - list: Parse JSON array
    - dict: Parse JSON object
    - Union types: Try each type in order
    - Optional: Handle None

    Args:
        response: Raw LLM response text
        return_type: Expected Python type from function signature

    Returns:
        Parsed value of correct type

    Raises:
        ResponseParsingError: If response cannot be parsed to expected type
    """
    response = response.strip()

    # Handle empty response
    if not response:
        if return_type is type(None) or return_type is None:
            return None
        raise ResponseParsingError(
            response=response,
            expected_type=return_type,
            error="Empty response",
            suggestions=["LLM returned empty string - check your prompt"],
        )

    # Get origin type for generics (e.g., list from list[str])
    origin = get_origin(return_type)

    # Handle None/NoneType
    if return_type is None or return_type is type(None):
        return None

    # Handle str
    if return_type is str:
        return response

    # Handle int
    if return_type is int:
        return parse_int(response)

    # Handle float
    if return_type is float:
        return parse_float(response)

    # Handle bool
    if return_type is bool:
        return parse_bool(response)

    # Handle Literal types
    from typing import Literal

    if get_origin(return_type) is Literal:
        return parse_literal(response, return_type)

    # Handle Union types (including Optional)
    if origin is Union:
        args = get_args(return_type)
        # Check if Optional (Union[X, None])
        if len(args) == 2 and type(None) in args:
            return parse_optional(response, return_type)
        else:
            return parse_union(response, return_type)

    # Handle Pydantic models
    if isinstance(return_type, type) and issubclass(return_type, BaseModel):
        return parse_pydantic_model(response, return_type)

    # Handle list
    if origin is list or return_type is list:
        return parse_list(response, return_type)

    # Handle dict
    if origin is dict or return_type is dict:
        return parse_dict(response, return_type)

    # Fallback: return as string
    return response
