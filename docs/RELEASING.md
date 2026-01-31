# Releasing omni-meeting-recorder

This document describes the process for releasing new versions of omni-meeting-recorder to PyPI.

## Prerequisites

### One-time Setup

#### 1. GitHub Environments

Run the setup script to create GitHub environments:

```bash
bash scripts/setup-pypi-environments.sh
```

#### 2. TestPyPI Trusted Publisher

1. Go to https://test.pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in:
   - **PyPI Project Name**: `omni-meeting-recorder`
   - **Owner**: `dobachi`
   - **Repository name**: `omni-meeting-recorder`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `testpypi`
4. Click "Add"

#### 3. PyPI Trusted Publisher

1. Go to https://pypi.org/manage/account/publishing/
2. Click "Add a new pending publisher"
3. Fill in:
   - **PyPI Project Name**: `omni-meeting-recorder`
   - **Owner**: `dobachi`
   - **Repository name**: `omni-meeting-recorder`
   - **Workflow name**: `publish.yml`
   - **Environment name**: `pypi`
4. Click "Add"

## Release Process

### 1. Update Version

Update the version in `pyproject.toml`:

```toml
[project]
version = "X.Y.Z"
```

Also update `src/omr/__init__.py` if it contains a `__version__` variable.

### 2. Update CHANGELOG

Add a new section to `CHANGELOG.md` with the release date:

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- ...

### Changed
- ...

### Fixed
- ...
```

### 3. Commit and Push

```bash
git add pyproject.toml CHANGELOG.md src/omr/__init__.py
git commit -m "chore: bump version to X.Y.Z"
git push
```

### 4. Test with TestPyPI

1. Go to GitHub Actions
2. Select "Publish to PyPI" workflow
3. Click "Run workflow"
4. Select `testpypi` as target
5. Click "Run workflow"

Verify the package at https://test.pypi.org/project/omni-meeting-recorder/

Test installation:

```bash
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    omni-meeting-recorder
omr --version
```

### 5. Publish to PyPI

#### Option A: Manual Trigger

1. Go to GitHub Actions
2. Select "Publish to PyPI" workflow
3. Click "Run workflow"
4. Select `pypi` as target
5. Click "Run workflow"

#### Option B: Create a GitHub Release

1. Go to https://github.com/dobachi/omni-meeting-recorder/releases/new
2. Create a new tag (e.g., `v0.7.2`)
3. Fill in release notes
4. Click "Publish release"

The release will automatically trigger a PyPI publish.

### 6. Verify

Check the package at https://pypi.org/project/omni-meeting-recorder/

Test installation:

```bash
pip install omni-meeting-recorder
omr --version
```

## Local Build Testing

Before publishing, you can test the build locally:

```bash
cd projects/omni-meeting-recorder
uv build
ls -la dist/

# Verify py.typed is included
unzip -l dist/omni_meeting_recorder-*.whl | grep py.typed
```

## Troubleshooting

### "Project does not exist" error

Ensure you have set up the Trusted Publisher on PyPI/TestPyPI before the first publish.

### OIDC token errors

- Check that the GitHub environment name matches exactly (`testpypi` or `pypi`)
- Verify the workflow filename is `publish.yml`
- Ensure `id-token: write` permission is set

### Build fails

- Run `uv sync` to ensure dependencies are up to date
- Check for syntax errors in `pyproject.toml`
- Verify the package builds locally with `uv build`
