# RAW Platform Architecture Proposal

## Vision

A **self-extending**, composable platform with three core modes:

| Mode | Package | Purpose |
|------|---------|---------|
| **Create** | `raw-creator` | Build new bots, agents, tools, skills |
| **Converse** | `raw-bot` | Handle voice/chat conversations |
| **Execute** | `raw-agent` | Run autonomous workflows |

Build anything from:
- Voice bots for call centers (Twilio, Vonage)
- Chat bots (WhatsApp, Slack, Web)
- Multi-channel support solutions
- Enterprise workflow orchestration
- **New bots, agents, and tools created by the platform itself**

## Design Principles

1. **Protocols over implementations** - Core defines contracts; packages implement them
2. **Composition over inheritance** - Solutions compose packages, not extend them
3. **No cross-layer imports** - Packages only import from their dependencies
4. **Optional everything** - Install only what you need
5. **Self-extending** - The platform can create more of itself

---

## Package Layers

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              META LAYER                                      │
│  Self-extension: create new bots, agents, tools, skills                     │
│  Packages: raw-creator, raw-codegen                                         │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SOLUTIONS                                       │
│  Pre-assembled combinations for common use cases                            │
│  Examples: solution-callcenter, solution-whatsapp-support                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              APPLICATIONS                                    │
│  CLI tools and servers                                                      │
│  Packages: raw-cli, raw-server                                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DEPLOYMENT                                      │
│  Production infrastructure: state, queues, telemetry                        │
│  Packages: raw-state, raw-queue, raw-telemetry                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SKILLS & TOOLS                                  │
│  Skills: Reusable bot capabilities (auth, faq, scheduling, escalation)     │
│  Tools: Reusable agent capabilities (http, email, database, search)        │
│  Packages: raw-skills, raw-tools                                            │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              TRANSPORTS                                      │
│  How to connect (I/O adapters)                                              │
│  Packages: transport-voice, transport-chat, transport-api, transport-webhook│
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INTEGRATIONS                                    │
│  Third-party service adapters                                               │
│  Packages: integration-twilio, integration-whatsapp, integration-deepgram,  │
│            integration-elevenlabs, integration-calcom, integration-hubspot, │
│            integration-slack, integration-sendgrid, integration-openai      │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              ENGINES                                         │
│  Core runtime logic                                                         │
│  Packages: raw-bot (conversations), raw-agent (workflows)                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FOUNDATION                                      │
│  Shared protocols, events, errors, DI container                             │
│  Package: raw-core                                                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## The Three Modes

### Create Mode (raw-creator)

The platform can build more of itself:

```
User: "I need a bot for dental appointments"
                    │
                    ▼
    ┌───────────────────────────────┐
    │       Creator Agent           │
    │  (raw-agent + creator skills) │
    └───────────────────────────────┘
           │         │         │
           ▼         ▼         ▼
      ┌────────┐ ┌────────┐ ┌────────┐
      │ Design │ │Generate│ │Validate│
      └────────┘ └────────┘ └────────┘
                    │
                    ▼
    ┌───────────────────────────────┐
    │   New Dental Appointment Bot  │
    │   - skill: booking            │
    │   - skill: procedures         │
    │   - skill: insurance          │
    └───────────────────────────────┘
                    │
                    ▼
           Ready to handle calls
```

**Creator skills:**
- `design` - Analyze requirements, suggest structure
- `generate` - Create bots, agents, tools, skills
- `validate` - Code quality, security audit
- `refine` - Improve based on simulation feedback

### Converse Mode (raw-bot)

Handle conversations across channels:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Twilio    │     │  WhatsApp   │     │    Slack    │
│   (voice)   │     │   (chat)    │     │   (chat)    │
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │   raw-bot   │
                    │   engine    │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
        ┌─────┴─────┐ ┌────┴────┐ ┌─────┴─────┐
        │   Auth    │ │   FAQ   │ │ Escalate  │
        │   skill   │ │  skill  │ │   skill   │
        └───────────┘ └─────────┘ └───────────┘
