# integration-elevenlabs

ElevenLabs integration for RAW Platform - text-to-speech synthesis.

## Overview

Provides high-quality text-to-speech synthesis through ElevenLabs API, supporting multiple voices and models with streaming audio output for low-latency playback.

## Installation

```bash
uv add integration-elevenlabs
```

## Usage

```python
from integration_elevenlabs import ElevenLabsTTS

# Initialize TTS service
tts = ElevenLabsTTS(
    api_key="your-api-key",
    voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel (default)
    model="eleven_turbo_v2_5"
)

# Synthesize text to speech with streaming
async for audio_chunk in tts.synthesize("Hello, world!"):
    # Process audio chunk (MP3 format)
    audio_player.write(audio_chunk)

# Get available voices
voices = await tts.get_available_voices()
for voice in voices:
    print(f"{voice['name']}: {voice['voice_id']}")

# Clean up
await tts.close()
```

## Configuration

### Voice settings

Control voice characteristics:
- `stability` (0.0-1.0): Higher values = more consistent, lower = more variable
- `similarity_boost` (0.0-1.0): Higher values = closer to original voice
- `style` (0.0-1.0): Higher values = more expressive and exaggerated
- `use_speaker_boost`: Enable for better clarity

```python
tts = ElevenLabsTTS(
    api_key="your-api-key",
    voice_id="21m00Tcm4TlvDq8ikWAM",
    model="eleven_turbo_v2_5",
    stability=0.5,
    similarity_boost=0.75,
    style=0.0,
    use_speaker_boost=True
)
```

## Available models

- `eleven_turbo_v2_5`: Fastest, lowest latency (recommended for real-time)
- `eleven_turbo_v2`: Fast with good quality
- `eleven_multilingual_v2`: Support for 29 languages
- `eleven_monolingual_v1`: Original high-quality English model

## Common voice IDs

Find more voices in your ElevenLabs dashboard or via `get_available_voices()`:
- `21m00Tcm4TlvDq8ikWAM`: Rachel (default)
- `AZnzlk1XvdvUeBnXmlld`: Domi
- `EXAVITQu4vr4xnSDxMaL`: Bella
- `ErXwobaYiN019PkySvjV`: Antoni
- `MF3mGyEYCl7XYWbV9V6O`: Elli
- `TxGEqnHWrfWFTfGW9XjX`: Josh

## Error handling

Uses `TTSServiceError` from `raw-core` for consistent error handling:

```python
from raw_core import TTSServiceError

try:
    async for chunk in tts.synthesize("Hello"):
        process_audio(chunk)
except TTSServiceError as e:
    print(f"TTS failed: {e}")
```

## Architecture

The `ElevenLabsTTS` class wraps the ElevenLabs SDK, providing:
- Streaming audio synthesis for low-latency playback
- Voice discovery and configuration
- Consistent error handling via `TTSServiceError`
- Proper resource cleanup

## Dependencies

- `raw-core`: Core protocols and errors
- `elevenlabs`: Official ElevenLabs Python SDK
