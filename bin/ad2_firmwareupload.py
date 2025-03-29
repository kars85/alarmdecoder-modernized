#!/usr/bin/env python3

import argparse
import os
import sys
import time
import logging
import traceback
import bin.ad2_firmwareupload as cli
from alarmdecoder.util.firmware import Firmware
from alarmdecoder.util.exceptions import UploadError, NoDeviceError
from alarmdecoder.devices import SerialDevice, SocketDevice


RETRIES = 3
RETRY_DELAY = 3  # seconds


def parse_args():
    parser = argparse.ArgumentParser(description="Upload firmware to an AlarmDecoder device.")
    parser.add_argument("firmware", help="Path to the firmware file.")
    parser.add_argument("device", help="Device path or host:port (e.g. /dev/ttyUSB0 or 192.168.0.10:10000)")
    parser.add_argument("--baudrate", type=int, default=115200, help="Baudrate for serial devices (default: 115200)")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def setup_logging(debug=False):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def get_device(device_path):
    if ':' in device_path:
        host, port = device_path.split(':')
        return SocketDevice(interface=(host, int(port)))
    else:
        return SerialDevice(interface=device_path)


def upload_firmware_with_retries(dev, firmware_path, debug=False):
    for attempt in range(1, RETRIES + 1):
        try:
            logging.info(f"Attempt {attempt} of {RETRIES} to upload firmware...")
            Firmware.upload(dev, firmware_path, debug=debug)
            logging.info("Firmware uploaded successfully.")
            return
        except UploadError as ex:
            logging.warning(f"Upload failed: {ex}")
        except Exception as ex:
            logging.error(f"Unexpected error: {ex}\n{traceback.format_exc()}")

        if attempt < RETRIES:
            logging.info(f"Retrying in {RETRY_DELAY} seconds...")
            time.sleep(RETRY_DELAY)

    logging.error("Firmware upload failed after all retry attempts.")
    raise RuntimeError("Firmware upload failed after retries.")


def main():
    args = parse_args()
    setup_logging(args.debug)

    logging.info(f"Flashing device: {args.device}")
    logging.info(f"Firmware path: {args.firmware}")
    logging.info(f"Baudrate: {args.baudrate}")

    dev = None
    try:
        dev = get_device(args.device)
        dev.open(baudrate=args.baudrate, no_reader_thread=True)
        time.sleep(3)
        upload_firmware_with_retries(dev, args.firmware, debug=args.debug)

    except NoDeviceError as ex:
        logging.error(f"No device found: {ex}")
    except Exception as ex:
        logging.error(f"Unexpected error: {ex}\n{traceback.format_exc()}")
    finally:
        if dev:
            dev.close()


if __name__ == "__main__":
    main()
