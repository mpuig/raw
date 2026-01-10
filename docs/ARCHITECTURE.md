# RAW Architecture: Event-Driven Workflow Execution

This document explains RAW's event-driven architecture and the rationale behind key design decisions.

---

## Core Concept: Event-Driven

In RAW's architecture, workflows don't just "run"—they **emit events** and **react to events**.

- `run.py` emits `StepStarted`, `StepCompleted`, `ArtifactCreated`
- Triggers emit `WorkflowTriggered` to start workflows
- Human approval emits `ApprovalRequested`, waits for `ApprovalReceived`

This turns a script into a conversation between components.

---

## Core Principle: Observability

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

## Production-Ready Data Plane

RAW's data plane implements **append-only journaling** and **event sourcing** for crash safety, resumability, and provenance tracking. This architecture borrows from:
- **Gas Town**: Durable work objects, explicit progress graphs
- **Codex**: Append-only JSONL rollouts, typed item lifecycle events
- **Kubernetes**: Reconciliation loops for crash detection

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Workflow Execution                       │
│                                                             │
│  @step decorators → Events → EventBus → JournalHandler     │
│                                            ↓                │
│                                     events.jsonl            │
└─────────────────────────────────────────────────────────────┘
                                             │
                    ┌────────────────────────┼────────────────────┐
                    │                        │                    │
                    ▼                        ▼                    ▼
            ┌──────────────┐        ┌──────────────┐    ┌──────────────┐
            │   Reducer    │        │ Reconciler   │    │    Index     │
            │              │        │              │    │              │
            │ Rebuild      │        │ Detect       │    │ Fast         │
            │ manifest     │        │ crashes      │    │ queries      │
            │ from events  │        │              │    │              │
            └──────────────┘        └──────────────┘    └──────────────┘
                    │                        │                    │
                    ▼                        ▼                    ▼
              manifest.json           CRASHED status         index.jsonl
```

### 1. Append-Only Journal (`events.jsonl`)

Every workflow execution writes events to an append-only journal for crash recovery and provenance.

**Format:**
```jsonl
{"version": 1, "event": {"event_type": "workflow.started", "workflow_id": "...", ...}}
{"version": 1, "event": {"event_type": "workflow.provenance", "git_sha": "...", ...}}
{"version": 1, "event": {"event_type": "step.started", "step_name": "fetch", ...}}
{"version": 1, "event": {"event_type": "step.completed", "step_name": "fetch", ...}}
{"version": 1, "event": {"event_type": "workflow.completed", ...}}
```

**Properties:**
- **Crash-safe**: Events fsync'ed immediately after write
- **Immutable**: Never modified, only appended
- **Complete history**: Full execution trace from start to finish
- **Rebuildable**: Manifest can be reconstructed from journal alone

**Implementation:**
```python
from raw_runtime import LocalJournalWriter, JournalEventHandler

# Set up journal handler
journal_path = Path(".raw/runs/run_123/events.jsonl")
writer = LocalJournalWriter(journal_path)
handler = JournalEventHandler(journal_path)

# Subscribe to event bus
event_bus.subscribe(handler)

# All events automatically written to journal
```

### 2. Manifest Reducer (Event Sourcing)

The **ManifestReducer** rebuilds workflow state from the event journal using event sourcing.

**Pattern:**
```
events.jsonl → [workflow.started, step.started, step.completed, ...] → reduce → manifest.json
```

**Implementation:**
```python
from raw_runtime import ManifestReducer

reducer = ManifestReducer()
manifest = reducer.reduce_from_file(Path("events.jsonl"))

# Manifest contains:
# - workflow metadata
# - run status (SUCCESS/FAILED/CRASHED)
# - all step results
# - provenance info
# - artifacts
```

**Benefits:**
- **Crash recovery**: Rebuild manifest from journal if process dies
- **Auditability**: Full event history preserved
- **Time travel**: Replay events to any point
- **Debugging**: Inspect exact event sequence that led to failure

### 3. Run Reconciliation (Crash Detection)

The **reconciler** detects and marks crashed/stale runs using a Kubernetes-style reconciliation loop.

**How it works:**
1. Scan run directories for incomplete runs (status = RUNNING)
2. Check journal file modification time
3. If inactive > timeout (default 1 hour), mark as CRASHED
4. Append `workflow.failed` event with "CRASHED:" prefix

**Implementation:**
```python
from raw_runtime import reconcile_run, scan_and_reconcile

# Reconcile single run
result = reconcile_run(
    run_dir=Path(".raw/runs/run_123"),
    stale_timeout_seconds=3600,  # 1 hour
    mark_as_crashed=True
)

# Scan all runs
results = scan_and_reconcile(
    workflows_dir=Path(".raw/workflows"),
    stale_timeout_seconds=3600
)
```

**Crash detection:**
- Uses file mtime as proxy for last activity
- Writes terminal event back to journal (never deletes data)
- Reducer recognizes "CRASHED:" prefix and sets `RunStatus.CRASHED`

### 4. Resume (Continue Interrupted Runs)

Workflows can resume from the last completed step after crashes or manual cancellation.

**Resume flow:**
1. Read journal from interrupted run
2. Identify steps with `StepStatus.SUCCESS`
3. Create new context with `resume_completed_steps` set
4. Execute workflow - `@step` decorator skips completed steps

**Implementation:**
```python
from raw_runtime import WorkflowContext, configure_context_for_resume

