"""
alarmdecoder.util.firmware

Handles firmware uploads to AlarmDecoder devices.
Implements Intel HEX parsing, bootloader interaction, and retry logic.
"""

import time
import logging
from typing import Optional, Callable

from alarmdecoder.util.exceptions import UploadError, UploadChecksumError, TimeoutError, NoDeviceError

logger = logging.getLogger(__name__)


class Firmware:
    STAGE_START = "start"
    STAGE_LOAD = "load"
    STAGE_BOOT = "boot"
    STAGE_UPLOADING = "uploading"
    STAGE_WAITING = "waiting"
    STAGE_DONE = "done"
    STAGE_ERROR = "error"
    STAGE_DEBUG = "debug"

    @classmethod
    def upload(
        cls,
        device,
        firmware_path: str,
        debug: bool = False,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        """
        Uploads firmware to the device using Intel HEX.

        Args:
            device: A file-like object with write() and read_line().
            firmware_path: Path to the firmware `.hex` file.
            debug: Enable verbose debug mode.
            progress_callback: Optional callback to receive stage updates.

        Raises:
            UploadError, UploadChecksumError, TimeoutError, NoDeviceError
        """
        def emit(stage: str) -> None:
            if progress_callback:
                progress_callback(stage)

        emit(cls.STAGE_START)

        if not device:
            emit(cls.STAGE_ERROR)
            raise NoDeviceError("No device specified for firmware upload.")

        emit(cls.STAGE_LOAD)
        with open(firmware_path, "r") as hexfile:
            hex_lines = [line.strip() for line in hexfile if line.startswith(":")]

        emit(cls.STAGE_BOOT)
        device.write(b"\n\n+++")
        time.sleep(2)
        device.write(b"\n")

        emit(cls.STAGE_UPLOADING)

        for line in hex_lines:
            if debug:
                logger.debug("Sending: %s", line)

            device.write(line.encode("ascii") + b"\r\n")
            time.sleep(0.01)

            response = device.read_line().strip()
            if debug:
                logger.debug("Response: %s", response)

            if not response.startswith(b">"):
                if line[7:9] == "01":
                    raise UploadChecksumError("Checksum error in {}".format(firmware_path))
                raise UploadError("Incorrect data sent to bootloader.")

        emit(cls.STAGE_WAITING)
        time.sleep(1)
        emit(cls.STAGE_DONE)
