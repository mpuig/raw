#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "pydantic-ai>=0.0.17"]
# ///
"""Example workflow demonstrating the @agent decorator for LLM-powered steps.

This workflow analyzes sentiment in text using an LLM and produces structured output.
Run with: uv run examples/sentiment_analysis.py --text "I love this product!"

Requires OPENAI_API_KEY environment variable (or use model="claude-3-5-sonnet-latest"
with ANTHROPIC_API_KEY).
"""

from pydantic import BaseModel, Field

from raw_ai import agent
from raw_runtime import BaseWorkflow


class SentimentResult(BaseModel):
    """Structured sentiment analysis result."""

    score: float = Field(description="Sentiment score from -1 (negative) to 1 (positive)")
    label: str = Field(description="One of: positive, negative, neutral")
    confidence: float = Field(description="Confidence score from 0 to 1")
    reasoning: str = Field(description="Brief explanation of the sentiment classification")


class SentimentParams(BaseModel):
    """Input parameters for sentiment analysis."""

    text: str = Field(description="Text to analyze for sentiment")


class SentimentWorkflow(BaseWorkflow[SentimentParams]):
    """Workflow that analyzes text sentiment using an LLM."""

    @agent(result_type=SentimentResult, model="gpt-4o-mini")
    def analyze_sentiment(self, text: str) -> SentimentResult:
        """You are a sentiment analysis expert. Analyze the given text and determine
        its emotional tone. Consider context, sarcasm, and nuance.

        Return a structured analysis with:
        - score: -1 (very negative) to 1 (very positive)
        - label: positive, negative, or neutral
        - confidence: how confident you are in your assessment
        - reasoning: brief explanation of your classification
        """
        ...

    def run(self) -> int:
        result = self.analyze_sentiment(self.params.text)

        self.console.print("\n[bold]Sentiment Analysis[/bold]")
        self.console.print(f"Text: {self.params.text[:100]}...")
        self.console.print(f"Label: [{'green' if result.label == 'positive' else 'red' if result.label == 'negative' else 'yellow'}]{result.label}[/]")
        self.console.print(f"Score: {result.score:.2f}")
        self.console.print(f"Confidence: {result.confidence:.0%}")
        self.console.print(f"Reasoning: {result.reasoning}")

        self.save("sentiment.json", result.model_dump())
        return 0


if __name__ == "__main__":
    SentimentWorkflow.main()
