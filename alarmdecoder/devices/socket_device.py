"""
This module contains :py:class:`SocketDevice` interface for `AlarmDecoder`_ devices
that are exposed through `ser2sock`_ or another IP to serial solution.  Also supports
SSL if using `ser2sock`_.

.. _ser2sock: http://github.com/nutechsoftware/ser2sock
.. _AlarmDecoder: http://www.alarmdecoder.com

.. moduleauthor:: Scott Petersen <scott@nutech.com>
"""
# Need to add imports at the top
import time
import os
import threading
import socket
import select
import logging # Import logging
from typing import Union, Optional, Tuple # Import typing helpers

from alarmdecoder.devices.base_device import Device
# Ensure these specific exceptions are importable or defined correctly
from alarmdecoder.util import CommError, TimeoutError, NoDeviceError

# Set up logger for this module
logger = logging.getLogger(__name__)

# --- SSL Import Section (Keep as is, defines OpenSSL_SSL and have_openssl) ---
try:
    # Import SSL from OpenSSL with an alias to avoid redefinition
    from OpenSSL import SSL as OpenSSL_SSL, crypto
    have_openssl = True

    # If you need another SSL module, use a different alias
    # import SomeOtherSSL as SocketSSL
except ImportError:
    # Keep the dummy class for now if other code relies on it when have_openssl is False,
    # but be aware it's limited.
    class SSL: # type: ignore # Ignore potential redefinition/type issues
        class Error(BaseException):
            pass
        class WantReadError(BaseException):
            pass
        class SysCallError(BaseException):
             def __init__(self, errno, msg): # Add basic init for unpacking
                 self.args = (errno, msg)

        # Dummy constants if needed by other non-functional parts
        TLSv1_METHOD = None
        VERIFY_PEER = None
        VERIFY_NONE = None
        class Context: pass
        class Connection: pass

    have_openssl = False
# --- End SSL Import Section ---


