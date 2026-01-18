"""Audio mixer for combining multiple audio streams."""

import struct
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from queue import Empty, Queue
from typing import Any


@dataclass
class MixerConfig:
    """Configuration for audio mixing."""

    sample_rate: int = 48000  # Output sample rate
    mic_sample_rate: int = 48000  # Mic input sample rate
    loopback_sample_rate: int = 48000  # Loopback input sample rate
    channels: int = 2  # Output channels (stereo)
    bit_depth: int = 16
    chunk_size: int = 1024
    stereo_split: bool = True  # True: left=mic, right=system


class AudioMixer:
    """Mixes two audio streams into one stereo output.

    In stereo split mode:
    - Left channel: Microphone audio
    - Right channel: System audio (loopback)

    In mix mode:
    - Both channels: Mixed audio from both sources
    """

    def __init__(self, config: MixerConfig | None = None) -> None:
        self._config = config or MixerConfig()
        self._mic_queue: Queue[bytes] = Queue(maxsize=100)
        self._loopback_queue: Queue[bytes] = Queue(maxsize=100)
        self._output_queue: Queue[bytes] = Queue(maxsize=100)
        self._running = False
        self._mixer_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def config(self) -> MixerConfig:
        """Get mixer configuration."""
        return self._config

    def start(self) -> None:
        """Start the mixer thread."""
        with self._lock:
            if self._running:
                return
            self._running = True
            self._mixer_thread = threading.Thread(target=self._mix_loop, daemon=True)
            self._mixer_thread.start()

    def stop(self) -> None:
        """Stop the mixer thread."""
        with self._lock:
            self._running = False
        if self._mixer_thread is not None:
            self._mixer_thread.join(timeout=2.0)
            self._mixer_thread = None

    def add_mic_data(self, data: bytes) -> None:
        """Add microphone audio data to the mixer."""
        try:
            self._mic_queue.put_nowait(data)
        except Exception:
            pass  # Drop data if queue is full

    def add_loopback_data(self, data: bytes) -> None:
        """Add loopback audio data to the mixer."""
        try:
            self._loopback_queue.put_nowait(data)
        except Exception:
            pass  # Drop data if queue is full

    def get_output(self, timeout: float = 0.1) -> bytes | None:
        """Get mixed output data."""
        try:
            return self._output_queue.get(timeout=timeout)
        except Empty:
            return None

    def _mix_loop(self) -> None:
        """Main mixing loop."""
        while self._running:
            try:
                # Get data from both queues with timeout
                mic_data = self._get_queue_data(self._mic_queue)
                loopback_data = self._get_queue_data(self._loopback_queue)

                if mic_data is None and loopback_data is None:
                    continue

                # Mix the audio
                mixed = self._mix_audio(mic_data, loopback_data)
                if mixed:
                    try:
                        self._output_queue.put_nowait(mixed)
                    except Exception:
                        pass  # Drop if output queue is full

            except Exception:
                if not self._running:
                    break

    def _get_queue_data(self, queue: Queue[bytes]) -> bytes | None:
        """Get data from queue with timeout."""
        try:
            return queue.get(timeout=0.05)
        except Empty:
            return None

    def _mix_audio(self, mic_data: bytes | None, loopback_data: bytes | None) -> bytes | None:
        """Mix audio from mic and loopback into stereo output.

        Input: mono or stereo 16-bit PCM
        Output: stereo 16-bit PCM (left=mic, right=loopback in split mode)
        """
        chunk_samples = self._config.chunk_size

        # Convert to samples
        mic_samples = self._bytes_to_samples(mic_data) if mic_data else []
        loopback_samples = self._bytes_to_samples(loopback_data) if loopback_data else []

        # Normalize to mono (average channels if stereo)
        mic_mono = self._to_mono(mic_samples)
        loopback_mono = self._to_mono(loopback_samples)

        # Resample to output sample rate if needed
        if self._config.mic_sample_rate != self._config.sample_rate:
            mic_mono = self._resample(
                mic_mono, self._config.mic_sample_rate, self._config.sample_rate
            )
        if self._config.loopback_sample_rate != self._config.sample_rate:
            loopback_mono = self._resample(
                loopback_mono, self._config.loopback_sample_rate, self._config.sample_rate
            )

        # Pad or trim to chunk size
        mic_mono = self._normalize_length(mic_mono, chunk_samples)
        loopback_mono = self._normalize_length(loopback_mono, chunk_samples)

        # Create stereo output
        if self._config.stereo_split:
            # Left = mic, Right = loopback
            output_samples = []
            for i in range(chunk_samples):
                left = mic_mono[i] if i < len(mic_mono) else 0
                right = loopback_mono[i] if i < len(loopback_mono) else 0
                output_samples.extend([left, right])
        else:
            # Mix both to both channels
            output_samples = []
            for i in range(chunk_samples):
                mic_val = mic_mono[i] if i < len(mic_mono) else 0
                loop_val = loopback_mono[i] if i < len(loopback_mono) else 0
                # Mix with 50% volume each to prevent clipping
                mixed = (mic_val + loop_val) // 2
                output_samples.extend([mixed, mixed])

        return self._samples_to_bytes(output_samples)

    def _bytes_to_samples(self, data: bytes) -> list[int]:
        """Convert bytes to 16-bit samples."""
        return list(struct.unpack(f"<{len(data) // 2}h", data))

    def _samples_to_bytes(self, samples: list[int]) -> bytes:
        """Convert 16-bit samples to bytes."""
        # Clamp samples to valid range
        clamped = [max(-32768, min(32767, s)) for s in samples]
        return struct.pack(f"<{len(clamped)}h", *clamped)

    def _to_mono(self, samples: list[int]) -> list[int]:
        """Convert stereo samples to mono by averaging channels."""
        if not samples:
            return []
        # Assume input might be stereo (even number of samples)
        if len(samples) % 2 == 0 and len(samples) > self._config.chunk_size:
            # Likely stereo, convert to mono
            mono = []
            for i in range(0, len(samples), 2):
                left = samples[i]
                right = samples[i + 1] if i + 1 < len(samples) else left
                mono.append((left + right) // 2)
            return mono
        return samples

    def _normalize_length(self, samples: list[int], target_length: int) -> list[int]:
        """Normalize sample list to target length."""
        if len(samples) >= target_length:
            return samples[:target_length]
        # Pad with zeros
        return samples + [0] * (target_length - len(samples))

    def _resample(self, samples: list[int], from_rate: int, to_rate: int) -> list[int]:
        """Resample audio using linear interpolation.

        Args:
            samples: Input samples
            from_rate: Source sample rate
            to_rate: Target sample rate

        Returns:
            Resampled audio samples
        """
        if from_rate == to_rate or not samples:
            return samples

        ratio = to_rate / from_rate
        new_length = int(len(samples) * ratio)

        if new_length == 0:
            return []

        resampled = []
        for i in range(new_length):
            # Calculate position in original samples
            pos = i / ratio
            idx = int(pos)
            frac = pos - idx

            if idx + 1 < len(samples):
                # Linear interpolation
                val = samples[idx] * (1 - frac) + samples[idx + 1] * frac
            else:
                val = samples[idx] if idx < len(samples) else 0

            resampled.append(int(val))

        return resampled
