# Omni Meeting Recorder - Technical Design

## Architecture Overview

### Module Structure

```
src/omr/
├── cli/                    # Command-line interface
│   ├── main.py             # Typer app entry point
│   └── commands/
│       ├── record.py       # Recording command implementation
│       └── devices.py      # Device listing command
├── core/                   # Core audio processing
│   ├── audio_capture.py    # High-level capture abstraction
│   ├── device_manager.py   # Device detection and management
│   ├── mixer.py            # Audio mixing and resampling
│   ├── aec_processor.py    # Acoustic Echo Cancellation
│   ├── encoder.py          # Audio encoding (MP3/WAV)
│   └── input_handler.py    # Keyboard input handling
├── backends/
│   └── wasapi.py           # Windows WASAPI implementation
└── config/
    └── settings.py         # Configuration management
```

### Data Flow Diagram

```
┌─────────────────┐     ┌─────────────────┐
│   Microphone    │     │   Loopback      │
│   (WASAPI)      │     │   (WASAPI)      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    ┌─────────┐             ┌─────────┐
    │ Reader  │             │ Reader  │
    │ Thread  │             │ Thread  │
    └────┬────┘             └────┬────┘
         │                       │
         │ Queue                 │ Queue
         ▼                       ▼
    ┌────────────────────────────────┐
    │        Main Processing         │
    │  ┌──────────────────────────┐  │
    │  │   Resample to common     │  │
    │  │   sample rate            │  │
    │  └────────────┬─────────────┘  │
    │               │                │
    │  ┌────────────▼─────────────┐  │
    │  │   AEC Processing         │  │
    │  │   (if enabled)           │  │
    │  └────────────┬─────────────┘  │
    │               │                │
    │  ┌────────────▼─────────────┐  │
    │  │   AGC (Automatic Gain    │  │
    │  │   Control)               │  │
    │  └────────────┬─────────────┘  │
    │               │                │
    │  ┌────────────▼─────────────┐  │
    │  │   Stereo Mix / Split     │  │
    │  └────────────┬─────────────┘  │
    └───────────────┼────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │ StreamingMP3   │
           │ Encoder        │
           └───────┬────────┘
                   │
                   ▼
           ┌────────────────┐
           │   .mp3 File    │
           └────────────────┘
```

## WASAPI Loopback Mechanism

### How It Works

Windows Audio Session API (WASAPI) provides a "loopback" mode that allows capturing audio data being played to an output device. This is the key technology that enables omr to work without virtual audio cables.

```python
# Simplified concept (actual implementation in wasapi.py)
stream = pyaudio.open(
    input=True,
    input_device_index=loopback_device.index,  # Output device opened as input
    format=pyaudio.paInt16,
    channels=device.channels,
    rate=device.sample_rate,
    frames_per_buffer=chunk_size
)
```

### PyAudioWPatch Integration

omr uses [PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch), a fork of PyAudio that adds WASAPI loopback support:

1. **Device Enumeration**: Discovers all audio devices including loopback-capable endpoints
2. **Stream Creation**: Opens loopback streams with the correct WASAPI settings
3. **Data Capture**: Reads PCM data in real-time from the audio stream

### Device Detection Logic

```python
# Device types are determined by hostApi and device properties
def _determine_device_type(device_info, host_api_info):
    if host_api_info["name"] == "Windows WASAPI":
        if device_info.get("isLoopbackDevice"):
            return DeviceType.LOOPBACK
        elif device_info["maxInputChannels"] > 0:
            return DeviceType.MICROPHONE
    return DeviceType.OUTPUT
```

## Audio Processing Pipeline

### Dual Recording Synchronization

The main challenge in dual recording is keeping mic and loopback audio synchronized. omr solves this by:

1. **Master Clock**: Using loopback stream as the timing reference
2. **Queue-based Buffering**: Separate threads read from each device into queues
3. **Synchronized Extraction**: Main thread extracts matching amounts from both queues

```python
# Loopback drives the output timing (master clock)
if loopback_buffer:
    chunk_size = len(loopback_buffer)
    loopback_chunk = loopback_buffer[:]

    # Take matching amount from mic buffer
    mic_chunk = mic_buffer[:chunk_size]
```

### Resampling

Devices often have different native sample rates (e.g., mic at 44100Hz, speakers at 48000Hz). omr resamples mic audio to match loopback:

```python
def resample_simple(samples, from_rate, to_rate):
    """Linear interpolation resampling."""
    ratio = to_rate / from_rate
    new_length = int(len(samples) * ratio)

    resampled = []
    for i in range(new_length):
        pos = i / ratio
        idx = int(pos)
        frac = pos - idx
        # Linear interpolation between adjacent samples
        val = samples[idx] * (1 - frac) + samples[idx + 1] * frac
        resampled.append(int(val))
    return resampled
```

## Acoustic Echo Cancellation (AEC)

### Problem

When using speakers, the microphone picks up:
- Your voice (desired)
- Audio from speakers (echo/feedback)

### Solution: pyaec Library

