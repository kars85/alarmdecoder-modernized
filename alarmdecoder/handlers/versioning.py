# alarmdecoder/handlers/versioning.py
from alarmdecoder.messages.parser import parse_message
from alarmdecoder.util.exceptions import InvalidMessageError
from alarmdecoder.logger import get_logger
logger = get_logger(__name__)

def handle_version(device, data):
    if data.startswith("!"):
        version_data = data[1:].strip()
        logger.info(f"Version info received: {data.strip()}")
        device._version_number = version_data
        device._version_flags = set()

        if version_data.endswith("a"):
            device._version_flags.add("ALPHA")
        elif version_data.endswith("b"):
            device._version_flags.add("BETA")
        elif version_data.endswith("r"):
            device._version_flags.add("RELEASE")

        device.on_version.fire(device)


def handle_config(device, data):
    if data.startswith("!"):
        config_data = data[1:].strip()
        device._configbits = config_data
        logger.info(f"Config info received: {data.strip()}")
        logger.debug(f"Parsed config bits: {device._configbits}")
        device.on_config_received.fire(device)
    
def handle_on_open(decoder, sender, *args, **kwargs):
    """
    Handler for when the device is opened.
    Triggers the on_open event and sends version query.
    """
    decoder.on_open.fire(decoder)
    logger.info("Device opened, sending version query")
    decoder.send("!V")

def handle_on_close(decoder, *args, **kwargs):
    """
    Handles device close event cleanup.
    """
    logger.info("Device closing, cleaning up state")
    decoder._version = None
    decoder._version_flags = None
    decoder._address = None
    decoder._configbits = None
    decoder._address_mask = None
    decoder._emulate_zone = [False] * 8
    decoder._emulate_relay = [False] * 4
    decoder._emulate_lrr = False
    decoder._deduplicate = False
    decoder._emulate_com = False
    decoder._mode = None

    decoder.on_close.fire(decoder)

def handle_on_read(decoder, data, *args, **kwargs):
    """
    Handles incoming raw data from the device.
    """
    decoder.on_read.fire(decoder, data)
    
    # Log boot messages or other special messages that start with !
    if data.startswith("!"):
        if not (data.startswith("!CONFIG") or data.startswith("!VER")):
            logger.info(f"Boot/special message received: {data.strip()}")

    try:
        message = parse_message(data)
        decoder._handle_message(message)
    except InvalidMessageError as err:
        decoder.logger.warning("Invalid message received: %s", data)
    except Exception as err:
        decoder.logger.exception("Unexpected error in _on_read: %s", err)

def handle_on_write(decoder, data, *args, **kwargs):
    """
    Handles write events for logging/debugging.
    """
    # Log configuration commands
    if data.startswith("!C"):
        logger.info(f"Sending configuration command: {data.strip()}")
    elif data.startswith("!V"):
        logger.debug("Sending version query")
    
    decoder.on_write.fire(decoder, data)

