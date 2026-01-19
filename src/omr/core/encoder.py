"""Audio encoder module for format conversion."""

import wave
from pathlib import Path
from types import TracebackType
from typing import BinaryIO, Protocol


class AudioWriter(Protocol):
    """音声書き込みインターフェース（WAVとMP3で共通）."""

    def write(self, data: bytes) -> None:
        """音声データを書き込む."""
        ...

    def close(self) -> None:
        """ライターを閉じる."""
        ...


class StreamingMP3Encoder:
    """リアルタイムストリーミングMP3エンコーダー.

    録音中にPCMデータをチャンクごとにMP3エンコードしてファイルに書き込む。
    長時間録音でもメモリを消費しない。
    """

    def __init__(
        self,
        output_path: Path,
        sample_rate: int,
        channels: int,
        bitrate: int = 128,
        quality: int = 2,
    ) -> None:
        """StreamingMP3Encoderを初期化.

        Args:
            output_path: 出力MP3ファイルパス
            sample_rate: サンプルレート (Hz)
            channels: チャンネル数 (1=モノラル, 2=ステレオ)
            bitrate: MP3ビットレート (kbps, default: 128)
            quality: エンコード品質 (0-9, 2=high quality)
        """
        import lameenc

        self._output_path = output_path
        self._file: BinaryIO = output_path.open("wb")
        self._encoder = lameenc.Encoder()
        self._encoder.set_bit_rate(bitrate)
        self._encoder.set_in_sample_rate(sample_rate)
        self._encoder.set_channels(channels)
        self._encoder.set_quality(quality)
        self._closed = False

    def write(self, data: bytes) -> None:
        """PCMデータをエンコードしてファイルに書き込む.

        Args:
            data: 16-bit PCMデータ
        """
        if self._closed:
            raise RuntimeError("Encoder is already closed")
        mp3_data = self._encoder.encode(data)
        if mp3_data:
            self._file.write(mp3_data)

    def close(self) -> None:
        """エンコーダーを閉じてファイルを完成させる."""
        if self._closed:
            return
        self._closed = True
        # 残りのデータをフラッシュ
        final_data = self._encoder.flush()
        if final_data:
            self._file.write(final_data)
        self._file.close()

    def __enter__(self) -> "StreamingMP3Encoder":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Context manager exit."""
        self.close()


def is_mp3_available() -> bool:
    """Check if lameenc is installed for MP3 encoding.

    Returns:
        True if lameenc is available, False otherwise.
    """
    import importlib.util

    return importlib.util.find_spec("lameenc") is not None


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