class SocketDevice(Device):
    """
    Device that supports communication with an `AlarmDecoder`_ (AD2) that is
    exposed via `ser2sock`_ or another Serial to IP interface.
    """

    # ... (Properties remain the same) ...

    def __init__(self, interface: tuple = ("localhost", 10000)): # Add type hint
        """
        Constructor

        :param interface: Tuple containing the hostname and port of our target
        :type interface: tuple
        """
        Device.__init__(self)

        self._host, self._port = interface
        self._use_ssl = False
        self._ssl_certificate = None
        self._ssl_key = None
        self._ssl_ca = None
        self._ssl_allow_self_signed = False
        # Initialize _device to None before open
        self._device: Optional[socket.socket | OpenSSL_SSL.Connection] = None

    # ... (open, close, fileno remain mostly the same, ensure _init_ssl uses OpenSSL_SSL) ...
    def open(self, baudrate=None, no_reader_thread=False):
        """
        Opens the device.

        :param baudrate: baudrate to use (ignored for socket)
        :type baudrate: int
        :param no_reader_thread: whether or not to automatically open the reader
                                 thread.
        :type no_reader_thread: bool

        :raises: :py:class:`~alarmdecoder.util.NoDeviceError`, :py:class:`~alarmdecoder.util.CommError`
        """
        # Ensure thread is created before potential errors in connection
        self._read_thread = Device.ReadThread(self)
        _sock = None # Temporary socket

        try:
            logger.info("Attempting to connect to %s:%d", self._host, self._port)
            _sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            _sock.connect((self._host, self._port))
            logger.info("Socket connection established.")

            if self._use_ssl:
                logger.info("Initializing SSL...")
                self._device = self._init_ssl(_sock) # Pass the raw socket
                logger.info("Performing SSL handshake...")
                while True:
                    try:
                        self._device.do_handshake()
                        logger.info("SSL handshake successful.")
                        break
                    except OpenSSL_SSL.WantReadError: # Use correct alias
                        # select() or other mechanism might be needed here in a real non-blocking scenario
                        # For blocking, this loop might just spin; consider adding select or short sleep
                        logger.debug("SSL WantRead during handshake, retrying...")
                        select.select([self._device], [self._device], [], 0.1) # Wait briefly
                    # Also consider WantWriteError if needed
            else:
                self._device = _sock # Assign the raw socket

            self._id = '{0}:{1}'.format(self._host, self._port)
            logger.info("Device opened successfully: %s", self._id)

        except socket.error as err:
            logger.error("Failed to open socket device at %s:%d - %s", self._host, self._port, err, exc_info=True)
            if _sock: _sock.close() # Clean up socket if connection failed partially
            raise NoDeviceError(f'Error opening device at {self._host}:{self._port}: {err}') from err
        except Exception as err: # Catch other potential errors (e.g., SSL setup)
             logger.error("Failed to open/setup device at %s:%d - %s", self._host, self._port, err, exc_info=True)
             if _sock and not self._device: _sock.close() # Clean up raw socket if SSL failed
             # Wrap generic errors too
             raise CommError(f"Failed to setup device: {err}") from err
        else:
            self._running = True
            self.on_open()

            if not no_reader_thread:
                logger.debug("Starting reader thread.")
                self._read_thread.start()

        return self

    def write(self, data: Union[str, bytes]) -> int:
        """
        Writes data to the device.

        :param data: data to write (str or bytes)
        :type data: Union[str, bytes]

        :returns: number of bytes sent
        :raises: :py:class:`~alarmdecoder.util.CommError`, TypeError
        """
        if self._device is None:
             raise CommError("Device not open.")

        data_sent: Optional[int] = None
        encoded_data: bytes

        # Define exceptions to catch based on OpenSSL availability
        comm_exceptions_to_catch: Tuple[type[Exception], ...] = (socket.error,)
        if have_openssl:
            comm_exceptions_to_catch += (OpenSSL_SSL.Error,)

        try:
            # Ensure data is bytes
            if isinstance(data, str):
                encoded_data = data.encode('utf-8')
            elif isinstance(data, bytes):
                encoded_data = data
            else:
                raise TypeError(f"Data must be str or bytes, not {type(data).__name__}")

            logger.debug("Writing to %s: %r", self._id, encoded_data)
            data_sent = self._device.send(encoded_data) # send() returns int bytes sent

            if data_sent == 0 and len(encoded_data) > 0:
                logger.warning("Attempted to write %d bytes to %s, but send() returned 0.", len(encoded_data), self._id)
                # Treat sending 0 bytes as an error
                raise CommError('Error writing to device (sent 0 bytes).')

            # Emit event if write was successful
            if hasattr(self, 'on_write'):
                 # Pass the bytes that were actually sent
                 self.on_write(data=encoded_data[:data_sent])
            logger.debug("Wrote %d bytes successfully.", data_sent)

        except comm_exceptions_to_catch as err:
            # Catch socket.error and OpenSSL_SSL.Error (if applicable)
            logger.error("Communication error during write on %s.", self._id, exc_info=True)
            raise CommError(f'Error writing to device: {err}') from err
        except TypeError as type_err: # Catch TypeError from encoding check
             logger.error("Invalid data type for write: %s", type_err, exc_info=True)
             raise type_err # Re-raise
        except Exception as general_err: # Catch any other unexpected errors
            logger.error("Unexpected error during write operation on %s.", self._id, exc_info=True)
            raise CommError(f'Unexpected error writing to device: {general_err}') from general_err

        # Ensure we return an int
        return data_sent if data_sent is not None else 0

    def read(self) -> str: # Add return type hint
        """
        Reads a single character (byte) from the device.

        :returns: character read from the device
        :raises: :py:class:`~alarmdecoder.util.CommError`
        """
        if self._device is None:
             raise CommError("Device not open.")

        data = b'' # Read bytes

        # Define communication exceptions
        comm_exceptions_to_catch: Tuple[type[Exception], ...] = (socket.error,)
        ssl_specific_exceptions = ()
        if have_openssl:
            # OpenSSL might raise WantReadError/WantWriteError during recv/send
            # SysCallError is often for lower-level issues during read/write
            comm_exceptions_to_catch += (OpenSSL_SSL.Error,)
            ssl_specific_exceptions = (OpenSSL_SSL.WantReadError, OpenSSL_SSL.SysCallError)


        try:
            # Use select for non-blocking check with a short timeout
            read_ready, _, _ = select.select([self._device], [], [], 0.1) # Short timeout

            if read_ready:
                data = self._device.recv(1) # Read 1 byte
                if data == b'':
                     # Socket closed by peer
                     logger.warning("Device %s closed connection during read.", self._id)
                     raise CommError("Connection closed by peer.")

        except ssl_specific_exceptions as ssl_err:
            ssl_err: OpenSSL_SSL.SysCallError
            # Specifically ignore WantReadError if non-blocking, or handle SysCallError
            if isinstance(ssl_err, OpenSSL_SSL.WantReadError):
                  logger.debug("SSL WantRead during single byte read.")
                  # Return empty string as if no data was ready immediately
                  return ""
            else: # SysCallError
                 errno, msg = ssl_err.args
                 logger.error("SSL SysCallError during read on %s: %s (%d)", self._id, msg, errno, exc_info=True)
                 raise CommError(f'SSL syscall error while reading from device: {msg} ({errno})') from ssl_err

        except comm_exceptions_to_catch as err:
            logger.error("Communication error during read on %s.", self._id, exc_info=True)
            raise CommError(f'Error while reading from device: {str(err)}') from err
        except Exception as general_err: # Catch any other unexpected errors
            logger.error("Unexpected error during read operation on %s.", self._id, exc_info=True)
            raise CommError(f'Unexpected error reading from device: {general_err}') from general_err


        # Decode assuming utf-8, handle potential errors gracefully
        try:
             decoded_data = data.decode('utf-8')
             logger.debug("Read from %s: %r", self._id, decoded_data)
             return decoded_data
        except UnicodeDecodeError:
             logger.warning("Read non-utf8 byte from %s: %r", self._id, data)
             # Decide how to handle non-utf8 bytes - return replacement char or raise?
             return data.decode('utf-8', errors='replace')


    def read_line(self, timeout: float = 0.0, purge_buffer: bool = False) -> str: # Add hints
        """
        Reads a line from the device.

        :param timeout: read timeout in seconds. 0 for non-blocking check, >0 for blocking with timeout.
        :type timeout: float
        :param purge_buffer: Indicates whether to purge the buffer prior to
                             reading.
        :type purge_buffer: bool

        :returns: line that was read (without trailing newline chars)
        :raises: :py:class:`~alarmdecoder.util.CommError`, :py:class:`~alarmdecoder.util.TimeoutError`
        """
        if self._device is None:
             raise CommError("Device not open.")

        # Purge internal buffer if requested
        if purge_buffer:
            self._buffer = b''

        # Check if a line is already in the buffer
        try:
            line_end = self._buffer.index(b"\n")
            ret = self._buffer[:line_end].rstrip(b"\r")
            self._buffer = self._buffer[line_end+1:]
            decoded_ret = ret.decode('utf-8', errors='replace') # Decode here
            logger.debug("Read from buffer: %s", decoded_ret)
            self.on_read(data=ret) # Emit event with original bytes
            return decoded_ret
        except ValueError:
            pass # No newline found yet

        # Set up for reading from socket
        start_time = time.time() # Need import time
        got_line = False
        ret = b''

        # Define communication exceptions
        comm_exceptions_to_catch: Tuple[type[Exception], ...] = (socket.error,)
        ssl_specific_exceptions = ()
        if have_openssl:
            comm_exceptions_to_catch += (OpenSSL_SSL.Error,)
            ssl_specific_exceptions = (OpenSSL_SSL.WantReadError, OpenSSL_SSL.SysCallError)

        try:
            while True:
                # Calculate remaining timeout
                time_elapsed = time.time() - start_time
                remaining_timeout = max(0.0,
                                        timeout - time_elapsed) if timeout > 0.0 else 0.05  # Short poll if timeout=0

                # Wait for data availability
                read_ready, _, _ = select.select([self._device], [], [], remaining_timeout)

                if not read_ready:
                    # Timeout occurred
                    elapsed = time.time() - start_time

                    if timeout > 0.0 and elapsed >= timeout:
                        logger.warning("Timeout waiting for line terminator on %s", self._id)
                        raise TimeoutError('Timeout while waiting for line terminator.')
                    elif timeout == 0.0:  # Non-blocking check failed
                        raise TimeoutError('No line immediately available (non-blocking).')
                    else:
                        continue  # Retry the loop

                # Data is ready, read a chunk
                try:
                     # Read a larger chunk for efficiency
                     chunk = self._device.recv(128)
                     if chunk == b'':
                          logger.warning("Device %s closed connection during read_line.", self._id)
                          raise CommError("Connection closed by peer.")

                     logger.debug("Read chunk: %r", chunk)
                     self._buffer += chunk

                     # Check for newline in the updated buffer
                     try:
                          line_end = self._buffer.index(b"\n")
                          ret = self._buffer[:line_end].rstrip(b"\r")
                          self._buffer = self._buffer[line_end+1:]
                          got_line = True
                          break # Exit the while loop
                     except ValueError:
                          continue # No newline yet, continue reading

                except ssl_specific_exceptions as ssl_err:
                     # Specifically handle WantReadError and SysCallError during recv
                     if isinstance(ssl_err, OpenSSL_SSL.WantReadError):
                          logger.debug("SSL WantRead during read_line chunk.")
                          # Continue loop after select indicated readability, maybe need more data
                          continue
                     else: # SysCallError
                         errno, msg = ssl_err.args
                         logger.error("SSL SysCallError during read_line on %s: %s (%d)", self._id, msg, errno, exc_info=True)
                         raise CommError(f'SSL syscall error while reading from device: {msg} ({errno})') from ssl_err


        except comm_exceptions_to_catch as err:
            logger.error("Communication error during read_line on %s.", self._id, exc_info=True)
            raise CommError(f'Error reading from device: {str(err)}') from err
        except TimeoutError:
             raise # Re-raise timeout explicitly caught logic
        except Exception as general_err:
            logger.error("Unexpected error during read_line operation on %s.", self._id, exc_info=True)
            raise CommError(f'Unexpected error reading line from device: {general_err}') from general_err

        # Process result if a line was found
        if got_line:
            decoded_ret = ret.decode('utf-8', errors='replace') # Decode here
            logger.debug("Read line: %s", decoded_ret)
            self.on_read(data=ret) # Emit event with original bytes
            return decoded_ret
        else:
            # Should be unreachable if timeout logic is correct, but safeguard
            raise TimeoutError('Timeout while waiting for line terminator (end of function).')


    # ... (purge remains the same) ...

    def _init_ssl(self, sock: socket.socket) -> 'OpenSSL_SSL.Connection':
        """
        Initializes our device as an SSL connection, wrapping the provided socket.

        :param sock: The raw socket to wrap.
        :returns: The SSL Connection object.
        :raises: :py:class:`~alarmdecoder.util.CommError`, ImportError
        """

        if not have_openssl:
            raise ImportError('SSL sockets have been disabled due to missing requirement: pyopenssl.')

        try:
            # Use the correct alias OpenSSL_SSL
            ctx = OpenSSL_SSL.Context(OpenSSL_SSL.TLSv1_METHOD) # Or newer TLS method if appropriate

            if self.ssl_key:
                logger.debug("Loading SSL private key: %s", self.ssl_key if isinstance(self.ssl_key, str) else "PKey object")
                if isinstance(self.ssl_key, crypto.PKey):
                    ctx.use_privatekey(self.ssl_key)
                else:
                    ctx.use_privatekey_file(self.ssl_key)

            if self.ssl_certificate:
                logger.debug("Loading SSL certificate: %s", self.ssl_certificate if isinstance(self.ssl_certificate, str) else "X509 object")
                if isinstance(self.ssl_certificate, crypto.X509):
                    ctx.use_certificate(self.ssl_certificate)
                else:
                    ctx.use_certificate_file(self.ssl_certificate)

            # CA Verification setup
            verify_method = OpenSSL_SSL.VERIFY_PEER
            if self._ssl_allow_self_signed:
                logger.warning("Allowing self-signed SSL certificates (VERIFY_NONE).")
                verify_method = OpenSSL_SSL.VERIFY_NONE
            else:
                 logger.debug("Setting SSL verify mode to VERIFY_PEER.")


            if self.ssl_ca:
                logger.debug("Loading SSL CA certificate(s): %s", self.ssl_ca if isinstance(self.ssl_ca, str) else "X509 object")
                # load_verify_locations can handle a file or directory path
                ca_path = self.ssl_ca if isinstance(self.ssl_ca, str) else None
                ca_file = ca_path if ca_path and os.path.isfile(ca_path) else None # Need import os
                ca_dir = ca_path if ca_path and os.path.isdir(ca_path) else None
                if ca_file or ca_dir:
                     ctx.load_verify_locations(ca_file, ca_dir)
                elif isinstance(self.ssl_ca, crypto.X509):
                     store = ctx.get_cert_store()
                     store.add_cert(self.ssl_ca)
                else:
                     logger.warning("SSL CA certificate path/object is invalid: %s", self.ssl_ca)
                     # Decide if this is an error or just proceed without custom CA
                     # raise CommError("Invalid SSL CA certificate provided.")

            # Only set verify if not allowing self-signed OR if a CA is explicitly provided
            if verify_method == OpenSSL_SSL.VERIFY_PEER:
                 ctx.set_verify(verify_method, self._verify_ssl_callback)
            elif self._ssl_allow_self_signed:
                 # If allowing self-signed, still use VERIFY_NONE but callback might not be needed?
                 # PyOpenSSL docs suggest VERIFY_NONE means callback is not called for cert errors.
                 ctx.set_verify(OpenSSL_SSL.VERIFY_NONE, lambda conn, cert, errno, depth, ok: True) # Dummy callback if needed


            logger.debug("Creating SSL connection object.")
            # Wrap the provided socket
            ssl_conn = OpenSSL_SSL.Connection(ctx, sock)
            ssl_conn.set_connect_state() # Set to client mode
            return ssl_conn


        except OpenSSL_SSL.Error as err: # Use correct alias
            logger.error("Failed to configure SSL context.", exc_info=True)
            raise CommError('Error setting up SSL connection.', err) from err
        except Exception as err: # Catch other errors like file not found
            logger.error("Unexpected error during SSL initialization.", exc_info=True)
            raise CommError(f'Error setting up SSL connection: {err}') from err


    def _verify_ssl_callback(self, connection, x509, errnum, errdepth, ok):
        """
        SSL verification callback. Logs verification issues.
        """
        # This callback is primarily useful for logging or complex verification.
        # The actual acceptance/rejection is often based on the errnum/ok status
        # and the VERIFY_ flags set on the context.
        if not ok:
             cert_subject = x509.get_subject()
             cert_issuer = x509.get_issuer()
             logger.warning(
                 "SSL Certificate Verification Error: errnum=%s, errdepth=%s, subject=%s, issuer=%s",
                 errnum, errdepth, cert_subject, cert_issuer
             )
             # If VERIFY_PEER is set, returning False here (or just letting ok=False pass)
             # will cause the handshake to fail. If VERIFY_NONE, this might still be called
             # but returning False might not matter. Check pyOpenSSL docs for specifics.

        # Return ok to accept based on default verification, or implement custom logic.
        # If self._ssl_allow_self_signed, we probably want to return True regardless of 'ok'
        # if the error is related to self-signed certs (needs specific errnum check).
        # However, setting VERIFY_NONE might be sufficient.
        # For simplicity now, just return ok.
        return ok

    @property
    def ssl_key(self):
        return self._ssl_key

    @property
    def ssl_certificate(self):
        return self._ssl_certificate

    @property
    def ssl_ca(self):
        return self._ssl_ca
