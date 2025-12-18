"""Pipecat processor that wraps ConversationEngine."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from pipecat.frames.frames import (
    BotStartedSpeakingFrame,
    BotStoppedSpeakingFrame,
    Frame,
    LLMFullResponseEndFrame,
    LLMFullResponseStartFrame,
    StartFrame,
    TextFrame,
    TranscriptionFrame,
    UserStartedSpeakingFrame,
    UserStoppedSpeakingFrame,
)
from pipecat.processors.frame_processor import FrameDirection, FrameProcessor

from raw_core.events import TextChunk, ToolCallEvent, ToolResultEvent, TurnComplete

if TYPE_CHECKING:
    from raw_bot.engine import ConversationEngine


class EngineProcessor(FrameProcessor):
    """
    Pipecat processor that uses ConversationEngine.

    Receives TranscriptionFrames (user input), processes through the engine,
    and emits TextFrames (for TTS to speak).

    Args:
        engine: The conversation engine to use.
        on_end_conversation: Callback when conversation should end.
        allow_interruptions: If True, user can interrupt bot speech (barge-in).
            If False, user input is ignored while bot is speaking.
        speech_rate_wps: Words per second rate for speech estimation.
        logger: Optional logger for activity logging (stt, tts, llm events).
    """

    def __init__(
        self,
        engine: ConversationEngine,
        on_end_conversation=None,
        allow_interruptions: bool = True,
        speech_rate_wps: float = 2.5,
        logger=None,
    ):
        super().__init__()
        self._engine = engine
        self._on_end_conversation = on_end_conversation
        self._allow_interruptions = allow_interruptions
        self._speech_rate_wps = speech_rate_wps
        self._logger = logger
        self._greeting_sent = False
        self._processing = False
        self._bot_speaking = False
        self._user_speaking = False
        self._conversation_ended = False
        # Tracking for interruption handling
        self._current_response_chunks: list[str] = []
        self._speech_start_time: float | None = None

    def _log(self, method: str, *args, **kwargs):
        """Helper to log if logger is available."""
        if self._logger and hasattr(self._logger, method):
            getattr(self._logger, method)(*args, **kwargs)

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        await super().process_frame(frame, direction)

        if isinstance(frame, StartFrame):
            await self._handle_start_frame(frame, direction)
        elif isinstance(frame, BotStartedSpeakingFrame):
            await self._handle_bot_started_speaking(frame, direction)
        elif isinstance(frame, BotStoppedSpeakingFrame):
            await self._handle_bot_stopped_speaking(frame, direction)
        elif isinstance(frame, UserStartedSpeakingFrame):
            self._user_speaking = True
            await self.push_frame(frame, direction)
        elif isinstance(frame, UserStoppedSpeakingFrame):
            self._user_speaking = False
            await self.push_frame(frame, direction)
        elif isinstance(frame, TranscriptionFrame):
            await self._handle_transcription(frame)
        else:
            await self.push_frame(frame, direction)

    async def _handle_start_frame(
        self, frame: StartFrame, direction: FrameDirection
    ) -> None:
        """Handle pipeline start and send greeting if configured."""
        await self.push_frame(frame, direction)
        if not self._greeting_sent:
            await self._send_greeting()
            self._greeting_sent = True

    async def _handle_bot_started_speaking(
        self, frame: BotStartedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """Track bot speech start for interruption handling."""
        self._bot_speaking = True
        self._speech_start_time = time.time()
        await self.push_frame(frame, direction)

    async def _handle_bot_stopped_speaking(
        self, frame: BotStoppedSpeakingFrame, direction: FrameDirection
    ) -> None:
        """Log spoken text and reset speech tracking state."""
        self._bot_speaking = False
        self._log_completed_speech()
        self._speech_start_time = None
        self._current_response_chunks = []
        await self.push_frame(frame, direction)

    def _log_completed_speech(self) -> None:
        """Log what was spoken, accounting for potential interruption."""
        if not self._current_response_chunks or not self._speech_start_time:
            return

        full_text = "".join(self._current_response_chunks).strip()
        if not full_text:
            return

        elapsed = time.time() - self._speech_start_time
        words = full_text.split()
        estimated_words = int(elapsed * self._speech_rate_wps)

        if estimated_words >= len(words):
            self._log("tts", full_text)
        else:
            truncated = " ".join(words[: max(1, estimated_words)])
            self._log("tts", truncated + " [interrupted]")

    async def _handle_transcription(self, frame: TranscriptionFrame) -> None:
        """Process user transcription with interruption and echo filtering."""
        if not frame.text.strip() or self._processing or self._conversation_ended:
            return

        if self._bot_speaking:
            await self._handle_barge_in(frame.text)
        else:
            self._log("stt", frame.text)
            await self._process_user_input(frame.text)

    async def _handle_barge_in(self, text: str) -> None:
        """Handle user speech while bot is speaking (barge-in/interruption)."""
        if not self._allow_interruptions or not self._user_speaking:
            return

        spoken_text = self._estimate_spoken_text()
        if spoken_text:
            self._log("tts", spoken_text + " [interrupted]")
        self._engine.interrupt(spoken_text)
        self._current_response_chunks = []
        self._log("stt", text)
        await self._process_user_input(text)

    async def _send_greeting(self) -> None:
        """Generate and send initial greeting if bot is configured for it."""
        self._current_response_chunks = []
        greeting_text: list[str] = []
        async for event in self._engine.generate_greeting():
            if isinstance(event, TextChunk):
                self._current_response_chunks.append(event.text)
                greeting_text.append(event.text)
                await self.push_frame(TextFrame(text=event.text))
            elif isinstance(event, TurnComplete):
                if greeting_text:
                    self._log("llm_response", "".join(greeting_text))
                await self.push_frame(LLMFullResponseEndFrame())

    async def _process_user_input(self, text: str) -> None:
        """Process user transcription through the engine."""
        self._processing = True
        response_started = False
        response_text: list[str] = []
        self._current_response_chunks = []

        try:
            await self.push_frame(LLMFullResponseStartFrame())
            response_started = True

            async for event in self._engine.process_turn(text):
                if isinstance(event, TextChunk):
                    response_text.append(event.text)
                    self._current_response_chunks.append(event.text)
                    await self.push_frame(TextFrame(text=event.text))

                elif isinstance(event, ToolCallEvent):
                    self._log("llm_tool_call", event.name, event.arguments)

                elif isinstance(event, ToolResultEvent):
                    self._log("tool_result", event.name, event.result)

                elif isinstance(event, TurnComplete):
                    if response_text:
                        self._log("llm_response", "".join(response_text))
                        response_text = []
                    if response_started:
                        await self.push_frame(LLMFullResponseEndFrame())
                        response_started = False
                    if event.end_conversation and self._on_end_conversation:
                        self._conversation_ended = True
                        self._on_end_conversation()

        except Exception as e:
            self._log("error", f"Engine processing error: {e}")
            if response_started:
                await self.push_frame(LLMFullResponseEndFrame())
            raise
        finally:
            self._processing = False

    def _estimate_spoken_text(self) -> str | None:
        """Estimate what text was spoken before interruption based on elapsed time."""
        if not self._current_response_chunks or self._speech_start_time is None:
            return None

        full_text = "".join(self._current_response_chunks)
        words = full_text.split()
        if not words:
            return None

        elapsed = time.time() - self._speech_start_time
        estimated_words_spoken = int(elapsed * self._speech_rate_wps)

        if estimated_words_spoken >= len(words):
            return full_text

        if estimated_words_spoken <= 0:
            return None

        return " ".join(words[:estimated_words_spoken])

    @property
    def engine(self) -> ConversationEngine:
        """Access the underlying conversation engine."""
        return self._engine
