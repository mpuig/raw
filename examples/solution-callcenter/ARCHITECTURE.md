# Architecture documentation

This document explains the architectural decisions and design patterns used in the call center solution.

## Design principles

This solution follows the clean architecture principles outlined in the RAW Platform:

1. **Separation of concerns** - Each layer has a single, well-defined responsibility
2. **Dependency injection** - Components receive dependencies from external configuration
3. **Programming to interfaces** - Components depend on protocols, not concrete implementations
4. **Single responsibility** - Each module/class has one reason to change
5. **Type safety** - Strong typing with Pydantic for validation
6. **Modularity** - Clear organization by feature and layer
7. **Error handling** - Graceful degradation with clear error messages
8. **Progressive disclosure** - Simple interface, complex capabilities

## Layer architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                   │
│                  (FastAPI Routes)                       │
│  - Voice endpoints (Twilio webhooks)                    │
│  - Webhook endpoints (HTTP/WebSocket)                   │
│  - Admin endpoints (stats, management)                  │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                     │
│              (Business Logic)                           │
│  - ConversationEngine (bot runtime)                     │
│  - PostCallWorkflow (agent runtime)                     │
│  - Skill execution orchestration                        │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                    Domain Layer                         │
│                  (Core Business Rules)                  │
│  - Skills (lookup_customer, check_order_status, etc.)  │
│  - Configuration models (Pydantic)                      │
│  - Prompts and business rules                           │
└────────────────────┬────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│                  Infrastructure Layer                   │
│              (External Services)                        │
│  - LLM integration (OpenAI, Anthropic)                  │
│  - Voice services (Deepgram, ElevenLabs)                │
│  - Telephony (Twilio)                                   │
│  - Database (PostgreSQL, Redis)                         │
│  - Telemetry (OpenTelemetry)                            │
└─────────────────────────────────────────────────────────┘
```

## Key components

### Configuration system

**Location:** `src/callcenter/config.py`

**Purpose:** Centralized configuration with validation and type safety.

**Design:**
- Nested Pydantic models for each subsystem
- Loads from YAML file + environment variable overrides
- Validates required API keys on startup
- Provides type-safe access to all settings

**Why:** Separates configuration from code, enables different configs per environment (dev/staging/prod), and catches configuration errors early.

### Conversation engine

**Location:** RAW Platform `raw-bot` package

**Purpose:** Transport-agnostic conversation orchestration.

**Design:**
- Manages LLM interactions and conversation state
- Executes tools (skills) when LLM requests them
- Streams responses for low latency
- Supports middleware for cross-cutting concerns
- Independent of voice/text transport

**Why:** Decoupling the "brain" from transport allows reuse across voice calls, web chat, SMS, etc. Testing becomes easier as you can test conversation logic without audio processing.

### Skills system

**Location:** `src/callcenter/skills/`

**Purpose:** Reusable tools that the AI agent can use during conversations.

**Design:**
- Each skill is a Python function with JSON schema
- Synchronous or async execution
- Mock data for development, real implementations for production
- Consistent error handling (returns dict with success/error)
- Tool executor protocol for abstraction

**Why:** Skills are the atomic units of capability. By defining them as pure functions with schemas, they can be:
- Tested independently
- Reused across different agents
- Documented automatically
- Swapped between mock and real implementations

### Workflows system

**Location:** `src/callcenter/workflows/`

**Purpose:** Autonomous agents that run after conversations to handle post-call tasks.

**Design:**
- Async workflow execution
- Step-based processing (summary, CRM update, email, ticket)
- Configurable via config.yaml
- Error handling per step (failures don't stop workflow)
- Logs all actions for observability

**Why:** Post-call automation ensures consistency and saves agent time. By making it configurable, different organizations can customize behavior without code changes.

### Transport layer

**Location:** RAW Platform transport packages

**Purpose:** Handle the specifics of voice/text communication.

**Design:**
- Voice transport: Pipecat pipeline for audio processing
- Webhook transport: FastAPI routes for HTTP/WebSocket
- Twilio adapter: Converts Twilio webhooks to internal events
- Streaming responses for low latency

**Why:** Transport layer is pure infrastructure. By abstracting it, we can:
- Support multiple communication channels
- Swap providers (Twilio → Vonage)
- Test conversation logic without real audio
- Optimize each transport independently

## Data flow

### Inbound call flow

```
1. Customer calls Twilio number
   ↓
2. Twilio sends webhook to /voice/twilio
   ↓
3. Server returns TwiML to connect to WebSocket
   ↓
4. Voice transport creates Pipecat pipeline
   ↓
5. Audio streams through: Deepgram STT → Text
   ↓
6. ConversationEngine processes text
   ↓
7. LLM generates response (may call skills)
   ↓
8. Text → ElevenLabs TTS → Audio
   ↓
9. Audio streams back to customer
   ↓
