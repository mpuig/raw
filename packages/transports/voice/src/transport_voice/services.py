"""Voice service factory.

Abstracts provider-specific service creation behind a unified interface.
This enables swapping STT/TTS providers without changing pipeline code.
"""

import os
from dataclasses import dataclass

from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.deepgram.stt import DeepgramSTTService
from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
from pipecat.services.stt_service import STTService
from pipecat.services.tts_service import TTSService
from pydantic import BaseModel

from raw_core.errors import STTServiceError, TTSServiceError


class STTConfig(BaseModel):
    """Speech-to-text service configuration."""

    service: str = "deepgram"
    model: str = "nova-2"
    language: str = "en"
    api_key_env: str = "DEEPGRAM_API_KEY"


class TTSConfig(BaseModel):
    """Text-to-speech service configuration."""

    service: str = "elevenlabs"
    voice_id: str = "zGjIP4SZlMnY9m93k97r"
    model: str = "eleven_turbo_v2"
    speech_rate_wps: float = 2.5
    api_key_env: str = "ELEVENLABS_API_KEY"


@dataclass
class VoiceServices:
    """Groups STT and TTS for pipeline injection."""

    stt: STTService
    tts: TTSService


class WrappedDeepgramSTT(DeepgramSTTService):
    """Wraps Deepgram errors in domain exceptions for consistent error handling."""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        try:
            await super().process_frame(frame, direction)
        except STTServiceError:
            raise
        except Exception as e:
            raise STTServiceError(f"Deepgram STT failed: {e}", cause=e) from e


class WrappedElevenLabsTTS(ElevenLabsTTSService):
    """Wraps ElevenLabs errors in domain exceptions for consistent error handling."""

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        try:
            await super().process_frame(frame, direction)
        except TTSServiceError:
            raise
        except Exception as e:
            raise TTSServiceError(f"ElevenLabs TTS failed: {e}", cause=e) from e


def create_stt_service(config: STTConfig) -> STTService:
    """Create STT service from config. Centralizes provider selection logic."""
    if config.service == "deepgram":
        return WrappedDeepgramSTT(
            api_key=os.getenv(config.api_key_env, ""),
            model=config.model,
            language=config.language,
        )
    raise ValueError(f"Unsupported STT service: {config.service}")


def create_tts_service(config: TTSConfig) -> TTSService:
    """Create TTS service from config. Centralizes provider selection logic."""
    if config.service == "elevenlabs":
        return WrappedElevenLabsTTS(
            api_key=os.getenv(config.api_key_env, ""),
            voice_id=config.voice_id,
            model=config.model,
        )
    raise ValueError(f"Unsupported TTS service: {config.service}")


def create_voice_services(stt_config: STTConfig, tts_config: TTSConfig) -> VoiceServices:
    """Create all voice services from configs. Single entry point for pipeline setup."""
    return VoiceServices(
        stt=create_stt_service(stt_config),
        tts=create_tts_service(tts_config),
    )
