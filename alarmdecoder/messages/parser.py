# alarmdecoder/messages/parser.py

from typing import Optional
import re
from alarmdecoder.util.exceptions import InvalidMessageError
from alarmdecoder.messages.panel_message import (
    PanelMessage,
    LRRMessage,
    ADEMCOContactID,
    AdemcoCIDEvent
)
from alarmdecoder.messages import ExpanderMessage, RFMessage, AUIMessage
from alarmdecoder.messages.base_message import BaseMessage
from alarmdecoder.logger import get_logger

logger = get_logger(__name__)


def parse_message(data: str) -> BaseMessage:
    """
    Entry point for message parsing. Detects type and delegates to handler.
    """
    logger.debug(f"Received message: {data}")

    try:
        if data.startswith("!AUI:"):
            logger.debug(f"Identified as AUI message")
            return parse_aui(data)
        elif data.startswith("!EXP:"):
            logger.debug(f"Identified as expander message")
            return parse_expander(data)
        elif data.startswith("!RFX:"):
            logger.debug(f"Identified as RF message")
            return parse_rf(data)
        elif data.startswith("!CID:"):
            logger.debug(f"Identified as ADEMCO CID message")
            return parse_ademco_cid(data)
        elif data.startswith("!LRR:"):
            logger.debug(f"Identified as LRR message")
            return parse_lrr(data)
        elif data.startswith("!"):
            logger.debug(f"Identified as panel message")
            return parse_panel(data)
        else:
            raise InvalidMessageError(f"Unknown message format: {data}")
    except Exception as e:
        logger.warning(f"Failed to parse message: {data}", exc_info=True)
        raise


def parse_panel(data: str) -> PanelMessage:
    """Parses standard panel messages."""
    try:
        logger.debug(f"Parsing panel message: {data}")
        text = data.strip()[1:]  # Removes the leading '!'
        return PanelMessage(
            raw=data,
            text=text,
            alarm_event_occurred="ALARM" in text,
            alarm_sounding="SOUND" in text,
            ready="READY" in text,
            armed_away="AWAY" in text,
            armed_home="STAY" in text,
            chime_on="CHIME" in text,
            bypass="BYPASS" in text,
            ac_power="AC LOSS" not in text,
            battery_low="BAT" in text,
            fire_alarm="FIRE" in text,
            check_zone="CHECK" in text,
            programming_mode="PROGRAM" in text,
            system_fault="FAULT" in text,
            zone_bypassed="BYPASS" in text
        )
    except Exception as ex:
        logger.error(f"Failed to parse panel message: {data}")
        raise InvalidMessageError(f"Failed to parse panel message: {data}") from ex


def parse_lrr(data: str) -> LRRMessage:
    """Parses Long Range Radio messages."""
    try:
        logger.debug(f"Parsing LRR message: {data}")
        # Future: Extract event_type, partition, timestamp, etc.
        return LRRMessage(raw=data)
    except Exception as ex:
        logger.error(f"Failed to parse LRR message: {data}")
        raise InvalidMessageError(f"Failed to parse LRR message: {data}") from ex


def parse_ademco_cid(data: str) -> ADEMCOContactID:
    """Parses Contact ID messages, if detected."""
    try:
        logger.debug(f"Parsing ADEMCO CID message: {data}")
        # ⚠️ Dummy regex — replace with true ADEMCO CID format
        match = re.search(r"(\d{3}),(\d),(\d{2}),(\d{3}),(\d)", data)
        if not match:
            logger.warning(f"ADEMCO CID format mismatch: {data}")
            raise InvalidMessageError(f"Could not parse ADEMCO CID: {data}")

        event = AdemcoCIDEvent(
            code=match.group(1),
            qualifier=match.group(2),
            group=match.group(3),
            zone=match.group(4),
            partition=match.group(5)
        )
        return ADEMCOContactID(raw=data, event=event)
    except Exception as ex:
        if not isinstance(ex, InvalidMessageError):
            logger.error(f"Failed to parse ADEMCO CID message: {data}")
            raise InvalidMessageError(f"Failed to parse ADEMCO CID message: {data}") from ex
        raise


