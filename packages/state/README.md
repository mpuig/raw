# raw-state

State management backends for RAW Platform providing Redis and PostgreSQL persistence for conversation and workflow state.

## Installation

```bash
pip install raw-state
```

## Usage

### Redis backend

```python
from raw_state import RedisBackend, RedisConfig, SessionManager

# Configure Redis connection
config = RedisConfig(
    host="localhost",
    port=6379,
    db=0,
    password=None,
    ssl=False,
    max_connections=10
)

# Create backend and session manager
backend = RedisBackend(config)
sessions = SessionManager(backend, prefix="conversation:")

# Create a session with TTL
session = await sessions.create_session(
    data={"user_id": "user123", "messages": []},
    metadata={"channel": "voice"},
    ttl=3600  # Expire after 1 hour
)

# Retrieve session
session = await sessions.get_session(session.id)
print(session.data)

# Update session
await sessions.update_session(
    session.id,
    data={"messages": [{"role": "user", "content": "Hello"}]}
)

# Delete session
await sessions.delete_session(session.id)

# Clean up
await backend.close()
```

### PostgreSQL backend

```python
from raw_state import PostgresBackend, PostgresConfig, SessionManager

# Configure PostgreSQL connection
config = PostgresConfig(
    dsn="postgresql://user:pass@localhost/dbname",
    min_pool_size=2,
    max_pool_size=10,
    table_name="raw_state"
)

# Create backend and session manager
backend = PostgresBackend(config)
sessions = SessionManager(backend, prefix="workflow:")

# Create a workflow session
session = await sessions.create_session(
    data={"step": "input", "context": {}},
    metadata={"workflow_type": "data_processing"},
    ttl=7200  # Expire after 2 hours
)

# List all workflow sessions
session_ids = await sessions.list_sessions()

# Clean up
await backend.close()
```

### Direct backend usage

```python
from raw_state import RedisBackend, RedisConfig

backend = RedisBackend(RedisConfig(host="localhost"))

# Store key-value with TTL
await backend.set("user:123:state", '{"logged_in": true}', ttl=300)

# Retrieve value
value = await backend.get("user:123:state")

# Check existence
exists = await backend.exists("user:123:state")

# Set TTL on existing key
await backend.expire("user:123:state", 600)

# Pattern matching
keys = await backend.keys("user:*:state")

# Delete key
await backend.delete("user:123:state")
```

## Components

- **StateBackend**: Protocol for key-value state persistence with async methods
- **RedisBackend**: Redis implementation with connection pooling
- **PostgresBackend**: PostgreSQL implementation with automatic table creation
- **SessionManager**: High-level session management with TTL support
- **Session**: Immutable session data structure with metadata

## Features

- Async/await throughout for efficient I/O
- Connection pooling for both Redis and PostgreSQL
- Automatic TTL support and expiration
- Pattern-based key listing
- Protocol-based design for easy testing and swapping backends
- Immutable configuration and session objects
- Automatic table creation for PostgreSQL
