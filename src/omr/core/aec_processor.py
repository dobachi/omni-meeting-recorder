"""Acoustic Echo Cancellation (AEC) processor using pyaec library."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pyaec import AEC

_AEC_AVAILABLE: bool | None = None


def is_aec_available() -> bool:
    """Check if pyaec is installed and available.

    Returns:
        True if pyaec can be imported, False otherwise.
    """
    global _AEC_AVAILABLE
    if _AEC_AVAILABLE is None:
        try:
            import pyaec  # noqa: F401

            _AEC_AVAILABLE = True
        except ImportError:
            _AEC_AVAILABLE = False
    return _AEC_AVAILABLE


class AECProcessor:
    """Wrapper for pyaec AEC (Acoustic Echo Cancellation).

    This processor removes echo from microphone input by using the
    loopback/speaker signal as a reference.
    """

    def __init__(
        self,
        sample_rate: int,
        frame_size: int,
        filter_length: int | None = None,
    ) -> None:
        """Initialize AEC processor.

        Args:
            sample_rate: Audio sample rate in Hz (e.g., 48000)
            frame_size: Number of samples per frame (typically 160-1024)
            filter_length: Adaptive filter length (default: frame_size * 10)

        Raises:
            RuntimeError: If pyaec is not installed.
        """
        if not is_aec_available():
            raise RuntimeError(
                "pyaec is not installed. Install with: uv sync --extra aec"
            )

        from pyaec import AEC

        self._sample_rate = sample_rate
        self._frame_size = frame_size
        self._filter_length = filter_length or frame_size * 10

        self._aec: AEC = AEC(
            frame_size=self._frame_size,
            filter_length=self._filter_length,
            sample_rate=self._sample_rate,
        )

        # Buffers for accumulating samples when input doesn't match frame_size
        self._mic_buffer: list[int] = []
        self._ref_buffer: list[int] = []
        self._output_buffer: list[int] = []

    @property
    def frame_size(self) -> int:
        """Get the frame size used by AEC."""
        return self._frame_size

    @property
    def sample_rate(self) -> int:
        """Get the sample rate."""
        return self._sample_rate

    def process_samples(
        self,
        mic_samples: list[int],
        ref_samples: list[int],
    ) -> list[int]:
        """Process samples through AEC to remove echo.

        Handles variable-length input by buffering and processing
        in frame_size chunks.

        Args:
            mic_samples: Microphone input samples (may contain echo)
            ref_samples: Reference signal samples (loopback/speaker output)

        Returns:
            Echo-cancelled microphone samples (may be fewer than input
            if buffering is needed)
        """
        # Add to buffers
        self._mic_buffer.extend(mic_samples)
        self._ref_buffer.extend(ref_samples)

        # Process complete frames
        while (
            len(self._mic_buffer) >= self._frame_size
            and len(self._ref_buffer) >= self._frame_size
        ):
            mic_frame = self._mic_buffer[: self._frame_size]
            ref_frame = self._ref_buffer[: self._frame_size]

            self._mic_buffer = self._mic_buffer[self._frame_size :]
            self._ref_buffer = self._ref_buffer[self._frame_size :]

            # Process through AEC
            processed = self._aec.cancel(mic_frame, ref_frame)
            self._output_buffer.extend(processed)

        # Return accumulated output
        result = self._output_buffer[:]
        self._output_buffer.clear()
        return result

    def process_bytes(
        self,
        mic_data: bytes,
        ref_data: bytes,
    ) -> bytes:
        """Process audio bytes through AEC.

        Args:
            mic_data: Microphone audio data (16-bit signed little-endian)
            ref_data: Reference audio data (16-bit signed little-endian)

        Returns:
            Echo-cancelled audio data (16-bit signed little-endian)
        """
        import struct

        # Convert bytes to samples
        mic_samples = list(struct.unpack(f"<{len(mic_data) // 2}h", mic_data))
        ref_samples = list(struct.unpack(f"<{len(ref_data) // 2}h", ref_data))

        # Process
        processed = self.process_samples(mic_samples, ref_samples)

        # Convert back to bytes
        if not processed:
            return b""
        return struct.pack(f"<{len(processed)}h", *processed)

    def flush(self) -> list[int]:
        """Flush remaining samples from buffers.

        Call this when recording ends to get any remaining buffered samples.

        Returns:
            Remaining samples (may be less than frame_size, unprocessed)
        """
        # Return unprocessed mic samples as-is
        result = self._mic_buffer[:]
        self._mic_buffer.clear()
        self._ref_buffer.clear()
        return result

    def reset(self) -> None:
        """Reset AEC state and clear buffers."""
        from pyaec import AEC

        self._aec = AEC(
            frame_size=self._frame_size,
            filter_length=self._filter_length,
            sample_rate=self._sample_rate,
        )
        self._mic_buffer.clear()
        self._ref_buffer.clear()
        self._output_buffer.clear()
