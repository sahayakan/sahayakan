#!/usr/bin/env bash
set -euo pipefail

echo "=== Sahayakan Development Setup ==="
echo ""

# 1. Create Python virtual environment
if [ ! -d ".venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv .venv
else
    echo "Virtual environment already exists."
fi

# 2. Activate and install dependencies
echo "Installing dependencies..."
source .venv/bin/activate
pip install -e ".[dev]" --quiet
pip install ruff pre-commit --quiet

# 3. Install pre-commit hooks
echo "Installing pre-commit hooks..."
pre-commit install

# 4. Copy .env if needed
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp infrastructure/.env.example .env
else
    echo ".env already exists, skipping."
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Next steps:"
echo "  source .venv/bin/activate"
echo "  make run       # Start containers"
echo "  make test      # Run unit tests"
echo "  make check     # Lint + test"
