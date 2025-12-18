"""LiteLLM integration for RAW Platform.

Provides multi-provider LLM support through LiteLLM, enabling unified access
to 100+ providers including OpenAI, Anthropic, Azure, AWS Bedrock, and more.
"""

from integration_llm.litellm import LiteLLMDriver

__version__ = "0.1.0"

__all__ = ["LiteLLMDriver"]
