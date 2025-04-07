import serial
import serial.tools.list_ports
import select
import logging
import time
from serial import SerialException, SerialTimeoutException
from alarmdecoder.devices.base_device import Device
from alarmdecoder.util.exceptions import CommError, TimeoutError, NoDeviceError
from alarmdecoder.util.io import filter_ad2prot_byte

# Logger configuration
logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)


class SerialDevice(Device):
    """
    Serial device handling via PySerial. This includes AD2USB, AD2SERIAL, or AD2PI devices.
    """

    # Constants
    BAUDRATE = 19200
    ENCODING = 'utf-8'

    def __init__(self, interface=None):
        """
        Constructor to initialize the SerialDevice.

        :param interface: Serial port name (e.g., COM1, /dev/ttyUSB0)
        :type interface: str or None
        """
        super().__init__()
        self._port = interface
        self._id = interface
        self._buffer = b''
        self._device = serial.Serial(timeout=0, writeTimeout=0)
        self._read_thread = None
        self._running = False

    @staticmethod
    def find_all(pattern=None):
        """
        Returns all available serial ports, optionally filtered by a pattern.
        """
        devices = []
        try:
            if pattern:
                devices = list(serial.tools.list_ports.grep(pattern))
            else:
                devices = list(serial.tools.list_ports.comports())
        except SerialException as err:
            logger.error(f"Error enumerating serial devices: {err}", exc_info=True)
            raise CommError(f"Error enumerating serial devices: {err}") from err
        return devices

    @property
    def interface(self):
        return self._port

    @interface.setter
    def interface(self, value):
        self._port = value

    def open(self, baudrate=BAUDRATE, no_reader_thread=False):
        if self._port is None:
            raise NoDeviceError("No device interface specified.")

        self._read_thread = self.ReadThread(self)

        try:
            self._device.port = self._port
            self._device.open()
            self._device.baudrate = baudrate
        except (SerialException, ValueError, OSError) as err:
            logger.error(f"Failed to open device on {self._port}: {err}", exc_info=True)
            raise NoDeviceError(f"Error opening device on {self._port}: {err}") from err

        self._running = True

        if not no_reader_thread:
            self._read_thread.start()

    def close(self):
        try:
            if self._read_thread and self._read_thread.is_alive():
                self._read_thread.stop()
                self._read_thread.join()
            self._device.close()
        except Exception as err:
            logger.warning(f"Error while closing the device: {err}", exc_info=True)

    def fileno(self):
        return self._device.fileno()

    def _encode_data(self, data: str) -> bytes:
        return data.encode(self.ENCODING)

    def write(self, data: str) -> None:
        try:
            encoded_data = self._encode_data(data)
            self._device.write(encoded_data)
        except SerialTimeoutException:
            logger.warning("Write operation timed out.")
        except SerialException as err:
            logger.error("Error writing to device.", exc_info=True)
            raise CommError("Error writing to device.") from err

    def read(self) -> str:
        try:
            read_ready, _, _ = select.select([self._device.fileno()], [], [], 0.5)
            if read_ready:
                raw_data = filter_ad2prot_byte(self._device.read(1))
                return raw_data.decode(self.ENCODING)
        except SerialException as err:
            logger.error("Error reading from device.", exc_info=True)
            raise CommError(f"Error reading from device: {err}") from err
        return ''

    def read_line(self, timeout=0.0, purge_buffer=False) -> str:
        if purge_buffer:
            self._buffer = b''

        end_time = time.monotonic() + timeout
        while timeout == 0.0 or time.monotonic() <= end_time:
            try:
                read_ready, _, _ = select.select([self._device.fileno()], [], [], 0.5)
                if read_ready:
                    buf = filter_ad2prot_byte(self._device.read(1))
                    self._buffer += buf
                    if buf == b'\n':
                        line = self._buffer.rstrip(b'\r\n')
                        self._buffer = b''
                        return line.decode(self.ENCODING)
            except (OSError, SerialException) as err:
                logger.error("Error reading a line from device.", exc_info=True)
                raise CommError(f"Error reading from device: {err}") from err

        raise TimeoutError("Timeout while reading a line from device.")

    def purge(self):
        self._device.reset_input_buffer()
        self._device.reset_output_buffer()
