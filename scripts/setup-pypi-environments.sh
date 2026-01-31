#!/bin/bash
# Setup GitHub Environments for PyPI publishing
# This script creates the testpypi and pypi environments on GitHub

set -e

REPO="dobachi/omni-meeting-recorder"

echo "Setting up GitHub environments for $REPO..."

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "Error: GitHub CLI (gh) is not installed."
    echo "Install it from: https://cli.github.com/"
    exit 1
fi

# Check if authenticated
if ! gh auth status &> /dev/null; then
    echo "Error: Not authenticated with GitHub CLI."
    echo "Run: gh auth login"
    exit 1
fi

# Create testpypi environment
echo "Creating testpypi environment..."
gh api -X PUT "repos/$REPO/environments/testpypi" \
    --silent \
    && echo "  ✓ testpypi environment created" \
    || echo "  ✗ Failed to create testpypi environment (may already exist)"

# Create pypi environment
echo "Creating pypi environment..."
gh api -X PUT "repos/$REPO/environments/pypi" \
    --silent \
    && echo "  ✓ pypi environment created" \
    || echo "  ✗ Failed to create pypi environment (may already exist)"

echo ""
echo "GitHub environments created successfully!"
echo ""
echo "Next steps (manual, required):"
echo ""
echo "1. Configure TestPyPI Trusted Publisher:"
echo "   https://test.pypi.org/manage/account/publishing/"
echo "   - PyPI Project Name: omni-meeting-recorder"
echo "   - Owner: dobachi"
echo "   - Repository name: omni-meeting-recorder"
echo "   - Workflow name: publish.yml"
echo "   - Environment name: testpypi"
echo ""
echo "2. Configure PyPI Trusted Publisher:"
echo "   https://pypi.org/manage/account/publishing/"
echo "   - PyPI Project Name: omni-meeting-recorder"
echo "   - Owner: dobachi"
echo "   - Repository name: omni-meeting-recorder"
echo "   - Workflow name: publish.yml"
echo "   - Environment name: pypi"