```

### Execute Mode (raw-agent)

Run autonomous workflows:

```
┌─────────────────────────────────────────────┐
│              InboundCallWorkflow            │
├─────────────────────────────────────────────┤
│ @step("lookup")                             │
│ def lookup_customer():                      │
│     return hubspot.find_contact(phone)      │
│                                             │
│ @step("conversation")                       │
│ def handle_call():                          │
│     return raw_bot.run(bot="support")       │
│                                             │
│ @step("post_call")                          │
│ def log_and_notify():                       │
│     hubspot.log_call(transcript)            │
│     slack.notify("#calls")                  │
└─────────────────────────────────────────────┘
```

---

## Mode Interoperability

All three modes can work together:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  Creator ──creates──► Bot ──triggers──► Agent ──uses──► Bot    │
│     │                                      │                    │
│     │                                      │                    │
│     └──────────creates────────────────────►│                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Examples:
- Creator builds a new support bot
- Support bot handles call, triggers post-call agent
- Agent runs workflow, uses bot to call customer back
- Agent uses creator to add new skill based on common questions
```

---

## Package Details

### Foundation Layer

#### `raw-core`
The universal foundation. All other packages depend on this.
**Dependencies:** `pydantic>=2.0` only

```
raw-core/
├── src/raw_core/
│   ├── __init__.py
│   ├── protocols/
│   │   ├── __init__.py
│   │   ├── llm.py              # LLMDriver protocol
│   │   ├── stt.py              # STTService protocol
│   │   ├── tts.py              # TTSService protocol
│   │   ├── storage.py          # StorageBackend protocol
│   │   ├── secrets.py          # SecretProvider protocol
│   │   ├── bus.py              # EventBus protocol
│   │   ├── executor.py         # ToolExecutor protocol
│   │   ├── logger.py           # ActivityLogger protocol
│   │   └── transport.py        # Transport protocol
│   ├── events/
│   │   ├── __init__.py
│   │   ├── base.py             # Event base class
│   │   ├── conversation.py     # TextChunk, ToolCall, TurnComplete
│   │   └── workflow.py         # StepStarted, StepCompleted
│   ├── errors/
│   │   ├── __init__.py
│   │   ├── base.py             # PlatformError base
│   │   ├── service.py          # LLMError, STTError, TTSError
│   │   ├── execution.py        # ToolError, TimeoutError
│   │   └── policy.py           # ErrorPolicy protocol
│   ├── models/
│   │   ├── __init__.py
│   │   ├── config.py           # Base config models
│   │   └── state.py            # Serializable state models
│   └── container.py            # Dependency injection container
└── pyproject.toml
```

**Dependencies:** `pydantic>=2.0` only

---

### Engine Layer

#### `raw-bot`
Transport-agnostic conversation engine. Handles dialogue, skills, and LLM interactions.

```
raw-bot/
├── src/raw_bot/
│   ├── __init__.py
│   ├── engine.py               # ConversationEngine
│   ├── context.py              # ContextManager (messages, tokens)
│   ├── skills/
│   │   ├── __init__.py
│   │   ├── loader.py           # Load skills from directory
│   │   ├── registry.py         # SkillRegistry
│   │   ├── executor.py         # ToolExecutor implementation
│   │   └── parser.py           # Parse SKILL.md
│   └── middleware.py           # Middleware protocol + implementations
└── pyproject.toml
```

**Dependencies:** `raw-core`

#### `raw-agent`
Workflow execution engine. Runs autonomous multi-step tasks.

```
raw-agent/
├── src/raw_agent/
│   ├── __init__.py
│   ├── base.py                 # BaseWorkflow
│   ├── decorators.py           # @step, @retry, @cache
│   ├── context.py              # WorkflowContext
│   ├── execution.py            # WorkflowRunner
│   ├── triggers.py             # Event triggers (@on_event)
│   └── manifest.py             # Workflow manifest handling
└── pyproject.toml
```

**Dependencies:** `raw-core`

### Meta Layer

#### `raw-codegen`
Code generation, validation, and sandboxing utilities.

