# Call Center Solution - RAW Platform Example

A production-ready, AI-powered call center solution built on the RAW Platform. This example demonstrates how to build an intelligent voice agent that can handle customer inquiries, look up information, and execute business logic through natural conversation.

## Overview

This solution showcases a complete call center implementation with:

- Real-time voice conversations using Deepgram (STT) and ElevenLabs (TTS)
- Twilio integration for phone call handling
- Customer lookup and order management skills
- Post-call workflow automation (summarization, CRM updates, email notifications)
- Production-ready FastAPI server with health checks and telemetry
- State management and conversation tracking
- Graceful error handling and escalation

## Use case

A customer calls your support line. The AI agent:

1. Greets the customer and identifies them by phone number
2. Looks up their account and recent orders
3. Answers questions using business logic and database lookups
4. Schedules callbacks or escalates to human agents when needed
5. After the call, automatically summarizes the conversation and updates your CRM

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Twilio Voice Gateway                     │
│                  (Incoming/Outgoing Calls)                  │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Server                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              Voice Transport Layer                   │   │
│  │  - Deepgram STT (Speech-to-Text)                    │   │
│  │  - ElevenLabs TTS (Text-to-Speech)                  │   │
│  │  - Pipecat Pipeline (Real-time Audio Processing)   │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Conversation Engine (Bot)                  │   │
│  │  - LLM Driver (Claude/GPT/etc)                      │   │
│  │  - Context Management                                │   │
│  │  - Tool Execution                                    │   │
│  └──────────────────────────────────────────────────────┘   │
│                         │                                    │
│                         ▼                                    │
│  ┌──────────────────────────────────────────────────────┐   │
│  │                 Skills (Tools)                       │   │
│  │  - lookup_customer                                   │   │
│  │  - check_order_status                                │   │
│  │  - schedule_callback                                 │   │
│  └──────────────────────────────────────────────────────┘   │
└───────────────────────┬─────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│              Post-Call Workflow (Agent)                     │
│  - Summarize conversation                                   │
│  - Update CRM with call details                             │
│  - Send follow-up email                                     │
│  - Create support ticket if needed                          │
└─────────────────────────────────────────────────────────────┘
```

## Setup

### Prerequisites

- Python 3.10+
- uv (recommended): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Twilio account with phone number
- Deepgram API key
- ElevenLabs API key
- OpenAI or Anthropic API key

### Installation

1. Clone and navigate to the example:

```bash
cd /path/to/raw/examples/solution-callcenter
```

2. Copy the environment template:

```bash
cp .env.example .env
```

3. Edit `.env` and add your credentials:

```bash
# LLM Provider
OPENAI_API_KEY=sk-...
# or
ANTHROPIC_API_KEY=sk-ant-...

# Voice Services
DEEPGRAM_API_KEY=...
ELEVENLABS_API_KEY=...

# Twilio
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_PHONE_NUMBER=+1...

# Optional: Database
DATABASE_URL=postgresql://user:pass@localhost/callcenter
REDIS_URL=redis://localhost:6379
```

4. Install dependencies:

```bash
uv sync
```

## Configuration

The solution is configured via `config.yaml`. Key sections:

### LLM settings

```yaml
llm:
  model: "claude-3-5-sonnet-20241022"  # or "gpt-4o"
  temperature: 0.7
  max_tokens: 2000
```

### Voice settings

```yaml
voice:
  stt:
    provider: "deepgram"
    model: "nova-2"
    language: "en-US"

  tts:
    provider: "elevenlabs"
    voice_id: "21m00Tcm4TlvDq8ikWAM"  # Rachel
    model: "eleven_turbo_v2_5"
    stability: 0.5
    similarity_boost: 0.75
```

### Server settings

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  log_level: "info"
  enable_cors: true
  enable_metrics: true
```

### Twilio integration

```yaml
twilio:
  webhook_path: "/voice/twilio"
  status_callback_path: "/voice/status"
```

## Running the solution

### Development mode

Start the server with auto-reload:

```bash
uv run python -m callcenter.main
```

