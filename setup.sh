#!/bin/bash
# Setup script for the open-Python Cross-DEX Arbitrage Bot.
# Installs dependencies and prepares .env. Runs nothing else.

echo "=================================================================="
echo "        CROSS-DEX ARBITRAGE BOT - SETUP (OPEN PYTHON)          "
echo "=================================================================="
echo ""

if ! command -v python3 &> /dev/null; then
    echo "✗ python3 not found. Install Python 3.9+ first."
    exit 1
fi
echo "✓ Python found: $(python3 --version)"

echo ""
echo "Creating virtual environment..."
python3 -m venv .venv 2>/dev/null || python3 -m venv venv

if [ -d ".venv" ]; then
    . .venv/bin/activate
elif [ -d "venv" ]; then
    . venv/bin/activate
else
    echo "✗ Failed to create virtual environment."
    exit 1
fi

echo ""
echo "Installing dependencies from requirements.txt..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "✗ Dependency install failed."
    exit 1
fi

if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "IMPORTANT: set PRIVATE_KEY in .env (dedicated backup wallet only)."
else
    echo ""
    echo "✓ .env already exists - keeping it."
fi

echo ""
echo "=================================================================="
echo "✅ Setup complete!"
echo "    Dry run  : source .venv/bin/activate && python3 main.py"
echo "    Live     : add PRIVATE_KEY to .env, then python3 main.py --live"
echo "=================================================================="