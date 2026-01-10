"""Voice pipeline adapter for Pipecat.

Bridges the transport-agnostic ConversationEngine to Pipecat's audio I/O,
enabling real-time voice conversations with STT, TTS, and VAD.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import EndFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineParams, PipelineTask
from pipecat.transports.local.audio import (
    LocalAudioTransport,
    LocalAudioTransportParams,
)
from pydantic import BaseModel
from raw_core.errors import ErrorAction, ErrorPolicy, ServiceError, TransportError

from .adapter import EngineProcessor
from .services import VoiceServices

if TYPE_CHECKING:
    from raw_bot.engine import ConversationEngine


class TransportConfig(BaseModel):
    """Audio transport settings with sensible defaults for voice conversations."""

    audio_in_enabled: bool = True
    audio_out_enabled: bool = True
    sample_rate: int = 16000
    vad_enabled: bool = True
    vad_stop_secs: float = 0.2


def create_pipeline(
    engine: ConversationEngine,
    services: VoiceServices,
    transport_config: TransportConfig | None = None,
    on_end_conversation: Callable[[], None] | None = None,
    allow_interruptions: bool = True,
    speech_rate_wps: float = 2.5,
    logger=None,
) -> tuple[Pipeline, PipelineTask, LocalAudioTransport]:
    """Wire up Pipecat pipeline with ConversationEngine.

    Dependencies are provided explicitly for full dependency injection and testing.

    Args:
        engine: The conversation engine to use.
        services: Voice services (STT, TTS) to use.
        transport_config: Audio transport settings.
        on_end_conversation: Callback when conversation ends.
        allow_interruptions: Whether to allow user to interrupt bot speech.
        speech_rate_wps: Words per second rate for speech estimation.
        logger: Optional logger for activity logging.

    Returns:
        Tuple of (pipeline, task, transport) for running the conversation.
    """
    if transport_config is None:
        transport_config = TransportConfig()

    engine_processor = EngineProcessor(
        engine,
        on_end_conversation=on_end_conversation,
        allow_interruptions=allow_interruptions,
        speech_rate_wps=speech_rate_wps,
        logger=logger,
    )

    vad_analyzer = None
    if transport_config.vad_enabled:
        vad_analyzer = SileroVADAnalyzer(
            sample_rate=transport_config.sample_rate,
            params=VADParams(stop_secs=transport_config.vad_stop_secs),
        )

    transport = LocalAudioTransport(
        LocalAudioTransportParams(
            audio_in_enabled=transport_config.audio_in_enabled,
            audio_out_enabled=transport_config.audio_out_enabled,
            audio_in_sample_rate=transport_config.sample_rate,
            audio_out_sample_rate=transport_config.sample_rate,
            vad_analyzer=vad_analyzer,
        )
    )
    pipeline = Pipeline(
        [
            transport.input(),
            services.stt,
            engine_processor,
            services.tts,
            transport.output(),
        ]
    )

    task = PipelineTask(
        pipeline,
        params=PipelineParams(allow_interruptions=allow_interruptions),
    )

    return pipeline, task, transport


def _classify_pipeline_error(error: Exception) -> Exception:
    """Classify pipeline errors into domain-specific types.

    Domain exceptions (LLMServiceError, STTServiceError, TTSServiceError) are raised
    at the source. This function passes them through and provides fallback
    classification for transport errors.
    """
    if isinstance(error, ServiceError):
        return error

    # Fallback for transport/audio errors not wrapped at source
    error_str = str(error).lower()
    error_type = type(error).__name__.lower()

    transport_indicators = ["transport", "audio", "connection", "socket", "microphone"]
    if any(ind in error_type or ind in error_str for ind in transport_indicators):
        return TransportError(str(error), cause=error)

    return error


async def run_voice_conversation(
    engine: ConversationEngine,
    services: VoiceServices,
    transport_config: TransportConfig | None = None,
    error_policy: ErrorPolicy | None = None,
    logger=None,
) -> list[dict[str, Any]]:
    """Run voice conversation with error recovery.

    Wraps pipeline execution with retry logic, allowing transient failures
    (network issues, rate limits) to recover without losing the conversation.

    Args:
        engine: The conversation engine to use.
        services: Voice services (STT, TTS) to use.
        transport_config: Audio transport settings.
        error_policy: Strategy for handling errors.
        logger: Optional logger for activity logging.

    Returns:
        List of conversation messages.
    """
    if logger:
        logger.bot_started(engine.config.name)

    task = None
    retry_count = 0

    def end_conversation():
        if logger:
            logger.system("Conversation ended: transfer to agent")
        if task:
            asyncio.create_task(task.queue_frame(EndFrame()))

    while True:
        try:
            pipeline, task, transport = create_pipeline(
                engine,
                services,
                transport_config=transport_config,
                on_end_conversation=end_conversation,
                logger=logger,
            )
            runner = PipelineRunner()
            await runner.run(task)
            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            if error_policy is None:
                if logger:
                    logger.error(f"Pipeline failed: {e}")
                break

            classified_error = _classify_pipeline_error(e)
            decision = error_policy.decide(classified_error, retry_count)

            if decision.action == ErrorAction.RETRY:
                retry_count += 1
                if logger:
                    logger.error(
                        f"Pipeline error ({decision.reason}), "
                        f"retry {retry_count}: {classified_error}"
                    )
                if decision.retry_delay > 0:
                    await asyncio.sleep(decision.retry_delay)
                continue

            if decision.action == ErrorAction.LOG_AND_CONTINUE:
                if logger:
                    logger.error(f"Pipeline error ({decision.reason}): {classified_error}")
                continue

            if logger:
                logger.error(f"Pipeline failed ({decision.reason}): {classified_error}")
            break

    if logger:
        logger.bot_stopped()

    return engine.messages
