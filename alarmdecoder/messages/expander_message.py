from dataclasses import dataclass
from typing import Optional
from alarmdecoder.messages.base_message import BaseMessage
from alarmdecoder.util.exceptions import InvalidMessageError
from alarmdecoder.logger import get_logger

logger = get_logger(__name__)


@dataclass
class ExpanderMessage(BaseMessage):
    address: Optional[int] = None
    type: Optional[int] = None
    channel: Optional[int] = None
    value: Optional[int] = None

    ZONE = 0
    RELAY = 1

    def __post_init__(self):
        if self.raw:
            self._parse_message(self.raw)

    def _parse_message(self, data):
        try:
            header, values = data.split(':')
            address, channel, value = values.split(',')
            self.address = int(address)
            self.channel = int(channel)
            self.value = int(value)

            if header == '!EXP':
                self.type = ExpanderMessage.ZONE
            elif header == '!REL':
                self.type = ExpanderMessage.RELAY
            else:
                raise InvalidMessageError(f"Unknown expander message header: {data}")

            logger.debug(f"Expander: addr={self.address}, chan={self.channel}, type={self.type}, value={self.value}")

        except ValueError:
            raise InvalidMessageError(f"Received invalid expander message: {data}")