def parse_expander(data: str) -> ExpanderMessage:
    """
    Parses Expander (relay or zone expander) messages.
    """
    try:
        logger.debug(f"Parsing expander message: {data}")
        # Example message: !EXP:18,Z,00
        parts = data.strip()[5:].split(",")

        if len(parts) < 3:
            logger.warning(f"Expander message has insufficient parts: {data}")
            raise InvalidMessageError(f"Expander message format invalid (expected at least 3 parts): {data}")

        address = parts[0]
        msg_type = parts[1]
        channel = parts[2]

        return ExpanderMessage(
            raw=data,
            address=int(address) if address and address.strip() else None,
            type=int(msg_type) if msg_type and msg_type.strip() else None,
            channel=int(channel) if channel and channel.strip() else None
        )
    except Exception as ex:
        if not isinstance(ex, InvalidMessageError):
            logger.error(f"Failed to parse expander message: {data}")
            raise InvalidMessageError(f"Failed to parse expander message: {data}") from ex
        raise


def parse_rf(data: str) -> RFMessage:
    """
    Parses RF messages from wireless sensors.
    """
    try:
        logger.debug(f"Parsing RF message: {data}")
        # Example message: !RFX:00000001,01,AA,00,C
        parts = data.strip()[5:].split(",")

        if len(parts) < 5:
            logger.warning(f"RF message has insufficient parts: {data}")
            raise InvalidMessageError(f"RF message format invalid (expected 5 parts): {data}")

        serial_number = parts[0]
        loop = parts[1]
        battery = parts[2]
        supervision = parts[3]
        value = parts[4]

        # Convert loop string to a list of booleans
        loop_converted = [c == '1' for c in loop] if isinstance(loop, str) else loop

        # Convert battery and supervision strings to booleans
        battery_converted = None
        if battery is not None:
            if isinstance(battery, str):
                battery_converted = battery.lower() in ('true', 'yes', '1', 'on', 't', 'y')
            else:
                battery_converted = bool(battery)

        supervision_converted = None
        if supervision is not None:
            if isinstance(supervision, str):
                supervision_converted = supervision.lower() in ('true', 'yes', '1', 'on', 't', 'y')
            else:
                supervision_converted = bool(supervision)

        # Convert value to integer
        value_converted = int(value) if value and value.strip() else None

        return RFMessage(
            raw=data,
            serial_number=serial_number,
            loop=loop_converted,
            battery=battery_converted,
            supervision=supervision_converted,
            value=value_converted
        )
    except Exception as ex:
        if not isinstance(ex, InvalidMessageError):
            logger.error(f"Failed to parse RF message: {data}")
            raise InvalidMessageError(f"Failed to parse RF message: {data}") from ex
        raise


def parse_aui(data: str) -> AUIMessage:
    """
    Parses AUI (touchscreen/keypad) messages.
    """
    try:
        logger.debug(f"Parsing AUI message: {data}")
        # Example: !AUI:012345,80,1,Line1 Text,Line2 Text
        if not data.startswith("!AUI:"):
            logger.warning(f"Invalid AUI message prefix: {data}")
            raise InvalidMessageError(f"AUI message must start with '!AUI:': {data}")

        parts = data.strip()[5:].split(",", 4)

        if len(parts) < 3:
            logger.warning(f"AUI message has insufficient parts: {data}")
            raise InvalidMessageError(f"AUI message format invalid (expected at least 3 parts): {data}")

        aui_id = parts[0]
        msg_type = parts[1]
        line = parts[2]
        text1 = parts[3] if len(parts) > 3 else ""
        text2 = parts[4] if len(parts) > 4 else ""

        message = AUIMessage(data)
        message.aui_id = aui_id
        message.msg_type = msg_type
        message.line = line
        message.text = text1  # Use text1 directly
        return message
    except Exception as ex:
        if not isinstance(ex, InvalidMessageError):
            logger.error(f"Failed to parse AUI message: {data}")
            raise InvalidMessageError(f"Failed to parse AUI message: {data}") from ex
        raise