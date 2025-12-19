"""Call Center Solution - AI-powered customer support built on RAW Platform.

This package provides a complete, production-ready call center solution with:
- Real-time voice conversations (Deepgram STT + ElevenLabs TTS)
- Twilio integration for phone calls
- Customer and order management skills
- Post-call automation workflows
- FastAPI server with health checks and telemetry
"""

__version__ = "0.1.0"

from callcenter.config import CallCenterConfig
from callcenter.prompts import ESCALATION_PROMPT, GREETING_MESSAGE, SYSTEM_PROMPT

__all__ = [
    "CallCenterConfig",
    "SYSTEM_PROMPT",
    "GREETING_MESSAGE",
    "ESCALATION_PROMPT",
]
