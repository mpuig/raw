# integration-deepgram

Deepgram integration for RAW Platform - real-time speech-to-text transcription.

## Overview

Provides real-time speech-to-text transcription through Deepgram's SDK, enabling voice input for conversational AI applications built on the RAW Platform.

## Installation

```bash
uv add integration-deepgram
```

## Usage

```python
from integration_deepgram import DeepgramSTT

# Initialize STT service (requires DEEPGRAM_API_KEY environment variable or explicit key)
stt = DeepgramSTT(
    api_key="your-deepgram-api-key",
    model="nova-2",
    language="en-US"
)

# Or with additional options
stt = DeepgramSTT(
    api_key="your-deepgram-api-key",
    model="nova-2",
    language="en-US",
    punctuate=True,
    interim_results=False,
    diarize=False,
    smart_format=True
)

# Use with Pipecat pipeline
from pipecat.pipeline.pipeline import Pipeline

pipeline = Pipeline([
    # ... transport/input processor
    stt,
    # ... other processors
])
```

## Supported models

Deepgram supports multiple models optimized for different use cases:
- `nova-2`: Latest general-purpose model (recommended)
- `nova`: Previous generation general-purpose model
- `whisper-large`: OpenAI Whisper large model
- `whisper-medium`: OpenAI Whisper medium model
- `whisper-small`: OpenAI Whisper small model
- `base`: Deepgram's base model

## Configuration options

- `api_key`: Deepgram API key (required)
- `model`: Model to use (default: "nova-2")
- `language`: Language code (default: "en-US")
- `punctuate`: Enable automatic punctuation (default: True)
- `profanity_filter`: Filter profanity (default: False)
- `interim_results`: Enable interim transcription results (default: False)
- `diarize`: Enable speaker diarization (default: False)
- `smart_format`: Enable smart formatting (default: False)

## Supported languages

Deepgram supports 30+ languages including:
- English: `en-US`, `en-GB`, `en-AU`, `en-IN`
- Spanish: `es`, `es-419`
- French: `fr`, `fr-CA`
- German: `de`
- Italian: `it`
- Portuguese: `pt`, `pt-BR`
- Chinese: `zh`, `zh-CN`, `zh-TW`
- Japanese: `ja`
- Korean: `ko`
- And many more...

## Architecture

Extends Pipecat's `DeepgramSTTService` with RAW Platform's error handling:
- Wraps all exceptions in `STTServiceError` from `raw-core`
- Maintains compatibility with Pipecat's frame processing pipeline
- Provides consistent error reporting across different STT providers

## Dependencies

- `raw-core`: Core protocols and errors
- `deepgram-sdk`: Deepgram Python SDK
- `pipecat-ai`: Pipeline framework for voice processing