The server will start on `http://localhost:8000`.

### Production mode

```bash
uv run uvicorn callcenter.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Testing with Twilio

1. Start the server (must be publicly accessible)
2. Use ngrok for local development:

```bash
ngrok http 8000
```

3. Configure your Twilio phone number webhook:
   - Voice webhook: `https://your-domain.ngrok.io/voice/twilio`
   - Status callback: `https://your-domain.ngrok.io/voice/status`

4. Call your Twilio number and interact with the AI agent

## API endpoints

### Health checks

- `GET /health` - Comprehensive health check with dependency status
- `GET /ready` - Readiness probe (returns 200 when ready)
- `GET /live` - Liveness probe (always returns 200)

### Voice

- `POST /voice/twilio` - Twilio webhook for incoming calls
- `POST /voice/status` - Call status updates from Twilio

### Webhooks

- `POST /webhook/conversation` - Create a new text-based conversation
- `POST /webhook/conversation/{id}/message` - Send a message to conversation

### Metrics

- `GET /metrics` - Application metrics (if enabled)

## Skills

Skills are the tools that the AI agent can use during conversations. Each skill is a Python function with a JSON schema that the LLM uses to determine when to call it.

### lookup_customer

Look up customer information by phone number or account ID.

```python
result = await lookup_customer(phone="+15551234567")
# Returns: {"id": "cust_123", "name": "John Doe", "tier": "premium", ...}
```

### check_order_status

Check the status of a customer's order.

```python
result = await check_order_status(order_id="ORD-12345")
# Returns: {"status": "shipped", "tracking": "1Z999...", "eta": "2024-12-20"}
```

### schedule_callback

Schedule a callback for the customer.

```python
result = await schedule_callback(
    customer_id="cust_123",
    preferred_time="2024-12-20T14:00:00Z",
    reason="Billing question"
)
# Returns: {"callback_id": "cb_456", "scheduled": True}
```

## Workflows

Workflows are autonomous agents that can run after a conversation ends. They use the RAW Agent runtime for orchestration.

### post_call workflow

Automatically triggered after each call ends:

1. Generates a summary of the conversation
2. Updates the CRM with call details and outcome
3. Sends follow-up email to customer if needed
4. Creates a support ticket for unresolved issues
5. Logs metrics for analytics

## Extending the solution

### Adding new skills

1. Create a new file in `src/callcenter/skills/`:

```python
# src/callcenter/skills/cancel_order.py

def cancel_order(order_id: str, reason: str) -> dict:
    """Cancel a customer order.

    Args:
        order_id: The order ID to cancel
        reason: Reason for cancellation

    Returns:
        Confirmation of cancellation
    """
    # Implementation
    return {"cancelled": True, "refund_amount": 99.99}

# Register the tool schema
TOOL_SCHEMA = {
    "type": "function",
    "function": {
        "name": "cancel_order",
        "description": "Cancel a customer order and issue refund",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {
                    "type": "string",
                    "description": "The order ID to cancel"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for cancellation"
                }
            },
            "required": ["order_id", "reason"]
        }
    }
}
```

2. Register it in `src/callcenter/app.py`:

```python
from callcenter.skills import cancel_order

tools_registry = {
    "cancel_order": cancel_order.cancel_order,
    # ... other tools
}

tools_schema = [cancel_order.TOOL_SCHEMA, ...]
```

### Customizing the prompt

Edit `src/callcenter/prompts.py` to customize the agent's personality, tone, and behavior:

```python
SYSTEM_PROMPT = """You are a friendly and professional customer service agent for Acme Corp.

Your role:
- Greet customers warmly
- Answer questions about orders and products
- Resolve issues efficiently
- Escalate complex problems to human agents

Guidelines:
- Be concise and clear
- Show empathy for customer concerns
- Always confirm actions before executing them
- End calls professionally
"""
```

### Adding custom workflows

Create a new workflow in `src/callcenter/workflows/`:

```python
# src/callcenter/workflows/quality_check.py

from raw_agent import BaseWorkflow, step

class QualityCheckWorkflow(BaseWorkflow):
    """Analyze call quality and agent performance."""

    @step("analyze_sentiment")
    async def analyze_sentiment(self) -> dict:
        # Analyze customer sentiment from transcript
        pass

    @step("score_interaction")
    async def score_interaction(self, sentiment: dict) -> float:
        # Score the interaction quality
        pass
```

## Monitoring and observability

### Logs

Structured JSON logs are written to stdout:

```json
{
  "timestamp": "2024-12-19T10:30:00Z",
  "level": "info",
  "message": "Call started",
  "call_sid": "CA123...",
  "customer_id": "cust_456"
}
```

### Telemetry

When telemetry is enabled, the solution exports traces to OpenTelemetry-compatible backends:

- Spans for each conversation turn
- Metrics for call duration, skill usage
- Attributes for customer ID, phone number, outcome

### Health monitoring

The health endpoint reports status of all dependencies:

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "healthy",
  "checks": {
    "liveness": {"status": "healthy"},
    "llm": {"status": "healthy"},
    "deepgram": {"status": "healthy"},
    "elevenlabs": {"status": "healthy"},
    "twilio": {"status": "healthy"},
    "database": {"status": "healthy"}
  }
}
```

## Deployment

### Docker

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependencies
COPY pyproject.toml .
RUN uv sync --frozen

# Copy application
COPY src/ src/
COPY config.yaml .

# Run
CMD ["uv", "run", "python", "-m", "callcenter.main"]
```

### Kubernetes

See `k8s/` directory for Kubernetes manifests including:
- Deployment
- Service
- Ingress
- ConfigMap
- Secrets

### Environment variables

All configuration can be overridden via environment variables:

```bash
# LLM
export LLM_MODEL="gpt-4o"
export LLM_TEMPERATURE="0.7"

# Voice
export VOICE_STT_PROVIDER="deepgram"
export VOICE_TTS_PROVIDER="elevenlabs"

# Server
export SERVER_HOST="0.0.0.0"
export SERVER_PORT="8000"
```

## Testing

Run the test suite:

```bash
# All tests
uv run pytest

# With coverage
uv run pytest --cov=callcenter --cov-report=html

# Integration tests only
uv run pytest -m integration
```

## Performance considerations

- The server uses async/await throughout for high concurrency
- Connection pooling for database and Redis
- Streaming responses for low latency
- Tool execution is concurrent when possible
- Voice pipeline uses efficient audio processing with Pipecat

### Scaling

- Horizontal: Run multiple server instances behind a load balancer
- Vertical: Increase CPU/memory for each instance
- Database: Use read replicas for customer/order lookups
- Caching: Redis for frequently accessed data

## Security

- API keys stored in environment variables, never committed
- HTTPS required for production (configure reverse proxy)
- Rate limiting on endpoints (configure in middleware)
- Input validation on all user inputs
- Audit logging for all customer data access

## Troubleshooting

### Common issues

**Voice not working:**
- Check Deepgram and ElevenLabs API keys
- Verify audio codecs match Twilio's requirements
- Check network connectivity and firewall rules

**Calls not connecting:**
- Verify Twilio webhook URLs are publicly accessible
- Check Twilio console for error logs
- Ensure phone number is configured correctly

**Skills not executing:**
- Check tool schema matches function signature
- Verify LLM has access to tool definitions
- Check logs for tool execution errors

### Debug mode

Enable detailed logging:

```bash
export LOG_LEVEL="debug"
uv run python -m callcenter.main
```

## License

This example is provided as-is for educational and reference purposes. Modify and extend as needed for your use case.

## Support

For questions about the RAW Platform, see:
- Main documentation: `/docs/`
- GitHub issues: `https://github.com/raw-labs/raw`
- Discord: `https://discord.gg/raw`

## What's next

- Add more skills (refunds, returns, product recommendations)
- Implement sentiment analysis
- Add multilingual support
- Integrate with your CRM system
- Build analytics dashboard
- Add A/B testing for prompts
- Implement callback queue management