```
raw-codegen/
├── src/raw_codegen/
│   ├── __init__.py
│   ├── templates/              # Code templates (bot, agent, tool, skill)
│   ├── validator.py            # AST-based code validation
│   ├── sandbox.py              # Safe execution environment
│   └── writer.py               # Write generated code to disk
└── pyproject.toml
```

**Dependencies:** `raw-core`

#### `raw-creator`
Pre-configured creator agent with skills for building bots, agents, tools.

```
raw-creator/
├── src/raw_creator/
│   ├── __init__.py
│   ├── agent.py                # Creator agent configuration
│   └── skills/
│       ├── design/             # Analyze, suggest, plan
│       │   ├── SKILL.md
│       │   └── tools.py
│       ├── generate/           # Create bots, agents, tools, skills
│       │   ├── SKILL.md
│       │   └── tools.py
│       ├── validate/           # Code quality, security audit
│       │   ├── SKILL.md
│       │   └── tools.py
│       └── refine/             # Improve based on feedback
│           ├── SKILL.md
│           └── tools.py
└── pyproject.toml
```

**Dependencies:** `raw-core`, `raw-bot`, `raw-codegen`

---

### Integration Layer

#### `integration-llm`
LLM provider implementations.

```
integration-llm/
├── src/integration_llm/
│   ├── __init__.py
│   ├── litellm.py              # LiteLLMDriver (OpenAI, Anthropic, etc.)
│   └── mock.py                 # MockLLMDriver for testing
└── pyproject.toml
```

**Dependencies:** `raw-core`, `litellm`

#### `integration-twilio`
Twilio voice and SMS.

```
integration-twilio/
├── src/integration_twilio/
│   ├── __init__.py
│   ├── voice.py                # Voice call handling
│   ├── sms.py                  # SMS sending/receiving
│   ├── webhook.py              # Webhook parsing
│   └── twiml.py                # TwiML generation
└── pyproject.toml
```

**Dependencies:** `raw-core`, `twilio`

#### `integration-deepgram`
Deepgram STT.

```
integration-deepgram/
├── src/integration_deepgram/
│   ├── __init__.py
│   └── stt.py                  # DeepgramSTT implements STTService
└── pyproject.toml
```

**Dependencies:** `raw-core`, `deepgram-sdk`

#### `integration-elevenlabs`
ElevenLabs TTS.

```
integration-elevenlabs/
├── src/integration_elevenlabs/
│   ├── __init__.py
│   └── tts.py                  # ElevenLabsTTS implements TTSService
└── pyproject.toml
```

**Dependencies:** `raw-core`, `elevenlabs`

---

### Transport Layer

#### `transport-voice`
Voice I/O via Pipecat.

```
transport-voice/
├── src/transport_voice/
│   ├── __init__.py
│   ├── pipeline.py             # VoicePipeline
│   ├── pipecat_adapter.py      # EngineProcessor for Pipecat
│   ├── vad.py                  # Voice activity detection config
│   └── local.py                # Local audio transport
└── pyproject.toml
```

**Dependencies:** `raw-core`, `converse-engine`, `pipecat-ai`

#### `transport-chat`
WebSocket/HTTP chat.

```
transport-chat/
├── src/transport_chat/
│   ├── __init__.py
│   ├── websocket.py            # WebSocket handler
│   ├── http.py                 # HTTP long-polling
│   └── session.py              # Session management
└── pyproject.toml
```

**Dependencies:** `raw-core`, `converse-engine`, `websockets`

#### `transport-webhook`
Inbound webhook handling.

```
transport-webhook/
├── src/transport_webhook/
│   ├── __init__.py
│   ├── server.py               # Webhook server
│   ├── router.py               # Route webhooks to handlers
│   └── verify.py               # Signature verification
└── pyproject.toml
```

**Dependencies:** `raw-core`, `fastapi`

---

### Application Layer

#### `raw-cli`
The `raw` command.

