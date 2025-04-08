from unittest.mock import MagicMock

from alarmdecoder.handlers.config_io import get_config, get_config_string, save_config
from alarmdecoder.handlers.versioning import handle_config, handle_version


def test_handle_version_sets_version_data():
    # Create a mock that has the necessary attributes and methods
    device = MagicMock()
    device._version_number = None
    device._version_flags = None
    # Mock the event handler
    device.on_version = MagicMock()

    # Test with a release version
    data = "!1.2.3r"
    handle_version(device, data)

    # Assertions based on actual implementation
    assert device._version_number == "1.2.3r"
    assert "RELEASE" in device._version_flags
    device.on_version.fire.assert_called_once_with(device)

    # Reset and test with beta
    device.reset_mock()
    device._version_flags = set()
    data = "!1.2.3b"
    handle_version(device, data)

    assert device._version_number == "1.2.3b"
    assert "BETA" in device._version_flags


def test_handle_config_sets_configbits():
    device = MagicMock()
    device._configbits = "ORIGINAL"
    data = "!1234"

    handle_config(device, data)
    # assuming handle_config sets device._configbits = data[1:]
    assert device._configbits == "1234"


def test_save_and_restore_config():
    device = MagicMock()
    device._version_number = "1.0.0"
    device._configbits = "AABBCC"

    save_config(device)

    # reset values
    device._version_number = ""
    device._configbits = ""

    get_config(device)

    assert device._version_number == "1.0.0"
    assert device._configbits == "AABBCC"


def test_get_config_string_format():
    device = MagicMock()
    device.address = 18
    device.configbits = 0xFF
    device.address_mask = 0xFFFFFFFF
    device.emulate_zone = [True, False, True, False, True]
    device.emulate_relay = [False, True, False, True]
    device.emulate_lrr = True
    device.deduplicate = False
    device.mode = "ADEMCO"
    device.emulate_com = True
    device.PANEL_TYPES = {"ADEMCO": "ADEMCO"}

    config_str = get_config_string(device)

    assert "ADDRESS=18" in config_str
    assert "CONFIGBITS=ff" in config_str
    assert "LRR=Y" in config_str
    assert "COM=Y" in config_str