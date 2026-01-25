# Contributing to Omni Meeting Recorder

Thank you for your interest in contributing to Omni Meeting Recorder! This document provides guidelines and information for contributors.

## Table of Contents

- [Development Environment Setup](#development-environment-setup)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing Guidelines](#testing-guidelines)
- [Pull Request Process](#pull-request-process)
- [Project Structure](#project-structure)

## Development Environment Setup

### Prerequisites

- **Python 3.11 - 3.13** (3.14+ not yet supported due to lameenc dependency)
- **uv** (recommended) - Fast Python package manager
- **Windows** - Required for audio capture functionality (tests can run on other platforms)

### Setting Up

1. **Clone the repository**

```bash
git clone https://github.com/dobachi/omni-meeting-recorder.git
cd omni-meeting-recorder
```

2. **Install uv** (if not already installed)

```bash
# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **Install dependencies**

```bash
# Install all dependencies including dev tools
uv sync --extra dev

# For building portable version
uv sync --extra dev --group build
```

4. **Verify installation**

```bash
uv run omr --version
uv run omr --help
```

### IDE Setup

#### VS Code (Recommended)

Install these extensions:
- Python
- Pylance
- Ruff

Recommended settings (`.vscode/settings.json`):

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

## Code Style Guidelines

### Type Hints

Type hints are **mandatory** for all functions and methods:

```python
# Good
def process_audio(data: bytes, sample_rate: int) -> list[int]:
    ...

# Bad - missing type hints
def process_audio(data, sample_rate):
    ...
```

### Formatting and Linting

We use **ruff** for both formatting and linting:

```bash
# Check for issues
uv run task lint

# Auto-fix issues
uv run task lint-fix

# Format code
uv run task format
```

### Ruff Configuration

Our ruff configuration (from `pyproject.toml`):

```toml
[tool.ruff]
target-version = "py311"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "C4", "SIM"]
```

Enabled rules:
- `E`, `W`: pycodestyle errors and warnings
- `F`: Pyflakes
- `I`: isort (import sorting)
- `N`: pep8-naming
- `UP`: pyupgrade
- `B`: flake8-bugbear
- `C4`: flake8-comprehensions
- `SIM`: flake8-simplify

### Type Checking

We use **mypy** with strict mode:

```bash
uv run task typecheck
```

Configuration:

```toml
[tool.mypy]
python_version = "3.11"
strict = true
warn_return_any = true
warn_unused_configs = true
mypy_path = "stubs"
```

### Naming Conventions

| Element | Convention | Example |
|---------|------------|---------|
| Classes | PascalCase | `AudioMixer`, `AECProcessor` |
| Functions/Methods | snake_case | `process_audio`, `get_devices` |
| Constants | UPPER_SNAKE_CASE | `DEFAULT_SAMPLE_RATE` |
| Private attributes | _leading_underscore | `self._buffer` |
| Type variables | PascalCase | `T`, `AudioData` |

### Docstrings

Use Google-style docstrings:

```python
def resample(samples: list[int], from_rate: int, to_rate: int) -> list[int]:
    """Resample audio using linear interpolation.

    Args:
        samples: Input audio samples.
        from_rate: Source sample rate in Hz.
        to_rate: Target sample rate in Hz.

    Returns:
        Resampled audio samples at the target rate.

    Raises:
        ValueError: If sample rates are invalid.
    """
```

## Testing Guidelines

### Running Tests

```bash
# Run all tests
uv run task test

# Run with coverage
uv run task test-cov

# Run specific test file
uv run pytest tests/test_mixer.py

# Run specific test
uv run pytest tests/test_mixer.py::test_resample_upsample
```

### Test Structure

```
tests/
├── __init__.py
├── test_mixer.py          # Tests for core/mixer.py
├── test_aec_processor.py  # Tests for core/aec_processor.py
├── test_encoder.py        # Tests for core/encoder.py
└── test_device_manager.py # Tests for core/device_manager.py
```

### Writing Tests

Use pytest with descriptive test names:

```python
import pytest
from omr.core.mixer import AudioMixer, MixerConfig


class TestAudioMixer:
    """Tests for AudioMixer class."""

    def test_init_with_default_config(self) -> None:
        """Mixer initializes with default configuration."""
        mixer = AudioMixer()
        assert mixer.config.sample_rate == 48000

    def test_resample_same_rate_returns_unchanged(self) -> None:
        """Resampling at same rate returns original samples."""
        mixer = AudioMixer()
        samples = [1, 2, 3, 4, 5]
        result = mixer._resample(samples, 48000, 48000)
        assert result == samples

    @pytest.mark.parametrize("from_rate,to_rate,expected_len", [
        (44100, 48000, 109),  # Upsample
        (48000, 44100, 92),   # Downsample
    ])
    def test_resample_length(
        self, from_rate: int, to_rate: int, expected_len: int
    ) -> None:
        """Resampling produces correct output length."""
        mixer = AudioMixer()
        samples = [100] * 100
        result = mixer._resample(samples, from_rate, to_rate)
        assert len(result) == expected_len
```

### Platform-Specific Tests

Some tests require Windows for WASAPI functionality:

```python
import sys
import pytest

@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_wasapi_device_enumeration() -> None:
    """WASAPI backend enumerates audio devices."""
    ...
```

### Coverage Requirements

Aim for high test coverage on core modules:

- `core/mixer.py`: >90%
- `core/aec_processor.py`: >85%
- `core/encoder.py`: >90%
- `backends/wasapi.py`: Best effort (hardware-dependent)

## Pull Request Process

### Branch Naming

Use descriptive branch names:

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/<description>` | `feature/flac-support` |
| Bug fix | `fix/<description>` | `fix/aec-buffer-overflow` |
| Documentation | `docs/<description>` | `docs/api-reference` |
| Refactor | `refactor/<description>` | `refactor/mixer-threading` |

### Commit Messages

Follow conventional commits format:

```
<type>: <description>

[optional body]
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

Examples:

```
feat: add FLAC output format support

- Implement FLACEncoder class
- Add --format flac option to CLI
- Update documentation

fix: resolve AEC buffer overflow on long recordings

The AEC processor was not properly flushing buffers, causing
memory growth during extended recording sessions.

docs: update installation instructions for Python 3.13
```

### PR Checklist

Before submitting a PR, ensure:

- [ ] All tests pass: `uv run task test`
- [ ] Linting passes: `uv run task lint`
- [ ] Type checking passes: `uv run task typecheck`
- [ ] New code has appropriate test coverage
- [ ] Documentation is updated if needed
- [ ] Commit messages follow conventions

### Review Process

1. Create a PR against `main` branch
2. Automated checks will run (lint, typecheck, test)
3. Request review from maintainers
4. Address feedback and update
5. Maintainer approves and merges

## Project Structure

```
omni-meeting-recorder/
├── src/omr/                 # Main package
│   ├── __init__.py
│   ├── cli/                 # Command-line interface
│   │   ├── __init__.py
│   │   ├── main.py          # CLI entry point (Typer app)
│   │   └── commands/
│   │       ├── __init__.py
│   │       ├── record.py    # `omr start` command
│   │       └── devices.py   # `omr devices` command
│   ├── core/                # Core functionality
│   │   ├── __init__.py
│   │   ├── audio_capture.py # High-level capture API
│   │   ├── device_manager.py# Device detection
│   │   ├── mixer.py         # Audio mixing/resampling
│   │   ├── aec_processor.py # Echo cancellation
│   │   ├── encoder.py       # MP3/WAV encoding
│   │   └── input_handler.py # Keyboard handling
│   ├── backends/            # Platform-specific code
│   │   ├── __init__.py
│   │   └── wasapi.py        # Windows WASAPI
│   └── config/              # Configuration
│       ├── __init__.py
│       └── settings.py      # Settings management
├── tests/                   # Test suite
├── stubs/                   # Type stubs for external libs
├── scripts/                 # Build/utility scripts
├── docs/                    # Documentation
├── pyproject.toml           # Project configuration
└── README.md
```

### Key Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Project metadata, dependencies, tool configs |
| `omr.spec` | PyInstaller spec for portable build |
| `scripts/build-portable.py` | Portable version build script |
| `stubs/*.pyi` | Type stubs for libraries without types |

### Adding New Features

1. **Core functionality** → Add to appropriate module in `src/omr/core/`
2. **CLI command** → Add to `src/omr/cli/commands/`
3. **Platform-specific** → Add to `src/omr/backends/`
4. **Configuration** → Update `src/omr/config/settings.py`

### Dependencies

When adding dependencies:

1. Add to `pyproject.toml` under appropriate section
2. Run `uv sync` to update lockfile
3. If library lacks type stubs, add stubs to `stubs/` directory

## Questions?

- Open an issue for questions or feature requests
- Check existing issues before creating new ones
- Join discussions on pull requests

Thank you for contributing!