10. Call ends → Status webhook → PostCallWorkflow
```

### Tool execution flow

```
1. User says: "What's the status of order 12345?"
   ↓
2. ConversationEngine sends to LLM with tools schema
   ↓
3. LLM decides to call check_order_status tool
   ↓
4. ToolExecutor runs skill function
   ↓
5. Skill returns order data (or error)
   ↓
6. Result sent back to LLM
   ↓
7. LLM generates natural language response
   ↓
8. Response spoken to customer
```

## Scalability considerations

### Horizontal scaling

The server is stateless (state in Redis/DB), so you can run multiple instances:

```
Load Balancer
    ├─ Server Instance 1
    ├─ Server Instance 2
    └─ Server Instance 3
         ↓
    Redis (shared state)
         ↓
    PostgreSQL (data)
```

### Performance optimization

1. **Connection pooling** - Reuse database connections
2. **Caching** - Redis for customer/order lookups
3. **Concurrent tool execution** - Run tools in parallel when possible
4. **Streaming responses** - Start speaking while LLM is generating
5. **Async I/O** - Non-blocking operations throughout

### Bottlenecks and solutions

| Bottleneck | Solution |
|-----------|----------|
| LLM latency | Use faster models (GPT-4o-mini, Claude Haiku), streaming |
| Voice latency | Optimize audio encoding, use edge servers |
| Database queries | Read replicas, caching, query optimization |
| Concurrent calls | Horizontal scaling, load balancing |
| Tool execution | Async operations, timeouts, circuit breakers |

## Security architecture

### Authentication and authorization

- API keys in environment variables (never committed)
- Twilio webhook validation (verify signatures)
- Rate limiting on endpoints
- CORS configuration for web clients

### Data protection

- TLS/HTTPS for all communications
- PII encryption at rest
- Audit logging for customer data access
- Retention policies for conversation data

### Secrets management

In production, use:
- AWS Secrets Manager
- HashiCorp Vault
- Azure Key Vault
- Google Secret Manager

## Observability

### Logging

Structured JSON logs with:
- Timestamp, level, message
- Context (customer_id, call_sid, etc.)
- Error details with stack traces

### Metrics

Key metrics to track:
- Call volume and duration
- Resolution rate (% calls resolved without escalation)
- Customer satisfaction (sentiment scores)
- Tool usage frequency
- Error rates

### Tracing

OpenTelemetry spans for:
- Each conversation turn
- Tool execution
- Workflow steps
- External API calls

## Testing strategy

### Unit tests

Test individual components in isolation:
- Skills with mock data
- Configuration loading
- Tool executor logic
- Workflow steps

### Integration tests

Test component interactions:
- ConversationEngine with skills
- Voice pipeline with mock audio
- Workflows with mock services

### End-to-end tests

Test complete user journeys:
- Customer calls, asks question, gets answer
- Complex scenarios with multiple tool calls
- Error handling and escalation flows

## Extension points

### Adding new skills

1. Create skill function in `src/callcenter/skills/your_skill.py`
2. Define JSON schema for the tool
3. Register in `skills/__init__.py`
4. Add configuration to `config.yaml`

### Adding new workflows

1. Create workflow class in `src/callcenter/workflows/your_workflow.py`
2. Implement async steps
3. Register in workflows config
4. Trigger from appropriate event

### Custom middleware

Add middleware to ConversationEngine for:
- Sentiment analysis
- Language detection
- Safety filtering
- Custom logging

### Alternative transports

Add support for new channels:
- SMS via Twilio
- WhatsApp Business API
- Slack integration
- Microsoft Teams

## Production checklist

Before deploying to production:

- [ ] All API keys configured via secrets manager
- [ ] Database connection pooling configured
- [ ] Redis for state management (not in-memory)
- [ ] HTTPS/TLS enabled on all endpoints
- [ ] Rate limiting configured
- [ ] Monitoring and alerting set up
- [ ] Error tracking (Sentry, Rollbar)
- [ ] Log aggregation (DataDog, CloudWatch)
- [ ] Backup and disaster recovery plan
- [ ] Load testing completed
- [ ] Security audit performed

## Future enhancements

Potential improvements for v2:

1. **Multi-language support** - Detect language and switch models
2. **Sentiment analysis** - Real-time emotion detection
3. **Agent handoff** - Seamless transfer to human agents
4. **Call recording** - For compliance and training
5. **Analytics dashboard** - Real-time metrics visualization
6. **A/B testing** - Test different prompts and strategies
7. **Knowledge base integration** - RAG for complex queries
8. **Queue management** - Handle high call volumes
9. **IVR integration** - Route calls based on input
10. **CRM deep integration** - Bidirectional sync with Salesforce/HubSpot

## References

- RAW Platform docs: `/docs/`
- Pipecat docs: https://pipecat.ai
- LiteLLM docs: https://docs.litellm.ai
- FastAPI docs: https://fastapi.tiangolo.com
- Twilio docs: https://www.twilio.com/docs
