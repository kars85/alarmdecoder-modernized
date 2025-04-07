#!/usr/bin/env python3

import argparse
import logging
import select
import sys
import termios
import tty

from alarmdecoder.devices import SocketDevice


def parse_args():
    parser = argparse.ArgumentParser(description="SSL Terminal to AlarmDecoder device.")
    parser.add_argument("host_port", help="Host:port of the AlarmDecoder device (e.g. 192.168.1.2:10000)")
    parser.add_argument("ca_cert", help="Path to the CA certificate")
    parser.add_argument("client_cert", help="Path to the client certificate")
    parser.add_argument("client_key", help="Path to the client private key")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    return parser.parse_args()


def setup_logging(debug=False):
    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )


def save_terminal_settings():
    return termios.tcgetattr(sys.stdin.fileno())


def restore_terminal_settings(settings):
    termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, settings)


def ssl_terminal(device, running_flag):
    while running_flag[0]:
        readable, _, _ = select.select([sys.stdin, device._device], [], [], 0)

        for source in readable:
            if source == sys.stdin:
                data = source.read(1)
                if data == '\x03':  # CTRL-C
                    print("Exiting...")
                    running_flag[0] = False
                    break
                else:
                    device.write(data)
            else:
                data = source.read(1024)
                sys.stdout.write(data)
                sys.stdout.flush()


def main():
    args = parse_args()
    setup_logging(args.debug)

    host, port = args.host_port.split(':')
    port = int(port)

    old_term_settings = save_terminal_settings()
    tty.setraw(sys.stdin.fileno())

    running = [True]
    dev = None

    try:
        logging.info(f"Connecting to {host}:{port} with SSL")
        dev = SocketDevice(interface=(host, port))
        dev.ssl = True
        dev.ssl_cert = args.client_cert
        dev.ssl_key = args.client_key
        dev.ssl_ca = args.ca_cert

        dev.open(no_reader_thread=True)
        dev.write("\r\n")  # Prompt/init newline

        ssl_terminal(dev, running)
        logging.info("Connection closed.")

    except Exception as ex:
        logging.error(f"Error: {ex}")
    finally:
        if dev:
            dev.close()
        restore_terminal_settings(old_term_settings)


if __name__ == "__main__":
    main()