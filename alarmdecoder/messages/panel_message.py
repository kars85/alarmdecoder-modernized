# alarmdecoder/messages/panel_message.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from alarmdecoder.messages.base_message import BaseMessage
from alarmdecoder.util.exceptions import InvalidMessageError
from alarmdecoder.logger import get_logger
logger = get_logger(__name__)


@dataclass
class PanelMessage(BaseMessage):
    """
    A general panel message with possible extensions.
    """
    text: Optional[str] = None
    alarm_event_occurred: bool = False
    alarm_sounding: bool = False
    ready: bool = False
    armed_away: bool = False
    armed_home: bool = False
    chime_on: bool = False
    bypass: bool = False
    ac_power: bool = True
    battery_low: bool = False
    fire_alarm: bool = False
    check_zone: bool = False
    programming_mode: bool = False
    system_fault: bool = False
    zone_bypassed: bool = False
    numeric_code: Optional[str] = None
    mask: Optional[str] = None
    beeps: Optional[int] = None
    cursor_location: Optional[int] = None
    panel_type: Optional[str] = None

    def dict(self) -> dict:
        base = super().dict()
        base.update(self.__dict__)
        return base


@dataclass
class LRRMessage(BaseMessage):
    """
    Represents an LRR (Long Range Radio) message.
    """
    event_type: Optional[str] = None
    partition: Optional[str] = None
    timestamp: Optional[datetime] = None

    def dict(self):
        base = super().dict()
        base.update({
            "event_type": self.event_type,
            "partition": self.partition,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        })
        return base


@dataclass
class AdemcoCIDEvent:
    """
    Represents a parsed ADEMCO Contact ID event.
    """
    code: str
    qualifier: str
    group: str
    zone: str
    partition: str


@dataclass
class ADEMCOContactID(LRRMessage):
    """
    Specialized LRR message for ADEMCO Contact ID format.
    """
    event: Optional[AdemcoCIDEvent] = None

    def dict(self):
        base = super().dict()
        base.update({
            "event": self.event.__dict__ if self.event else None
        })
        return base