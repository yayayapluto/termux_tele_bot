#!/data/data/com.termux/files/usr/bin/bash
set -euo pipefail

pkg update
pkg install -y python termux-api

echo
echo "Termux dependencies installed."
echo "Now create agent/.env and run:"
echo "  python -m agent.main"
