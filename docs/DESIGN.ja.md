# Omni Meeting Recorder - 技術設計

## アーキテクチャ概要

### モジュール構成

```
src/omr/
├── cli/                    # コマンドラインインターフェース
│   ├── main.py             # Typerアプリのエントリポイント
│   └── commands/
│       ├── record.py       # 録音コマンドの実装
│       └── devices.py      # デバイス一覧コマンド
├── core/                   # コア音声処理
│   ├── audio_capture.py    # 高レベルキャプチャ抽象化
│   ├── device_manager.py   # デバイス検出と管理
│   ├── mixer.py            # 音声ミキシングとリサンプリング
│   ├── aec_processor.py    # 音響エコーキャンセル
│   ├── encoder.py          # 音声エンコード（MP3/WAV）
│   └── input_handler.py    # キーボード入力処理
├── backends/
│   └── wasapi.py           # Windows WASAPI実装
└── config/
    └── settings.py         # 設定管理
```

### データフロー図

```
┌─────────────────┐     ┌─────────────────┐
│   マイク        │     │   ループバック   │
│   (WASAPI)      │     │   (WASAPI)      │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ▼                       ▼
    ┌─────────┐             ┌─────────┐
    │ Reader  │             │ Reader  │
    │ Thread  │             │ Thread  │
    └────┬────┘             └────┬────┘
         │                       │
         │ Queue                 │ Queue
         ▼                       ▼
    ┌────────────────────────────────┐
    │        メイン処理              │
    │  ┌──────────────────────────┐  │
    │  │   共通サンプルレートに    │  │
    │  │   リサンプリング          │  │
    │  └────────────┬─────────────┘  │
    │               │                │
    │  ┌────────────▼─────────────┐  │
    │  │   AEC処理               │  │
    │  │   （有効時）             │  │
    │  └────────────┬─────────────┘  │
    │               │                │
    │  ┌────────────▼─────────────┐  │
    │  │   AGC（自動ゲイン        │  │
    │  │   コントロール）          │  │
    │  └────────────┬─────────────┘  │
    │               │                │
    │  ┌────────────▼─────────────┐  │
    │  │   ステレオミックス/分離   │  │
    │  └────────────┬─────────────┘  │
    └───────────────┼────────────────┘
                    │
                    ▼
           ┌────────────────┐
           │ StreamingMP3   │
           │ Encoder        │
           └───────┬────────┘
                   │
                   ▼
           ┌────────────────┐
           │   .mp3 ファイル │
           └────────────────┘
```

## WASAPI Loopbackの仕組み

### 動作原理

Windows Audio Session API（WASAPI）は、出力デバイスに再生されている音声データをキャプチャできる「ループバック」モードを提供しています。これがomrが仮想オーディオケーブルなしで動作できる鍵となる技術です。

```python
# 簡略化した概念（実際の実装はwasapi.pyにあります）
stream = pyaudio.open(
    input=True,
    input_device_index=loopback_device.index,  # 出力デバイスを入力として開く
    format=pyaudio.paInt16,
    channels=device.channels,
    rate=device.sample_rate,
    frames_per_buffer=chunk_size
)
```

### PyAudioWPatch統合

