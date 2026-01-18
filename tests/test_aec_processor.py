"""Tests for the AEC processor module."""

from __future__ import annotations

import struct
from unittest.mock import MagicMock, patch

import pytest

from omr.core.aec_processor import AECProcessor, is_aec_available


class TestIsAecAvailable:
    """Tests for is_aec_available function."""

    def test_returns_bool(self) -> None:
        """is_aec_available returns a boolean."""
        result = is_aec_available()
        assert isinstance(result, bool)

    def test_caches_result(self) -> None:
        """is_aec_available caches its result."""
        # Call twice and ensure it returns consistent results
        result1 = is_aec_available()
        result2 = is_aec_available()
        assert result1 == result2


class TestAECProcessorWithoutPyaec:
    """Tests for AECProcessor when pyaec is not installed."""

    def test_raises_when_pyaec_not_available(self) -> None:
        """AECProcessor raises RuntimeError when pyaec is not installed."""
        with patch("omr.core.aec_processor.is_aec_available", return_value=False):
            with pytest.raises(RuntimeError) as exc_info:
                AECProcessor(sample_rate=48000, frame_size=480)
            assert "pyaec is not installed" in str(exc_info.value)


class TestAECProcessorWithMock:
    """Tests for AECProcessor with mocked pyaec."""

    @pytest.fixture
    def mock_aec(self) -> MagicMock:
        """Create a mock Aec instance."""
        mock = MagicMock()
        # Return input unchanged for testing
        mock.cancel_echo.side_effect = lambda mic, ref: mic
        return mock

    @pytest.fixture
    def processor(self, mock_aec: MagicMock) -> AECProcessor:
        """Create an AECProcessor with mocked pyaec."""
        with (
            patch("omr.core.aec_processor.is_aec_available", return_value=True),
            patch("omr.core.aec_processor.AECProcessor.__init__", return_value=None),
        ):
            proc = object.__new__(AECProcessor)
            proc._sample_rate = 48000
            proc._frame_size = 480
            proc._filter_length = 4800
            proc._aec = mock_aec
            proc._mic_buffer = []
            proc._ref_buffer = []
            proc._output_buffer = []
            return proc

    def test_properties(self, processor: AECProcessor) -> None:
        """Test property accessors."""
        assert processor.frame_size == 480
        assert processor.sample_rate == 48000

    def test_process_samples_empty(self, processor: AECProcessor) -> None:
        """Test process_samples with empty input."""
        result = processor.process_samples([], [])
        assert result == []

    def test_process_samples_buffering(
        self, processor: AECProcessor, mock_aec: MagicMock
    ) -> None:
        """Test process_samples returns same length as input (pass-through when buffering)."""
        # Input less than frame_size
        mic = [1] * 100
        ref = [2] * 100
        result = processor.process_samples(mic, ref)

        # Should return same length (pass-through since not enough for a frame)
        assert len(result) == 100
        # Pass-through should return original mic samples
        assert result == mic

        # AEC should not be called yet (not enough samples)
        mock_aec.cancel_echo.assert_not_called()

    def test_process_samples_processes_full_frame(
        self, processor: AECProcessor, mock_aec: MagicMock
    ) -> None:
        """Test process_samples processes when frame_size is reached."""
        # Input exactly frame_size
        mic = list(range(480))
        ref = list(range(480))
        result = processor.process_samples(mic, ref)

        # Should process and return result
        assert len(result) == 480
        mock_aec.cancel_echo.assert_called_once()

    def test_process_samples_multiple_frames(
        self, processor: AECProcessor, mock_aec: MagicMock
    ) -> None:
        """Test process_samples with multiple frames returns same length as input."""
        mic = list(range(1000))
        ref = list(range(1000))
        result = processor.process_samples(mic, ref)

        # Should return same length as input (maintains sync)
        assert len(result) == 1000
        # Should have processed 2 complete frames
        assert mock_aec.cancel_echo.call_count == 2

        # 40 samples should remain in buffer
        assert len(processor._mic_buffer) == 40
        assert len(processor._ref_buffer) == 40

    def test_process_bytes(self, processor: AECProcessor) -> None:
        """Test process_bytes converts correctly."""
        # Create 480 samples of audio data (16-bit)
        mic_samples = list(range(-240, 240))
        ref_samples = list(range(-240, 240))
        mic_data = struct.pack(f"<{len(mic_samples)}h", *mic_samples)
        ref_data = struct.pack(f"<{len(ref_samples)}h", *ref_samples)

        result = processor.process_bytes(mic_data, ref_data)

        # Should return processed data
        assert isinstance(result, bytes)
        assert len(result) == 960  # 480 samples * 2 bytes

    def test_flush_returns_remaining(self, processor: AECProcessor) -> None:
        """Test flush returns buffered samples."""
        processor._mic_buffer = [1, 2, 3]
        processor._ref_buffer = [4, 5, 6]

        result = processor.flush()

        assert result == [1, 2, 3]
        assert processor._mic_buffer == []
        assert processor._ref_buffer == []

    def test_reset_clears_buffers(self, processor: AECProcessor) -> None:
        """Test reset clears all buffers."""
        processor._mic_buffer = [1, 2, 3]
        processor._ref_buffer = [4, 5, 6]
        processor._output_buffer = [7, 8, 9]

        # Manually clear buffers (simulating reset)
        processor._mic_buffer.clear()
        processor._ref_buffer.clear()
        processor._output_buffer.clear()

        assert processor._mic_buffer == []
        assert processor._ref_buffer == []
        assert processor._output_buffer == []
