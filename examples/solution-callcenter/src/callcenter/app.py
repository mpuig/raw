"""FastAPI application for call center solution.

Creates the main application with all routes, middleware, and integrations.
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from raw_bot import BotConfig, ContextManager, ConversationEngine
from raw_core.protocols import ToolExecutor
from raw_server import create_app

from callcenter.config import CallCenterConfig
from callcenter.prompts import SYSTEM_PROMPT
from callcenter.skills import TOOLS_REGISTRY, TOOLS_SCHEMA
from callcenter.workflows.post_call import create_post_call_workflow

logger = logging.getLogger(__name__)


class CallCenterToolExecutor(ToolExecutor):
    """Tool executor for call center skills.

    Why: Implements the ToolExecutor protocol to integrate skills with
    the conversation engine.
    """

    def __init__(self, tools_registry: dict[str, Any]):
        """Initialize with tools registry.

        Args:
            tools_registry: Mapping of tool names to functions
        """
        self.tools = tools_registry

    async def execute(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a tool by name with given arguments.

        Args:
            name: Tool name
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            KeyError: If tool not found

        Why: Provides async interface for tool execution with error handling.
        """
        if name not in self.tools:
            logger.error(f"Tool not found: {name}")
            return {
                "success": False,
                "error": "tool_not_found",
                "message": f"Tool '{name}' does not exist.",
            }

        try:
            # Execute tool (convert async if needed)
            tool_fn = self.tools[name]
            result = tool_fn(**arguments)

            # Handle async tools
            if hasattr(result, "__await__"):
                result = await result

            return result

        except Exception as e:
            logger.exception(f"Tool execution failed: {name}", extra={"error": str(e)})
            return {
                "success": False,
                "error": "execution_failed",
                "message": f"Tool execution failed: {str(e)}",
            }


def create_conversation_engine(config: CallCenterConfig) -> ConversationEngine:
    """Create conversation engine with skills and configuration.

    Args:
        config: Call center configuration

    Returns:
        Configured ConversationEngine

    Why: Factory function for creating the conversation engine with all
    dependencies properly injected.
    """
    # Create bot configuration
    bot_config = BotConfig(
        name=config.bot.name,
        system_prompt=SYSTEM_PROMPT,
        model=config.llm.model,
        temperature=config.llm.temperature,
        greeting_first=config.bot.greeting_first,
    )

    # Create LLM driver (in production, use integration_llm.LiteLLMDriver)
    from integration_llm import LiteLLMDriver

    driver = LiteLLMDriver()

    # Create tool executor
    executor = CallCenterToolExecutor(TOOLS_REGISTRY)

    # Create context manager
    context = ContextManager()

    # Create engine
    engine = ConversationEngine(
        config=bot_config,
        driver=driver,
        executor=executor,
        context=context,
        tools_schema=TOOLS_SCHEMA,
    )

    return engine


def create_callcenter_app(config: CallCenterConfig) -> FastAPI:
    """Create FastAPI application for call center solution.

    Args:
        config: Call center configuration

    Returns:
        Configured FastAPI application

    Why: Creates production-ready application with all routes, middleware,
    and integrations configured.
    """

    async def startup():
        """Startup tasks."""
        logger.info("Call center application starting")

        # Initialize conversation engine
        app.state.engine = create_conversation_engine(config)

        # Initialize post-call workflow
        app.state.post_call_workflow = create_post_call_workflow(
            config.workflows.post_call.model_dump()
        )

        logger.info("Call center application ready")

    async def shutdown():
        """Shutdown tasks."""
        logger.info("Call center application shutting down")

    # Create base app with health checks and middleware
    app = create_app(
        config=config.server,
        startup_tasks=[startup],
        shutdown_tasks=[shutdown],
        enable_telemetry=config.telemetry.enabled,
    )

    # Register call center routes
    register_voice_routes(app, config)
    register_webhook_routes(app, config)

    return app


