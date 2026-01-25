# Omni Meeting Recorderへの貢献

Omni Meeting Recorderへの貢献に興味を持っていただきありがとうございます。このドキュメントでは、コントリビューターのためのガイドラインと情報を提供します。

## 目次

- [開発環境のセットアップ](#開発環境のセットアップ)
- [コーディング規約](#コーディング規約)
- [テストガイドライン](#テストガイドライン)
- [プルリクエストプロセス](#プルリクエストプロセス)
- [プロジェクト構成](#プロジェクト構成)

## 開発環境のセットアップ

### 必要条件

- **Python 3.11 - 3.13**（lameenc依存関係のため3.14+は未サポート）
- **uv**（推奨）- 高速なPythonパッケージマネージャー
- **Windows** - 音声キャプチャ機能に必要（テストは他のプラットフォームでも実行可能）

### セットアップ手順

1. **リポジトリをクローン**

```bash
git clone https://github.com/dobachi/omni-meeting-recorder.git
cd omni-meeting-recorder
```

2. **uvをインストール**（まだの場合）

```bash
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **依存関係をインストール**

```bash
# 開発ツールを含むすべての依存関係をインストール
uv sync --extra dev

# ポータブルビルド用
uv sync --extra dev --group build
```

4. **インストールを確認**

```bash
uv run omr --version
uv run omr --help
```

### IDEセットアップ

#### VS Code（推奨）

以下の拡張機能をインストール：
- Python
- Pylance
- Ruff

推奨設定（`.vscode/settings.json`）：

```json
{
    "python.defaultInterpreterPath": ".venv/Scripts/python",
    "python.analysis.typeCheckingMode": "strict",
    "[python]": {
        "editor.defaultFormatter": "charliermarsh.ruff",
        "editor.formatOnSave": true
    }
}
```

## コーディング規約

### 型ヒント

型ヒントはすべての関数とメソッドで**必須**です：

```python
# 良い例
def process_audio(data: bytes, sample_rate: int) -> list[int]:
    ...

# 悪い例 - 型ヒントがない
def process_audio(data, sample_rate):
    ...
```

### フォーマットとリント

フォーマットとリントの両方に**ruff**を使用しています：

```bash
# 問題をチェック
uv run task lint

# 問題を自動修正
uv run task lint-fix

# コードをフォーマット
uv run task format
```

### Ruff設定

ruff設定（`pyproject.toml`より）：

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
```

有効なルール：
- `E`, `W`: pycodestyleエラーと警告
- `F`: Pyflakes
- `I`: isort（インポートのソート）
- `N`: pep8-naming
- `UP`: pyupgrade
- `B`: flake8-bugbear
- `C4`: flake8-comprehensions
- `SIM`: flake8-simplify

### 型チェック

strictモードで**mypy**を使用：

```bash
uv run task typecheck
```

設定：

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
mypy_path = "stubs"
```

### 命名規則

| 要素 | 規則 | 例 |
|------|------|-----|
| クラス | PascalCase | `AudioMixer`, `AECProcessor` |
| 関数/メソッド | snake_case | `process_audio`, `get_devices` |
| 定数 | UPPER_SNAKE_CASE | `DEFAULT_SAMPLE_RATE` |
| プライベート属性 | _先頭アンダースコア | `self._buffer` |
| 型変数 | PascalCase | `T`, `AudioData` |

### ドキュメント文字列

Googleスタイルのドキュメント文字列を使用：

```python
def resample(samples: list[int], from_rate: int, to_rate: int) -> list[int]:
    """線形補間を使用して音声をリサンプリングする。

    Args:
        samples: 入力音声サンプル。
        from_rate: ソースサンプルレート（Hz）。
        to_rate: ターゲットサンプルレート（Hz）。

    Returns:
        ターゲットレートでリサンプリングされた音声サンプル。

    Raises:
        ValueError: サンプルレートが無効な場合。
    """
```

## テストガイドライン

### テストの実行

```bash
# すべてのテストを実行
uv run task test

# カバレッジ付きで実行
uv run task test-cov

# 特定のテストファイルを実行
uv run pytest tests/test_mixer.py

# 特定のテストを実行
uv run pytest tests/test_mixer.py::test_resample_upsample
```

### テスト構成

```
tests/
├── __init__.py
├── test_mixer.py          # core/mixer.pyのテスト
├── test_aec_processor.py  # core/aec_processor.pyのテスト
├── test_encoder.py        # core/encoder.pyのテスト
└── test_device_manager.py # core/device_manager.pyのテスト
```

### テストの書き方

pytestを使用し、わかりやすいテスト名を付ける：

```python
import pytest
from omr.core.mixer import AudioMixer, MixerConfig


class TestAudioMixer:
    """AudioMixerクラスのテスト。"""

    def test_init_with_default_config(self) -> None:
        """デフォルト設定でMixerを初期化する。"""
        mixer = AudioMixer()
        assert mixer.config.sample_rate == 48000

    def test_resample_same_rate_returns_unchanged(self) -> None:
        """同じレートでのリサンプリングは元のサンプルを返す。"""
        mixer = AudioMixer()
        samples = [1, 2, 3, 4, 5]
        result = mixer._resample(samples, 48000, 48000)
        assert result == samples

    @pytest.mark.parametrize("from_rate,to_rate,expected_len", [
        (44100, 48000, 109),  # アップサンプル
        (48000, 44100, 92),   # ダウンサンプル
    ])
    def test_resample_length(
        self, from_rate: int, to_rate: int, expected_len: int
    ) -> None:
        """リサンプリングが正しい出力長を生成する。"""
        mixer = AudioMixer()
        samples = [100] * 100
        result = mixer._resample(samples, from_rate, to_rate)
        assert len(result) == expected_len
```

### プラットフォーム固有のテスト

一部のテストはWASAPI機能のためにWindowsが必要：

```python
import sys
import pytest

@pytest.mark.skipif(sys.platform != "win32", reason="Windowsのみ")
def test_wasapi_device_enumeration() -> None:
    """WASAPIバックエンドが音声デバイスを列挙する。"""
    ...
```

### カバレッジ要件

コアモジュールで高いテストカバレッジを目指す：

- `core/mixer.py`: >90%
- `core/aec_processor.py`: >85%
- `core/encoder.py`: >90%
- `backends/wasapi.py`: ベストエフォート（ハードウェア依存）

## プルリクエストプロセス

### ブランチ命名規則

わかりやすいブランチ名を使用：

| タイプ | パターン | 例 |
|--------|----------|-----|
| 機能 | `feature/<説明>` | `feature/flac-support` |
| バグ修正 | `fix/<説明>` | `fix/aec-buffer-overflow` |
| ドキュメント | `docs/<説明>` | `docs/api-reference` |
| リファクタリング | `refactor/<説明>` | `refactor/mixer-threading` |

### コミットメッセージ

Conventional Commits形式に従う：

```
<タイプ>: <説明>

[オプションの本文]
```

タイプ：
- `feat`: 新機能
- `fix`: バグ修正
- `docs`: ドキュメントのみ
- `refactor`: コードのリファクタリング
- `test`: テストの追加または更新
- `chore`: メンテナンスタスク

例：

```
feat: FLAC出力フォーマットのサポートを追加

- FLACEncoderクラスを実装
- CLIに--format flacオプションを追加
- ドキュメントを更新

fix: 長時間録音時のAECバッファオーバーフローを解決

AECプロセッサがバッファを適切にフラッシュしておらず、
長時間の録音セッション中にメモリが増加していた。

docs: Python 3.13のインストール手順を更新
```

### PRチェックリスト

PRを提出する前に確認：

- [ ] すべてのテストがパス: `uv run task test`
- [ ] リントがパス: `uv run task lint`
- [ ] 型チェックがパス: `uv run task typecheck`
- [ ] 新しいコードに適切なテストカバレッジがある
- [ ] 必要に応じてドキュメントを更新
- [ ] コミットメッセージが規則に従っている

### レビュープロセス

1. `main`ブランチに対してPRを作成
2. 自動チェックが実行される（lint、typecheck、test）
3. メンテナーにレビューをリクエスト
4. フィードバックに対応して更新
5. メンテナーが承認してマージ

## プロジェクト構成

```
omni-meeting-recorder/
├── src/omr/                 # メインパッケージ
│   ├── __init__.py
│   ├── cli/                 # コマンドラインインターフェース
│   │   ├── __init__.py
│   │   ├── main.py          # CLIエントリポイント（Typerアプリ）
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── record.py    # `omr start`コマンド
│   │       └── devices.py   # `omr devices`コマンド
│   ├── core/                # コア機能
│   │   ├── __init__.py
│   │   ├── audio_capture.py # 高レベルキャプチャAPI
│   │   ├── device_manager.py# デバイス検出
│   │   ├── mixer.py         # 音声ミキシング/リサンプリング
│   │   ├── aec_processor.py # エコーキャンセル
│   │   ├── encoder.py       # MP3/WAVエンコード
│   │   └── input_handler.py # キーボード処理
│   ├── backends/            # プラットフォーム固有コード
│   │   ├── __init__.py
│   │   └── wasapi.py        # Windows WASAPI
│   └── config/              # 設定
│       ├── __init__.py
│       └── settings.py      # 設定管理
├── tests/                   # テストスイート
├── stubs/                   # 外部ライブラリの型スタブ
├── scripts/                 # ビルド/ユーティリティスクリプト
├── docs/                    # ドキュメント
├── pyproject.toml           # プロジェクト設定
└── README.md
```

### 主要ファイル

| ファイル | 目的 |
|----------|------|
| `pyproject.toml` | プロジェクトメタデータ、依存関係、ツール設定 |
| `omr.spec` | ポータブルビルド用PyInstaller spec |
| `scripts/build-portable.py` | ポータブル版ビルドスクリプト |
| `stubs/*.pyi` | 型のないライブラリ用の型スタブ |

### 新機能の追加

1. **コア機能** → `src/omr/core/`の適切なモジュールに追加
2. **CLIコマンド** → `src/omr/cli/commands/`に追加
3. **プラットフォーム固有** → `src/omr/backends/`に追加
4. **設定** → `src/omr/config/settings.py`を更新

### 依存関係

依存関係を追加する場合：

1. `pyproject.toml`の適切なセクションに追加
2. `uv sync`を実行してロックファイルを更新
3. ライブラリに型スタブがない場合、`stubs/`ディレクトリにスタブを追加

## 質問がありますか？

- 質問や機能リクエストはissueを作成
- 新しいissueを作成する前に既存のissueを確認
- プルリクエストのディスカッションに参加

貢献ありがとうございます！
