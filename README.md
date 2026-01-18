# Omni Meeting Recorder (omr)

[日本語](README.ja.md) | English

A Windows CLI tool for recording online meeting audio. Capture both remote participants' voices (system audio) and your own voice (microphone) simultaneously, even when using headphones.

## Features

- **System Audio Recording (Loopback)**: Capture audio output to speakers/headphones
- **Microphone Recording**: Record microphone input
- **Simultaneous Recording**: Record both mic and system audio together (stereo split or mixed)
- **No Virtual Audio Cable Required**: Direct WASAPI Loopback support
- **Simple CLI**: Start/stop recording with easy commands

## Requirements

- Windows 10/11
- Python 3.11+
- uv (recommended) or pip

## Installation

### 1. Install Python

If Python 3.11+ is not installed:

1. Download Windows installer from [Python official site](https://www.python.org/downloads/)
2. Run installer with **"Add Python to PATH" checked**
3. Verify in PowerShell:
   ```powershell
   python --version
   # Should show Python 3.11.x or higher
   ```

### 2. Install uv (Recommended)

uv is a fast Python package manager.

**Run in PowerShell:**
```powershell
# Install uv
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Verify installation
uv --version
```

Or install via pip:
```powershell
pip install uv
```

### 3. Install omr

#### Option A: Clone from GitHub (for developers)

```powershell
# Clone repository
git clone https://github.com/dobachi/omni-meeting-recorder.git
cd omni-meeting-recorder

# Install dependencies
uv sync

# Verify installation
uv run omr --version
uv run omr --help
```

#### Option B: Install via pip (for users)

```powershell
# Install from PyPI (after publication)
pip install omni-meeting-recorder

# Or install directly from GitHub
pip install git+https://github.com/dobachi/omni-meeting-recorder.git

# Verify installation
omr --version
```

## Quick Start

```bash
# List available devices
omr devices

# Record system audio (Loopback)
omr start --loopback

# Record microphone
omr start --mic

# Record both (stereo split: left=mic, right=system)
omr start --loopback --mic

# Record both (mixed mode)
omr start --loopback --mic --mix

# Specify output file
omr start --loopback --output meeting.wav

# Specify device by index
omr start --loopback --loopback-device 5
```

Press `Ctrl+C` to stop recording.

## Testing Your Setup

### Step 1: Check Device List

```powershell
# If installed with uv
uv run omr devices

# If installed with pip
omr devices
```

**Expected output:**
```
                    Recording Devices
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Index  ┃ Type     ┃ Name                           ┃ Channels   ┃ Sample Rate  ┃ Default  ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 0      │ MIC      │ Microphone (Realtek Audio)     │     2      │    44100 Hz  │    *     │
│ 3      │ LOOP     │ Speakers (Realtek Audio)       │     2      │    48000 Hz  │          │
└────────┴──────────┴────────────────────────────────┴────────────┴──────────────┴──────────┘
```

- **MIC**: Microphone devices
- **LOOP**: Loopback devices (can capture system audio)
- **\***: Default device

### Step 2: Test System Audio (Loopback) Recording

1. Play audio (e.g., YouTube)
2. Start recording:
   ```powershell
   uv run omr start --loopback
   ```
3. Wait a few seconds, then press `Ctrl+C` to stop
4. Play the generated `recording_YYYYMMDD_HHMMSS.wav` to verify

### Step 3: Test Microphone Recording

1. While speaking into the microphone:
   ```powershell
   uv run omr start --mic
   ```
2. Press `Ctrl+C` to stop
3. Play the generated WAV file to verify

### Step 4: Test Simultaneous Recording

```powershell
# Record both mic and system audio (stereo split)
uv run omr start --loopback --mic

# Record with specific devices
uv run omr start --loopback --mic --loopback-device 3 --mic-device 0
```

## Commands

### `omr devices`

List available audio devices.

```bash
omr devices           # Recording devices (mic + loopback)
omr devices --all     # All devices (including output)
omr devices --mic     # Microphone only
omr devices --loopback  # Loopback devices only
```

### `omr start`

Start recording.

```bash
omr start --loopback           # Record system audio
omr start --mic                # Record microphone
omr start --loopback --mic     # Record both (stereo split)
omr start --loopback --mic --mix  # Record both (mixed)
omr start -o output.wav        # Specify output file
```

## Troubleshooting

### "No devices found"

- Check that audio devices are enabled in Windows Sound settings
- Go to "Sound settings" → "Sound Control Panel" and enable disabled devices

### Loopback device not showing

- Verify output device (speakers/headphones) is connected and enabled
- Ensure WASAPI-compatible audio driver is installed

### Recording file is silent

- Verify system audio is actually playing during recording
- Check you're selecting the correct device with `omr devices --all`
- Try a different loopback device: `--loopback-device <index>`

### PyAudioWPatch installation error

PyAudioWPatch only supports Windows. On Linux/macOS, only tests can be run.

```powershell
# Manually install PyAudioWPatch
pip install PyAudioWPatch
```

## Known Limitations

### Echo in Dual Recording Mode (Mic + Loopback)

When recording with both `--mic` and `--loopback` options while using **speakers** (not headphones), the microphone may pick up audio from the speakers. This results in echo or doubled audio in the recording.

**Workaround**: Use headphones instead of speakers when using dual recording mode. This prevents the microphone from capturing the speaker output.

```powershell
# The CLI will display a warning when using both options
uv run omr start --mic --loopback
# Warning: Using mic and loopback together may cause echo if speakers are used.
# Recommendation: Use headphones to prevent microphone from picking up speaker audio.
```

See [Issue #6](https://github.com/dobachi/omni-meeting-recorder/issues/6) for more details and future plans for software-based echo cancellation.

## Development

### Setup Development Environment

```bash
# Install dependencies (including dev)
make dev-install
# Or: uv sync --extra dev
```

### Running Checks

Use `make` to run linting, type checking, and tests:

```bash
# Run all checks (lint + typecheck + test)
make check

# Or run individually:
make lint       # Run ruff linter
make typecheck  # Run mypy type checker
make test       # Run pytest

# Other useful commands:
make lint-fix   # Auto-fix lint issues
make format     # Format code with ruff
make test-cov   # Run tests with coverage
make clean      # Clean up cache files
make help       # Show all available commands
```

### Project Structure

```
omni-meeting-recorder/
├── src/omr/
│   ├── cli/
│   │   ├── main.py           # CLI entry point
│   │   └── commands/
│   │       ├── record.py     # Recording command
│   │       └── devices.py    # Device list
│   ├── core/
│   │   ├── audio_capture.py  # Audio capture abstraction
│   │   ├── device_manager.py # Device detection/management
│   │   └── mixer.py          # Audio mixing/resampling
│   ├── backends/
│   │   └── wasapi.py         # Windows WASAPI implementation
│   └── config/
│       └── settings.py       # Settings management
├── tests/
├── pyproject.toml
└── README.md
```

## Roadmap

- [x] Phase 1: MVP
  - [x] Device list display
  - [x] System audio recording (Loopback)
  - [x] Microphone recording
  - [x] WAV format output
  - [x] Stop with Ctrl+C

- [x] Phase 2: Simultaneous Recording
  - [x] Mic + system audio simultaneous recording
  - [x] Stereo split mode (left=mic, right=system)
  - [x] Timestamp synchronization

- [ ] Phase 3: Encoding
  - [ ] FLAC output support
  - [ ] MP3 output support
  - [ ] Configuration file support

- [ ] Phase 4: Stability & UX
  - [ ] Long-duration recording stability
  - [ ] Device disconnection handling
  - [ ] Recording status display improvements
  - [ ] Background recording support

## License

MIT License
