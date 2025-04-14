"""
This module contains the USBDevice interface for the AD2USB hardware.

Refactored for Python 3.11+ with modern structure, error handling, and device detection.
"""

import threading
import time

from alarmdecoder.util.io import bytes_hack

from ..event import event
from ..util import CommError, NoDeviceError, TimeoutError
from .base_device import Device

# Handle pyftdi import
try:
    import usb.core
    import usb.util
    from pyftdi.pyftdi.ftdi import Ftdi, FtdiError
    HAVE_PYFTDI = True
except ImportError:
    try:
        import usb.core
        import usb.util
        from pyftdi.ftdi import Ftdi, FtdiError
        HAVE_PYFTDI = True
    except ImportError:
        HAVE_PYFTDI = False


class USBDevice(Device):
    PRODUCT_IDS = ((0x0403, 0x6001), (0x0403, 0x6015))
    DEFAULT_VENDOR_ID = PRODUCT_IDS[0][0]
    DEFAULT_PRODUCT_ID = PRODUCT_IDS[0][1]
    BAUDRATE = 115200

    _devices = []
    _detect_thread = None

    def __init__(self, interface=0, vid=None, pid=None):
        if not HAVE_PYFTDI:
            raise ImportError('Missing pyftdi/pyusb – USBDevice disabled.')

        super().__init__()

        self._device = Ftdi()
        self._interface = 0
        self._serial_number = None
        self._device_number = 0
        self._vendor_id = vid or self.DEFAULT_VENDOR_ID
        self._product_id = pid or self.DEFAULT_PRODUCT_ID
        self._endpoint = 0
        self._description = None
        self.interface = interface

    @property
    def interface(self):
        return self._interface

    @interface.setter
    def interface(self, value):
        self._interface = value
        if isinstance(value, int):
            self._device_number = value
        else:
            self._serial_number = value

    @property
    def serial_number(self):
        return self._serial_number

    @serial_number.setter
    def serial_number(self, value):
        self._serial_number = value

    @property
    def description(self):
        return self._description

    @description.setter
    def description(self, value):
        self._description = value

    def open(self, baudrate=BAUDRATE, no_reader_thread=False):
        if baudrate is None:
            baudrate = self.BAUDRATE

        self._read_thread = Device.ReadThread(self)

        try:
            self._device.open(
                self._vendor_id,
                self._product_id,
                self._endpoint,
                self._device_number,
                self._serial_number,
                self._description,
            )
            self._device.set_baudrate(baudrate)

            if not self._serial_number:
                self._serial_number = self._get_serial_number()
            self._id = self._serial_number

        except (usb.core.USBError, FtdiError) as err:
            raise NoDeviceError(f"Error opening device: {err}", err)

        except KeyError as err:
            raise NoDeviceError(
                f"Unsupported device {err} — pyftdi upgrade needed."
            )

        self._running = True
        self.on_open()

        if not no_reader_thread:
            self._read_thread.start()

        return self

    def close(self):
        try:
            super().close()
            self._device.usb_dev.attach_kernel_driver(self._device_number)
        except Exception:
            pass

    def write(self, data):
        try:
            self._device.write_data(data)
            self.on_write(data=data)
        except FtdiError as err:
            raise CommError(f"Error writing to device: {err}", err)

    def read(self):
        try:
            return self._device.read_data(1)
        except (usb.core.USBError, FtdiError) as err:
            raise CommError(f"Error reading from device: {err}", err)

    def read_line(self, timeout=0.0, purge_buffer=False):
        def timeout_event():
            timeout_event.reading = False

        timeout_event.reading = True

        if purge_buffer:
            self._buffer = b''

        got_line, ret = False, None
        timer = threading.Timer(timeout, timeout_event)
        if timeout > 0:
            timer.start()

        try:
            while timeout_event.reading:
                buf = self._device.read_data(1)
                if buf:
                    ub = bytes_hack(buf)
                    self._buffer += ub
                    if ub == b'\n':
                        self._buffer = self._buffer.rstrip(b'\r\n')
                        if self._buffer:
                            got_line = True
                            break
                else:
                    time.sleep(0.01)
        except (usb.core.USBError, FtdiError) as err:
            raise CommError(f"Error reading from device: {err}", err)
        finally:
            timer.cancel()

        if got_line:
            ret, self._buffer = self._buffer, b''
            self.on_read(data=ret)
            return ret

        raise TimeoutError("Timeout waiting for line terminator.")

    def purge(self):
        self._device.purge_buffers()

    def fileno(self):
        raise NotImplementedError("USB devices do not support fileno()")

    def _get_serial_number(self):
        return usb.util.get_string(
            self._device.usb_dev, 64, self._device.usb_dev.iSerialNumber
        )

    @classmethod
    def find_all(cls, vid=None, pid=None):
        if not HAVE_PYFTDI:
            raise ImportError('Missing pyftdi/pyusb.')

        cls._devices = []
        query = cls.PRODUCT_IDS if not (vid and pid) else [(vid, pid)]

        try:
            cls._devices = Ftdi.find_all(query, nocache=True)
        except (usb.core.USBError, FtdiError) as err:
            raise CommError(f"Error enumerating AD2USB devices: {err}", err)

        return cls._devices

    @classmethod
    def devices(cls):
        return cls._devices

    @classmethod
    def find(cls, device=None):
        if not HAVE_PYFTDI:
            raise ImportError('Missing pyftdi/pyusb.')

        cls.find_all()
        if not cls._devices:
            raise NoDeviceError("No AD2USB devices present.")

        device = device or cls._devices[0]
        vendor, product, sernum, *_ = device
        return USBDevice(interface=sernum, vid=vendor, pid=product)

    @classmethod
    def start_detection(cls, on_attached=None, on_detached=None):
        if not HAVE_PYFTDI:
            raise ImportError('Missing pyftdi/pyusb.')

        cls._detect_thread = cls.DetectThread(on_attached, on_detached)
        try:
            cls.find_all()
        except CommError:
            pass
        cls._detect_thread.start()

    @classmethod
    def stop_detection(cls):
        if cls._detect_thread:
            try:
                cls._detect_thread.stop()
            except Exception:
                pass

    class DetectThread(threading.Thread):
        on_attached = event.Event("Device attached")
        on_detached = event.Event("Device detached")

        def __init__(self, on_attached=None, on_detached=None):
            super().__init__()
            if on_attached:
                self.on_attached += on_attached
            if on_detached:
                self.on_detached += on_detached
            self._running = False

        def stop(self):
            self._running = False

        def run(self):
            self._running = True
            last_devices = set()

            while self._running:
                try:
                    current_devices = set(USBDevice.find_all())

                    for dev in current_devices - last_devices:
                        self.on_attached(device=dev)

                    for dev in last_devices - current_devices:
                        self.on_detached(device=dev)

                    last_devices = current_devices
                    time.sleep(0.25)

                except CommError:
                    pass
