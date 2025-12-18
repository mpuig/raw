# integration-llm

LiteLLM integration for RAW Platform - multi-provider LLM support.

## Overview

Provides a unified interface for 100+ LLM providers through LiteLLM, including OpenAI, Anthropic, Azure OpenAI, AWS Bedrock, Google Vertex AI, and local models via Ollama.

## Installation

```bash
uv add integration-llm
```

## Usage

```python
from integration_llm import LiteLLMDriver

# Initialize driver (uses environment variables for API keys by default)
driver = LiteLLMDriver()

# Or provide explicit configuration
driver = LiteLLMDriver(
    api_key="your-api-key",
    api_base="https://custom-endpoint.com",
    default_headers={"Custom-Header": "value"}
)

# Stream chat completion
messages = [{"role": "user", "content": "Hello!"}]
async for chunk in driver.stream_chat(
    messages=messages,
    model="gpt-4o",
    temperature=0.7
):
    if chunk.content:
        print(chunk.content, end="", flush=True)
```

## Supported providers

Model names follow LiteLLM conventions:
- OpenAI: `gpt-4o`, `gpt-4-turbo`
- Anthropic: `claude-3-opus-20240229`, `claude-3-sonnet-20240229`
- Azure: `azure/deployment-name`
- Bedrock: `bedrock/anthropic.claude-3-sonnet`
- Ollama: `ollama/llama2`

## Architecture

Implements the `LLMDriver` protocol from `raw-core`, providing:
- Streaming chat completions
- Tool calling support
- Multi-provider abstraction
- Consistent error handling via `LLMServiceError`

## Dependencies

- `raw-core`: Core protocols and errors
- `litellm`: Multi-provider LLM client
