#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   # Add your dependencies here:
#   # "requests>=2.28",
#   # "pandas>=2.0",
# ]
# ///
"""
TOOL_NAME - TOOL_DESCRIPTION

A reusable RAW tool for WHAT_IT_DOES.

This tool lives in tools/<tool_name>/ and can be imported as:
    from tools.<tool_name> import <function_name>

Usage (CLI):
    uv run tool.py --param1 value [--param2 value]

Example:
    uv run tool.py --param1 "example"
"""

from typing import Any


def tool_name(
    param1: str,
    param2: int = 10,
) -> dict[str, Any]:
    """TOOL_DESCRIPTION

    Args:
        param1: Description of required parameter
        param2: Description of optional parameter with default

    Returns:
        Dictionary containing:
        - result: The main output
        - metadata: Additional information

    Raises:
        ValueError: If param1 is empty or invalid

    Example:
        >>> result = tool_name("test", param2=5)
        >>> result["result"]
        'processed'
    """
    # === Input Validation ===
    if not param1:
        raise ValueError("param1 cannot be empty")

    if param2 < 0:
        raise ValueError(f"param2 must be non-negative, got {param2}")

    # === Main Logic ===
    # TODO: Implement your tool logic here

    # Example processing
    processed_value = f"processed_{param1}"

    # === Return Results ===
    return {
        "success": True,
        "result": processed_value,
        "metadata": {
            "param1": param1,
            "param2": param2,
        },
    }


# === CLI Support ===
if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description=__doc__.split("\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Required arguments
    parser.add_argument(
        "--param1",
        required=True,
        help="Required parameter description",
    )

    # Optional arguments with defaults
    parser.add_argument(
        "--param2",
        type=int,
        default=10,
        help="Optional parameter (default: 10)",
    )

    args = parser.parse_args()

    try:
        result = tool_name(
            param1=args.param1,
            param2=args.param2,
        )
        print(json.dumps(result, indent=2, default=str))
    except ValueError as e:
        print(json.dumps({"success": False, "error": str(e)}, indent=2))
        exit(1)
    except Exception as e:
        print(json.dumps({"success": False, "error": f"Unexpected error: {e}"}, indent=2))
        exit(1)
