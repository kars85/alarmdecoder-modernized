from dataclasses import dataclass

from alarmdecoder.logger import get_logger
from alarmdecoder.messages.base_message import BaseMessage
from alarmdecoder.util.exceptions import InvalidMessageError

logger = get_logger(__name__)


@dataclass(init=False)  # Disable auto-generated init
class ExpanderMessage(BaseMessage):
    address: int | None = None
    type: int | None = None
    channel: int | None = None
    value: int | None = None

    ZONE = 0
    RELAY = 1

    def __init__(self, data: str | None = None, address=None, type=None, channel=None, value=None):
        super().__init__(data)
        self.address = address
        self.type = type
        self.channel = channel
        self.value = value
        if data:
            self._parse_message(data)

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
