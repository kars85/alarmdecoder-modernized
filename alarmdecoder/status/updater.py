# alarmdecoder/status/updater.py
from alarmdecoder.logger import get_logger

logger = get_logger(__name__)


def update_power_status(device, message=None, status=None):
    """
    Handles AC power status changes.
    """
    new_status = message.ac_power if message else status
    if new_status != device._ac_power:
        logger.info(f"Power state changed: AC power is {'ON' if new_status else 'OFF'}")
        device._ac_power = new_status
        device.on_power_changed.fire(device, new_status)


def update_chime_status(device, message=None, status=None):
    """
    Handles chime status changes.
    """
    new_status = message.chime_on if message else status
    if new_status != device._chime_on:
        logger.debug(f"Chime status changed to: {'ON' if new_status else 'OFF'}")
        device._chime_on = new_status
        device.on_chime_changed.fire(device, message or status)


def update_alarm_status(device, message=None, status=None, zone=None):
    """
    Handles alarm state changes.
    """
    new_status = message.alarm_event_occurred if message else status

    if new_status and not device._alarm_occurring:
        zone_info = f" in zone {zone}" if zone else ""
        logger.warning(f"ALARM EVENT OCCURRING{zone_info}")
        device._alarm_occurring = True
        device.on_alarm.fire(device, zone)

    elif not new_status and device._alarm_occurring:
        logger.info("Alarm restored to normal state")
        device._alarm_occurring = False
        device.on_alarm_restored.fire(device, zone)


def update_armed_status(device, message=None, status=None, status_stay=None):
    """
    Handles arming state changes.
    """
    if message:
        status = message.armed_away or message.armed_home
        status_stay = message.armed_home

    if status != device._armed:
        armed_type = "STAY" if status_stay else "AWAY" if status else "DISARMED"
        logger.info(f"System armed status changed: {armed_type}")
        device._armed = status
        device._armed_stay = status_stay
        device.on_arm.fire(device, status_stay)
    elif status_stay != device._armed_stay:
        logger.info(f"Armed stay status changed: {'ARMED STAY' if status_stay else 'ARMED AWAY'}")
        device._armed_stay = status_stay
        device.on_arm.fire(device, status_stay)


def update_armed_ready_status(decoder, message=None):
    if message is not None:
        # Ready status
        if message.ready != decoder._ready:
            logger.debug(f"Ready status changed: {'READY' if message.ready else 'NOT READY'}")
            decoder._ready = message.ready
            decoder.on_ready_changed.fire(decoder, decoder._ready)

        # Armed status
        if message.armed_away and not decoder._armed_away:
            logger.info("Alarm status: ARMED AWAY")
            decoder._armed_away = True
            decoder._armed_home = False
            decoder.on_arm.fire(decoder, False)

        elif message.armed_home and not decoder._armed_home:
            logger.info("Alarm status: ARMED STAY")
            decoder._armed_home = True
            decoder._armed_away = False
            decoder.on_arm.fire(decoder, True)

        elif not message.armed_away and not message.armed_home and (decoder._armed_away or decoder._armed_home):
            logger.info("Alarm status: DISARMED")
            decoder._armed_away = False
            decoder._armed_home = False
            decoder.on_disarm.fire(decoder)


def update_battery_status(decoder, message=None, status=None):
    if message is not None:
        status = message.battery_low

    if status is not None and status != decoder._battery:
        logger.warning(f"Battery status changed: {'LOW BATTERY' if status else 'BATTERY NORMAL'}")
        decoder._battery = status
        decoder.on_low_battery.fire(decoder, status)


def update_fire_status(decoder, message=None, status=None):
    if message is not None:
        status = message.fire_alarm

    if status is not None and status != decoder._fire:
        log_level = logger.critical if status else logger.info
        log_level(f"Fire status changed: {'FIRE ALARM' if status else 'FIRE ALARM CLEARED'}")
        decoder._fire = status
        decoder.on_fire.fire(decoder, status)


def update_panic_status(decoder, status=None):
    if status is not None and status != decoder._panic:
        log_level = logger.critical if status else logger.info
        log_level(f"Panic status changed: {'PANIC ACTIVE' if status else 'PANIC CLEARED'}")
        decoder._panic = status
        decoder.on_panic.fire(decoder, status)


def update_expander_status(decoder, message):
    if hasattr(message, "relay") and hasattr(message, "channel") and hasattr(message, "value"):
        logger.debug(f"Relay changed: relay={message.relay}, channel={message.channel}, value={message.value}")
        decoder.on_relay_changed.fire(decoder, message)


def update_zone_bypass_status(device, message=None, status=None, zone=None):
    """
    Handles zone bypass status changes.
    """
    new_status = message.zone_bypassed if message else status
    if zone is None:
        logger.warning("Unexpected bypass update with missing zone info")
    else:
        logger.info(f"Zone {zone} bypass status: {'BYPASSED' if new_status else 'NOT BYPASSED'}")
    device.on_bypass.fire(device, new_status)


def update_zone_tracker(decoder, message):
    """
    Passes the message to the zonetracker for processing.
    The zonetracker will call the appropriate zone_fault/restore events.
    """
    if decoder._zonetracker is not None:
        logger.debug(f"Updating zone tracker with message: {message}")
        decoder._zonetracker.update(message)


def handle_zone_fault(decoder, zone, *args, **kwargs):
    """
    Fires the zone fault event.
    """
    logger.warning(f"Zone fault detected in zone {zone}")
    decoder.on_zone_fault.fire(decoder, zone)


def handle_zone_restore(decoder, zone, *args, **kwargs):
    """
    Fires the zone restore event.
    """
    logger.info(f"Zone {zone} restored to normal state")
    decoder.on_zone_restore.fire(decoder, zone)


def handle_low_battery(decoder, status=None, *args, **kwargs):
    """
    Fires the low battery event if the status has changed.
    """
    old_status = decoder._battery_low
    decoder._battery_low = status

    if old_status is not None and old_status != status:
        logger.warning(f"Battery status changed: {'LOW BATTERY' if status else 'BATTERY NORMAL'}")
        decoder.on_low_battery.fire(decoder, status)