#!/bin/bash
# Activate the project's virtual environment
# Usage: source scripts/activate.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "❌ Virtual environment not found at $PROJECT_DIR/.venv"
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv "$PROJECT_DIR/.venv"
    "$PROJECT_DIR/.venv/bin/pip" install --upgrade pip -q
    "$PROJECT_DIR/.venv/bin/pip" install -e "$PROJECT_DIR" -q
    "$PROJECT_DIR/.venv/bin/pip" install pytest pytest-asyncio pytest-mock -q
    echo "✅ Virtual environment created"
fi

# Activate the venv
source "$PROJECT_DIR/.venv/bin/activate"

echo "✅ Activated project virtual environment"
echo "   Python: $(which python)"
echo "   Version: $(python --version 2>&1)"
echo ""
echo "Common commands:"
echo "  pip install -e .          # Install project"
echo "  pytest tests/ -v          # Run tests"
echo "  python scripts/test_dhan_connection.py  # Test Dhan connection"
echo ""
echo "To deactivate: deactivate"
