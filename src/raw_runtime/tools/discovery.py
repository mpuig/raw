"""Tool discovery for RAW workflows.

Automatically scans tools/ directory and discovers tool packages,
enabling dynamic tool registration without code changes.
"""

import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from raw_runtime.tools.base import Tool

logger = logging.getLogger(__name__)


def discover_tools(tools_dir: Path) -> dict[str, type[Tool]]:
    """Scan tools/ directory and discover all tool packages.

    For each package in tools/:
    - Look for tool.py or __init__.py
    - Look for config.yaml with metadata
    - Extract tool class or function
    - Return dict of {name: tool_class}

    Args:
        tools_dir: Path to tools directory to scan

    Returns:
        Dict mapping tool name to tool class/instance

    Example:
        tools = discover_tools(Path("tools"))
        # {'coingecko': CoinGeckoTool, 'email_helper': EmailTool}
    """
    if not tools_dir.exists() or not tools_dir.is_dir():
        logger.warning(f"Tools directory does not exist: {tools_dir}")
        return {}

    discovered: dict[str, type[Tool]] = {}

    for package_dir in tools_dir.iterdir():
        if not package_dir.is_dir():
            continue

        if package_dir.name.startswith("_") or package_dir.name.startswith("."):
            continue

        try:
            metadata = load_tool_metadata(package_dir)
            tool_cls = scan_tool_module(package_dir)

            if tool_cls is not None:
                tool_name = metadata.get("name", package_dir.name)
                discovered[tool_name] = tool_cls
                logger.debug(f"Discovered tool: {tool_name} from {package_dir}")
            else:
                logger.debug(f"No tool class found in {package_dir}")

        except Exception as e:
            logger.warning(f"Failed to discover tool in {package_dir}: {e}")
            continue

    return discovered


def load_tool_metadata(tool_dir: Path) -> dict[str, Any]:
    """Load metadata from config.yaml if exists.

    Args:
        tool_dir: Path to tool package directory

    Returns:
        Dict with metadata, empty if no config.yaml found
    """
    config_path = tool_dir / "config.yaml"
    if not config_path.exists():
        return {}

    try:
        with config_path.open("r") as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    except Exception as e:
        logger.warning(f"Failed to load config from {config_path}: {e}")
        return {}


def scan_tool_module(module_path: Path) -> type[Tool] | Tool | None:
    """Import module and find tool class/function.

    Looks for:
    1. tool.py with Tool subclass or @tool decorated function
    2. __init__.py with Tool subclass or @tool decorated function

    Args:
        module_path: Path to tool package directory

    Returns:
        Tool class, Tool instance, or None if not found
    """
    tool_py = module_path / "tool.py"
    init_py = module_path / "__init__.py"

    module_file = tool_py if tool_py.exists() else init_py if init_py.exists() else None

    if module_file is None:
        return None

    try:
        module_name = f"tools.{module_path.name}"
        spec = importlib.util.spec_from_file_location(module_name, module_file)

        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        # Look for Tool subclass
        for attr_name in dir(module):
            if attr_name.startswith("_"):
                continue

            attr = getattr(module, attr_name)

            # Check if it's a Tool subclass (not the base Tool class)
            if isinstance(attr, type) and issubclass(attr, Tool) and attr is not Tool:
                return attr

            # Check if it's a Tool instance (from @tool decorator)
            if isinstance(attr, Tool):
                return attr

        return None

    except ImportError as e:
        logger.warning(f"Failed to import tool module {module_path}: {e}")
        return None
    except Exception as e:
        logger.warning(f"Error scanning tool module {module_path}: {e}")
        return None
