from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from alarmdecoder.messages.base_message import BaseMessage
from alarmdecoder.util.exceptions import InvalidMessageError
from alarmdecoder.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RFMessage(BaseMessage):
    serial_number: Optional[str] = None
    value: Optional[int] = None
    battery: Optional[bool] = None
    supervision: Optional[bool] = None
    loop: List[bool] = field(default_factory=lambda: [False for _ in range(4)])

    def __post_init__(self):
        if self.raw:
            self._parse_message(self.raw)

    def _parse_message(self, data):
        try:
            _, values = data.split(':')
            self.serial_number, value_hex = values.split(',')
            self.value = int(value_hex, 16)

            def is_bit_set(b):
                return self.value & (1 << (b - 1)) > 0

            self.battery = is_bit_set(2)
            self.supervision = is_bit_set(3)
            self.loop[2] = is_bit_set(5)
            self.loop[1] = is_bit_set(6)
            self.loop[3] = is_bit_set(7)
            self.loop[0] = is_bit_set(8)

            logger.debug(
                f"RF parsed: serial={self.serial_number}, battery={self.battery}, supervision={self.supervision}, loops={self.loop}")

        except ValueError:
            raise InvalidMessageError(f"Received invalid RF message: {data}")