```
raw-cli/
├── src/raw_cli/
│   ├── __init__.py
│   ├── main.py                 # Entry point
│   └── commands/
│       ├── run.py
│       ├── create.py
│       ├── list.py
│       └── ...
└── pyproject.toml
```

**Dependencies:** `raw-core`, `raw-bot`, `raw-agent`, `click`, `rich`

---

## Dependency Graph

```
                                    pydantic
                                       │
                                       ▼
                                  ┌─────────┐
                                  │raw-core │
                                  └────┬────┘
                                       │
     ┌─────────────────┬───────────────┼───────────────┬─────────────────┐
     │                 │               │               │                 │
     ▼                 ▼               ▼               ▼                 ▼
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────────┐
│ raw-bot │     │raw-agent│     │raw-state│     │raw-queue│     │raw-telemetry│
└────┬────┘     └────┬────┘     └────┬────┘     └────┬────┘     └──────┬──────┘
     │               │               │               │                 │
     │               │               └───────────────┴─────────────────┘
     │               │                               │
     ▼               ▼                               ▼
┌─────────────┐ ┌─────────────┐               ┌───────────┐
│transport-*  │ │integration-*│               │raw-server │
└──────┬──────┘ └──────┬──────┘               └─────┬─────┘
       │               │                           │
       └───────────────┴───────────────────────────┘
                               │
                               ▼
                         ┌─────────┐
                         │ raw-cli │
                         └─────────┘
```

---

## Use Case Compositions

### 1. Standalone Voice Bot (No RAW)

```toml
dependencies = [
    "raw-core",
    "converse-engine",
    "transport-voice",
    "integration-llm",
    "integration-deepgram",
    "integration-elevenlabs",
]
```

```python
from raw_core import Container
from converse_engine import ConversationEngine, load_bot
from transport_voice import VoicePipeline
from integration_llm import LiteLLMDriver
from integration_deepgram import DeepgramSTT
from integration_elevenlabs import ElevenLabsTTS

container = Container()
container.register(LLMDriver, LiteLLMDriver)
container.register(STTService, DeepgramSTT)
container.register(TTSService, ElevenLabsTTS)

bot = load_bot("support")
engine = ConversationEngine(bot, driver=container.get(LLMDriver))
pipeline = VoicePipeline(engine, container)

await pipeline.run_local()  # Local mic/speaker
```

### 2. Twilio Voice Bot (No RAW)

```toml
dependencies = [
    "raw-core",
    "converse-engine",
    "transport-voice",
    "transport-webhook",
    "integration-llm",
    "integration-twilio",
    "integration-deepgram",
    "integration-elevenlabs",
]
```

```python
from transport_webhook import WebhookServer
from integration_twilio import TwilioVoiceHandler

server = WebhookServer()
server.register("/twilio/voice", TwilioVoiceHandler(
    on_call=lambda call: VoicePipeline(
        engine=ConversationEngine(load_bot("support")),
        transport=call.media_stream,
    )
))

await server.run(port=8000)
```

### 3. WhatsApp Chatbot (No RAW)

```toml
dependencies = [
    "raw-core",
    "converse-engine",
    "transport-chat",
    "transport-webhook",
    "integration-llm",
    "integration-whatsapp",
]
```

```python
from transport_chat import ChatHandler
from integration_whatsapp import WhatsAppWebhook

server = WebhookServer()
server.register("/whatsapp", WhatsAppWebhook(
    on_message=lambda msg: ChatHandler(
        engine=ConversationEngine(load_bot("support")),
        session_id=msg.from_number,
    ).handle(msg.text)
))
```

### 4. Voice Bot with RAW Orchestration

```toml
dependencies = [
    "raw-core",
    "raw-engine",
    "converse-engine",
    "transport-voice",
    "integration-twilio",
    "integration-hubspot",
]
```

