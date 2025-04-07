"""
Provides the main AlarmDecoder class.

.. _AlarmDecoder: http://www.alarmdecoder.com

.. moduleauthor:: Scott Petersen <scott@nutech.com>
"""
import logging
import sys
from alarmdecoder.event import event
from alarmdecoder.event.wiring import wire_events, unwire_events
from alarmdecoder.logger import get_logger
from alarmdecoder.messages import ExpanderMessage, RFMessage, AUIMessage
from alarmdecoder.messages.panel_message import (
    PanelMessage,
    LRRMessage
)
from alarmdecoder.panels import ADEMCO
from alarmdecoder.status import updater
from alarmdecoder.status.updater import (
    update_armed_ready_status,
)
from alarmdecoder.util.exceptions import InvalidMessageError
from alarmdecoder.messages.base_message import BaseMessage
from alarmdecoder.zonetracking import Zonetracker
from alarmdecoder.messages.lrr.system import LRRSystem
logger = get_logger(__name__)


class AlarmDecoder(object):
    def _delegate_update(self, method, *args, **kwargs):
        try:
            logger.debug("Delegating update to %s with args=%s kwargs=%s", method.__name__, args, kwargs)
            method(self, *args, **kwargs)
        except Exception as e:
            logger.error("Error in update method %s: %s", method.__name__, e, exc_info=True)

    """
    High-level wrapper around `AlarmDecoder`_ (AD2) devices.
    """

    # High-level Events
    on_arm = event.Event(
        "This event is called when the panel is armed.\n\n**Callback definition:** *def callback(device, stay)*")
    on_disarm = event.Event(
        "This event is called when the panel is disarmed.\n\n**Callback definition:** *def callback(device)*")
    on_power_changed = event.Event(
        "This event is called when panel power switches between AC and DC.\n\n**Callback definition:** *def callback(device, status)*")
    on_ready_changed = event.Event(
        "This event is called when panel ready state changes.\n\n**Callback definition:** *def callback(device, status)*")
    on_alarm = event.Event(
        "This event is called when the alarm is triggered.\n\n**Callback definition:** *def callback(device, zone)*")
    on_alarm_restored = event.Event(
        "This event is called when the alarm stops sounding.\n\n**Callback definition:** *def callback(device, zone)*")
    on_fire = event.Event(
        "This event is called when a fire is detected.\n\n**Callback definition:** *def callback(device, status)*")
    on_bypass = event.Event(
        "This event is called when a zone is bypassed.  \n\n\n\n**Callback definition:** *def callback(device, status)*")
    on_boot = event.Event(
        "This event is called when the device finishes booting.\n\n**Callback definition:** *def callback(device)*")
    on_config_received = event.Event(
        "This event is called when the device receives its configuration. \n\n**Callback definition:** *def callback(device)*")
    on_zone_fault = event.Event(
        "This event is called when :py:class:`~alarmdecoder.zonetracking.Zonetracker` detects a zone fault.\n\n**Callback definition:** *def callback(device, zone)*")
    on_zone_restore = event.Event(
        "This event is called when :py:class:`~alarmdecoder.zonetracking.Zonetracker` detects that a fault is restored.\n\n**Callback definition:** *def callback(device, zone)*")
    on_low_battery = event.Event(
        "This event is called when the device detects a low battery.\n\n**Callback definition:** *def callback(device, status)*")
    on_panic = event.Event(
        "This event is called when the device detects a panic.\n\n**Callback definition:** *def callback(device, status)*")
    on_relay_changed = event.Event(
        "This event is called when a relay is opened or closed on an expander board.\n\n**Callback definition:** *def callback(device, message)*")
    on_chime_changed = event.Event(
        "This event is called when chime state changes.\n\n**Callback definition:** *def callback(device, message)*")

    # Mid-level Events
    on_message = event.Event(
        "This event is called when standard panel :py:class:`~alarmdecoder.messages.Message` is received.\n\n**Callback definition:** *def callback(device, message)*")
    on_expander_message = event.Event(
        "This event is called when an :py:class:`~alarmdecoder.messages.ExpanderMessage` is received.\n\n**Callback definition:** *def callback(device, message)*")
    on_lrr_message = event.Event(
        "This event is called when an :py:class:`~alarmdecoder.messages.LRRMessage` is received.\n\n**Callback definition:** *def callback(device, message)*")
    on_rfx_message = event.Event(
        "This event is called when an :py:class:`~alarmdecoder.messages.RFMessage` is received.\n\n**Callback definition:** *def callback(device, message)*")
    on_sending_received = event.Event(
        "This event is called when a !Sending.done message is received from the AlarmDecoder.\n\n**Callback definition:** *def callback(device, status, message)*")
    on_aui_message = event.Event(
        "This event is called when an :py:class`~alarmdecoder.messages.AUIMessage` is received\n\n**Callback definition:** *def callback(device, message)*")

    # Low-level Events
    on_open = event.Event(
        "This event is called when the device has been opened.\n\n**Callback definition:** *def callback(device)*")
    on_close = event.Event(
        "This event is called when the device has been closed.\n\n**Callback definition:** *def callback(device)*")
    on_read = event.Event(
        "This event is called when a line has been read from the device.\n\n**Callback definition:** *def callback(device, data)*")
    on_write = event.Event(
        "This event is called when data has been written to the device.\n\n**Callback definition:** *def callback(device, data)*")

    # Constants
    KEY_F1 = chr(1) + chr(1) + chr(1)
    """Represents panel function key #1"""
    KEY_F2 = chr(2) + chr(2) + chr(2)
    """Represents panel function key #2"""
    KEY_F3 = chr(3) + chr(3) + chr(3)
    """Represents panel function key #3"""
    KEY_F4 = chr(4) + chr(4) + chr(4)
    """Represents panel function key #4"""
    KEY_PANIC = chr(2) + chr(2) + chr(2)
    """Represents a panic keypress"""
    KEY_S1 = chr(1) + chr(1) + chr(1)
    """Represents panel special key #1"""
    KEY_S2 = chr(2) + chr(2) + chr(2)
    """Represents panel special key #2"""
    KEY_S3 = chr(3) + chr(3) + chr(3)
    """Represents panel special key #3"""
    KEY_S4 = chr(4) + chr(4) + chr(4)
    """Represents panel special key #4"""
    KEY_S5 = chr(5) + chr(5) + chr(5)
    """Represents panel special key #5"""
    KEY_S6 = chr(6) + chr(6) + chr(6)
    """Represents panel special key #6"""
    KEY_S7 = chr(7) + chr(7) + chr(7)
    """Represents panel special key #7"""
    KEY_S8 = chr(8) + chr(8) + chr(8)
    """Represents panel special key #8"""

    BATTERY_TIMEOUT = 30
    """Default timeout (in seconds) before the battery status reverts."""
    FIRE_TIMEOUT = 30
    """Default tTimeout (in seconds) before the fire status reverts."""

    # Attributes
    address = 18
    """The keypad address in use by the device."""
    configbits = 0xFF00
    """The configuration bits set on the device."""
    address_mask = 0xFFFFFFFF
    """The address mask configured on the device."""
    emulate_zone = [False for _ in list(range(5))]
    """List containing the devices zone emulation status."""
    emulate_relay = [False for _ in list(range(4))]
    """List containing the devices relay emulation status."""
    emulate_lrr = False
    """The status of the devices LRR emulation."""
    deduplicate = False
    """The status of message deduplication as configured on the device."""
    mode = ADEMCO
    """The panel mode that the AlarmDecoder is in.  Currently supports ADEMCO and DSC."""
    emulate_com = False
    """The status of the devices COM emulation."""

    # Version Information
    serial_number = 'Unknown'
    """The device serial number"""
    version_number = 'Unknown'
    """The device firmware version"""
    version_flags = ""
    """Device flags enabled"""

    def __init__(self, device, ignore_message_states=False, ignore_lrr_states=True):
        logger.info("Initializing AlarmDecoder with device: %s", device)
        """
        Constructor

        :param device: The low-level device used for this `AlarmDecoder`_
                       interface.
        :type device: Device
        :param ignore_message_states: Ignore regular panel messages when updating internal states
        :type ignore_message_states: bool
        :param ignore_lrr_states: Ignore LRR panel messages when updating internal states
        :type ignore_lrr_states: bool
        """
        self._log = get_logger(__name__)
        self._device = device
        self._zonetracker = Zonetracker(self)
        self._lrr_system = LRRSystem(self)
        self._ignore_message_states = ignore_message_states
        self._ignore_lrr_states = ignore_lrr_states
        self._battery_timeout = AlarmDecoder.BATTERY_TIMEOUT
        self._fire_timeout = AlarmDecoder.FIRE_TIMEOUT
        self._power_status = None
        self._chime_status = None
        self._ready_status = None
        self._alarm_status = None
        self._bypass_status = {}
        self._armed_status = None
        self._entry_delay_off_status = None
        self._perimeter_only_status = None
        self._armed_stay = False
        self._exit = False
        self._fire_status = False
        self._fire_status_timeout = 0
        self._battery_status = (False, 0)
        self._panic_status = False
        self._relay_status = {}
        self._internal_address_mask = 0xFFFFFFFF
        self.last_fault_expansion = 0
        self.fault_expansion_time_limit = 30  # Seconds
        self.address = 18
        self.configbits = 0xFF00
        self.address_mask = 0xFFFFFFFF
        self.emulate_zone = [False for x in list(range(5))]
        self.emulate_relay = [False for x in list(range(4))]
        self.emulate_lrr = False
        self.deduplicate = False
        self.mode = ADEMCO
        self.emulate_com = False
        self.serial_number = 'Unknown'
        self.version_number = 'Unknown'
        self.version_flags = ""
        self._log = logging.getLogger(__name__)

    def __enter__(self):
        """
        Support for context manager __enter__.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Support for context manager __exit__.
        """
        self.close()

        return False

    @property
    def id(self):
        """
        The ID of the `AlarmDecoder`_ device.

        :returns: identification string for the device
        """
        return self._device.id

    @property
    def battery_timeout(self):
        """
        Retrieves the timeout for restoring the battery status, in seconds.

        :returns: battery status timeout
        """
        return self._battery_timeout

    @battery_timeout.setter
    def battery_timeout(self, value):
        """
        Sets the timeout for restoring the battery status, in seconds.

        :param value: timeout in seconds
        :type value: int
        """
        self._battery_timeout = value

    @property
    def fire_timeout(self):
        """
        Retrieves the timeout for restoring the fire status, in seconds.

        :returns: fire status timeout
        """
        return self._fire_timeout

    @fire_timeout.setter
    def fire_timeout(self, value):
        """
        Sets the timeout for restoring the fire status, in seconds.

        :param value: timeout in seconds
        :type value: int
        """
        self._fire_timeout = value

    @property
    def internal_address_mask(self):
        """
        Retrieves the address mask used for updating internal status.

        :returns: address mask
        """
        return self._internal_address_mask

    @internal_address_mask.setter
    def internal_address_mask(self, value):
        """
        Sets the address mask used internally for updating status.

        :param value: address mask
        :type value: int
        """
        self._internal_address_mask = value

    def open(self, baudrate=None, no_reader_thread=False):
        logger.info("Opening device with baudrate=%s and no_reader_thread=%s", baudrate, no_reader_thread)
        """Opens the device.

        If the device cannot be opened, an exception is thrown.  In that
        case, open() can be called repeatedly to try and open the
        connection.

        :param baudrate: baudrate used for the device.  Defaults to the lower-level device default.
        :type baudrate: int
        :param no_reader_thread: Specifies whether or not the automatic reader
                                 thread should be started.
        :type no_reader_thread: bool
        """
        wire_events(self)

        try:
            self._device.open(baudrate=baudrate,
                              no_reader_thread=no_reader_thread)
        except:
            unwire_events(self)

            raise

        return self

    def close(self):
        logger.info("Closing device.")

        """
        Closes the device.
        """
        self._device.close()
        unwire_events(self)

    def send(self, data):
        logger.debug("Sending data: %s", data)
        """
        Sends data to the `AlarmDecoder`_ device.

        :param data: data to send
        :type data: string
        """

        if self._device:
            if isinstance(data, str):
                data = str.encode(data)

            self._device.write(data)

    def get_version(self):
        """
        Retrieves the version string from the device.  Called automatically by :py:meth:`_on_open`.
        """
        self.send("V\r")

    def reboot(self):
        """
        Reboots the device.
        """
        self.send('=')

    def fault_zone(self, zone, simulate_wire_problem=False):
        """
        Faults a zone if we are emulating a zone expander.

        :param zone: zone to fault
        :type zone: int
        :param simulate_wire_problem: Whether or not to simulate a wire fault
        :type simulate_wire_problem: bool
        """

        # Allow ourselves to also be passed an address/channel combination
        # for zone expanders.
        #
        # Format (expander index, channel)
        if isinstance(zone, tuple):
            expander_idx, channel = zone

            zone = self._zonetracker.expander_to_zone(expander_idx, channel)

        status = 2 if simulate_wire_problem else 1

        self.send("L{0:02}{1}\r".format(zone, status))

    def clear_zone(self, zone):
        """
        Clears a zone if we are emulating a zone expander.

        :param zone: zone to clear
        :type zone: int
        """
        self.send("L{0:02}0\r".format(zone))

    def _handle_message(self, data):
        logger.debug("Handling incoming message: %s", data)
        """
        Central message handler. Dispatches parsed message to appropriate sub-handler and events.
        """
        from alarmdecoder.messages.parser import parse_message

        try:
            message = parse_message(data)
            self.on_message.fire(self, message)

            # Dispatch based on message type
            if isinstance(message, PanelMessage):
                self._handle_keypad_message(data)
            elif isinstance(message, ExpanderMessage):
                self._handle_expander_message(data)
            elif isinstance(message, RFMessage):
                self._handle_rfx(data)
            elif isinstance(message, LRRMessage):
                self._handle_lrr(data)
            elif isinstance(message, AUIMessage):
                self._handle_aui(data)

        except InvalidMessageError as ex:
            logger.warning("Invalid message received: %s", data)

    def _handle_keypad_message(self, data):
        """
        Handle keypad messages.

        :param data: keypad message to parse
        :type data: string

        :returns: :py:class:`~alarmdecoder.messages.Message`
        """

        msg = BaseMessage(data)

        if self._internal_address_mask & msg.mask > 0:
            if not self._ignore_message_states:
                self._update_internal_states(msg)

            self.on_message(message=msg)

        return msg

    def _handle_expander_message(self, data):
        """
        Handle expander messages.

        :param data: expander message to parse
        :type data: string

        :returns: :py:class:`~alarmdecoder.messages.ExpanderMessage`
        """
        msg = ExpanderMessage(data)

        self._update_internal_states(msg)
        self.on_expander_message(message=msg)

        return msg

    def _handle_rfx(self, data):
        """
        Handle RF messages.

        :param data: RF message to parse
        :type data: string

        :returns: :py:class:`~alarmdecoder.messages.RFMessage`
        """
        msg = RFMessage(data)

        self.on_rfx_message(message=msg)

        return msg

    def _handle_lrr(self, data):
        """
        Handle Long Range Radio messages.

        :param data: LRR message to parse
        :type data: string

        :returns: :py:class:`~alarmdecoder.messages.LRRMessage`
        """
        msg = LRRMessage(data)

        if not self._ignore_lrr_states:
            self._lrr_system.update(msg)
        self.on_lrr_message(message=msg)

        return msg

    def _handle_aui(self, data):
        """
        Handle AUI messages.

        :param data: RF message to parse
        :type data: string

        :returns: :py:class`~alarmdecoder.messages.AUIMessage`
        """
        msg = AUIMessage(data)

        self.on_aui_message(message=msg)

        return msg

    def _update_internal_states(self, message):
        """
        Updates internal device states.

        :param message: :py:class:`~alarmdecoder.messages.Message` to update internal states with
        :type message: :py:class:`~alarmdecoder.messages.Message`, :py:class:`~alarmdecoder.messages.ExpanderMessage`, :py:class:`~alarmdecoder.messages.LRRMessage`, or :py:class:`~alarmdecoder.messages.RFMessage`
        """
        if isinstance(message, BaseMessage) and not self._ignore_message_states:
            self._delegate_update(update_armed_ready_status, message)
            self._delegate_update(updater.update_power_status, message)
            self._delegate_update(updater.update_chime_status, message)
            self._delegate_update(updater.update_alarm_status, message)
            self._delegate_update(updater.update_zone_bypass_status, message)
            self._delegate_update(updater.update_battery_status, message)
            self._delegate_update(updater.update_fire_status, message)
        elif isinstance(message, ExpanderMessage):
            self._delegate_update(updater.update_expander_status, message)
            # Always update zone tracking
        self._delegate_update(updater.update_zone_tracker, message)

    def _update_power_status(self, message=None, status=None):
        updater.update_power_status(self, message, status)

    def _update_chime_status(self, message=None, status=None):
        updater.update_chime_status(self, message, status)

    def _update_alarm_status(self, message=None, status=None, zone=None):
        updater.update_alarm_status(self, message, status, zone)

    def _update_zone_bypass_status(self, message=None, status=None, zone=None):
        updater.update_zone_bypass_status(self, message, status, zone)

    def update_armed_ready_status(self, message=None):
        """
        Delegates the update of armed and ready status to the updater module.
        """
        from alarmdecoder.status.updater import update_armed_ready_status
        update_armed_ready_status(self, message)

    def _update_armed_status(self, message=None, status=None, status_stay=None):
        updater.update_armed_status(self, message, status, status_stay)

    def update_battery_status(self, message=None, status=None):
        """
        Delegates the update of battery status to the updater module.
        """
        from alarmdecoder.status.updater import update_battery_status
        update_battery_status(self, message, status)

    def update_fire_status(self, message=None, status=None):
        """
        Delegates the update of fire status to the updater module.
        """
        from alarmdecoder.status.updater import update_fire_status
        update_fire_status(self, message, status)

    def update_panic_status(self, status=None):
        """
        Delegates the update of panic status to the updater module.
        """
        from alarmdecoder.status.updater import update_panic_status
        update_panic_status(self, status)

    def update_expander_status(self, message):
        """
        Delegates the update of expander status to the updater module.
        """
        from alarmdecoder.status.updater import update_expander_status
        update_expander_status(self, message)

    def update_zone_tracker(self, message):
        """
        Delegates the update of zone tracking to the updater module.
        """
        from alarmdecoder.status.updater import update_zone_tracker
        update_zone_tracker(self, message)

    def _on_relay_changed(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when the device detects a relay state change.
        """
        self.on_relay_changed.fire(self, *args, **kwargs)

    def _on_open(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Handles the device open event using the centralized handler.
        """
        from alarmdecoder.handlers.versioning import handle_on_open
        handle_on_open(self, sender, *args, **kwargs)

    def _on_close(self, sender: object, *args: object, **kwargs: object) -> None:
        from alarmdecoder.handlers.versioning import handle_on_close
        handle_on_close(self, *args, **kwargs)

    def _on_read(self, sender: object, *args: object, **kwargs: object) -> None:
        from alarmdecoder.handlers.versioning import handle_on_read
        data = args[0] if args else None
        if data:
            handle_on_read(self, data, *args[1:], **kwargs)

    def _on_write(self, sender: object, *args: object, **kwargs: object) -> None:
        from alarmdecoder.handlers.versioning import handle_on_write
        data = args[0] if args else None
        if data:
            handle_on_write(self, data, *args[1:], **kwargs)

    def _on_zone_fault(self, sender: object, *args: object, **kwargs: object) -> None:
        from alarmdecoder.status.updater import handle_zone_fault
        zone = args[0] if args else None
        if zone:
            handle_zone_fault(self, zone, *args[1:], **kwargs)

    def _on_zone_restore(self, sender: object, *args: object, **kwargs: object) -> None:
        from alarmdecoder.status.updater import handle_zone_restore
        zone = args[0] if args else None
        if zone:
            handle_zone_restore(self, zone, *args[1:], **kwargs)

    def _on_panic(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Handles panic status updates.
        """
        status = kwargs.get('status')
        self._panic = status
        self.on_panic.fire(self, status)

    def _on_chime_changed(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when the device detects a chime state change.
        """
        self.on_chime_changed.fire(self, *args, **kwargs)

    def _on_alarm(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when the alarm is triggered.
        """
        self.on_alarm.fire(self, *args, **kwargs)

    def _on_alarm_restored(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when the alarm is restored.
        """
        self.on_alarm_restored.fire(self, *args, **kwargs)

    def _on_fire(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when a fire event occurs.
        """
        self.on_fire.fire(self, *args, **kwargs)

    def _on_config_received(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when the device configuration is received.
        """
        self.on_config_received.fire(self, *args, **kwargs)

    def _on_arm(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when the panel is armed.
        """
        self.on_arm.fire(self, *args, **kwargs)

    def _on_disarm(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when the panel is disarmed.
        """
        self.on_disarm.fire(self, *args, **kwargs)

    def _on_bypass(self, sender: object, *args: object, **kwargs: object) -> None:
        """Called when a zone is bypassed."""
        self.on_bypass.fire(self, *args, **kwargs)

    def _on_ready_changed(self, sender: object, *args: object, **kwargs: object) -> None:
        """
        Called when the panel ready state changes.
        """
        self.on_ready_changed.fire(self, *args, **kwargs)

    def _on_power_changed(self, sender: object, *args: object, **kwargs: object) -> None:
        message = kwargs.get('message')
        status = kwargs.get('status')

        if message is not None and hasattr(message, 'ac_power'):
            status = message.ac_power

        if status is None:
            return

        if self._power_status != status:
            self._power_status = status
            self.on_power_changed.fire(self, self._power_status)
