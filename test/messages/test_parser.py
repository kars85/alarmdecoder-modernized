import pytest

from alarmdecoder.messages import ExpanderMessage
from alarmdecoder.messages.panel_message import AdemcoCIDEvent, ADEMCOContactID, LRRMessage, PanelMessage
from alarmdecoder.messages.parser import parse_message
from alarmdecoder.util.exceptions import InvalidMessageError


def test_parse_panel_message():
    data = "!READY STAY CHIME BAT"
    msg = parse_message(data)
    assert isinstance(msg, PanelMessage)
    assert msg.ready
    assert msg.chime_on
    assert msg.battery_low
    assert msg.armed_home
    assert msg.armed_away is False  # Not present in message



def test_parse_expander_message():
    data = "!EXP:18,0,00"
    msg = parse_message(data)
    assert isinstance(msg, ExpanderMessage)
    assert msg.address == 18  # not '18'
    assert msg.channel == 0
    assert msg.value == 0


def _parse_message(self, data):
    try:
        _, values = data.split(':')
        parts = values.split(',')

        self.serial_number = parts[0]
        self.loop = parts[1]
        self.battery = parts[2]
        self.supervision = parts[3]
        self.value = parts[4]
    except ValueError:
        raise InvalidMessageError(f"Received invalid RF message: {data}")




def test_parse_lrr_message():
    data = "!LRR:MockEvent"
    msg = parse_message(data)
    assert isinstance(msg, LRRMessage)


def test_parse_ademco_cid():
    data = "!CID:601,1,02,456,7"
    msg = parse_message(data)
    assert isinstance(msg, ADEMCOContactID)
    assert isinstance(msg.event, AdemcoCIDEvent)
    assert msg.event.code == "601"
    assert msg.event.zone == "456"

def test_parse_invalid():
    with pytest.raises(InvalidMessageError):
        parse_message("UNKNOWN")