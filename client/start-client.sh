#!/bin/bash
# YaP Mic Pass Ult - Client Launcher Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Check if PyAudio is installed
python3 -c "import pyaudio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: PyAudio is not installed."
    echo "Install it with: pip install pyaudio"
    echo "Or install system dependencies first:"
    echo "  Debian/Ubuntu: sudo apt-get install portaudio19-dev python3-pyaudio"
    echo "  Arch/Manjaro: sudo pacman -S portaudio python-pyaudio"
    exit 1
fi

# Run the client
python3 client.py "$@"
