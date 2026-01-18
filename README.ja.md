# Omni Meeting Recorder (omr)

日本語 | [English](README.md)

Windows向けオンライン会議の音声録音CLIツール。スピーカーやイヤホン使用時でも相手の声（システム音声）と自分の声（マイク）の両方を同時に録音可能。

## 機能

- **システム音声録音（Loopback）**: スピーカー/イヤホンに出力される音声をキャプチャ
- **マイク録音**: マイク入力を録音
- **同時録音**: マイクとシステム音声を同時に録音（デフォルトモード）
- **エコーキャンセル（AEC）**: スピーカー使用時のソフトウェアエコーキャンセル
- **自動音量正規化**: マイクとシステム音声のレベルを自動調整
- **MP3出力**: ビットレート指定可能なMP3直接エンコード
- **Virtual Audio Cable不要**: WASAPI Loopbackを直接使用
- **シンプルなCLI**: 1コマンドで録音開始

## 動作要件

- Windows 10/11
- Python 3.11 - 3.13（3.14以降はlameenc依存関係のため未サポート）
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

## 使い方

```bash
omr start
```

これだけ！`Ctrl+C`で停止。出力: `recording_YYYYMMDD_HHMMSS.mp3`

### インストールせずに試す

```bash
uvx --from git+https://github.com/dobachi/omni-meeting-recorder.git omr start
```

## クイックスタート

```bash
# デバイス一覧を表示
omr devices

# ファイル名を指定して録音
omr start -o meeting.mp3

# システム音声のみ録音
omr start -L -o system.mp3

# マイクのみ録音
omr start -M -o mic.mp3

# AECを無効化（イヤホン使用時）
omr start --no-aec -o meeting.mp3

# MP3ではなくWAVで出力
omr start -f wav -o meeting.wav

# ステレオ分離モード（左=マイク、右=システム）
omr start --stereo-split -o meeting.mp3

# デバイスをインデックスで指定
omr start --loopback-device 5 --mic-device 0 -o meeting.mp3
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

### Step 2: デフォルト録音テスト（マイク＋システム）

1. YouTubeなどで音声を再生し、マイクに向かって話す
2. 録音開始:
   ```powershell
   uv run omr start -o test.mp3
   ```
3. 数秒待ってから `Ctrl+C` で停止
4. 生成されたMP3を再生して両方の音声が録音されていることを確認

### Step 3: システム音声のみテスト

```powershell
uv run omr start -L -o system.mp3
```

### Step 4: マイクのみテスト

```powershell
uv run omr start -M -o mic.mp3
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

録音を開始します。デフォルトではマイクとシステム音声を両方録音し、AECが有効になります。

```bash
omr start                      # マイク＋システム録音（デフォルト）
omr start -o meeting.mp3       # 出力ファイルを指定
omr start -L                   # システム音声のみ（--loopback-only）
omr start -M                   # マイクのみ（--mic-only）
omr start --no-aec             # エコーキャンセルを無効化
omr start --stereo-split       # ステレオ分離: 左=マイク、右=システム
omr start -f wav               # MP3ではなくWAVで出力
omr start -b 192               # MP3ビットレート 192kbps（デフォルト: 128）
```

**オプション:**

| オプション | 説明 |
|-----------|------|
| `-o`, `--output` | 出力ファイルパス |
| `-L`, `--loopback-only` | システム音声のみ録音 |
| `-M`, `--mic-only` | マイクのみ録音 |
| `--aec/--no-aec` | エコーキャンセルの有効/無効（デフォルト: 有効） |
| `--stereo-split/--mix` | ステレオ分離またはミックス（デフォルト: ミックス） |
| `-f`, `--format` | 出力形式: wav, mp3（デフォルト: mp3） |
| `-b`, `--bitrate` | MP3ビットレート（kbps、デフォルト: 128） |
| `--mic-device` | マイクデバイスのインデックス |
| `--loopback-device` | Loopbackデバイスのインデックス |

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

## エコーキャンセル（AEC）

マイクとシステム音声を同時に録音し、**スピーカー**を使用している場合、マイクがスピーカーからの音声を拾います。これにより録音にエコーが発生します。

**解決策**: AECはデフォルトで有効になっており、[pyaec](https://pypi.org/project/pyaec/)ライブラリを使用してエコーを除去します。

```powershell
# AECはデフォルトで有効
omr start -o meeting.mp3

# イヤホン使用時はAECを無効化（若干音質向上）
omr start --no-aec -o meeting.mp3
```

**注意**: 最良の結果を得るには、可能な限りイヤホンの使用を推奨します。AECは効果的ですが、イヤホンが最もクリアな音声を提供します。

## 自動音量正規化

マイクとシステム音声では音量レベルが大きく異なることがあります。例えば、マイク入力が小さくシステム音声が大きい場合、録音した音声のバランスが悪くなります。

**解決策**: 自動音量正規化（AGC: Automatic Gain Control）がデフォルトで有効になっており、両方の音声を目標レベル（16ビットピークの約25%）に自動調整します。

- マイクとシステム音声のRMS（二乗平均平方根）を継続的に計測
- 直近の音声チャンクから平均レベルを算出
- 両方の音声を同じ目標レベルに正規化
- ゲインは0.5〜6.0倍の範囲で自動調整

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

- [x] Phase 3: 音声処理
  - [x] MP3出力対応
  - [x] エコーキャンセル（AEC）
  - [x] 自動音量正規化
  - [ ] FLAC出力対応

- [ ] Phase 4: 安定化・UX
  - [ ] 長時間録音の安定性
  - [ ] デバイス切断対応
  - [ ] 録音中ステータス表示改善
  - [ ] バックグラウンド録音対応
  - [ ] 設定ファイル対応

## ライセンス

MIT License