```python
from raw_engine import BaseWorkflow, step, on_event

@on_event("twilio.call.incoming")
class InboundCallWorkflow(BaseWorkflow):

    @step("lookup")
    async def lookup_customer(self):
        return await self.tool("hubspot").find_contact(
            phone=self.trigger.from_number
        )

    @step("conversation")
    async def handle_call(self, customer):
        async for event in self.tool("converse").run(
            bot="support",
            call_sid=self.trigger.call_sid,
            context={"customer": customer},
        ):
            if event.type == "completed":
                return event.data["transcript"]

    @step("post_call")
    async def log_call(self, transcript):
        await self.tool("hubspot").log_activity(transcript)
        await self.tool("slack").notify("#calls", f"Call completed")
```

### 5. Enterprise Multi-Channel Platform

```toml
dependencies = [
    "raw-core",
    "raw-engine",
    "raw-cli",
    "converse-engine",
    "transport-voice",
    "transport-chat",
    "transport-webhook",
    "integration-*",  # All integrations
]
```

Full platform with:
- Voice via Twilio
- Chat via WhatsApp + Slack
- CRM integration (HubSpot/Salesforce)
- Scheduling via Cal.com
- Email via SendGrid
- Workflows for complex processes

---

## Protocol Definitions (raw-core)

### LLMDriver

```python
class LLMChunk(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = []
    finish_reason: str | None = None

class LLMDriver(Protocol):
    async def stream_chat(
        self,
        messages: list[Message],
        model: str,
        tools: list[ToolDef] | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[LLMChunk]: ...
```

### STTService

```python
class Transcript(BaseModel):
    text: str
    confidence: float
    is_final: bool

class STTService(Protocol):
    async def transcribe_stream(
        self,
        audio_stream: AsyncIterator[bytes],
    ) -> AsyncIterator[Transcript]: ...
```

### TTSService

```python
class TTSService(Protocol):
    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
    ) -> AsyncIterator[bytes]: ...
```

### Transport

```python
class Transport(Protocol):
    async def receive(self) -> str | bytes:
        """Receive input from user."""
        ...

    async def send(self, data: str | bytes) -> None:
        """Send output to user."""
        ...

    async def close(self) -> None:
        """Close the transport."""
        ...
```

---

## Migration from Current Codebases

### From voicebot-with-skills

| Current | New Package |
|---------|-------------|
| `src/converse/domain/protocols.py` | `raw-core/protocols/` |
| `src/converse/domain/events.py` | `raw-core/events/` |
| `src/converse/domain/errors.py` | `raw-core/errors/` |
| `src/converse/application/engine.py` | `raw-bot/engine.py` |
| `src/converse/application/context.py` | `raw-bot/context.py` |
| `src/converse/application/skills/` | `raw-bot/skills/` |
| `src/converse/infrastructure/llm_driver.py` | `integration-llm/litellm.py` |
| `src/converse/infrastructure/voice_services.py` | `integration-deepgram/`, `integration-elevenlabs/` |
| `src/converse/infrastructure/pipecat_adapter.py` | `transport-voice/pipecat_adapter.py` |
| `src/converse/application/voice_pipeline.py` | `transport-voice/pipeline.py` |
| `src/converse/interfaces/cli/` | `raw-cli/` (merged) |
| `src/converse/codegen/` | `raw-codegen/` |
| `bots/creator/` | `raw-creator/` |

### From raw

| Current | New Package |
|---------|-------------|
| `src/raw_runtime/protocols/` | `raw-core/protocols/` (merge) |
| `src/raw_runtime/base.py` | `raw-agent/base.py` |
| `src/raw_runtime/decorators.py` | `raw-agent/decorators.py` |
| `src/raw_runtime/context.py` | `raw-agent/context.py` |
| `src/raw_runtime/triggers.py` | `raw-agent/triggers.py` |
| `src/raw_runtime/drivers/` | `raw-agent/drivers/` |
| `src/raw_runtime/tools/builtin/` | Individual integration packages |
| `src/raw/cli.py` | `raw-cli/` |
| `src/raw/engine/` | `raw-agent/execution.py` |

---

## Resolved Questions

1. **Naming**: `raw-bot` for conversations, `raw-agent` for workflows
2. **Skills location**: Part of `raw-bot` engine (skills are bot-specific)
3. **Meta layer**: `raw-creator` + `raw-codegen` for self-extension
4. **Server**: Single `raw-server` handling all transports
5. **CLI**: Single `raw-cli` with subcommands (`raw bot`, `raw agent`, `raw create`)

