"""
Message representations received from the panel through the `AlarmDecoder`_ (AD2)
devices.

:py:class:`AUIMessage`: Message received destined for an AUI keypad.

.. _AlarmDecoder: http://www.alarmdecoder.com

.. moduleauthor:: Scott Petersen <scott@nutech.com>
"""

from alarmdecoder.messages.base_message import BaseMessage
from alarmdecoder.util.exceptions import InvalidMessageError
from alarmdecoder.logger import get_logger
logger = get_logger(__name__)
from typing import Optional

class AUIMessage(BaseMessage):
    """
    Represents a message destined for an AUI keypad.
    """
    value: Optional[str] = None
    """Raw value of the AUI message"""
    aui_id: Optional[str] = None
    """AUI ID"""
    msg_type: Optional[str] = None
    """Message type"""
    line: Optional[str] = None
    """Line number"""
    text: Optional[str] = None
    """Message text"""
    
    def __init__(self, data=None):
        """
        Constructor
        :param data: message data to parse
        :type data: string
        """
        BaseMessage.__init__(self, data)
        if data is not None:
            self._parse_message(data)