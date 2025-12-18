# raw-core

Foundation package for RAW Platform providing shared protocols, events, and errors.

## Installation

```bash
pip install raw-core
```

## Usage

```python
from raw_core import LLMDriver, TextChunk, PlatformError
from raw_core.protocols import EventBus, StorageBackend
from raw_core.events import ToolCallEvent, TurnComplete
from raw_core.errors import LLMServiceError, ToolExecutionError
```

## Components

- **Protocols**: Interface definitions (LLMDriver, ToolExecutor, EventBus, StorageBackend)
- **Events**: Immutable event types (TextChunk, ToolCallEvent, StepStarted, etc.)
- **Errors**: Structured error hierarchy (PlatformError, ServiceError, ToolExecutionError)
