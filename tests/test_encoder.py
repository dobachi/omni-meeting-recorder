"""Tests for the encoder module."""

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

from omr.core.encoder import StreamingMP3Encoder, encode_to_mp3, is_mp3_available


def _create_test_wav(path: Path, duration_ms: int = 100) -> None:
    """Create a minimal valid WAV file for testing."""
    sample_rate = 44100
    channels = 2
    sample_width = 2  # 16-bit
    num_frames = int(sample_rate * duration_ms / 1000)

    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        # Generate silent audio
        wav_file.writeframes(b"\x00" * (num_frames * channels * sample_width))


class TestIsMp3Available:
    """Tests for is_mp3_available function."""

    def test_returns_true_when_lameenc_installed(self) -> None:
        """Returns True when lameenc can be found."""
        mock_spec = MagicMock()
        with patch("importlib.util.find_spec", return_value=mock_spec):
            assert is_mp3_available() is True

    def test_returns_false_when_lameenc_not_installed(self) -> None:
        """Returns False when lameenc cannot be found."""
        with patch("importlib.util.find_spec", return_value=None):
            assert is_mp3_available() is False


class TestEncodeToMp3:
    """Tests for encode_to_mp3 function."""

    def test_returns_false_when_lameenc_not_available(self, tmp_path: Path) -> None:
        """Returns False when lameenc is not installed."""
        wav_path = tmp_path / "test.wav"
        mp3_path = tmp_path / "test.mp3"
        _create_test_wav(wav_path)

        with (
            patch.dict("sys.modules", {"lameenc": None}),
            patch("builtins.__import__", side_effect=ImportError),
        ):
            result = encode_to_mp3(wav_path, mp3_path)
            assert result is False
            assert not mp3_path.exists()

    def test_returns_false_for_invalid_wav(self, tmp_path: Path) -> None:
        """Returns False when input file is not a valid WAV."""
        wav_path = tmp_path / "invalid.wav"
        mp3_path = tmp_path / "test.mp3"
        wav_path.write_text("not a wav file")

        mock_lameenc = MagicMock()
        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            result = encode_to_mp3(wav_path, mp3_path)
            assert result is False

    def test_returns_false_for_nonexistent_file(self, tmp_path: Path) -> None:
        """Returns False when input file does not exist."""
        wav_path = tmp_path / "nonexistent.wav"
        mp3_path = tmp_path / "test.mp3"

        mock_lameenc = MagicMock()
        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            result = encode_to_mp3(wav_path, mp3_path)
            assert result is False

    def test_successful_encoding_with_lameenc(self, tmp_path: Path) -> None:
        """Successfully encodes WAV to MP3 when lameenc is available."""
        wav_path = tmp_path / "test.wav"
        mp3_path = tmp_path / "test.mp3"
        _create_test_wav(wav_path)

        # Create a mock encoder that returns valid MP3 data
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = b"fake_mp3_data"
        mock_encoder.flush.return_value = b"_end"

        mock_lameenc = MagicMock()
        mock_lameenc.Encoder.return_value = mock_encoder

        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            result = encode_to_mp3(wav_path, mp3_path, bitrate=192)

            assert result is True
            assert mp3_path.exists()
            assert mp3_path.read_bytes() == b"fake_mp3_data_end"

            # Verify encoder configuration
            mock_encoder.set_bit_rate.assert_called_once_with(192)
            mock_encoder.set_in_sample_rate.assert_called_once_with(44100)
            mock_encoder.set_channels.assert_called_once_with(2)
            mock_encoder.set_quality.assert_called_once_with(2)

    def test_uses_default_bitrate(self, tmp_path: Path) -> None:
        """Uses 128kbps as default bitrate."""
        wav_path = tmp_path / "test.wav"
        mp3_path = tmp_path / "test.mp3"
        _create_test_wav(wav_path)

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = b"data"
        mock_encoder.flush.return_value = b""

        mock_lameenc = MagicMock()
        mock_lameenc.Encoder.return_value = mock_encoder

        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            encode_to_mp3(wav_path, mp3_path)  # No bitrate specified
            mock_encoder.set_bit_rate.assert_called_once_with(128)

    def test_returns_false_for_non_16bit_wav(self, tmp_path: Path) -> None:
        """Returns False for WAV files that are not 16-bit."""
        wav_path = tmp_path / "test_8bit.wav"
        mp3_path = tmp_path / "test.mp3"

        # Create an 8-bit WAV file
        sample_rate = 44100
        channels = 2
        sample_width = 1  # 8-bit
        num_frames = 100

        with wave.open(str(wav_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(sample_width)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(b"\x80" * (num_frames * channels * sample_width))

        mock_encoder = MagicMock()
        mock_lameenc = MagicMock()
        mock_lameenc.Encoder.return_value = mock_encoder

        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            result = encode_to_mp3(wav_path, mp3_path)
            assert result is False
            assert not mp3_path.exists()


class TestStreamingMP3Encoder:
    """Tests for StreamingMP3Encoder class."""

    def test_encoder_writes_mp3_data(self, tmp_path: Path) -> None:
        """Encoder writes MP3 data to file."""
        output_path = tmp_path / "output.mp3"

        # Create a mock encoder
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = b"mp3_chunk"
        mock_encoder.flush.return_value = b"_final"

        mock_lameenc = MagicMock()
        mock_lameenc.Encoder.return_value = mock_encoder

        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            encoder = StreamingMP3Encoder(
                output_path=output_path,
                sample_rate=48000,
                channels=2,
                bitrate=128,
            )

            # Write some PCM data
            encoder.write(b"\x00" * 1024)
            encoder.write(b"\x00" * 1024)
            encoder.close()

            # Verify encoder was configured correctly
            mock_encoder.set_bit_rate.assert_called_once_with(128)
            mock_encoder.set_in_sample_rate.assert_called_once_with(48000)
            mock_encoder.set_channels.assert_called_once_with(2)
            mock_encoder.set_quality.assert_called_once_with(2)

            # Verify file was created with expected content
            assert output_path.exists()
            content = output_path.read_bytes()
            assert b"mp3_chunk" in content
            assert b"_final" in content

    def test_encoder_context_manager(self, tmp_path: Path) -> None:
        """Encoder works as context manager and auto-closes."""
        output_path = tmp_path / "output.mp3"

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = b"data"
        mock_encoder.flush.return_value = b"end"

        mock_lameenc = MagicMock()
        mock_lameenc.Encoder.return_value = mock_encoder

        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            with StreamingMP3Encoder(
                output_path=output_path,
                sample_rate=44100,
                channels=1,
            ) as encoder:
                encoder.write(b"\x00" * 512)

            # File should be closed and contain data
            assert output_path.exists()
            content = output_path.read_bytes()
            assert content == b"dataend"

    def test_encoder_raises_error_after_close(self, tmp_path: Path) -> None:
        """Encoder raises error when writing after close."""
        import pytest

        output_path = tmp_path / "output.mp3"

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = b"data"
        mock_encoder.flush.return_value = b""

        mock_lameenc = MagicMock()
        mock_lameenc.Encoder.return_value = mock_encoder

        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            encoder = StreamingMP3Encoder(
                output_path=output_path,
                sample_rate=48000,
                channels=2,
            )
            encoder.close()

            with pytest.raises(RuntimeError, match="already closed"):
                encoder.write(b"\x00" * 100)

    def test_encoder_close_is_idempotent(self, tmp_path: Path) -> None:
        """Calling close multiple times is safe."""
        output_path = tmp_path / "output.mp3"

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = b""
        mock_encoder.flush.return_value = b"final"

        mock_lameenc = MagicMock()
        mock_lameenc.Encoder.return_value = mock_encoder

        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            encoder = StreamingMP3Encoder(
                output_path=output_path,
                sample_rate=48000,
                channels=2,
            )
            encoder.close()
            encoder.close()  # Should not raise

            # flush should only be called once
            mock_encoder.flush.assert_called_once()

    def test_encoder_custom_quality(self, tmp_path: Path) -> None:
        """Encoder respects custom quality setting."""
        output_path = tmp_path / "output.mp3"

        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = b""
        mock_encoder.flush.return_value = b""

        mock_lameenc = MagicMock()
        mock_lameenc.Encoder.return_value = mock_encoder

        with patch.dict("sys.modules", {"lameenc": mock_lameenc}):
            encoder = StreamingMP3Encoder(
                output_path=output_path,
                sample_rate=48000,
                channels=2,
                bitrate=320,
                quality=0,  # Best quality
            )
            encoder.close()

            mock_encoder.set_bit_rate.assert_called_once_with(320)
            mock_encoder.set_quality.assert_called_once_with(0)
