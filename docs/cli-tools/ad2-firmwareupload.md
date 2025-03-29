# `ad2-firmwareupload`

**Purpose:**  
Uploads firmware to an AlarmDecoder device via serial or socket interface.

---

## 🔧 Usage

```bash
./bin/ad2-firmwareupload <firmware_path> <device> [--baudrate 115200] [--debug]

# Examples:
./bin/ad2-firmwareupload firmware.hex /dev/ttyUSB0
./bin/ad2-firmwareupload firmware.hex 192.168.0.10:10000 --debug


---

## 🐳 Running via Docker

If you have Docker installed, you can run this tool in a containerized environment with no setup:

```bash
docker build -t alarmdecoder-cli .
docker run --rm \
  --device=/dev/ttyAMA0 \
  -v $PWD:/app \
  alarmdecoder-cli firmware.hex /dev/ttyAMA0