# Create context for resumed run
context = WorkflowContext(
    workflow_id="my-workflow",
    short_name="my-workflow",
    parameters={"arg": "value"}
)

# Configure resume from previous run's journal
configure_context_for_resume(
    context,
    journal_path=Path(".raw/runs/run_previous/events.jsonl")
)

# Execute workflow - completed steps automatically skipped
with context:
    result = my_workflow.run()
```

**Resume semantics:**
- Skips steps that completed successfully
- Reruns failed/incomplete steps
- No mid-step resumption (step must complete or start over)
- User ensures steps are idempotent (resume-safe)

**Provenance:**
- Resumed run links to original run via `resumed_from_run_id`
- Both journals preserved for full audit trail

### 5. Provenance Tracking

Every workflow captures git state, tool versions, and configuration at start.

**Captured metadata:**
- **Git**: SHA, branch, dirty status
- **Workflow**: File hash (SHA256)
- **Tools**: Version hash for each tool in `tools/`
- **Environment**: Python version, hostname, working directory
- **Config**: RAW_* env vars (secrets redacted)

**Implementation:**
```python
# Automatically captured on workflow start
# Emits WorkflowProvenanceEvent after WorkflowStartedEvent

# Access provenance from manifest
from raw_runtime import ManifestReducer

reducer = ManifestReducer()
manifest = reducer.reduce_from_file(journal_path)

if manifest.provenance:
    print(f"Git SHA: {manifest.provenance.git_sha}")
    print(f"Branch: {manifest.provenance.git_branch}")
    print(f"Dirty: {manifest.provenance.git_dirty}")
    print(f"Tools: {manifest.provenance.tool_versions}")
```

**Secrets redaction:**
Environment variables containing `KEY`, `TOKEN`, `SECRET`, or `PASSWORD` are automatically redacted in provenance snapshots.

### 6. Run Index (Fast Queries)

The **RunIndex** provides fast queries over run history without scanning all journals.

**Format:** Append-only JSONL
```jsonl
{"run_id": "run_123", "workflow_id": "my-workflow", "status": "success", ...}
{"run_id": "run_124", "workflow_id": "my-workflow", "status": "crashed", ...}
```

**Capabilities:**
```python
from raw_runtime import RunIndexReader, RunIndexWriter

reader = RunIndexReader(Path(".raw/index.jsonl"))

# List runs with filters
runs = reader.list_runs(
    status=RunStatus.SUCCESS,
    workflow_id="my-workflow",
    offset=0,
    limit=10
)

# Get specific run
run = reader.get_run("run_123")

# Count runs
count = reader.count_runs(status=RunStatus.FAILED)
```

**Pagination:**
- Cursor-based (offset + limit)
- Stable ordering for consistent page boundaries
- Efficient for large run histories

**Rebuild:**
```python
from raw_runtime import rebuild_index_from_journals

# Rebuild from all journals (for recovery)
count = rebuild_index_from_journals(
    workflows_dir=Path(".raw/workflows"),
    index_path=Path(".raw/index.jsonl")
)
```

### Directory Structure

```
.raw/
├── workflows/
│   └── my-workflow/
│       └── runs/
│           ├── run_20260110_120000/
│           │   ├── events.jsonl        # Append-only event journal
│           │   ├── manifest.json       # Derived from events.jsonl
│           │   ├── output.log          # Stdout/stderr
│           │   └── results/            # Artifacts
│           └── run_20260110_130000/
│               └── ...
├── index.jsonl                          # Run index (fast queries)
└── config.yaml                          # Project config
```

### Design Decisions

**Why append-only?**
- Crash safety: Partial writes don't corrupt existing data
- Auditability: Complete history preserved
- Simplicity: No update/delete logic needed

**Why event sourcing?**
- Single source of truth: Journal is canonical, manifest is derived
- Recovery: Rebuild state after crashes
- Debugging: Full execution trace available

**Why not SQLite?**
- JSONL is simpler and more portable
- No locking/concurrency issues
- Easy to inspect/debug with text tools
- Sufficient for typical run volumes

**Why reconciliation loops?**
- Kubernetes pattern proven at scale
- Handles edge cases (crashes, network failures)
- Self-healing: System detects and corrects invalid states

### Migration & Compatibility

**No backward compatibility guarantees** for run formats during development. Older run directories may not be compatible with newer RAW versions. This is acceptable for a pre-1.0 project.

**Future stability:** Post-1.0, we'll commit to:
- Schema versioning in journal/index
- Migration tools for major upgrades
- Deprecation warnings for breaking changes

---

## See Also

- [../README.md](../README.md) - Project overview
- [QUICKSTART.md](QUICKSTART.md) - Setup guide
- [GUIDE.md](GUIDE.md) - Building workflows
- [API.md](API.md) - Runtime API reference
