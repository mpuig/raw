# RAW Architecture: Event-Driven Workflow Execution

This document explains RAW's event-driven architecture and the rationale behind key design decisions.

---

## Core Concept: Everything is an Event

In RAW's architecture, workflows don't just "run"—they **emit events** and **react to events**.

- `run.py` emits `StepStarted`, `StepCompleted`, `ArtifactCreated`
- Triggers emit `WorkflowTriggered` to start workflows
- Human approval emits `ApprovalRequested`, waits for `ApprovalReceived`

This turns a script into a conversation between components.

---

## Core Principle: Decoupled Observability

RAW separates **execution** from **observation**. Workflows emit events for every state change; handlers decide what to do with them. This enables:

- **Real-time console output** during interactive runs
- **Structured logging** for daemon mode
- **Human-in-the-loop** approval without blocking the event loop
- **External integrations** (webhooks, dashboards) without touching workflow code

```
Workflow Steps  →  Events  →  EventBus  →  Handlers
                                            ├── Console (pretty print)
                                            ├── File Logger (JSON)
                                            ├── Approval (human-in-loop)
                                            └── Custom (webhooks, etc.)
```

---

## Two Execution Modes

### `raw run` (Interactive)

Single-shot execution for development and ad-hoc runs.

- **LocalEventBus**: Synchronous, in-process
- **ConsoleEventHandler**: Pretty console output
- **ConsoleApprovalHandler**: Prompts via stdin
- Process spawns → runs workflow → prints events → exits

### `raw serve` (Daemon)

Long-running server for webhook-triggered workflows and human-in-the-loop approvals.

- **AsyncEventBus**: Uses `asyncio.Queue` for non-blocking event dispatch
- **RunRegistry**: Tracks connected workflow runs and pending events
- **Multiple concurrent workflows**: Events routed by run_id
- HTTP API for approvals, webhooks, and status queries

---

## Connected Mode (RAW_SERVER_URL)

When `RAW_SERVER_URL` environment variable is set, workflows operate in **connected mode**, enabling server-mediated approvals and webhooks.

### How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│                        raw serve (:8000)                        │
├─────────────────────────────────────────────────────────────────┤
│  RunRegistry:                                                   │
│    run-123: status=waiting, step=deploy                         │
│    run-456: status=running                                      │
│                                                                 │
│  EventQueue:                                                    │
│    run-123: [{type: approval, decision: approve}]               │
└─────────────────────────────────────────────────────────────────┘
         ▲                              │
         │ HTTP                         │ Poll events
         │                              ▼
┌────────┴────────────────────────────────────────────────────────┐
│  Workflow Process (run-123)                                     │
│                                                                 │
│  1. Startup → POST /runs/register                               │
│  2. Heartbeat thread (every 30s)                                │
│  3. wait_for_approval() →                                       │
│       POST /runs/run-123/waiting                                │
│       GET /runs/run-123/events (poll every 1s)                  │
│  4. Finish → POST /runs/run-123/complete                        │
└─────────────────────────────────────────────────────────────────┘
```

### Server Endpoints

| Endpoint | Purpose |
|----------|---------|
| `POST /runs/register` | Workflow registers on startup |
| `POST /runs/{id}/waiting` | Mark waiting for approval/webhook |
| `GET /runs/{id}/events` | Poll pending events (returns & clears) |
| `POST /runs/{id}/heartbeat` | Keep-alive signal |
| `POST /runs/{id}/complete` | Mark run finished |
| `POST /approve/{run_id}/{step}` | Deliver approval decision |
| `GET /approvals` | List all pending approvals |
| `GET /runs` | List all connected runs |

### Local vs Connected Mode

| Feature | Local Mode | Connected Mode |
|---------|------------|----------------|
| `RAW_SERVER_URL` | Not set | Set |
| Approvals | Console prompt | Server-mediated (HTTP) |
| Webhooks | Not available | Full support |
| Logging | Console/file | Console/file + server |
| Multi-user | No | Yes |

### Fallback Behavior

- **Server unreachable at startup**: Workflow runs in local mode with warning
- **Server dies mid-execution**: Approval polls timeout after 5 min (configurable)
- **Workflow crashes**: Server marks run as "stale" after 60s without heartbeat

---

## Event Types

All events include: `event_id`, `timestamp`, `workflow_id`, `run_id`

| Category | Events |
|----------|--------|
| Workflow | `WorkflowTriggered`, `WorkflowStarted`, `WorkflowCompleted`, `WorkflowFailed` |
| Step | `StepStarted`, `StepCompleted`, `StepFailed`, `StepSkipped`, `StepRetry` |
| Approval | `ApprovalRequested`, `ApprovalReceived`, `ApprovalTimeout` |
| Output | `ArtifactCreated`, `CacheHit`, `CacheMiss` |

Events are Pydantic models for type safety and serialization.

---

## EventBus Implementations

### LocalEventBus (Synchronous)

For `raw run`. Handlers are called synchronously in registration order.

```
emit(event) → handler1(event) → handler2(event) → return
```

### AsyncEventBus (Async-Native)

For `raw serve`. Uses `asyncio.Queue` for non-blocking dispatch.

```
emit_async(event) → queue.put(event)
                         ↓
