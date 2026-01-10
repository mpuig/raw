"""FastAPI router for webhook-based conversation endpoints.

Provides RESTful API for creating conversations, sending messages, and
streaming events. This module handles HTTP concerns (request/response parsing,
validation, error handling) while delegating conversation logic to handlers.
"""

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from raw_bot import ConversationEngine

from transport_webhook.handlers import ConversationManager, ConversationState, ConversationStatus

logger = logging.getLogger(__name__)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""

    conversation_id: str | None = Field(
        default=None, description="Optional custom conversation ID"
    )
    auto_greet: bool = Field(default=True, description="Generate greeting immediately")
    context: dict[str, Any] = Field(
        default_factory=dict, description="Initial context for conversation"
    )


class CreateConversationResponse(BaseModel):
    """Response after creating a conversation."""

    conversation_id: str
    status: ConversationStatus
    greeting: str | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message to a conversation."""

    text: str = Field(..., description="Message text to send")


class SendMessageResponse(BaseModel):
    """Response after sending a message."""

    response: str
    status: ConversationStatus
    outcome: str | None = None


class ConversationListResponse(BaseModel):
    """Response listing conversations."""

    conversations: list[ConversationState]
    count: int


def create_webhook_router(
    engine_factory: Callable[[dict[str, Any]], ConversationEngine],
) -> APIRouter:
    """Create a FastAPI router for webhook endpoints.

    This factory function allows callers to provide their own engine creation
    logic, supporting dependency injection and custom bot configurations.

    Why: Decouples router from specific bot loading mechanisms, enabling
    reuse across different deployment scenarios (file-based, database-backed,
    registry-based, etc.).

    Args:
        engine_factory: Function that creates a ConversationEngine from context.
            The context dict may include bot_name, custom parameters, etc.

    Returns:
        Configured FastAPI router with all webhook endpoints.

    Example:
        ```python
        def my_engine_factory(context: dict) -> ConversationEngine:
            bot_name = context.get("bot_name", "default")
            config = load_bot_config(bot_name)
            driver = LiteLLMDriver()
            executor = ToolExecutor()
            ctx_mgr = ContextManager()
            return ConversationEngine(config, driver, executor, ctx_mgr)

        router = create_webhook_router(my_engine_factory)
        app = FastAPI()
        app.include_router(router)
        ```
    """
    manager = ConversationManager()
    router = APIRouter(prefix="/webhooks", tags=["webhooks"])

    @router.post("/conversations", response_model=CreateConversationResponse)
    async def create_conversation(request: CreateConversationRequest):
        """Create a new conversation session.

        Initializes the bot with provided context. If auto_greet is True,
        also generates the initial greeting message from the bot.

        Returns:
            Conversation ID, status, and optional greeting message.

        Raises:
            HTTPException: If conversation creation or engine initialization fails.
        """
        try:
            # Create engine using factory
            engine = engine_factory(request.context)

            # Create conversation handler
            conversation = await manager.create(
                engine=engine,
                conversation_id=request.conversation_id,
            )

            # Generate greeting if requested
            greeting = None
            if request.auto_greet:
                greeting = await conversation.generate_greeting()

            return CreateConversationResponse(
                conversation_id=conversation.id,
                status=conversation.state.status,
                greeting=greeting,
            )
        except Exception as e:
            logger.exception("Failed to create conversation")
            raise HTTPException(
                status_code=500, detail=f"Failed to create conversation: {e}"
            ) from e

    @router.get("/conversations", response_model=ConversationListResponse)
    async def list_conversations():
        """List all active conversations.

        Returns:
            List of conversation states and total count.
        """
        conversations = await manager.list_all()
        return ConversationListResponse(
            conversations=conversations,
            count=len(conversations),
        )

    @router.get("/conversations/{conversation_id}", response_model=ConversationState)
    async def get_conversation(conversation_id: str):
        """Get conversation details.

        Args:
            conversation_id: Conversation identifier.

        Returns:
            Current conversation state.

        Raises:
            HTTPException: If conversation not found.
        """
        conversation = await manager.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")
        return conversation.state

    @router.post(
        "/conversations/{conversation_id}/message", response_model=SendMessageResponse
    )
    async def send_message(conversation_id: str, request: SendMessageRequest):
        """Send a message to a conversation.

        Processes the user message and returns the bot's complete response.
        Handles streaming internally and returns a single aggregated response.

        Args:
            conversation_id: Conversation identifier.
            request: Message request with text.

        Returns:
            Bot response text, current status, and optional outcome.

        Raises:
            HTTPException: If conversation not found, inactive, or processing fails.
        """
        conversation = await manager.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        if conversation.state.status != ConversationStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="Conversation is not active")

        try:
            response = await conversation.process_message(request.text)
            return SendMessageResponse(
                response=response,
                status=conversation.state.status,
                outcome=conversation.state.outcome,
            )
        except Exception as e:
            logger.exception("Failed to process message")
            raise HTTPException(
                status_code=500, detail=f"Failed to process message: {e}"
            ) from e

    @router.delete("/conversations/{conversation_id}")
    async def end_conversation(conversation_id: str, reason: str = "user_ended"):
        """End a conversation.

        Args:
            conversation_id: Conversation identifier.
            reason: Reason for ending the conversation.

        Returns:
            Status confirmation and conversation ID.

        Raises:
            HTTPException: If conversation not found.
        """
        conversation = await manager.get(conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="Conversation not found")

        conversation.end(reason)
        return {"status": "ended", "conversation_id": conversation_id}

    @router.websocket("/conversations/{conversation_id}/stream")
    async def stream_events(websocket: WebSocket, conversation_id: str):
        """Stream real-time conversation events via WebSocket.

        Provides push-based delivery of events including text chunks, tool calls,
        and tool results. Essential for building responsive UIs with typing indicators.

        Args:
            websocket: WebSocket connection.
            conversation_id: Conversation identifier.

        Why: WebSocket streaming enables real-time UX feedback during long-running
        LLM generations or tool executions, improving perceived responsiveness.
        """
        conversation = await manager.get(conversation_id)
        if not conversation:
            await websocket.close(code=4004, reason="Conversation not found")
            return

        await websocket.accept()

        try:
            while conversation.state.status == ConversationStatus.ACTIVE:
                event = await conversation.get_events(timeout=30.0)
                if event:
                    await websocket.send_json(event)
                else:
                    # Send keepalive to prevent connection timeout
                    await websocket.send_json({"type": "keepalive"})
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected for conversation %s", conversation_id)
        except Exception as e:
            logger.exception("WebSocket error for conversation %s", conversation_id)
            await websocket.close(code=1011, reason=str(e))
        finally:
            await websocket.close()

    return router


def create_webhook_app(
    engine_factory: Callable[[dict[str, Any]], ConversationEngine],
    cleanup_interval: int = 300,
    cleanup_max_age: int = 3600,
) -> FastAPI:
    """Create a complete FastAPI application with webhook endpoints.

    Includes lifecycle management for periodic cleanup of completed conversations.

    Why: Provides a ready-to-use application for simple deployments while still
    allowing advanced users to just use the router for custom applications.

    Args:
        engine_factory: Function that creates a ConversationEngine from context.
        cleanup_interval: Interval in seconds for cleanup task (default: 5 minutes).
        cleanup_max_age: Max age in seconds for completed conversations (default: 1 hour).

    Returns:
        FastAPI application with webhook endpoints and lifecycle management.

    Example:
        ```python
        app = create_webhook_app(my_engine_factory)
        uvicorn.run(app, host="0.0.0.0", port=8000)
        ```
    """
    router = create_webhook_router(engine_factory)
    manager = ConversationManager()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Manage application lifecycle with periodic cleanup."""
        cleanup_task = asyncio.create_task(periodic_cleanup())
        yield
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass

    async def periodic_cleanup():
        """Periodically clean up old completed conversations."""
        while True:
            await asyncio.sleep(cleanup_interval)
            removed = await manager.cleanup_completed(max_age_seconds=cleanup_max_age)
            if removed > 0:
                logger.info("Cleaned up %d completed conversations", removed)

    app = FastAPI(
        title="RAW Webhook Transport",
        description="HTTP/WebSocket transport for RAW Platform conversations",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(router)

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint for load balancers."""
        return {"status": "healthy"}

    return app
