"""
alarmdecoder.util.exceptions

Defines custom exception types used throughout the AlarmDecoder package.
These support granular error handling across devices, messages, and firmware utilities.
"""


class NoDeviceError(Exception):
    """Raised when no device is found for communication."""
    pass


class CommError(Exception):
    """Raised when a communication error occurs with the device."""
    pass


class TimeoutError(Exception):
    """Raised when a communication attempt times out."""
    pass


class InvalidMessageError(Exception):
    """Raised when a message from the panel is malformed or cannot be parsed."""
    pass


class UploadError(Exception):
    """Raised when a generic firmware upload error occurs."""
    pass


class UploadChecksumError(UploadError):
    """Raised when the firmware upload fails due to a checksum mismatch."""
    pass
