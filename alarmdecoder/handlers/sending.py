# alarmdecoder/handlers/sending.py
from alarmdecoder.logger import get_logger
logger = get_logger(__name__)

def handle_sending(device, data):
    if "Sending.done" in data:
        device.on_sending_received.fire(device, True, data)
