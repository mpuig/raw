"""ElevenLabs TTS service implementation."""

from typing import AsyncIterator

from elevenlabs import VoiceSettings
from elevenlabs.client import AsyncElevenLabs

from raw_core import TTSServiceError


class ElevenLabsTTS:
    """TTS service using ElevenLabs for high-quality speech synthesis.

    Supports multiple voices and models through ElevenLabs API:
    - Turbo v2.5: Fastest, lowest latency (recommended for real-time)
    - Turbo v2: Fast with good quality
    - Multilingual v2: Support for 29 languages
    - English v1: Original high-quality English model

    Voice IDs can be found in your ElevenLabs dashboard or via API.
    """

    def __init__(
        self,
        api_key: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default: Rachel (English)
        model: str = "eleven_turbo_v2_5",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        style: float = 0.0,
        use_speaker_boost: bool = True,
    ):
        """Initialize the ElevenLabs TTS service.

        Args:
            api_key: ElevenLabs API key.
            voice_id: Voice identifier from ElevenLabs (default: Rachel).
            model: Model name (e.g., "eleven_turbo_v2_5", "eleven_multilingual_v2").
            stability: Voice stability (0.0-1.0). Higher = more consistent.
            similarity_boost: Voice similarity (0.0-1.0). Higher = closer to original.
            style: Style exaggeration (0.0-1.0). Higher = more expressive.
            use_speaker_boost: Enable speaker boost for better clarity.
        """
        self._client = AsyncElevenLabs(api_key=api_key)
        self._voice_id = voice_id
        self._model = model
        self._voice_settings = VoiceSettings(
            stability=stability,
            similarity_boost=similarity_boost,
            style=style,
            use_speaker_boost=use_speaker_boost,
        )

    async def synthesize(self, text: str) -> AsyncIterator[bytes]:
        """Synthesize text to speech, streaming audio chunks.

        Why: Streaming enables low-latency playback as audio is generated,
        rather than waiting for complete synthesis.

        Args:
            text: Text to convert to speech.

        Yields:
            Audio chunks as bytes (MP3 format).

        Raises:
            TTSServiceError: If synthesis request or streaming fails.
        """
        if not text or not text.strip():
            return

        try:
            audio_stream = await self._client.text_to_speech.convert(
                text=text,
                voice_id=self._voice_id,
                model_id=self._model,
                voice_settings=self._voice_settings,
                output_format="mp3_44100_128",
            )

            async for chunk in audio_stream:
                if chunk:
                    yield chunk

        except TTSServiceError:
            raise
        except Exception as e:
            raise TTSServiceError(f"ElevenLabs TTS synthesis failed: {e}", cause=e) from e

    async def get_available_voices(self) -> list[dict[str, str]]:
        """Retrieve available voices from ElevenLabs.

        Returns:
            List of voice dictionaries with 'voice_id', 'name', and 'description'.

        Raises:
            TTSServiceError: If API request fails.
        """
        try:
            voices = await self._client.voices.get_all()
            return [
                {
                    "voice_id": voice.voice_id,
                    "name": voice.name,
                    "description": voice.description or "",
                }
                for voice in voices.voices
            ]
        except Exception as e:
            raise TTSServiceError(f"Failed to fetch voices: {e}", cause=e) from e

    async def close(self) -> None:
        """Close the ElevenLabs client connection.

        Why: Ensures proper cleanup of HTTP connections and resources.
        """
        await self._client.close()
