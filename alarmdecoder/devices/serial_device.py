import logging
import select
import time

import serial
import serial.tools.list_ports
from serial import SerialException, SerialTimeoutException

from alarmdecoder.devices.base_device import Device
from alarmdecoder.util.exceptions import CommError, NoDeviceError, TimeoutError
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

    # Ensure _encode_data is robust (example fix from previous discussion)
    def _encode_data(self, data: str | bytes) -> bytes:
        # Safely get encoding, default to utf-8
        encoding = getattr(self, 'ENCODING', 'utf-8')
        if isinstance(data, str):
            return data.encode(encoding)
        elif isinstance(data, bytes):
            return data  # Already bytes
        else:
            # Handle unexpected type if necessary, or raise TypeError
            raise TypeError(f"Data to write must be str or bytes, not {type(data).__name__}")

    def write(self, data: str | bytes) -> int:  # Return int (bytes written)
        """
        Writes data to the serial device after ensuring it is bytes.

        Args:
            data: The string or bytes to write.

        Returns:
            The number of bytes written to the underlying device.

        Raises:
            CommError: If a non-timeout serial error occurs or an unexpected error happens.
            SerialTimeoutException: If the write operation times out (re-raised).
            TypeError: If the input data is not str or bytes.
        """
        bytes_written: int = 0
        encoded_data: bytes

        try:
            # Ensure data is correctly encoded bytes
            encoded_data = self._encode_data(data)  # Raises TypeError on bad input type

            # Write to the underlying pyserial device
            # self._device is assumed to be the pyserial Serial object instance
            bytes_written = self._device.write(encoded_data)

            # Check if zero bytes were written when data was expected
            # This might indicate an issue, though pyserial often raises timeout instead
            if bytes_written == 0 and len(encoded_data) > 0:
                logger.warning("Attempted to write %d bytes, but underlying write() returned 0.", len(encoded_data))
                # Consider if this should be a CommError depending on expected pyserial behavior

            # Emit event upon successful write (pass the actual bytes written)
            # Assuming self.on_write is an EventHandler or similar mechanism
            if hasattr(self, 'on_write'):
                # Pass data that was actually confirmed written
                self.on_write(data=encoded_data[:bytes_written])

            return bytes_written

        except SerialTimeoutException as timeout_err:
            # Log the timeout specifically
            logger.warning("Write operation timed out on %s.", getattr(self._device, 'port', 'serial device'))
            # Re-raise the original exception so callers can distinguish timeouts
            raise timeout_err

        except SerialException as serial_err:
            # Handle other general pyserial errors
            logger.error("SerialException during write on %s.", getattr(self._device, 'port', 'serial device'),
                         exc_info=True)
            # Wrap in custom CommError for consistent API error handling
            raise CommError(f"Error writing to serial device: {serial_err}") from serial_err

        except TypeError as type_err:
            # Catch TypeError from _encode_data
            logger.error("Invalid data type for write: %s", type_err, exc_info=True)
            raise type_err  # Re-raise TypeError

        except Exception as general_err:
            # Catch any other unexpected errors
            logger.error("Unexpected error during write operation on %s.",
                         getattr(self._device, 'port', 'serial device'), exc_info=True)
            raise CommError(f"Unexpected error writing to device: {general_err}") from general_err

    # Ensure self.on_write exists, usually an EventHandler instance
    # Example: self.on_write = EventHandler(Event(), self)

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
