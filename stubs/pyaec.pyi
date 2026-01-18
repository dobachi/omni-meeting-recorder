"""Type stubs for pyaec (Python Acoustic Echo Cancellation library)."""

class AEC:
    """Acoustic Echo Cancellation processor.

    Uses adaptive filtering to remove echo from microphone signal
    by subtracting the reference (speaker) signal.
    """

    def __init__(
        self,
        frame_size: int,
        filter_length: int | None = None,
        sample_rate: int | None = None,
    ) -> None:
        """Initialize AEC processor.

        Args:
            frame_size: Number of samples per frame (typically 160-1024)
            filter_length: Adaptive filter length (default: frame_size * 10)
            sample_rate: Sample rate in Hz (default: 16000)
        """
        ...

    def process(
        self,
        mic_frame: list[int],
        reference_frame: list[int],
    ) -> list[int]:
        """Process a frame of audio through AEC.

        Args:
            mic_frame: Microphone input samples (may contain echo)
            reference_frame: Reference signal (speaker/loopback output)

        Returns:
            Echo-cancelled microphone samples
        """
        ...

    def cancel(
        self,
        mic_frame: list[int],
        reference_frame: list[int],
    ) -> list[int]:
        """Alias for process() - cancel echo from microphone signal.

        Args:
            mic_frame: Microphone input samples (may contain echo)
            reference_frame: Reference signal (speaker/loopback output)

        Returns:
            Echo-cancelled microphone samples
        """
        ...
