# transport-voice

Voice transport adapter for RAW Platform. Connects the transport-agnostic ConversationEngine to Pipecat's audio I/O pipeline for real-time voice conversations.

## Installation

```bash
pip install transport-voice
```

## Features

- Pipecat pipeline adapter for voice I/O
- STT/TTS service factory with error wrapping
- Voice Activity Detection (VAD) support
- Interruption handling (barge-in)
- Speech rate estimation for interruption logging
- Error recovery with configurable retry policies

## Usage

```python
from raw_bot import ConversationEngine, BotConfig
from raw_core.protocols import LLMDriver, ToolExecutor
from raw_bot.context import ContextManager
from transport_voice import (
    create_pipeline,
    create_voice_services,
    run_voice_conversation,
    STTConfig,
    TTSConfig,
    TransportConfig,
)

# Configure services
stt_config = STTConfig(
    service="deepgram",
    model="nova-2",
    language="en",
)

tts_config = TTSConfig(
    service="elevenlabs",
    voice_id="zGjIP4SZlMnY9m93k97r",
    model="eleven_turbo_v2",
    speech_rate_wps=2.5,
)

# Create voice services
services = create_voice_services(stt_config, tts_config)

# Create engine (you provide driver, executor, context)
engine = ConversationEngine(
    config=BotConfig(
        name="assistant",
        system_prompt="You are a helpful assistant.",
        greeting_first=True,
    ),
    driver=driver,  # Your LLM driver
    executor=executor,  # Your tool executor
    context=ContextManager(),
)

# Run voice conversation
messages = await run_voice_conversation(
    engine=engine,
    services=services,
    transport_config=TransportConfig(
        sample_rate=16000,
        vad_enabled=True,
    ),
)
```

## Architecture

The package follows clean architecture principles:

- **adapter.py**: Pipecat processor that wraps ConversationEngine
- **pipeline.py**: Pipeline factory and runner with error recovery
- **services.py**: STT/TTS service factory with error wrapping

### Error handling

Service errors (STT, TTS) are wrapped in domain exceptions:

```python
from raw_core.errors import STTServiceError, TTSServiceError

# Errors are raised with cause chain
try:
    services = create_voice_services(stt_config, tts_config)
except STTServiceError as e:
    print(f"STT error: {e}, caused by: {e.cause}")
```

### Interruption handling

The adapter supports user barge-in (interrupting bot speech):

```python
pipeline, task, transport = create_pipeline(
    engine=engine,
    services=services,
    allow_interruptions=True,  # Enable barge-in
    speech_rate_wps=2.5,  # Words per second for estimation
)
```

When interrupted, the engine updates the conversation context with the truncated speech.

## Dependencies

- `raw-core`: Core protocols, events, and errors
- `raw-bot`: Transport-agnostic conversation engine
- `pipecat-ai`: Real-time audio pipeline framework
- `pydantic`: Configuration validation
