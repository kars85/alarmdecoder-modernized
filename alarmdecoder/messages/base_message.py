# alarmdecoder/messages/message_base.py
from dataclasses import dataclass
from datetime import datetime


@dataclass
class BaseMessage:
    """
    Base class for all alarmdecoder messages.
    """
    raw: str | None = None
    timestamp: datetime | None = None

    # Change this:
    # def __init__(self):
    #     ...

    # To this (allow data to be passed, defaulting to None):
    def __init__(self, data=None):
        # Your existing __init__ logic here...
        # Make sure you actually *use* the data argument if needed for parsing
        # e.g., self.raw = data
        #      if data:
        #          self.parse(data) # Or similar
        pass  # Replace pass with actual logic

    def dict(self) -> dict:
        return {
            "raw": self.raw,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
