# Omni Meeting Recorder (omr)

日本語 | [English](README.md)

Windows向けオンライン会議の音声録音CLIツール。イヤホン使用時でも相手の声（システム音声）と自分の声（マイク）の両方を同時に録音可能。

## 機能

- **システム音声録音（Loopback）**: スピーカー/イヤホンに出力される音声をキャプチャ
- **マイク録音**: マイク入力を録音
- **同時録音**: マイクとシステム音声を同時に録音（ステレオ分離またはミックス）
- **Virtual Audio Cable不要**: WASAPI Loopbackを直接使用
- **シンプルなCLI**: 簡単なコマンドで録音開始/停止

## 動作要件

- Windows 10/11
- Python 3.11以上
- uv（推奨）またはpip

## インストール

### 1. Pythonのインストール

Python 3.11以上がインストールされていない場合:

1. [Python公式サイト](https://www.python.org/downloads/)からWindows用インストーラをダウンロード
2. インストーラを実行し、**「Add Python to PATH」にチェック**を入れてインストール
3. PowerShellまたはコマンドプロンプトで確認:
   ```powershell
   python --version
   # Python 3.11.x 以上が表示されればOK
   ```

### 2. uvのインストール（推奨）

uvは高速なPythonパッケージマネージャーです。

**PowerShellで実行:**
```powershell
# uvをインストール
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# インストール確認
uv --version
```

または、pipでインストール:
```powershell
pip install uv
```

### 3. omrのインストール

#### 方法A: GitHubからclone（開発者向け）

```powershell
# リポジトリをclone
git clone https://github.com/dobachi/omni-meeting-recorder.git
cd omni-meeting-recorder

# 依存関係をインストール
uv sync

# 動作確認
uv run omr --version
uv run omr --help
```

#### 方法B: pipで直接インストール（ユーザー向け）

```powershell
# PyPIからインストール（公開後）
pip install omni-meeting-recorder

# または、GitHubから直接インストール
pip install git+https://github.com/dobachi/omni-meeting-recorder.git

# 動作確認
omr --version
```

## クイックスタート

```bash
# デバイス一覧を表示
omr devices

# システム音声（Loopback）を録音
omr start --loopback

# マイクを録音
omr start --mic

# 両方を録音（ステレオ分離: 左=マイク、右=システム）
omr start --loopback --mic

# 両方を録音（ミックスモード）
omr start --loopback --mic --mix

# 出力ファイルを指定して録音
omr start --loopback --output meeting.wav

# 特定のデバイスを指定
omr start --loopback --loopback-device 5
```

録音を停止するには `Ctrl+C` を押してください。

## 動作テスト

### Step 1: デバイス一覧の確認

```powershell
# uvでインストールした場合
uv run omr devices

# pipでインストールした場合
omr devices
```

**期待される出力例:**
```
                    Recording Devices
┏━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Index  ┃ Type     ┃ Name                           ┃ Channels   ┃ Sample Rate  ┃ Default  ┃
┡━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 0      │ MIC      │ マイク (Realtek Audio)          │     2      │    44100 Hz  │    *     │
│ 3      │ LOOP     │ スピーカー (Realtek Audio)      │     2      │    48000 Hz  │          │
└────────┴──────────┴────────────────────────────────┴────────────┴──────────────┴──────────┘
```

- **MIC**: マイクデバイス
- **LOOP**: Loopbackデバイス（システム音声をキャプチャ可能）
- **\***: デフォルトデバイス

### Step 2: システム音声（Loopback）録音テスト

1. YouTubeなどで音声を再生
2. 録音開始:
   ```powershell
   uv run omr start --loopback
   ```
3. 数秒待ってから `Ctrl+C` で停止
4. 生成された `recording_YYYYMMDD_HHMMSS.wav` を再生して確認

### Step 3: マイク録音テスト

1. マイクに向かって話しながら:
   ```powershell
   uv run omr start --mic
   ```
2. `Ctrl+C` で停止
3. 生成されたWAVファイルを再生して確認

### Step 4: 同時録音テスト

```powershell
# マイクとシステム音声を同時に録音（ステレオ分離）
uv run omr start --loopback --mic

# 特定のデバイスを指定して録音
uv run omr start --loopback --mic --loopback-device 3 --mic-device 0
```

## コマンド

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
omr start --loopback --mic     # 両方を録音（ステレオ分離）
omr start --loopback --mic --mix  # 両方を録音（ミックス）
omr start -o output.wav        # 出力ファイルを指定
```

## トラブルシューティング

### 「No devices found」と表示される

- Windowsのサウンド設定で、オーディオデバイスが有効になっているか確認
- 「サウンドの設定」→「サウンドコントロールパネル」で無効なデバイスを有効化

### Loopbackデバイスが表示されない

- 出力デバイス（スピーカー/イヤホン）が接続・有効になっているか確認
- WASAPI対応のオーディオドライバがインストールされているか確認

### 録音ファイルが無音

- 録音中にシステム音声が実際に再生されているか確認
- `omr devices --all` で正しいデバイスを選択しているか確認
- 別のLoopbackデバイスを試す: `--loopback-device <index>`

### PyAudioWPatchのインストールエラー

PyAudioWPatchはWindowsのみ対応しています。Linux/macOSではテストのみ実行可能です。

```powershell
# 手動でPyAudioWPatchをインストール
pip install PyAudioWPatch
```

## 既知の制限事項

### 同時録音時のエコー問題（マイク + Loopback）

`--mic` と `--loopback` オプションを同時に使用し、**スピーカー**（ヘッドホンではなく）を使用している場合、マイクがスピーカーからの音声を拾ってしまうことがあります。これにより、録音にエコーや音声の重複が発生します。

**対処方法**: 同時録音モードを使用する際は、スピーカーの代わりにヘッドホンを使用してください。これにより、マイクがスピーカー出力をキャプチャするのを防ぐことができます。

```powershell
# 両方のオプションを使用すると警告が表示されます
uv run omr start --mic --loopback
# Warning: Using mic and loopback together may cause echo if speakers are used.
# Recommendation: Use headphones to prevent microphone from picking up speaker audio.
```

詳細とソフトウェアベースのエコーキャンセルの将来計画については、[Issue #6](https://github.com/dobachi/omni-meeting-recorder/issues/6) を参照してください。

## 開発

### 開発環境セットアップ

```bash
# 依存関係（開発用含む）をインストール
uv sync --extra dev
```

### チェックの実行

`uv run task`を使ってリント、型チェック、テストを実行できます：

```bash
# 全チェック実行（lint + typecheck + test）
uv run task check

# 個別に実行:
uv run task lint       # ruffでリント
uv run task typecheck  # mypyで型チェック
uv run task test       # pytestでテスト

# その他のコマンド:
uv run task lint-fix   # リント問題を自動修正
uv run task format     # ruffでコード整形
uv run task test-cov   # カバレッジ付きテスト
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
│   │   ├── device_manager.py # デバイス検出・管理
│   │   └── mixer.py          # 音声ミキシング・リサンプリング
│   ├── backends/
│   │   └── wasapi.py         # Windows WASAPI実装
│   └── config/
│       └── settings.py       # 設定管理
├── tests/
├── pyproject.toml
└── README.md
```

## ロードマップ

- [x] Phase 1: MVP
  - [x] デバイス一覧表示
  - [x] システム音声のみ録音（Loopback）
  - [x] マイク音声のみ録音
  - [x] WAV形式出力
  - [x] Ctrl+Cで停止

- [x] Phase 2: 同時録音
  - [x] マイク＋システム音声の同時録音
  - [x] ステレオ分離モード（左=マイク、右=システム）
  - [x] タイムスタンプ同期

- [ ] Phase 3: エンコーディング
  - [ ] FLAC出力対応
  - [ ] MP3出力対応
  - [ ] 設定ファイル対応

- [ ] Phase 4: 安定化・UX
  - [ ] 長時間録音の安定性
  - [ ] デバイス切断対応
  - [ ] 録音中ステータス表示改善
  - [ ] バックグラウンド録音対応

## ライセンス

MIT License
