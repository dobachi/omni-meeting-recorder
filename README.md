# Omni Meeting Recorder (omr)

Windows向けオンライン会議の音声録音CLIツール。イヤホン使用時でも相手の声（システム音声）と自分の声（マイク）の両方を録音可能。

## Features

- **システム音声録音（Loopback）**: スピーカー/イヤホンに出力される音声をキャプチャ
- **マイク録音**: マイク入力を録音
- **Virtual Audio Cable不要**: WASAPI Loopbackを直接使用
- **シンプルなCLI**: 簡単なコマンドで録音開始/停止

## Requirements

- Windows 10/11
- Python 3.11+
- uv（推奨）またはpip

## Installation

### uvを使用（推奨）

```bash
# リポジトリをclone
git clone https://github.com/dobachi/omni-meeting-recorder.git
cd omni-meeting-recorder

# 依存関係をインストール
uv sync

# 実行
uv run omr --help
```

### pipを使用

```bash
pip install omni-meeting-recorder
omr --help
```

## Quick Start

```bash
# デバイス一覧を表示
omr devices

# システム音声（Loopback）を録音
omr start --loopback

# マイクを録音
omr start --mic

# 出力ファイルを指定して録音
omr start --loopback --output meeting.wav

# 特定のデバイスを指定
omr start --loopback --loopback-device 5
```

録音を停止するには `Ctrl+C` を押してください。

## Commands

### `omr devices`

利用可能なオーディオデバイスを一覧表示します。

```bash
omr devices           # 録音可能なデバイス（マイク + Loopback）
omr devices --all     # 全デバイス（出力デバイス含む）
omr devices --mic     # マイクのみ
omr devices --loopback  # Loopbackデバイスのみ
```

### `omr start`

録音を開始します。

```bash
omr start --loopback           # システム音声を録音
omr start --mic                # マイクを録音
omr start --loopback --mic     # 両方を録音（Phase 2で実装予定）
omr start -o output.wav        # 出力ファイルを指定
```

## Development

### 開発環境セットアップ

```bash
# 依存関係（開発用含む）をインストール
uv sync --extra dev

# テスト実行
uv run pytest

# リント
uv run ruff check src/

# 型チェック
uv run mypy src/
```

### プロジェクト構成

```
omni-meeting-recorder/
├── src/omr/
│   ├── cli/
│   │   ├── main.py           # CLIエントリーポイント
│   │   └── commands/
│   │       ├── record.py     # 録音コマンド
│   │       └── devices.py    # デバイス一覧
│   ├── core/
│   │   ├── audio_capture.py  # 音声キャプチャ抽象化
│   │   └── device_manager.py # デバイス検出・管理
│   ├── backends/
│   │   └── wasapi.py         # Windows WASAPI実装
│   └── config/
│       └── settings.py       # 設定管理
├── tests/
├── pyproject.toml
└── README.md
```

## Roadmap

- [x] Phase 1: MVP
  - [x] デバイス一覧表示
  - [x] システム音声のみ録音（Loopback）
  - [x] マイク音声のみ録音
  - [x] WAV形式出力
  - [x] Ctrl+Cで停止

- [ ] Phase 2: 同時録音
  - [ ] マイク＋システム音声の同時録音
  - [ ] ステレオ分離モード（左=マイク、右=システム）
  - [ ] タイムスタンプ同期

- [ ] Phase 3: エンコーディング
  - [ ] FLAC出力対応
  - [ ] MP3出力対応
  - [ ] 設定ファイル対応

- [ ] Phase 4: 安定化・UX
  - [ ] 長時間録音の安定性
  - [ ] デバイス切断対応
  - [ ] 録音中ステータス表示改善

## License

MIT License
