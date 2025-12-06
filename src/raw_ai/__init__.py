"""RAW AI - Agentic capabilities for RAW workflows.

This module provides LLM-powered steps using PydanticAI for structured output.

Example:
    from pydantic import BaseModel
    from raw_runtime import BaseWorkflow, step
    from raw_ai import agent

    class Sentiment(BaseModel):
        score: float
        label: str

    class MyWorkflow(BaseWorkflow):
        @agent(result_type=Sentiment)
        def analyze(self, text: str) -> Sentiment:
            '''Analyze the sentiment of the given text.'''
            ...

        def run(self) -> int:
            result = self.analyze("I love this product!")
            self.save("sentiment.json", result.model_dump())
            return 0
"""

from raw_ai.decorator import agent
from raw_ai.tools import to_ai_tool
from raw_ai.config import AIConfig, get_model

__all__ = ["agent", "to_ai_tool", "AIConfig", "get_model"]
