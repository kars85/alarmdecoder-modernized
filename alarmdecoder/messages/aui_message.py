"""
Message representations received from the panel through the `AlarmDecoder`_ (AD2)
devices.

:py:class:`AUIMessage`: Message received destined for an AUI keypad.

.. _AlarmDecoder: http://www.alarmdecoder.com

.. moduleauthor:: Scott Petersen <scott@nutech.com>
"""


from alarmdecoder.logger import get_logger
from alarmdecoder.messages.base_message import BaseMessage
from alarmdecoder.util.exceptions import InvalidMessageError

# Initialize the logger
logger = get_logger(__name__)


class AUIMessage(BaseMessage):
    """
    Represents a message destined for an AUI keypad.
    """

    value: str | None = None  # Raw value of the AUI message
    aui_id: str | None = None  # AUI ID
    msg_type: str | None = None  # Message type
    line: str | None = None  # Line number
    text: str | None = None  # Message text

    def __init__(self, data: str | None = None):
        """
        Constructor for AUIMessage.

        :param data: Raw message data to parse.
        :type data: Optional[str]
        """
        super().__init__()  # Initialize base class
        if data is not None:
            try:
                self._parse_message(data)
            except InvalidMessageError as e:
                logger.error(f"Failed to parse AUI message: {data}. Error: {str(e)}")
                raise e  # Re-raise exception after logging

    def _parse_message(self, data: str) -> None:
        """
        Parses the raw AUI message data and populates the AUIMessage attributes.

        Expected data format (example):
        "AUI<ID>,<msgtype>,<line>,<text>"

        :param data: Raw message string to parse.
        :type data: str
        :raises InvalidMessageError: If the message format is invalid.
        """
        try:
            logger.debug(f"Parsing AUI message: {data}")
            # Split the data into components
            parts = data.split(",")
            if len(parts) < 4:
                raise InvalidMessageError(f"Malformed AUI message: {data}")

            self.aui_id = parts[0].strip()  # Extract AUI ID
            self.msg_type = parts[1].strip()  # Extract message type
            self.line = parts[2].strip()  # Extract line number
            self.text = ",".join(parts[3:]).strip()  # Combine remaining parts as text

            # Set the raw data as the message's value
            self.value = data

            logger.debug(
                f"Parsed AUIMessage successfully: "
                f"aui_id={self.aui_id}, msg_type={self.msg_type}, "
                f"line={self.line}, text={self.text}"
            )

        except Exception as e:
            logger.error(f"Error parsing AUI message: {data}. Exception: {str(e)}")
            raise InvalidMessageError(
                f"Unable to parse AUI message. Invalid data: {data}"
            ) from e

    def dict(self) -> dict[str, str | None]:
        """
        Returns the AUIMessage as a dictionary.

        :return: Dictionary representation of the message.
        :rtype: Dict[str, Optional[str]]
        """
        return {
            "value": self.value,
            "aui_id": self.aui_id,
            "msg_type": self.msg_type,
            "line": self.line,
            "text": self.text,
            "raw": self.raw,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
