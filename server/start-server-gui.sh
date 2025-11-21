#!/bin/bash
# YaP Mic Pass Ult - Server GUI Launcher Script

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed."
    exit 1
fi

# Check if PulseAudio is available (Linux)
if [ "$(uname)" = "Linux" ]; then
    if ! command -v pactl &> /dev/null; then
        echo "Warning: PulseAudio (pactl) not found."
        echo "Virtual device creation may fail."
        echo "Install PulseAudio: sudo apt-get install pulseaudio pulseaudio-utils"
    fi
fi

# Check if tkinter is available
python3 -c "import tkinter" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: tkinter is not installed."
    echo "Install it with your package manager:"
    echo "  Debian/Ubuntu: sudo apt-get install python3-tk"
    echo "  Arch/Manjaro: sudo pacman -S tk"
    exit 1
fi

# Check if PyAudio is installed
python3 -c "import pyaudio" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Error: PyAudio is not installed."
    echo "Install it with: pip install pyaudio"
    exit 1
fi

# Run the server GUI
python3 server_gui.py "$@"
