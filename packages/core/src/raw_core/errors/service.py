"""Service-related errors for external API failures."""

from raw_core.errors.base import PlatformError


class ServiceError(PlatformError):
    """Base for external service errors (LLM, STT, TTS)."""

    pass


class LLMServiceError(ServiceError):
    """LLM API errors (OpenAI, Anthropic, etc.)."""

    pass


class STTServiceError(ServiceError):
    """Speech-to-text service errors (Deepgram, etc.)."""

    pass


class TTSServiceError(ServiceError):
    """Text-to-speech service errors (ElevenLabs, etc.)."""

    pass
