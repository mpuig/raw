# transport-webhook

FastAPI webhook transport for RAW Platform - HTTP-based bot integration.

## Overview

Provides RESTful HTTP/WebSocket endpoints for integrating RAW bots with external systems. Decouples conversation logic from transport layer, enabling stateless webhook handling with session management.

## Installation

```bash
uv add transport-webhook
```

## Usage

### Basic setup

```python
from transport_webhook import create_webhook_app
from raw_bot import BotConfig, ConversationEngine, ContextManager
from raw_core import ToolExecutor
from integration_llm import LiteLLMDriver

def engine_factory(context: dict) -> ConversationEngine:
    """Create conversation engine with bot configuration."""
    bot_name = context.get("bot_name", "default")

    # Load bot configuration
    config = BotConfig(
        name=bot_name,
        system_prompt="You are a helpful assistant.",
        model="gpt-4o-mini",
        temperature=0.7,
    )

    # Initialize components
    driver = LiteLLMDriver()
    executor = ToolExecutor()
    ctx_manager = ContextManager()

    return ConversationEngine(
        config=config,
        driver=driver,
        executor=executor,
        context=ctx_manager,
    )

# Create FastAPI app
app = create_webhook_app(engine_factory)

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

### Using the router in an existing app

```python
from fastapi import FastAPI
from transport_webhook import create_webhook_router

app = FastAPI()

# Create and mount webhook router
router = create_webhook_router(engine_factory)
app.include_router(router)

# Add your own endpoints
@app.get("/")
async def root():
    return {"message": "My custom API with webhook transport"}
```

### REST API endpoints

#### Create conversation

```bash
POST /webhooks/conversations
Content-Type: application/json

{
  "conversation_id": "optional-custom-id",
  "auto_greet": true,
  "context": {
    "bot_name": "customer-support",
    "user_id": "12345"
  }
}
```

Response:
```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "greeting": "Hello! How can I help you today?"
}
```

#### Send message

```bash
POST /webhooks/conversations/{conversation_id}/message
Content-Type: application/json

{
  "text": "I need help with my order"
}
```

Response:
```json
{
  "response": "I'd be happy to help with your order. Could you please provide your order number?",
  "status": "active",
  "outcome": null
}
```

#### List conversations

```bash
GET /webhooks/conversations
```

Response:
```json
{
  "conversations": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "active",
      "created_at": "2025-12-18T20:00:00Z",
      "updated_at": "2025-12-18T20:05:00Z",
      "message_count": 3,
      "outcome": null,
      "error": null
    }
  ],
  "count": 1
}
```

#### Get conversation details

```bash
GET /webhooks/conversations/{conversation_id}
```

#### End conversation

```bash
DELETE /webhooks/conversations/{conversation_id}?reason=user_ended
```

### WebSocket streaming

For real-time event streaming during message processing:

```javascript
const ws = new WebSocket('ws://localhost:8000/webhooks/conversations/{conversation_id}/stream');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  switch (data.type) {
    case 'text_chunk':
      console.log('Bot says:', data.text);
      break;
    case 'tool_call':
      console.log('Calling tool:', data.name, data.arguments);
      break;
    case 'tool_result':
      console.log('Tool result:', data.result);
      break;
    case 'turn_complete':
      console.log('Turn finished');
      break;
    case 'keepalive':
      // Heartbeat to keep connection alive
      break;
  }
};
```

## Architecture

### Component separation

The package follows clean architecture principles with three main layers:

1. **Router** (`router.py`): HTTP/WebSocket transport layer
   - Handles request/response parsing and validation
   - Maps HTTP endpoints to handler operations
   - Manages WebSocket connections

2. **Handlers** (`handlers.py`): Session management layer
   - Manages conversation lifecycle
   - Coordinates between engine and transport
   - Maintains conversation state and history

3. **Engine** (from `raw-bot`): Core conversation logic
   - LLM interaction and streaming
   - Tool execution and coordination
   - Context and message management

### Dependency injection

The `engine_factory` pattern enables flexible bot configuration:

```python
# Simple static configuration
def simple_factory(context: dict) -> ConversationEngine:
    return ConversationEngine(config, driver, executor, ctx_manager)

# Dynamic bot loading from filesystem
def file_based_factory(context: dict) -> ConversationEngine:
    bot_name = context.get("bot_name", "default")
    config = load_bot_config(f"bots/{bot_name}/config.yaml")
    return ConversationEngine(config, driver, executor, ctx_manager)

# Database-backed bot registry
def db_factory(context: dict) -> ConversationEngine:
    bot_id = context.get("bot_id")
    config = await db.get_bot_config(bot_id)
    return ConversationEngine(config, driver, executor, ctx_manager)
```

### State management

Conversations are ephemeral and stored in-memory. The `ConversationManager` provides:
- Unique conversation ID generation
- Concurrent access control with asyncio locks
- Automatic cleanup of completed conversations

For persistent storage, implement a custom manager that wraps database operations.

## Configuration

### Cleanup settings

```python
app = create_webhook_app(
    engine_factory,
    cleanup_interval=300,    # Check every 5 minutes
    cleanup_max_age=3600,    # Remove completed conversations after 1 hour
)
```

### Custom middleware

```python
from fastapi import Request

@app.middleware("http")
async def add_auth(request: Request, call_next):
    # Add authentication, logging, etc.
    response = await call_next(request)
    return response
```

## Integration examples

### Slack bot webhook

```python
from fastapi import FastAPI, Request
from transport_webhook import create_webhook_router

app = FastAPI()
webhook_router = create_webhook_router(engine_factory)
app.include_router(webhook_router)

@app.post("/slack/events")
async def slack_webhook(request: Request):
    data = await request.json()

    # Handle Slack event
    if data["type"] == "event_callback":
        event = data["event"]
        if event["type"] == "message":
            # Forward to conversation engine
            response = await client.post(
                f"/webhooks/conversations/{event['channel']}/message",
                json={"text": event["text"]}
            )
            # Send response back to Slack
            await send_to_slack(event["channel"], response.json()["response"])

    return {"ok": True}
```

### Twilio SMS webhook

```python
@app.post("/twilio/sms")
async def twilio_webhook(request: Request):
    form = await request.form()
    from_number = form.get("From")
    message = form.get("Body")

    # Create or get conversation for this phone number
    response = await client.post(
        f"/webhooks/conversations/{from_number}/message",
        json={"text": message}
    )

    # Return TwiML response
    return Response(
        content=f'<Response><Message>{response.json()["response"]}</Message></Response>',
        media_type="application/xml"
    )
```

## Dependencies

- `raw-core`: Core protocols, events, and errors
- `raw-bot`: Conversation engine and context management
- `fastapi`: Web framework for HTTP/WebSocket endpoints
- `uvicorn`: ASGI server for running FastAPI apps
- `pydantic`: Data validation and serialization

## Error handling

All endpoints return appropriate HTTP status codes:
- `200`: Success
- `404`: Conversation not found
- `400`: Invalid request (inactive conversation, validation error)
- `500`: Internal server error

WebSocket connections close with specific codes:
- `4004`: Conversation not found
- `1011`: Internal error during streaming
