"""
RAW Creator - Self-extension capabilities for RAW Platform.

This package provides a creator agent that can:
- Design and generate new tools
- Create workflows from user intent
- Validate implementations
- Refine based on feedback

The creator agent uses a skills-based architecture where each capability
(design, generate, validate, refine) is implemented as a separate skill
that can be loaded on demand.
"""

from .agent import CreatorAgent

__all__ = ["CreatorAgent"]
__version__ = "0.1.0"
