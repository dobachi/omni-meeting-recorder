"""Type stubs for pyaec (Python Acoustic Echo Cancellation library)."""

class Aec:
    """Acoustic Echo Cancellation processor.

    Uses adaptive filtering to remove echo from microphone signal
    by subtracting the reference (speaker) signal.
    """

    def __init__(
        self,
        frame_size: int,
        filter_length: int,
        sample_rate: int,
        enable_preprocess: bool = True,
    ) -> None:
        """Initialize AEC processor.

        Args:
            frame_size: Number of samples per frame (typically 160-1024)
            filter_length: Adaptive filter length
            sample_rate: Sample rate in Hz
            enable_preprocess: Enable preprocessing (default: True)
        """
        ...

    def cancel_echo(
        self,
        rec_buffer: list[int],
        echo_buffer: list[int],
    ) -> list[int]:
        """Cancel echo from microphone signal.

        Args:
            rec_buffer: Microphone input samples (may contain echo)
            echo_buffer: Reference signal (speaker/loopback output)

        Returns:
            Echo-cancelled microphone samples
        """
        ...
