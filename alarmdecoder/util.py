"""
Provides utility classes for the `AlarmDecoder`_ (AD2) devices.

.. _AlarmDecoder: http://www.alarmdecoder.com

.. moduleauthor:: Scott Petersen <scott@nutech.com>
"""

import select
import time

import alarmdecoder
from alarmdecoder.util.io import bytes_available, read_firmware_file


class NoDeviceError(Exception):
    """
    No devices found.
    """
    pass


class CommError(Exception):
    """
    There was an error communicating with the device.
    """
    pass


class TimeoutError(Exception):
    """
    There was a timeout while trying to communicate with the device.
    """
    pass


class InvalidMessageError(Exception):
    """
    The format of the panel message was invalid.
    """
    pass


class UploadError(Exception):
    """
    Generic firmware upload error.
    """
    pass


class UploadChecksumError(UploadError):
    """
    The firmware upload failed due to a checksum error.
    """
    pass


class Firmware:
    """
    Represents firmware for the `AlarmDecoder`_ devices.
    """

    # Constants
    STAGE_START = 0
    STAGE_WAITING = 1
    STAGE_BOOT = 2
    STAGE_WAITING_ON_LOADER = 2.5
    STAGE_LOAD = 3
    STAGE_UPLOADING = 4
    STAGE_DONE = 5
    STAGE_ERROR = 98
    STAGE_DEBUG = 99

    @staticmethod
    def read(device):
        """
        Reads data from the specified device.

        :param device: the AlarmDecoder device
        :type device: :py:class:`~alarmdecoder.devices.Device`

        :returns: string
        """
        response = None
        bytes_avail = bytes_available(device)

        if isinstance(device, alarmdecoder.devices.SerialDevice):
            response = device._device.read(bytes_avail)
        elif isinstance(device, alarmdecoder.devices.SocketDevice):
            response = device._device.recv(bytes_avail)

        return response

    @staticmethod
    def upload(device, file_path, progress_callback=None, debug=False):
        """
        Uploads firmware to an `AlarmDecoder`_ device.

        :param file_path: firmware file path
        :type file_path: string
        :param progress_callback: callback function used to report progress
        :type progress_callback: function

        :raises: :py:class:`~alarmdecoder.util.NoDeviceError`, :py:class:`~alarmdecoder.util.TimeoutError`
        """

        def progress_stage(stage, **kwargs):
            """Callback to update progress for the specified stage."""
            if progress_callback is not None:
                progress_callback(stage, **kwargs)

            return stage

        if device is None:
            raise NoDeviceError('No device specified for firmware upload.')

        fds = [device._device.fileno()]

        # Read firmware file into memory
        try:
            write_queue = read_firmware_file(file_path)
        except OSError as err:
            stage = progress_stage(Firmware.STAGE_ERROR, error=str(err))
            return

        data_read = ''
        got_response = False
        running = True
        stage = progress_stage(Firmware.STAGE_START)

        if device.is_reader_alive():
            # Close the reader thread and wait for it to die, otherwise
            # it interferes with our reading.
            device.stop_reader()
            while device._read_thread.is_alive():
                stage = progress_stage(Firmware.STAGE_WAITING)
                time.sleep(0.5)

            time.sleep(3)

        try:
            while running:
                rr, wr, _ = select.select(fds, fds, [], 0.5)

                if len(rr) != 0:
                    response = Firmware.read(device)

                    for c in response:
                        # HACK: Python 3 / PySerial hack.
                        if isinstance(c, int):
                            c = chr(c)

                        if c == '\xff' or c == '\r':  # HACK: odd case for our mystery \xff byte.
                            # Boot started, start looking for the !boot message
                            if data_read.startswith("!sn"):
                                stage = progress_stage(Firmware.STAGE_BOOT)
                            # Entered bootloader upload mode, start uploading
                            elif data_read.startswith("!load"):
                                got_response = True
                                stage = progress_stage(Firmware.STAGE_UPLOADING)
                            # Checksum error
                            elif data_read == '!ce':
                                running = False
                                raise UploadChecksumError(f"Checksum error in {file_path}")
                            # Bad data
                            elif data_read == '!no':
                                running = False
                                raise UploadError("Incorrect data sent to bootloader.")
                            # Firmware upload complete
                            elif data_read == '!ok':
                                running = False
                                stage = progress_stage(Firmware.STAGE_DONE)
                            # All other responses are valid during upload.
                            else:
                                got_response = True
                                if stage == Firmware.STAGE_UPLOADING:
                                    progress_stage(stage)

                            data_read = ''
                        elif c == '\n':
                            pass
                        else:
                            data_read += c

                if len(wr) != 0:
                    # Reboot device
                    if stage in [Firmware.STAGE_START, Firmware.STAGE_WAITING]:
                        device.write('=')
                        stage = progress_stage(Firmware.STAGE_WAITING_ON_LOADER)

                    # Enter bootloader
                    elif stage == Firmware.STAGE_BOOT:
                        device.write('=')
                        stage = progress_stage(Firmware.STAGE_LOAD)

                    # Upload firmware
                    elif stage == Firmware.STAGE_UPLOADING:
                        if len(write_queue) > 0 and got_response:
                            got_response = False
                            device.write(write_queue.popleft())

        except UploadError as err:
            stage = progress_stage(Firmware.STAGE_ERROR, error=str(err))
        else:
            stage = progress_stage(Firmware.STAGE_DONE)
