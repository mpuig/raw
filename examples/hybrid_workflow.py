#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pydantic>=2.0", "anthropic>=0.40.0", "httpx>=0.27"]
# ///
"""Example: Hybrid workflow with both deterministic and agentic steps.

This demonstrates the cost-effective agent-native pattern:
- Use deterministic code for predictable operations (parsing, HTTP, math)
- Use @agentic only when LLM reasoning adds value (summarization, extraction)
- Track costs throughout execution

The workflow analyzes an article:
1. Fetch HTML (deterministic, $0)
2. Extract text (deterministic, $0)
3. Summarize (agentic, ~$0.001)
4. Extract topics (agentic, ~$0.0005, cached)

Total cost: ~$0.0015 per execution (first run), ~$0.001 (cached)

Usage:
    python examples/hybrid_workflow.py --article-url "https://example.com/article"
"""

from pydantic import BaseModel, Field

from raw_runtime import BaseWorkflow, agentic
from raw_runtime import raw_step as step


class Params(BaseModel):
    """CLI parameters."""

    article_url: str = Field(..., description="Article URL to analyze")


class HybridWorkflow(BaseWorkflow[Params]):
    """Workflow mixing deterministic and agentic steps.

    Demonstrates best practices:
    - Most operations are deterministic (fast, free)
    - LLM used only for semantic tasks (costs money, adds intelligence)
    - Cache enabled for agentic steps (reduces repeated costs)
    """

    @step("fetch_article")
    def fetch_article(self) -> str:
        """Fetch article HTML from URL.

        Deterministic step - simple HTTP request.
        Cost: $0
        Time: ~0.5 seconds
        """
        import httpx

        self.log(f"Fetching: {self.params.article_url}")

        try:
            response = httpx.get(
                self.params.article_url,
                timeout=10.0,
                follow_redirects=True,
            )
            response.raise_for_status()
            html = response.text

            self.log(f"Fetched {len(html)} characters")
            return html

        except httpx.HTTPError as e:
            self.log(f"HTTP error: {e}")
            raise

    @step("extract_text")
    def extract_text(self, html: str) -> str:
        """Extract text content from HTML.

        Deterministic step - regex and string operations.
        Cost: $0
        Time: <0.1 seconds
        """
        import re

        # Simple extraction (in production, use BeautifulSoup or similar)
        # Remove script and style tags
        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)

        # Remove HTML tags
        text = re.sub(r"<[^>]+>", " ", text)

        # Clean up whitespace
        text = re.sub(r"\s+", " ", text).strip()

        # Limit to save tokens (first 5000 chars usually contain main content)
        text = text[:5000]

        self.log(f"Extracted {len(text)} characters of text")
        return text

    @step("summarize")
    @agentic(
        prompt="""
Summarize this article in 2-3 concise sentences. Focus on the main points.

Article text:
{context.text}

Return only the summary, no preamble.
""",
        model="claude-3-5-haiku-20241022",  # Cheapest model for summarization
        max_tokens=100,  # Limit output tokens to control cost
        cost_limit=0.05,  # Safety limit
        cache=True,  # Cache result for this article
    )
    def summarize(self, text: str) -> str:
        """Generate article summary using LLM.

        Agentic step - requires understanding and synthesis.
        Cost: ~$0.001 per call (first time), $0 (cached)
        Time: ~1-2 seconds (first time), ~0.1 seconds (cached)
        """
        pass  # Implementation injected by @agentic decorator

    @step("extract_topics")
    @agentic(
        prompt="""
Extract 3-5 main topics or themes from this article.

Article text:
{context.text}

Return as a comma-separated list, e.g.: technology, innovation, startups, AI, future
""",
        model="claude-3-5-haiku-20241022",
        max_tokens=50,
        cost_limit=0.05,
        cache=True,  # Cache response for same article
    )
    def extract_topics(self, text: str) -> str:
        """Extract main topics using LLM.

        Agentic step - requires semantic understanding.
        Cost: ~$0.0005 per call (first time), $0 (cached)
        Time: ~1 second (first time), ~0.1 seconds (cached)
        """
        pass  # Implementation injected by @agentic decorator

    @step("analyze_sentiment")
    @agentic(
        prompt="""
Analyze the sentiment/tone of this article.

Article text:
{context.text}

Return one word: positive, negative, or neutral
""",
        model="claude-3-5-haiku-20241022",
        max_tokens=10,
        cost_limit=0.05,
        cache=True,
    )
    def analyze_sentiment(self, text: str) -> str:
        """Analyze article sentiment using LLM.

        Agentic step - requires semantic interpretation.
        Cost: ~$0.0003 per call (first time), $0 (cached)
        Time: ~1 second (first time), ~0.1 seconds (cached)
        """
        pass  # Implementation injected by @agentic decorator

    def run(self) -> int:
        """Execute the hybrid workflow.

        Cost breakdown:
        - Deterministic steps (fetch, extract): $0
        - Agentic steps (summarize, topics, sentiment): ~$0.002 total
        - Subsequent runs (cached): ~$0 (cache hit)

        Total: ~$0.002 per unique article, $0 for repeats
        """
        # Deterministic steps (free)
        html = self.fetch_article()
        text = self.extract_text(html)

        # Agentic steps (cost money, but cached)
        self.log("\nAnalyzing with LLM...")

        summary = self.summarize(text)
        topics = self.extract_topics(text)
        sentiment = self.analyze_sentiment(text)

        # Parse topics into list
        topic_list = [t.strip() for t in topics.split(",")]

        # Save results
        result = {
            "url": self.params.article_url,
            "summary": summary,
            "topics": topic_list,
            "sentiment": sentiment,
            "text_length": len(text),
        }
        self.save("analysis.json", result)

        # Show detailed output
        self.log("\nAnalysis Results:")
        self.log(f"  Summary: {summary}")
        self.log(f"  Topics: {', '.join(topic_list)}")
        self.log(f"  Sentiment: {sentiment}")

        # Show cost breakdown
        if self.context:
            total_cost = sum(
                step_data.get("cost", 0)
                for step_data in self.context._steps.values()
                if "cost" in step_data
            )

            self.log("\nCost Breakdown:")
            self.log("  Deterministic steps (fetch, extract): $0.00")

            agentic_costs = []
            for step_name, step_data in self.context._steps.items():
                if "cost" in step_data:
                    cost = step_data["cost"]
                    cached = step_data.get("cached", False)
                    status = "(cached)" if cached else "(API call)"
                    agentic_costs.append((step_name, cost, status))

            for step_name, cost, status in agentic_costs:
                self.log(f"  {step_name}: ${cost:.4f} {status}")

            self.log(f"\n  Total agentic cost: ${total_cost:.4f}")
            self.log(f"  Total workflow cost: ${total_cost:.4f}")

            # Cache info
            cache_hits = sum(
                1 for data in self.context._steps.values() if data.get("cached", False)
            )
            if cache_hits > 0:
                self.log(
                    f"\n  Note: {cache_hits} steps used cache - rerunning this workflow will be cheaper!"
                )

        return 0


if __name__ == "__main__":
    HybridWorkflow.main()
