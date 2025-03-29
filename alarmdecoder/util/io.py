"""
alarmdecoder.util.io

Utility functions for byte handling, firmware file parsing,
and low-level data manipulation for AlarmDecoder devices.
"""

import os
import select
from typing import Union

from alarmdecoder.util.exceptions import UploadChecksumError, UploadError

def bytes_available(device) -> int:
    """
    Checks how many bytes are available to be read on a device (serial/socket).
    """
    try:
        r, _, _ = select.select([device], [], [], 0)
        return 1 if device in r else 0
    except Exception:
        return 0

def bytes_hack(buf: Union[str, bytes]) -> bytes:
    """
    Ensures a bytes-compatible object from str or bytes input.
    Legacy compatibility for byte operations.
    """
    return buf.encode("utf-8") if isinstance(buf, str) else buf

def filter_ad2prot_byte(buf: bytes) -> bytes:
    """
    Filters out special control characters from AlarmDecoder protocol stream.
    """
    return bytes([b for b in buf if b >= 0x20 and b != 0x7F])

def read_firmware_file(file_path: str) -> list[str]:
    """
    Reads an Intel HEX firmware file and returns a cleaned list of lines.

    Raises:
        UploadChecksumError: If a checksum mismatch is detected.
        UploadError: If the data is malformed or incorrect.
    """
    with open(file_path, "r") as hexfile:
        lines = []
        for line_number, line in enumerate(hexfile, 1):
            line = line.strip()
            if not line.startswith(":"):
                continue

            # Verify checksum (Intel HEX format)
            try:
                byte_data = bytes.fromhex(line[1:])
                checksum = sum(byte_data) & 0xFF
                if checksum != 0:
                    raise UploadChecksumError(f"Checksum error on line {line_number} of {file_path}")
            except Exception:
                raise UploadError("Incorrect data sent to bootloader.")

            lines.append(line)

        return lines