omr uses the [pyaec](https://pypi.org/project/pyaec/) library which implements an adaptive filter algorithm for echo cancellation.

### How AEC Works

```
                 ┌─────────────┐
   Loopback ────▶│   pyaec     │
   (Reference)   │   AEC       │◀──── Mic (with echo)
                 │   Filter    │
                 └──────┬──────┘
                        │
                        ▼
                  Mic (echo removed)
```

The AEC algorithm:
1. Takes the loopback signal as a reference
2. Identifies how the reference appears in the mic signal (through room acoustics)
3. Subtracts the estimated echo from the mic signal

### Frame-based Processing

AEC requires fixed-size frames for processing:

```python
class AECProcessor:
    def __init__(self, sample_rate, frame_size, filter_length=None):
        self._frame_size = frame_size  # Typically 160-1024 samples
        self._filter_length = filter_length or frame_size * 10
        self._aec = Aec(
            frame_size=self._frame_size,
            filter_length=self._filter_length,
            sample_rate=sample_rate,
        )
        # Buffers for accumulating samples
        self._mic_buffer = []
        self._ref_buffer = []
```

Input samples are accumulated until a full frame is available, then processed:

```python
def process_samples(self, mic_samples, ref_samples):
    # Add to buffers
    self._mic_buffer.extend(mic_samples)
    self._ref_buffer.extend(ref_samples)

    # Process complete frames
    while len(self._mic_buffer) >= self._frame_size:
        mic_frame = self._mic_buffer[:self._frame_size]
        ref_frame = self._ref_buffer[:self._frame_size]

        processed = self._aec.cancel_echo(mic_frame, ref_frame)
        self._output_buffer.extend(processed)
```

## Automatic Gain Control (AGC)

### Problem

Mic and system audio often have very different volume levels, resulting in unbalanced recordings.

### Solution: RMS-based Level Normalization

1. **RMS Calculation**: Measure the "loudness" of each audio chunk

```python
def calc_rms(samples):
    """Root Mean Square - measures audio power."""
    sum_sq = sum(s * s for s in samples)
    return (sum_sq / len(samples)) ** 0.5
```

2. **Sliding Window Average**: Track RMS history for stable gain calculation

```python
mic_rms_history = []
agc_window = 100  # Number of chunks to average

if mic_rms > 50:  # Threshold to avoid amplifying silence
    mic_rms_history.append(mic_rms)
    if len(mic_rms_history) > agc_window:
        mic_rms_history.pop(0)
```

3. **Gain Calculation**: Compute gain to reach target level

```python
target_rms = 8000.0  # ~25% of 16-bit peak
avg_rms = sum(rms_history) / len(rms_history)
auto_gain = target_rms / avg_rms
auto_gain = max(0.5, min(6.0, auto_gain))  # Clamp to safe range
```

4. **Soft Clipping**: Prevent harsh distortion from over-amplification

```python
def apply_gain(samples, gain):
    result = []
    for s in samples:
        val = s * gain
        # Hard clip at 16-bit limits
        val = max(-32768, min(32767, val))
        result.append(int(val))
    return result
```

## Streaming MP3 Encoding

### Why Streaming?

Traditional approach:
1. Record to WAV (uncompressed, large file)
2. Convert to MP3 after recording

Problems:
- Large temporary files (WAV is ~10x larger than MP3)
- Conversion takes extra time
- Risk of data loss if conversion fails

### Streaming Solution

omr uses the [lameenc](https://pypi.org/project/lameenc/) library to encode audio to MP3 in real-time:

```python
class StreamingMP3Encoder:
    def __init__(self, output_path, sample_rate, channels, bitrate=128):
        self._encoder = lameenc.Encoder()
        self._encoder.set_bit_rate(bitrate)
        self._encoder.set_in_sample_rate(sample_rate)
        self._encoder.set_channels(channels)
        self._file = output_path.open("wb")

    def write(self, data):
        """Encode and write PCM data chunk."""
        mp3_data = self._encoder.encode(data)
        if mp3_data:
            self._file.write(mp3_data)

    def close(self):
        """Flush remaining data and close."""
        final_data = self._encoder.flush()
        self._file.write(final_data)
        self._file.close()
```

Benefits:
- Constant memory usage regardless of recording length
- Immediate MP3 output
- No post-processing required

## Threading Model

```
Main Thread                    Reader Threads
    │                              │
    │                    ┌─────────┴─────────┐
    │                    │                   │
    │               mic_reader          loopback_reader
    │                    │                   │
    │                    ▼                   ▼
    │               ┌─────────┐         ┌─────────┐
    │               │mic_queue│         │loop_queue│
    │               └────┬────┘         └────┬────┘
    │                    │                   │
    ▼                    ▼                   │
┌───────────────────────────────────────────┐│
│            Main Recording Loop            ││
│  - Drain queues                           ◀┘
│  - Process audio (AEC, AGC)               │
│  - Write to encoder                       │
└───────────────────────────────────────────┘
```

### Device Switching

Live device switching is supported through:

1. **Pause Event**: Signal reader threads to pause
2. **Stream Recreation**: Close old stream, create new one
3. **Buffer Clear**: Clear queues to avoid mixing old/new device data
4. **Resume**: Signal threads to continue

## Configuration

### AudioSettings (config/settings.py)

```python
class AudioSettings:
    sample_rate: int = 48000    # Default output sample rate
    channels: int = 2           # Stereo output
    chunk_size: int = 1024      # Frames per buffer
    bit_depth: int = 16         # 16-bit audio
```

### Recording Options

| Option | Description | Default |
|--------|-------------|---------|
| `--aec/--no-aec` | Acoustic Echo Cancellation | Enabled |
| `--stereo-split/--mix` | Channel separation | Mix |
| `--mic-gain` | Microphone gain multiplier | 1.5 |
| `--loopback-gain` | System audio gain multiplier | 1.0 |
| `-b, --bitrate` | MP3 bitrate (kbps) | 128 |
| `-f, --format` | Output format (mp3/wav) | mp3 |
