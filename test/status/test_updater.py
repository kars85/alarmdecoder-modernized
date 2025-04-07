import pytest
from unittest.mock import MagicMock
from alarmdecoder.status import updater

class MockDevice:
    def __init__(self):
        self._ready = False
        self._armed_away = False
        self._armed_home = False
        self.on_ready_changed = MagicMock()
        self.on_arm = MagicMock()
        self.on_disarm = MagicMock()

def test_update_armed_ready_status_arm_away():
    device = MockDevice()
    msg = MagicMock()
    msg.ready = True
    msg.armed_away = True
    msg.armed_home = False

    updater.update_armed_ready_status(device, msg)

    assert device._ready is True
    assert device._armed_away is True
    assert device._armed_home is False
    device.on_ready_changed.fire.assert_called_once_with(device, True)
    device.on_arm.fire.assert_called_once_with(device, False)

def test_update_armed_ready_status_disarm():
    device = MockDevice()
    device._armed_away = True
    msg = MagicMock()
    msg.ready = True
    msg.armed_away = False
    msg.armed_home = False

    updater.update_armed_ready_status(device, msg)

    assert device._armed_away is False
    assert device._armed_home is False
    device.on_disarm.fire.assert_called_once_with(device)

def test_update_alarm_status_triggers_on_alarm():
    device = MagicMock()
    device._alarm_occurring = False
    message = MagicMock()
    message.alarm_event_occurred = True

    updater.update_alarm_status(device, message)

    assert device._alarm_occurring is True
    device.on_alarm.fire.assert_called_once_with(device, None)

def test_update_alarm_status_triggers_on_alarm_restored():
    device = MagicMock()
    device._alarm_occurring = True
    message = MagicMock()
    message.alarm_event_occurred = False

    updater.update_alarm_status(device, message)

    assert device._alarm_occurring is False
    device.on_alarm_restored.fire.assert_called_once_with(device, None)

def test_update_battery_status():
    device = MagicMock()
    device._battery = False
    message = MagicMock()
    message.battery_low = True

    updater.update_battery_status(device, message)

    assert device._battery is True
    device.on_low_battery.fire.assert_called_once_with(device, True)

def test_update_fire_status():
    device = MagicMock()
    device._fire = False
    message = MagicMock()
    message.fire_alarm = True

    updater.update_fire_status(device, message)

    assert device._fire is True
    device.on_fire.fire.assert_called_once_with(device, True)

def test_update_chime_status():
    device = MagicMock()
    device._chime_on = False
    message = MagicMock()
    message.chime_on = True

    updater.update_chime_status(device, message)

    assert device._chime_on is True
    device.on_chime_changed.fire.assert_called_once_with(device, message)

def test_update_zone_tracker_forwards_call():
    tracker = MagicMock()
    device = MagicMock()
    device._zonetracker = tracker
    message = MagicMock()

    updater.update_zone_tracker(device, message)

    tracker.update.assert_called_once_with(message)