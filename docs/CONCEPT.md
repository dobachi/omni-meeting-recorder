# Omni Meeting Recorder - Concept

## Why This Tool Exists

Recording online meetings should be simple. Yet, for Windows users, capturing both your own voice and remote participants' voices has traditionally required:

- Installing virtual audio cables
- Complex audio routing configurations
- Multiple software applications running simultaneously
- Technical knowledge of audio routing

**Omni Meeting Recorder (omr)** was created to solve this problem with a single command.

## Problem Statement

### The Challenge of Meeting Recording

When participating in online meetings (Zoom, Teams, Google Meet, etc.), audio comes from two separate sources:

1. **Remote participants' voices**: Played through your speakers or headphones (system audio)
2. **Your own voice**: Captured by your microphone

Most recording software can only capture one or the other, not both simultaneously.

### Traditional Solutions and Their Drawbacks

| Solution | Drawback |
|----------|----------|
| Virtual Audio Cable | Complex setup, costs money, may introduce latency |
| OBS with multiple sources | Heavyweight, steep learning curve |
| Meeting platform's built-in recording | Often requires host permission, cloud storage, privacy concerns |
| Multiple recorders | Sync issues, file management overhead |

### The Speaker Echo Problem

When using speakers (not headphones), the microphone picks up the sound from the speakers, creating echo in the recording. This requires Acoustic Echo Cancellation (AEC), which most simple recorders don't provide.

## Target Users

- **Business professionals** who need to record meetings for note-taking or compliance
- **Students** recording online lectures
- **Content creators** capturing interview sessions
- **Anyone** who wants a simple, local recording solution without cloud dependencies

## Key Principles

### 1. Simplicity First

```bash
omr start
```

That's it. One command to start recording. Press Ctrl+C to stop. No configuration required.

### 2. No Additional Software Required

omr uses Windows' native WASAPI Loopback feature to capture system audio directly. No virtual audio cables or drivers needed.

### 3. Privacy-Focused

- All recordings stay on your local machine
- No cloud upload, no account required
- No telemetry or data collection

### 4. Portable

Download the portable version, extract, and run. No installation, no admin rights required (in most cases).

## Comparison with Alternatives

| Feature | omr | Virtual Audio Cable | OBS | Meeting Built-in |
|---------|-----|---------------------|-----|------------------|
| Setup complexity | One command | Manual routing | Moderate | Varies |
| Additional software | None | Driver install | Large app | None |
| Local storage | Yes | Yes | Yes | Often cloud |
| AEC support | Built-in | Manual | Plugins | Varies |
| Mic + System audio | Native | Complex routing | Possible | Sometimes |
| Price | Free | Paid/Free | Free | Included |
| Portable | Yes | No | No | N/A |

## Use Cases

### Basic Meeting Recording

```bash
# Start recording with default settings
omr start -o team_meeting.mp3
# Press Ctrl+C when meeting ends
```

### Lecture Recording (System Audio Only)

```bash
# Record only the speaker's presentation
omr start -L -o lecture.mp3
```

### Interview Recording (Headphone User)

```bash
# Disable AEC when using headphones for best quality
omr start --no-aec -o interview.mp3
```

### Separate Tracks for Post-Processing

```bash
# Left channel = your voice, Right channel = remote participants
omr start --stereo-split -o meeting_split.mp3
```

## Philosophy

> "The best tool is the one you don't have to think about."

omr aims to be invisible - a utility that does one thing well and gets out of your way. No feature bloat, no unnecessary complexity. Record your meetings, get your files, move on with your day.
