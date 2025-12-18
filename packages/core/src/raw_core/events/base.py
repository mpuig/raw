"""Base event class for RAW Platform."""

from pydantic import BaseModel


class Event(BaseModel):
    """Base for all platform events. Frozen for safe concurrent handling."""

    model_config = {"frozen": True}
