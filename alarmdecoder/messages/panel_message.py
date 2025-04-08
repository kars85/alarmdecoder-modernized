# alarmdecoder/messages/panel_message.py
from dataclasses import dataclass
from datetime import datetime

from alarmdecoder.logger import get_logger
from alarmdecoder.messages.base_message import BaseMessage

logger = get_logger(__name__)


@dataclass
class PanelMessage(BaseMessage):
    """
    A general panel message with possible extensions.
    """
    text: str | None = None
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
    numeric_code: str | None = None
    mask: int | None = None
    beeps: int | None = None
    cursor_location: int | None = None
    panel_type: str | None = None

    def dict(self) -> dict:
        base = super().dict()
        base.update(self.__dict__)
        return base


@dataclass
class LRRMessage(BaseMessage):
    """
    Represents an LRR (Long Range Radio) message.
    """
    event_type: str | None = None
    partition: str | None = None
    timestamp: datetime | None = None

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
    event: AdemcoCIDEvent | None = None

    def dict(self):
        base = super().dict()
        base.update({
            "event": self.event.__dict__ if self.event else None
        })
        return base