start() loop → queue.get() → dispatch to handlers concurrently
```

Supports both sync and async handlers. Sync handlers run directly; async handlers run via `asyncio.gather()`.

---

## Human-in-the-Loop

### Console Mode (raw run)

`wait_for_approval()` calls `input()` directly—blocks the thread until user responds.

### Daemon Mode (raw serve)

`wait_for_approval_async()` uses **ApprovalRegistry** with `asyncio.Future`:

1. Workflow calls `wait_for_approval_async("Deploy?")`
2. Registry creates a Future, emits `ApprovalRequested` event
3. Workflow awaits the Future (non-blocking to event loop)
4. External API receives approval → calls `registry.resolve(workflow_id, step, "approve")`
5. Future resolves → workflow continues

This pattern allows workflows to pause indefinitely without consuming resources.

---

## Clean Architecture: Protocols and Drivers

RAW's runtime uses a **Clean Architecture** pattern that separates interfaces (protocols) from implementations (drivers). This enables:

- **Pluggable backends**: Swap FileSystem for S3, env vars for Vault
- **Testability**: Use MemoryStorage and AutoApprovalHandler in tests
- **Flexibility**: Different drivers for different environments

### Structure

```
src/raw_runtime/
├── protocols/          # Interface definitions (ports)
│   ├── storage.py      # StorageBackend protocol
│   ├── secrets.py      # SecretProvider protocol
│   ├── orchestrator.py # Orchestrator protocol
│   ├── telemetry.py    # TelemetrySink protocol
│   ├── approval.py     # ApprovalHandler protocol
│   ├── human.py        # HumanInterface protocol
│   └── bus.py          # EventBus protocol
│
├── drivers/            # Concrete implementations (adapters)
│   ├── storage.py      # FileSystemStorage, MemoryStorage
│   ├── secrets.py      # EnvVarSecretProvider, DotEnvSecretProvider
│   ├── orchestrator.py # LocalOrchestrator, HttpOrchestrator
│   ├── telemetry.py    # NullSink, ConsoleSink, JsonFileSink
│   ├── approval.py     # ConsoleApprovalHandler, AutoApprovalHandler
│   ├── human.py        # ConsoleInterface, ServerInterface
│   └── bus.py          # LocalEventBus, AsyncEventBus
│
├── __init__.py         # Facade re-exports (public API)
└── *.py                # Core modules (context, decorators, models)
```

### Protocol Pattern

Protocols define the contract; drivers implement it:

```python
# Protocol (in protocols/storage.py)
from typing import Protocol

class StorageBackend(Protocol):
    def save_artifact(self, run_id: str, name: str, content: bytes | str) -> str: ...
    def load_artifact(self, run_id: str, name: str) -> bytes: ...

# Driver (in drivers/storage.py)
class FileSystemStorage:
    def __init__(self, base_dir: Path = Path(".raw")):
        self._base_dir = base_dir

    def save_artifact(self, run_id: str, name: str, content: bytes | str) -> str:
        path = self._base_dir / "runs" / run_id / "results" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content if isinstance(content, bytes) else content.encode())
        return str(path)
```

### Global Getters/Setters

Each driver type has a global getter/setter for dependency injection:

```python
from raw_runtime import get_storage, set_storage, MemoryStorage

# In tests
set_storage(MemoryStorage())

