"""Cost tracking and estimation for agentic steps.

This module provides utilities for tracking and managing LLM API costs,
including pre-call estimation, actual cost calculation, and per-step tracking.
"""

from typing import Any

# Claude pricing (as of Jan 2025)
PRICING = {
    "claude-3-5-sonnet-20241022": {
        "input": 3.00 / 1_000_000,  # $3 per 1M input tokens
        "output": 15.00 / 1_000_000,  # $15 per 1M output tokens
    },
    "claude-3-5-haiku-20241022": {
        "input": 0.80 / 1_000_000,  # $0.80 per 1M input tokens
        "output": 4.00 / 1_000_000,  # $4.00 per 1M output tokens
    },
    "claude-3-opus-20240229": {
        "input": 15.00 / 1_000_000,  # $15 per 1M input tokens
        "output": 75.00 / 1_000_000,  # $75 per 1M output tokens
    },
}


def estimate_cost(prompt: str, max_tokens: int, model: str) -> float:
    """Estimate cost before API call using tiktoken.

    Args:
        prompt: The prompt text to send to the API
        max_tokens: Maximum output tokens requested
        model: Model identifier

    Returns:
        Estimated cost in USD

    Raises:
        ImportError: If tiktoken is not installed
    """
    try:
        import tiktoken
    except ImportError as e:
        raise ImportError(
            "tiktoken library not installed. Install with: pip install tiktoken"
        ) from e

    # Get pricing for model (default to sonnet)
    pricing = PRICING.get(model, PRICING["claude-3-5-sonnet-20241022"])

    # Count input tokens using tiktoken
    # Claude uses cl100k_base encoding
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        input_tokens = len(encoding.encode(prompt))
    except Exception:
        # Fallback: rough estimate of 4 chars per token
        input_tokens = len(prompt) // 4

    # Estimate output tokens (use max_tokens as upper bound)
    output_tokens = max_tokens

    # Calculate estimated cost
    estimated_cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

    return estimated_cost


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """Calculate actual cost from API response usage.

    Args:
        input_tokens: Number of input tokens used
        output_tokens: Number of output tokens generated
        model: Model identifier

    Returns:
        Actual cost in USD
    """
    # Get pricing for model (default to sonnet)
    pricing = PRICING.get(model, PRICING["claude-3-5-sonnet-20241022"])

    cost = (input_tokens * pricing["input"]) + (output_tokens * pricing["output"])

    return cost


class CostTracker:
    """Tracks costs across multiple agentic steps in a workflow."""

    def __init__(self) -> None:
        self.steps: list[dict[str, Any]] = []
        self.total: float = 0.0

    def add_step(
        self,
        step_name: str,
        cost: float,
        tokens: dict[str, int],
        model: str,
        prompt: str | None = None,
    ) -> None:
        """Track cost for a step.

        Args:
            step_name: Name of the step
            cost: Cost in USD
            tokens: Dictionary with 'input' and 'output' token counts
            model: Model identifier
            prompt: Optional prompt text (first 100 chars for logging)
        """
        step_data = {
            "step_name": step_name,
            "cost": cost,
            "tokens": tokens,
            "model": model,
        }

        if prompt:
            # Store first 100 chars for debugging
            step_data["prompt_preview"] = prompt[:100]

        self.steps.append(step_data)
        self.total += cost

    def get_breakdown(self) -> list[dict[str, Any]]:
        """Return per-step cost breakdown.

        Returns:
            List of dictionaries with step cost information
        """
        return self.steps.copy()

    def get_total(self) -> float:
        """Get total cost across all steps.

        Returns:
            Total cost in USD
        """
        return self.total

    def get_total_tokens(self) -> dict[str, int]:
        """Get total token counts across all steps.

        Returns:
            Dictionary with 'input' and 'output' token totals
        """
        total_input = sum(step["tokens"].get("input", 0) for step in self.steps)
        total_output = sum(step["tokens"].get("output", 0) for step in self.steps)
        return {"input": total_input, "output": total_output}
