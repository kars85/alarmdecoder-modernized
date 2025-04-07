# alarmdecoder-modernized

**Modernized Python interface for the AlarmDecoder (AD2) family of alarm devices.**

This package provides event-driven control and monitoring for AD2USB, AD2SERIAL, AD2PI, and AD2 over IP (ser2sock) devices. Now rewritten to support Python 3.11+ with modern best practices.

## 🚀 Features

- Fully typed, Python 3.11+ compliant codebase
- Plug-and-play device abstractions (USB, Serial, Socket)
- LRR (Long Range Radio) and AUI message parsing
- Event-driven architecture using `on_*` hooks
- Config upload/download support
- Robust test suite using `pytest` and `unittest.mock`

## 🔧 Installation

```bash
pip install .
```

## 🧪 Testing

```bash
pytest
```

## 📦 CLI Tools

- `ad2-firmwareupload`: Upload firmware to any supported AlarmDecoder device.

## 📚 Documentation

Coming soon.

## 🤝 Contributing

Pull requests welcome. For major changes, please open an issue first to discuss.

## 📜 License

MIT License