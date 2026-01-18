"""Audio encoder module for format conversion."""

import wave
from pathlib import Path


def is_mp3_available() -> bool:
    """Check if lameenc is installed for MP3 encoding.

    Returns:
        True if lameenc is available, False otherwise.
    """
    try:
        import lameenc  # type: ignore[import-not-found]  # noqa: F401

        return True
    except ImportError:
        return False


def encode_to_mp3(wav_path: Path, mp3_path: Path, bitrate: int = 128) -> bool:
    """Convert a WAV file to MP3 format.

    Args:
        wav_path: Path to the input WAV file.
        mp3_path: Path for the output MP3 file.
        bitrate: MP3 bitrate in kbps (default: 128).

    Returns:
        True if conversion succeeded, False otherwise.
    """
    try:
        import lameenc
    except ImportError:
        return False

    try:
        with wave.open(str(wav_path), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_rate = wav_file.getframerate()
            sample_width = wav_file.getsampwidth()
            pcm_data = wav_file.readframes(wav_file.getnframes())

        # lameenc only supports 16-bit PCM
        if sample_width != 2:
            return False

        encoder = lameenc.Encoder()
        encoder.set_bit_rate(bitrate)
        encoder.set_in_sample_rate(sample_rate)
        encoder.set_channels(channels)
        encoder.set_quality(2)  # 2 = high quality

        mp3_data = encoder.encode(pcm_data)
        mp3_data += encoder.flush()

        with open(mp3_path, "wb") as mp3_file:
            mp3_file.write(mp3_data)

        return True
    except Exception:
        return False