def register_voice_routes(app: FastAPI, config: CallCenterConfig) -> None:
    """Register voice-related routes (Twilio integration).

    Args:
        app: FastAPI application
        config: Call center configuration

    Why: Separates route registration for better organization and testability.
    """

    @app.post(config.twilio.webhook_path, tags=["voice"])
    async def twilio_voice_webhook(request: Request):
        """Handle incoming Twilio voice calls.

        This endpoint receives Twilio's webhook when a call comes in.
        It returns TwiML instructions to connect the call to the voice pipeline.
        """
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        from_number = form_data.get("From")
        to_number = form_data.get("To")

        logger.info(
            "Incoming call",
            extra={"call_sid": call_sid, "from": from_number, "to": to_number},
        )

        # In production, return TwiML to connect to voice pipeline
        # For this example, return basic TwiML
        twiml = """<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>Thank you for calling Acme Corporation. Please wait while we connect you.</Say>
    <Connect>
        <Stream url="wss://your-domain.com/voice/stream" />
    </Connect>
</Response>"""

        return JSONResponse(
            content={"twiml": twiml},
            media_type="application/xml",
        )

    @app.post(config.twilio.status_callback_path, tags=["voice"])
    async def twilio_status_callback(request: Request):
        """Handle Twilio call status updates.

        Receives updates about call status (completed, failed, etc.)
        and triggers post-call workflow if needed.
        """
        form_data = await request.form()
        call_sid = form_data.get("CallSid")
        call_status = form_data.get("CallStatus")
        call_duration = form_data.get("CallDuration")

        logger.info(
            "Call status update",
            extra={
                "call_sid": call_sid,
                "status": call_status,
                "duration": call_duration,
            },
        )

        # If call completed, trigger post-call workflow
        if call_status == "completed":
            # In production, fetch conversation data and trigger workflow
            call_data = {
                "call_sid": call_sid,
                "duration": int(call_duration or 0),
                "outcome": "completed",
                "sentiment": 0.8,  # Would be calculated from transcript
                "transcript": [],
            }

            # Trigger workflow asynchronously
            workflow = app.state.post_call_workflow
            # In production, run in background task or queue
            # await workflow.run(call_data)

        return JSONResponse(content={"status": "received"})


def register_webhook_routes(app: FastAPI, config: CallCenterConfig) -> None:
    """Register webhook routes for text-based conversations.

    Args:
        app: FastAPI application
        config: Call center configuration

    Why: Provides HTTP/WebSocket interface for integrating with external
    systems (web chat, SMS, etc.).
    """
    from pydantic import BaseModel

    class CreateConversationRequest(BaseModel):
        customer_id: str | None = None
        phone: str | None = None
        email: str | None = None
        context: dict[str, Any] = {}

    class SendMessageRequest(BaseModel):
        text: str

    @app.post("/webhook/conversation", tags=["webhook"])
    async def create_conversation(request: CreateConversationRequest):
        """Create a new text-based conversation.

        Use this endpoint to start a conversation from external systems
        (web chat, SMS, etc.).
        """
        # In production, create conversation session and return ID
        conversation_id = f"conv_{request.customer_id or 'anonymous'}"

        logger.info(
            "Conversation created",
            extra={"conversation_id": conversation_id, "customer_id": request.customer_id},
        )

        return {
            "conversation_id": conversation_id,
            "status": "active",
        }

    @app.post("/webhook/conversation/{conversation_id}/message", tags=["webhook"])
    async def send_message(conversation_id: str, request: SendMessageRequest):
        """Send a message in an existing conversation.

        Returns the AI agent's response.
        """
        # In production, retrieve conversation session and process message
        logger.info(
            "Message received",
            extra={"conversation_id": conversation_id, "text": request.text[:50]},
        )

        # Mock response
        return {
            "conversation_id": conversation_id,
            "response": "Thank you for your message. How can I help you today?",
        }


# Additional utility routes


def register_admin_routes(app: FastAPI) -> None:
    """Register admin/management routes.

    Why: Provides endpoints for managing the call center system
    (viewing active calls, agent status, etc.).
    """

    @app.get("/admin/calls", tags=["admin"])
    async def list_active_calls():
        """List active calls."""
        # In production, query active call sessions
        return {"active_calls": []}

    @app.get("/admin/stats", tags=["admin"])
    async def get_statistics():
        """Get call center statistics."""
        # In production, query metrics database
        return {
            "total_calls_today": 0,
            "average_duration": 0,
            "average_satisfaction": 0.0,
        }
