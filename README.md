# Omni Meeting Recorder (omr)

[日本語](README.ja.md) | English

A Windows CLI tool for recording online meeting audio. Capture both remote participants' voices (system audio) and your own voice (microphone) simultaneously, even when using speakers or headphones.

## Features

- **System Audio Recording (Loopback)**: Capture audio output to speakers/headphones
- **Microphone Recording**: Record microphone input
- **Simultaneous Recording**: Record both mic and system audio together (default mode)
- **Acoustic Echo Cancellation (AEC)**: Software echo cancellation for speaker use
- **Automatic Volume Normalization**: Match mic and system audio levels
- **MP3 Output**: Direct MP3 encoding with configurable bitrate
- **No Virtual Audio Cable Required**: Direct WASAPI Loopback support
- **Simple CLI**: Start recording with a single command

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

## Usage

```bash
omr start
```

That's it! Press `Ctrl+C` to stop. Output: `recording_YYYYMMDD_HHMMSS.mp3`

## Quick Start

```bash
# List available devices
omr devices

# Record with custom filename
omr start -o meeting.mp3

# Record system audio only
omr start -L -o system.mp3

# Record microphone only
omr start -M -o mic.mp3

# Disable AEC (if using headphones)
omr start --no-aec -o meeting.mp3

# Output as WAV instead of MP3
omr start -f wav -o meeting.wav

# Stereo split mode (left=mic, right=system)
omr start --stereo-split -o meeting.mp3

# Specify device by index
omr start --loopback-device 5 --mic-device 0 -o meeting.mp3
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

### Step 2: Test Default Recording (Mic + System)

1. Play audio (e.g., YouTube) and speak into the microphone
2. Start recording:
   ```powershell
   uv run omr start -o test.mp3
   ```
3. Wait a few seconds, then press `Ctrl+C` to stop
4. Play the generated MP3 to verify both sources are captured

### Step 3: Test System Audio Only

```powershell
uv run omr start -L -o system.mp3
```

### Step 4: Test Microphone Only

```powershell
uv run omr start -M -o mic.mp3
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

Start recording. By default, records both mic and system audio with AEC enabled.

```bash
omr start                      # Record mic + system (default)
omr start -o meeting.mp3       # Specify output file
omr start -L                   # Record system audio only (--loopback-only)
omr start -M                   # Record microphone only (--mic-only)
omr start --no-aec             # Disable echo cancellation
omr start --stereo-split       # Stereo: left=mic, right=system
omr start -f wav               # Output as WAV instead of MP3
omr start -b 192               # MP3 bitrate 192kbps (default: 128)
```

**Options:**

| Option | Description |
|--------|-------------|
| `-o`, `--output` | Output file path |
| `-L`, `--loopback-only` | Record system audio only |
| `-M`, `--mic-only` | Record microphone only |
| `--aec/--no-aec` | Enable/disable echo cancellation (default: enabled) |
| `--stereo-split/--mix` | Stereo split or mix mode (default: mix) |
| `-f`, `--format` | Output format: wav, mp3 (default: mp3) |
| `-b`, `--bitrate` | MP3 bitrate in kbps (default: 128) |
| `--mic-device` | Microphone device index |
| `--loopback-device` | Loopback device index |

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

## Acoustic Echo Cancellation (AEC)

When recording both mic and system audio while using **speakers**, the microphone picks up audio from the speakers. This causes echo in the recording.

**Solution**: AEC is enabled by default and removes this echo using the [pyaec](https://pypi.org/project/pyaec/) library.

```powershell
# AEC is enabled by default
omr start -o meeting.mp3

# Disable AEC if using headphones (slightly better audio quality)
omr start --no-aec -o meeting.mp3
```

**Note**: For best results, use headphones when possible. AEC works well but headphones provide the cleanest audio.

## Automatic Volume Normalization

Microphone and system audio often have significantly different volume levels. For example, if mic input is quiet while system audio is loud, the recorded audio will be unbalanced.

**Solution**: Automatic Gain Control (AGC) is enabled by default, normalizing both audio sources to a target level (~25% of 16-bit peak).

- Continuously measures RMS (Root Mean Square) of both mic and system audio
- Calculates average level from recent audio chunks
- Normalizes both sources to the same target level
- Gain is automatically adjusted within 0.5x to 6.0x range

## Development

### Setup Development Environment

```bash
# Install dependencies (including dev)
uv sync --extra dev
```

### Running Checks

Use `uv run task` to run linting, type checking, and tests:

```bash
# Run all checks (lint + typecheck + test)
uv run task check

# Or run individually:
uv run task lint       # Run ruff linter
uv run task typecheck  # Run mypy type checker
uv run task test       # Run pytest

# Other useful commands:
uv run task lint-fix   # Auto-fix lint issues
uv run task format     # Format code with ruff
uv run task test-cov   # Run tests with coverage
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

- [x] Phase 3: Audio Processing
  - [x] MP3 output support
  - [x] Acoustic Echo Cancellation (AEC)
  - [x] Automatic volume normalization
  - [ ] FLAC output support

- [ ] Phase 4: Stability & UX
  - [ ] Long-duration recording stability
  - [ ] Device disconnection handling
  - [ ] Recording status display improvements
  - [ ] Background recording support
  - [ ] Configuration file support

## License

MIT License
