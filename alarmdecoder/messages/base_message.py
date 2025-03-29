# alarmdecoder/messages/message_base.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from alarmdecoder.util.exceptions import InvalidMessageError

@dataclass
class BaseMessage:
    """
    Base class for all alarmdecoder messages.
    """
    raw: Optional[str] = None
    timestamp: Optional[datetime] = None

    def dict(self) -> dict:
        return {
            "raw": self.raw,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
