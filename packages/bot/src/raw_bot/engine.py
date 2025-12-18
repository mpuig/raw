"""Transport-agnostic conversation engine.

Core "brain" that manages LLM interactions, tool execution, and conversation state.
Decoupled from transport (voice/text) to enable reuse across different interfaces.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator, Protocol

from raw_core.events import TextChunk, ToolCallEvent, ToolResultEvent, TurnComplete
from raw_core.protocols import LLMDriver, ToolExecutor

if TYPE_CHECKING:
    from raw_bot.context import ContextManager


class EngineMiddleware(Protocol):
    """Extension point for cross-cutting concerns."""

    async def before_turn(self, user_text: str, engine: Any) -> str:
        """Intercept/modify user input before LLM processing."""
        ...

    async def after_event(self, event: Any, engine: Any) -> Any | None:
        """Intercept/modify/suppress events before yielding to caller."""
        ...


@dataclass
class BotConfig:
    """Configuration for a conversation bot."""

    name: str
    system_prompt: str
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    greeting_first: bool = False


@dataclass
class ConversationEngine:
    """Orchestrates LLM interactions with tool execution and context management.

    Designed for dependency injection: all collaborators (driver, executor, context)
    are pluggable, enabling testing and alternative implementations.
    """

    config: BotConfig
    driver: LLMDriver
    executor: ToolExecutor
    context: ContextManager
    tools_schema: list[dict[str, Any]] = field(default_factory=list)
    middlewares: list[EngineMiddleware] = field(default_factory=list)
    _conversation_ended: bool = field(default=False)
    _interrupted: bool = field(default=False)
    _pending_tasks: set[asyncio.Task[Any]] = field(default_factory=set)

    def __post_init__(self) -> None:
        if not self.context.messages:
            self.context.initialize(self.config.system_prompt)

    def add_middleware(self, middleware: EngineMiddleware) -> None:
        self.middlewares.append(middleware)

    async def _apply_before_turn(self, user_text: str) -> str:
        for mw in self.middlewares:
            user_text = await mw.before_turn(user_text, self)
        return user_text

    async def _apply_after_event(self, event: Any) -> Any | None:
        result: Any | None = event
        for mw in self.middlewares:
            result = await mw.after_event(result, self)
            if result is None:
                return None
        return result

    async def process_turn(self, user_text: str) -> AsyncIterator[Any]:
        """Process user input and stream events."""
        self._interrupted = False
        user_text = await self._apply_before_turn(user_text)
        self.context.add_user_message(user_text)

        async for event in self._process_llm_turn():
            if self._interrupted:
                break

            event = await self._apply_after_event(event)
            if event is None:
                continue

            yield event

            if isinstance(event, ToolResultEvent):
                if isinstance(event.result, dict) and event.result.get("end_conversation"):
                    self._conversation_ended = True

        yield TurnComplete(end_conversation=self._conversation_ended)

    async def _process_llm_turn(self) -> AsyncIterator[Any]:
        """Single LLM round with tool loop."""
        while not self._interrupted:
            collected_content: list[str] = []
            collected_tool_calls: list[dict[str, Any]] = []

            async for chunk in self.driver.stream_chat(
                messages=self.context.get_messages(),
                model=self.config.model,
                tools=self.tools_schema if self.tools_schema else None,
                temperature=self.config.temperature,
            ):
                if self._interrupted:
                    break

                if chunk.content:
                    collected_content.append(chunk.content)
                    yield TextChunk(text=chunk.content)

                if chunk.finish_reason and chunk.tool_calls:
                    collected_tool_calls = chunk.tool_calls

            full_content = "".join(collected_content)
            if full_content and not collected_tool_calls:
                self.context.add_assistant_message(full_content)

            if not collected_tool_calls:
                break

            async for event in self._execute_tool_calls(collected_tool_calls, full_content):
                yield event
                if isinstance(event, ToolResultEvent):
                    if isinstance(event.result, dict) and event.result.get("end_conversation"):
                        return

    async def _execute_tool_calls(
        self, tool_calls: list[dict[str, Any]], assistant_content: str
    ) -> AsyncIterator[Any]:
        """Execute all tool calls concurrently."""
        assistant_msg = {
            "role": "assistant",
            "content": assistant_content or "",
            "tool_calls": [
                {
                    "id": tc["id"],
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": tc["arguments"]},
                }
                for tc in tool_calls
            ],
        }
        self.context.add_tool_call(assistant_msg)

        for tc in tool_calls:
            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            yield ToolCallEvent(name=tc["name"], arguments=args, call_id=tc["id"])

        async def execute_one(tc: dict[str, Any]) -> tuple[str, str, dict[str, Any]]:
            args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            result = await self.executor.execute(tc["name"], args)
            return tc["id"], tc["name"], result

        tasks = [execute_one(tc) for tc in tool_calls]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, BaseException):
                call_id = "unknown"
                name = "unknown"
                result_dict: dict[str, Any] = {"error": str(result)}
            else:
                call_id, name, result_dict = result

            self.context.add_tool_result(call_id, result_dict)
            yield ToolResultEvent(name=name, result=result_dict, call_id=call_id)

    def interrupt(self, spoken_text: str | None = None) -> None:
        """Handle user barge-in by stopping generation."""
        self._interrupted = True
        for task in self._pending_tasks:
            if not task.done():
                task.cancel()
        self._pending_tasks.clear()

        if spoken_text is not None and spoken_text.strip():
            self.context.update_last_assistant_message(spoken_text + " [interrupted]")

    async def generate_greeting(self) -> AsyncIterator[Any]:
        """Trigger bot-initiated greeting."""
        if not self.config.greeting_first:
            return
        async for event in self.process_turn("(User just connected)"):
            yield event

    def reset(self) -> None:
        """Clear conversation history."""
        self.context.initialize(self.config.system_prompt)
        self._conversation_ended = False
        self._interrupted = False
        self._pending_tasks.clear()

    @property
    def conversation_ended(self) -> bool:
        return self._conversation_ended

    @property
    def messages(self) -> list[dict[str, Any]]:
        return self.context.get_messages()