omrは[PyAudioWPatch](https://github.com/s0d3s/PyAudioWPatch)を使用しています。これはWASAPIループバックサポートを追加したPyAudioのフォークです：

1. **デバイス列挙**: ループバック対応エンドポイントを含むすべての音声デバイスを検出
2. **ストリーム作成**: 正しいWASAPI設定でループバックストリームを開く
3. **データキャプチャ**: 音声ストリームからリアルタイムでPCMデータを読み取る

### デバイス検出ロジック

```python
# デバイスタイプはhostApiとデバイスプロパティで判定
def _determine_device_type(device_info, host_api_info):
    if host_api_info["name"] == "Windows WASAPI":
        if device_info.get("isLoopbackDevice"):
            return DeviceType.LOOPBACK
        elif device_info["maxInputChannels"] > 0:
            return DeviceType.MICROPHONE
    return DeviceType.OUTPUT
```

## 音声処理パイプライン

### デュアル録音の同期

デュアル録音の主な課題は、マイクとループバックの音声を同期させることです。omrはこれを以下の方法で解決します：

1. **マスタークロック**: ループバックストリームをタイミングの基準として使用
2. **キューベースのバッファリング**: 別々のスレッドが各デバイスからキューに読み込む
3. **同期された抽出**: メインスレッドが両方のキューから一致する量を抽出

```python
# ループバックが出力タイミングを駆動（マスタークロック）
if loopback_buffer:
    chunk_size = len(loopback_buffer)
    loopback_chunk = loopback_buffer[:]

    # マイクバッファから一致する量を取得
    mic_chunk = mic_buffer[:chunk_size]
```

### リサンプリング

デバイスは異なるネイティブサンプルレートを持つことが多いです（例：マイクが44100Hz、スピーカーが48000Hz）。omrはマイク音声をループバックに合わせてリサンプリングします：

```python
def resample_simple(samples, from_rate, to_rate):
    """線形補間によるリサンプリング"""
    ratio = to_rate / from_rate
    new_length = int(len(samples) * ratio)

    resampled = []
    for i in range(new_length):
        pos = i / ratio
        idx = int(pos)
        frac = pos - idx
        # 隣接サンプル間の線形補間
        val = samples[idx] * (1 - frac) + samples[idx + 1] * frac
        resampled.append(int(val))
    return resampled
```

## 音響エコーキャンセル（AEC）

### 問題

スピーカーを使用している場合、マイクは以下を拾います：
- 自分の声（望ましい）
- スピーカーからの音声（エコー/フィードバック）

### 解決策：pyaecライブラリ

omrは[pyaec](https://pypi.org/project/pyaec/)ライブラリを使用しています。これはエコーキャンセルのための適応フィルタアルゴリズムを実装しています。

### AECの動作原理

```
                 ┌─────────────┐
   ループバック ──▶│   pyaec     │
   （参照信号）    │   AEC       │◀──── マイク（エコー含む）
                 │   Filter    │
                 └──────┬──────┘
                        │
                        ▼
                  マイク（エコー除去済み）
```

AECアルゴリズム：
1. ループバック信号を参照として使用
2. 参照信号がマイク信号にどのように現れるかを特定（室内音響を通じて）
3. 推定されたエコーをマイク信号から減算

### フレームベース処理

AECは処理に固定サイズのフレームを必要とします：

```python
class AECProcessor:
    def __init__(self, sample_rate, frame_size, filter_length=None):
        self._frame_size = frame_size  # 通常160-1024サンプル
        self._filter_length = filter_length or frame_size * 10
        self._aec = Aec(
            frame_size=self._frame_size,
            filter_length=self._filter_length,
            sample_rate=sample_rate,
        )
        # サンプルを蓄積するバッファ
        self._mic_buffer = []
        self._ref_buffer = []
```

入力サンプルは完全なフレームが利用可能になるまで蓄積され、その後処理されます：

```python
def process_samples(self, mic_samples, ref_samples):
    # バッファに追加
    self._mic_buffer.extend(mic_samples)
    self._ref_buffer.extend(ref_samples)

    # 完全なフレームを処理
    while len(self._mic_buffer) >= self._frame_size:
        mic_frame = self._mic_buffer[:self._frame_size]
        ref_frame = self._ref_buffer[:self._frame_size]

        processed = self._aec.cancel_echo(mic_frame, ref_frame)
        self._output_buffer.extend(processed)
```

## 自動ゲインコントロール（AGC）

### 問題

マイクとシステム音声は音量レベルが大きく異なることが多く、バランスの悪い録音になります。

### 解決策：RMSベースのレベル正規化

1. **RMS計算**: 各音声チャンクの「音量」を測定

```python
def calc_rms(samples):
    """Root Mean Square - 音声パワーを測定"""
    sum_sq = sum(s * s for s in samples)
    return (sum_sq / len(samples)) ** 0.5
```

2. **スライディングウィンドウ平均**: 安定したゲイン計算のためにRMS履歴を追跡

```python
mic_rms_history = []
agc_window = 100  # 平均を取るチャンク数

if mic_rms > 50:  # 無音を増幅しないための閾値
    mic_rms_history.append(mic_rms)
    if len(mic_rms_history) > agc_window:
        mic_rms_history.pop(0)
```

3. **ゲイン計算**: ターゲットレベルに達するためのゲインを計算

```python
target_rms = 8000.0  # 16ビットピークの約25%
avg_rms = sum(rms_history) / len(rms_history)
auto_gain = target_rms / avg_rms
auto_gain = max(0.5, min(6.0, auto_gain))  # 安全な範囲にクランプ
```

4. **ソフトクリッピング**: 過増幅による歪みを防止

```python
def apply_gain(samples, gain):
    result = []
    for s in samples:
        val = s * gain
        # 16ビット限界でハードクリップ
        val = max(-32768, min(32767, val))
        result.append(int(val))
    return result
```

## ストリーミングMP3エンコード

### ストリーミングを使う理由

従来のアプローチ：
1. WAVに録音（非圧縮、大きなファイル）
2. 録音後にMP3に変換

問題点：
- 大きな一時ファイル（WAVはMP3の約10倍）
- 変換に追加の時間がかかる
- 変換に失敗した場合のデータ損失リスク

### ストリーミングソリューション

omrは[lameenc](https://pypi.org/project/lameenc/)ライブラリを使用して、リアルタイムで音声をMP3にエンコードします：

```python
class StreamingMP3Encoder:
    def __init__(self, output_path, sample_rate, channels, bitrate=128):
        self._encoder = lameenc.Encoder()
        self._encoder.set_bit_rate(bitrate)
        self._encoder.set_in_sample_rate(sample_rate)
        self._encoder.set_channels(channels)
        self._file = output_path.open("wb")

    def write(self, data):
        """PCMデータチャンクをエンコードして書き込む"""
        mp3_data = self._encoder.encode(data)
        if mp3_data:
            self._file.write(mp3_data)

    def close(self):
        """残りのデータをフラッシュして閉じる"""
        final_data = self._encoder.flush()
        self._file.write(final_data)
        self._file.close()
```

利点：
- 録音の長さに関係なく一定のメモリ使用量
- 即座にMP3出力
- 後処理が不要

## スレッディングモデル

```
メインスレッド                   リーダースレッド
    │                              │
    │                    ┌─────────┴─────────┐
    │                    │                   │
    │               mic_reader          loopback_reader
    │                    │                   │
    │                    ▼                   ▼
    │               ┌─────────┐         ┌─────────┐
    │               │mic_queue│         │loop_queue│
    │               └────┬────┘         └────┬────┘
    │                    │                   │
    ▼                    ▼                   │
┌───────────────────────────────────────────┐│
│            メイン録音ループ               ││
│  - キューを排出                           ◀┘
│  - 音声処理（AEC、AGC）                   │
│  - エンコーダーに書き込む                  │
└───────────────────────────────────────────┘
```

### デバイス切り替え

ライブデバイス切り替えは以下を通じてサポートされます：

1. **一時停止イベント**: リーダースレッドに一時停止を通知
2. **ストリーム再作成**: 古いストリームを閉じて新しいものを作成
3. **バッファクリア**: 古い/新しいデバイスのデータが混ざらないようにキューをクリア
4. **再開**: スレッドに続行を通知

## 設定

### AudioSettings（config/settings.py）

```python
class AudioSettings:
    sample_rate: int = 48000    # デフォルト出力サンプルレート
    channels: int = 2           # ステレオ出力
    chunk_size: int = 1024      # バッファあたりのフレーム数
    bit_depth: int = 16         # 16ビット音声
```

### 録音オプション

| オプション | 説明 | デフォルト |
|------------|------|------------|
| `--aec/--no-aec` | 音響エコーキャンセル | 有効 |
| `--stereo-split/--mix` | チャンネル分離 | ミックス |
| `--mic-gain` | マイクゲイン乗数 | 1.5 |
| `--loopback-gain` | システム音声ゲイン乗数 | 1.0 |
| `-b, --bitrate` | MP3ビットレート（kbps） | 128 |
| `-f, --format` | 出力フォーマット（mp3/wav） | mp3 |