# In workflow code
storage = get_storage()  # Returns current driver
storage.save_artifact("run-123", "output.json", data)
```

### Default Drivers

| Component | Default Driver | Alternative |
|-----------|---------------|-------------|
| Storage | FileSystemStorage | MemoryStorage |
| Secrets | EnvVarSecretProvider | DotEnvSecretProvider, ChainedSecretProvider |
| Orchestrator | LocalOrchestrator | HttpOrchestrator |
| Telemetry | NullSink | ConsoleSink, JsonFileSink, MemorySink |
| Approval | ConsoleApprovalHandler | AutoApprovalHandler |
| HumanInterface | ConsoleInterface | ServerInterface, AutoInterface |

---

## Why This Architecture?

### Problem: Coupling

Traditional approaches couple observation to execution:
- Print statements hardcoded in workflow code
- Log levels mixed with business logic
- Approval flows require different code paths per environment

### Solution: Events as First-Class Citizens

Every state change becomes an event. Workflows don't know (or care) who's listening.

**Benefits:**
- **Testability**: Subscribe a mock handler, assert events emitted
- **Flexibility**: Add file logging without changing workflow code
- **Composability**: Multiple handlers react to same events
- **Separation of concerns**: Console formatting isolated from step execution

### Trade-offs

- **Indirection**: Events add a layer between action and reaction
- **Learning curve**: Developers must understand event flow
- **Memory**: Events are objects that get created and garbage collected

These trade-offs are acceptable for RAW's use case: workflows that may run for minutes/hours and need rich observability.

---

## How Triggers Fit (raw serve)

Triggers are just **producers** that fire the "start pistol."

### Cron (APScheduler)

Scheduler emits `WorkflowTriggered(source="cron")`. The Runner subscribes, sees it, starts the workflow.

### Webhook (FastAPI)

1. FastAPI receives `POST /webhook/stock-report`
2. Verifies token
3. Emits `WorkflowTriggered(source="webhook", payload={...})`
4. Runner starts workflow with payload as parameters

---

## Human-in-the-Loop: The Full Flow

Event-driven architecture enables scripts to function as pausable conversations.

### The Flow

1. **The Pause**: Workflow hits `wait_for_approval("Approve deployment?")`. It emits `ApprovalRequested` and enters a wait loop.

2. **The Notification**: `raw serve` detects the `ApprovalRequested` event and triggers a notification (e.g., email or Slack) with a link: `http://localhost:8000/approve/step_id`.

3. **The Interaction**: A human clicks the link. FastAPI receives the request and emits `ApprovalReceived(decision="approve")`.

4. **The Resume**: The waiting workflow picks up the `ApprovalReceived` event, breaks its loop, and continues execution.

### Architecture Diagram

```
[ External World ]       [ raw serve (FastAPI) ]           [ Workflow Process ]
       |                          |                                 |
       | --(HTTP Request)-->  [ Webhook Handler ]                   |
       |                          |                                 |
       |                          v                                 |
       |                 (WorkflowTriggered) ---------------------->| starts run()
       |                          |                                 |
       |                          | <----- (StepStarted) ---------- |
       |                          |                                 |
       |                          | <-- (ApprovalRequested) ------- | hits pause
       | <--- (Email/Slack) ----- |                                 |
       |                          |                                 |
(Human clicks link)               |                                 |
       | --(HTTP Approve)-->  [ Approval Handler ]                  |
       |                          |                                 |
       |                          v                                 |
       |                 (ApprovalReceived) ----------------------->| resumes run()
       |                          |                                 |
```

---

## Integration Points

### Adding Custom Handlers

```python
from raw_runtime import LocalEventBus, Event

bus = LocalEventBus()

def my_handler(event: Event) -> None:
    if event.event_type == EventType.STEP_COMPLETED:
        send_webhook(event.model_dump())

bus.subscribe(my_handler, event_types=[EventType.STEP_COMPLETED])
```

### Testing with Events

```python
def test_workflow_emits_events():
    bus = LocalEventBus()
    events = []
    bus.subscribe(lambda e: events.append(e))

    ctx = WorkflowContext(workflow_id="test", event_bus=bus)
    with ctx:
        ctx.add_artifact("report", Path("output.txt"))

    assert isinstance(events[0], WorkflowStartedEvent)
    assert isinstance(events[1], ArtifactCreatedEvent)
```

---

## See Also

- [../README.md](../README.md) - Project overview
- [QUICKSTART.md](QUICKSTART.md) - 30-second setup
- [GUIDE.md](GUIDE.md) - Building workflows
- [API.md](API.md) - Runtime API reference
