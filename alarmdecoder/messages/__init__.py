from .aui_message import AUIMessage
from .expander_message import ExpanderMessage
from .lrr import LRRMessage
from .rf_message import RFMessage


def __init__(self, data: str | None = None, address=None, type=None, channel=None, value=None):
    super().__init__(data)
    self.address = address
    self.type = type
    self.channel = channel
    self.value = value
    if data:
        self._parse_message(data)


__all__ = ['ExpanderMessage', 'LRRMessage', 'RFMessage', 'AUIMessage']