6. **Bot definitions**: Live in user's project (like now)
7. **Versioning**: Lock-step with `raw-core` (semver)
8. **Monorepo name**: `raw-platform`

---

## Deployment Layer (Enterprise Scale)

For enterprise deployments, additional packages handle state, queueing, observability, and serving:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DEPLOYMENT LAYER                               │
│  Production infrastructure: state, queues, telemetry, serving              │
│  Packages: raw-state, raw-queue, raw-telemetry, raw-server                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### `raw-state`
Externalized state management for horizontal scaling.

```
raw-state/
├── src/raw_state/
│   ├── __init__.py
│   ├── protocols.py           # StateBackend protocol
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── memory.py          # In-memory (dev/testing)
│   │   ├── redis.py           # Redis (session state, caching)
│   │   └── postgres.py        # PostgreSQL (persistent state)
│   ├── session.py             # Session state management
│   ├── conversation.py        # Conversation history storage
│   └── distributed.py         # Distributed locks, leader election
└── pyproject.toml
```

**Dependencies:** `raw-core`, `redis`, `asyncpg`

**Capabilities:**
- Session state across instances (user context, conversation history)
- Distributed locks for singleton operations
- Conversation persistence for compliance/analytics
- Cache layer for skills data, LLM responses

### `raw-queue`
Async job processing for decoupled, scalable workloads.

```
raw-queue/
├── src/raw_queue/
│   ├── __init__.py
│   ├── protocols.py           # QueueBackend protocol
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── memory.py          # In-memory (dev/testing)
│   │   ├── redis.py           # Redis Streams / Bull-style
│   │   ├── sqs.py             # AWS SQS
│   │   └── kafka.py           # Kafka for high throughput
│   ├── worker.py              # Worker process runner
│   ├── scheduler.py           # Cron-style scheduled jobs
│   └── retry.py               # Retry policies, dead-letter handling
└── pyproject.toml
```

**Dependencies:** `raw-core`, `redis` | `aiobotocore` | `aiokafka`

**Capabilities:**
- Decouple call handling from post-call workflows
- Scheduled tasks (reminders, follow-ups)
- Retry with exponential backoff
- Dead-letter queues for failed jobs
- Priority queues for urgent tasks

### `raw-telemetry`
Observability with OpenTelemetry.

```
raw-telemetry/
├── src/raw_telemetry/
│   ├── __init__.py
│   ├── tracing.py             # Distributed tracing
│   ├── metrics.py             # Metrics collection
│   ├── logging.py             # Structured logging
│   ├── exporters/
│   │   ├── __init__.py
│   │   ├── otlp.py            # OpenTelemetry Protocol
│   │   ├── datadog.py         # Datadog APM
│   │   └── cloudwatch.py      # AWS CloudWatch
│   └── middleware.py          # Auto-instrumentation middleware
└── pyproject.toml
```

**Dependencies:** `raw-core`, `opentelemetry-api`, `opentelemetry-sdk`

**Capabilities:**
- Distributed tracing across bot → agent → tool calls
- Metrics: latency, token usage, error rates, conversation outcomes
- Structured logging with correlation IDs
- Export to Datadog, New Relic, Grafana, CloudWatch

### `raw-server`
Production-ready FastAPI server.

```
raw-server/
├── src/raw_server/
│   ├── __init__.py
│   ├── app.py                 # FastAPI application factory
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── webhooks.py        # Twilio, WhatsApp webhook handlers
│   │   ├── chat.py            # WebSocket chat endpoints
│   │   ├── api.py             # REST API for management
│   │   └── health.py          # Health checks, readiness probes
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py            # API key / JWT authentication
│   │   ├── tenant.py          # Multi-tenant context injection
│   │   ├── rate_limit.py      # Rate limiting per tenant
│   │   └── telemetry.py       # Request tracing
│   ├── workers/
│   │   ├── __init__.py
│   │   ├── voice.py           # Voice call worker
│   │   └── queue.py           # Background queue worker
│   └── config.py              # Server configuration
└── pyproject.toml
```

