"""Webhook transport for RAW Platform.

Provides FastAPI-based HTTP/WebSocket endpoints for integrating RAW bots
with external systems via webhooks. Decouples conversation logic from
transport layer, enabling stateless webhook handling.
"""

__version__ = "0.1.0"

from transport_webhook.handlers import (
    ConversationManager,
    ConversationState,
    ConversationStatus,
    WebhookHandler,
)
from transport_webhook.router import (
    CreateConversationRequest,
    CreateConversationResponse,
    SendMessageRequest,
    SendMessageResponse,
    create_webhook_app,
    create_webhook_router,
)

__all__ = [
    # Handlers
    "ConversationManager",
    "ConversationState",
    "ConversationStatus",
    "WebhookHandler",
    # Router
    "CreateConversationRequest",
    "CreateConversationResponse",
    "SendMessageRequest",
    "SendMessageResponse",
    "create_webhook_app",
    "create_webhook_router",
]
