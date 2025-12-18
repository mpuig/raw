"""Deepgram STT service implementation for real-time transcription."""

from typing import Any

from pipecat.frames.frames import Frame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.deepgram.stt import DeepgramSTTService

from raw_core import STTServiceError


class DeepgramSTT(DeepgramSTTService):
    """Deepgram speech-to-text service wrapper.

    Wraps Deepgram's real-time transcription service with RAW Platform's
    error handling, providing consistent STTServiceError exceptions.

    Supports all Deepgram features:
    - Real-time streaming transcription
    - Multiple language support
    - Custom models (nova-2, whisper, etc.)
    - Punctuation and formatting
    - Interim results
    - Speaker diarization
    """

    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str = "en-US",
        **kwargs: Any,
    ):
        """Initialize Deepgram STT service.

        Args:
            api_key: Deepgram API key.
            model: Model to use (e.g., "nova-2", "whisper-large").
            language: Language code (e.g., "en-US", "es", "fr").
            **kwargs: Additional Deepgram configuration options:
                - punctuate: Enable punctuation (default: True)
                - profanity_filter: Filter profanity (default: False)
                - interim_results: Enable interim results (default: False)
                - diarize: Enable speaker diarization (default: False)
                - smart_format: Enable smart formatting (default: False)
        """
        super().__init__(
            api_key=api_key,
            model=model,
            language=language,
            **kwargs,
        )

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Process audio frames with error handling.

        Why: Wraps Deepgram's frame processing in RAW Platform's error handling
        to ensure consistent error reporting across all STT providers.

        Args:
            frame: Pipecat frame to process (typically audio frames).
            direction: Frame processing direction.

        Raises:
            STTServiceError: If transcription fails (network, API, or processing error).
        """
        try:
            await super().process_frame(frame, direction)
        except STTServiceError:
            # Re-raise if already our error type
            raise
        except Exception as e:
            # Wrap all other exceptions in our domain error
            raise STTServiceError(f"Deepgram STT failed: {e}", cause=e) from e
