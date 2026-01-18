"""Tests for audio mixer."""

import struct

from omr.core.mixer import AudioMixer, MixerConfig


class TestMixerConfig:
    """Tests for MixerConfig."""

    def test_default_values(self):
        """Test default mixer config values."""
        config = MixerConfig()
        assert config.sample_rate == 48000
        assert config.channels == 2
        assert config.bit_depth == 16
        assert config.chunk_size == 1024
        assert config.stereo_split is True

    def test_custom_values(self):
        """Test custom mixer config values."""
        config = MixerConfig(
            sample_rate=44100,
            channels=2,
            chunk_size=512,
            stereo_split=False,
        )
        assert config.sample_rate == 44100
        assert config.chunk_size == 512
        assert config.stereo_split is False


class TestAudioMixer:
    """Tests for AudioMixer."""

    def test_mixer_creation(self):
        """Test mixer can be created."""
        mixer = AudioMixer()
        assert mixer.config.stereo_split is True

    def test_mixer_start_stop(self):
        """Test mixer can start and stop."""
        mixer = AudioMixer()
        mixer.start()
        assert mixer._running is True
        mixer.stop()
        assert mixer._running is False

    def test_bytes_to_samples(self):
        """Test bytes to samples conversion."""
        mixer = AudioMixer()
        # Create 16-bit PCM samples: [100, 200, -100]
        samples = [100, 200, -100]
        data = struct.pack("<3h", *samples)
        result = mixer._bytes_to_samples(data)
        assert result == samples

    def test_samples_to_bytes(self):
        """Test samples to bytes conversion."""
        mixer = AudioMixer()
        samples = [100, 200, -100]
        result = mixer._samples_to_bytes(samples)
        expected = struct.pack("<3h", *samples)
        assert result == expected

    def test_samples_to_bytes_clamping(self):
        """Test samples are clamped to valid range."""
        mixer = AudioMixer()
        samples = [40000, -40000]  # Out of 16-bit range
        result = mixer._samples_to_bytes(samples)
        # Should be clamped to [-32768, 32767]
        expected = struct.pack("<2h", 32767, -32768)
        assert result == expected

    def test_normalize_length_pad(self):
        """Test normalize_length pads short samples."""
        mixer = AudioMixer()
        samples = [1, 2, 3]
        result = mixer._normalize_length(samples, 5)
        assert result == [1, 2, 3, 0, 0]

    def test_normalize_length_trim(self):
        """Test normalize_length trims long samples."""
        mixer = AudioMixer()
        samples = [1, 2, 3, 4, 5]
        result = mixer._normalize_length(samples, 3)
        assert result == [1, 2, 3]

    def test_to_mono_passthrough(self):
        """Test to_mono passes through short mono samples."""
        mixer = AudioMixer()
        samples = [100, 200, 300]
        result = mixer._to_mono(samples)
        assert result == samples

    def test_mix_audio_stereo_split(self):
        """Test stereo split mixing (left=mic, right=system)."""
        config = MixerConfig(chunk_size=4, stereo_split=True)
        mixer = AudioMixer(config)

        # Create simple test data
        mic_samples = [100, 100, 100, 100]
        loopback_samples = [200, 200, 200, 200]

        mic_data = struct.pack("<4h", *mic_samples)
        loopback_data = struct.pack("<4h", *loopback_samples)

        result = mixer._mix_audio(mic_data, loopback_data)
        result_samples = list(struct.unpack(f"<{len(result) // 2}h", result))

        # In stereo split: left=mic, right=loopback
        # Output should be [mic[0], loop[0], mic[1], loop[1], ...]
        assert result_samples[0] == 100  # left = mic
        assert result_samples[1] == 200  # right = loopback

    def test_mix_audio_mixed_mode(self):
        """Test mixed mode (both channels combined)."""
        config = MixerConfig(chunk_size=4, stereo_split=False)
        mixer = AudioMixer(config)

        mic_samples = [100, 100, 100, 100]
        loopback_samples = [100, 100, 100, 100]

        mic_data = struct.pack("<4h", *mic_samples)
        loopback_data = struct.pack("<4h", *loopback_samples)

        result = mixer._mix_audio(mic_data, loopback_data)
        result_samples = list(struct.unpack(f"<{len(result) // 2}h", result))

        # In mixed mode: both channels should have (mic + loopback) / 2
        # (100 + 100) / 2 = 100
        assert result_samples[0] == 100
        assert result_samples[1] == 100

    def test_mix_audio_with_none_mic(self):
        """Test mixing when mic data is None."""
        config = MixerConfig(chunk_size=4, stereo_split=True)
        mixer = AudioMixer(config)

        loopback_samples = [200, 200, 200, 200]
        loopback_data = struct.pack("<4h", *loopback_samples)

        result = mixer._mix_audio(None, loopback_data)
        result_samples = list(struct.unpack(f"<{len(result) // 2}h", result))

        # Left (mic) should be 0, right (loopback) should have data
        assert result_samples[0] == 0  # left = no mic
        assert result_samples[1] == 200  # right = loopback

    def test_mix_audio_with_none_loopback(self):
        """Test mixing when loopback data is None."""
        config = MixerConfig(chunk_size=4, stereo_split=True)
        mixer = AudioMixer(config)

        mic_samples = [100, 100, 100, 100]
        mic_data = struct.pack("<4h", *mic_samples)

        result = mixer._mix_audio(mic_data, None)
        result_samples = list(struct.unpack(f"<{len(result) // 2}h", result))

        # Left (mic) should have data, right (loopback) should be 0
        assert result_samples[0] == 100  # left = mic
        assert result_samples[1] == 0  # right = no loopback