**Dependencies:** `raw-core`, `raw-state`, `raw-queue`, `raw-telemetry`, `fastapi`, `uvicorn`

**Capabilities:**
- Multi-tenant isolation (tenant context per request)
- Horizontal scaling (stateless workers)
- Health checks for Kubernetes
- WebSocket support for real-time chat
- Background worker management

---

## Enterprise Deployment Architecture

```
                                    ┌─────────────────────┐
                                    │   Load Balancer     │
                                    │   (ALB / nginx)     │
                                    └──────────┬──────────┘
                                               │
                    ┌──────────────────────────┼──────────────────────────┐
                    │                          │                          │
           ┌────────▼────────┐       ┌────────▼────────┐       ┌────────▼────────┐
           │  raw-server     │       │  raw-server     │       │  raw-server     │
           │  (instance 1)   │       │  (instance 2)   │       │  (instance N)   │
           └────────┬────────┘       └────────┬────────┘       └────────┬────────┘
                    │                          │                          │
                    └──────────────────────────┼──────────────────────────┘
                                               │
              ┌────────────────────────────────┼────────────────────────────────┐
              │                                │                                │
     ┌────────▼────────┐              ┌────────▼────────┐              ┌────────▼────────┐
     │     Redis       │              │   PostgreSQL    │              │  Message Queue  │
     │ (session state) │              │ (persistent)    │              │ (SQS/Kafka)     │
     └─────────────────┘              └─────────────────┘              └────────┬────────┘
                                                                                │
                                                                       ┌────────▼────────┐
                                                                       │  Queue Workers  │
                                                                       │  (raw-agent)    │
                                                                       └─────────────────┘
```

### Scaling Strategies

| Component | Strategy | Notes |
|-----------|----------|-------|
| **raw-server** | Horizontal (N instances) | Stateless, scale to traffic |
| **Queue Workers** | Horizontal (M workers) | Scale to queue depth |
| **Redis** | Cluster mode | Session state, distributed locks |
| **PostgreSQL** | Read replicas | Conversation history, analytics |
| **Voice streams** | Sticky sessions | WebSocket affinity per call |

### Multi-Tenancy

```python
# Per-request tenant context
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    tenant_id = extract_tenant(request)  # From header, API key, or domain

    async with tenant_context(tenant_id):
        # All operations scoped to tenant
        # - State keys prefixed: {tenant_id}:session:{session_id}
        # - Logs tagged: tenant_id={tenant_id}
        # - Metrics labeled: tenant={tenant_id}
        response = await call_next(request)

    return response
```

### Configuration Example

```yaml
# raw-server.yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4

state:
  backend: redis
  redis:
    url: redis://redis-cluster:6379
    prefix: raw

queue:
  backend: sqs
  sqs:
    region: us-west-2
    queue_url: https://sqs.us-west-2.amazonaws.com/123456/raw-jobs

telemetry:
  tracing:
    enabled: true
    exporter: otlp
    endpoint: http://otel-collector:4317
  metrics:
    enabled: true
    exporter: otlp

tenants:
  isolation: prefix  # prefix | database | none
  rate_limits:
    default:
      requests_per_minute: 1000
      concurrent_calls: 100
```

---

## Next Steps

1. **Finalize this architecture** (current)
2. **Create beads epic + tasks** for migration
3. **Extract `raw-core`** - protocols, events, errors, DI
4. **Extract `raw-bot`** - conversation engine from voicebot-with-skills
5. **Extract `raw-agent`** - workflow engine from raw_runtime
6. **Extract `raw-codegen`** - code generation utilities
7. **Extract `raw-creator`** - creator skills
8. **Extract integrations** - twilio, deepgram, elevenlabs, etc.
9. **Extract transports** - voice, chat, webhook
10. **Unify CLIs** - single `raw` command
11. **Create examples** - callcenter, whatsapp-bot
