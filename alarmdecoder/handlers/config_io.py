# alarmdecoder/handlers/config_io.py
from alarmdecoder.logger import get_logger

logger = get_logger(__name__)


def get_config_string(device):
    """
    Build a configuration string that's compatible with the AlarmDecoder configuration
    command from the current values in the object.
    """
    config_entries = []

    config_entries.append(('ADDRESS', str(device.address)))
    config_entries.append(('CONFIGBITS', f"{device.configbits:x}"))
    config_entries.append(('MASK', f"{device.address_mask:x}"))
    config_entries.append(('EXP', ''.join(['Y' if z else 'N' for z in device.emulate_zone])))
    config_entries.append(('REL', ''.join(['Y' if r else 'N' for r in device.emulate_relay])))
    config_entries.append(('LRR', 'Y' if device.emulate_lrr else 'N'))
    config_entries.append(('DEDUPLICATE', 'Y' if device.deduplicate else 'N'))

    mode_str = next((k for k, v in device.PANEL_TYPES.items() if v == device.mode), "ADEMCO")
    config_entries.append(('MODE', mode_str))
    config_entries.append(('COM', 'Y' if device.emulate_com else 'N'))

    config_string = '&'.join(['='.join(t) for t in config_entries])
    logger.debug(f"Generated config string: {config_string}")

    return config_string


def save_config(device):
    """
    Captures the current version and config state.
    """
    device._saved_version = device._version_number
    device._saved_config = device._configbits
    logger.debug(f"Saved config state: version={device._saved_version}, config={device._saved_config}")


def get_config(device):
    """
    Restores the saved config and triggers event.
    """
    device._version_number = getattr(device, "_saved_version", "")
    device._configbits = getattr(device, "_saved_config", "")
    logger.debug(f"Restored config state: version={device._version_number}, config={device._configbits}")
    device.on_config_received.fire(device)
