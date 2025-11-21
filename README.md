<div align="center">
  <img src="icons/yapmicpassult.png" alt="YaP Mic Pass Ult Logo" width="200">
</div>

# YaP Mic Pass Ult

A client-server application for streaming microphone audio over the network. The server creates a virtual audio input device that can be selected in any application, making remote microphone streaming seamless.

## Features

- **Client**: Captures microphone audio and streams it to a server over TCP
- **Server**: Receives audio stream and creates a virtual input device (Linux using PulseAudio)
- **Low Latency**: Direct streaming with minimal buffering and quality presets
- **Volume Control**: Adjustable volume/gain on both client and server (0.0-2.0)
- **Quality Presets**: Choose between low latency, balanced, or high quality modes
- **Cross-Platform Client**: Works on Linux, Windows, and macOS
- **GUI and CLI**: Both graphical and command-line interfaces available
- **Simple Configuration**: Easy-to-use interfaces for configuration

## Requirements

### Linux (Server)
- Python 3.6+
- PulseAudio (for virtual device support)
- `pactl` command-line tool (usually included with PulseAudio)
- PortAudio development libraries (for PyAudio)

### All Platforms (Client)
- Python 3.6+
- PyAudio library
- tkinter (for GUI - usually included with Python)

### Installing Dependencies

#### Quick Install (Recommended)

We provide an automated dependency installer that works on all major Linux distributions:

```bash
./install-dependencies.sh
```

This script will:
- Detect your Linux distribution automatically
- Install all required system packages
- Install Python dependencies via pip
- Verify all installations
- Start PulseAudio service if needed

**Supported distributions:**
- Debian/Ubuntu (and derivatives: Mint, Pop!_OS, Elementary OS, etc.)
- Arch Linux/Manjaro (and derivatives: EndeavourOS, Garuda, etc.)
- Fedora/RHEL/CentOS Stream
- openSUSE/SLE
- Alpine Linux
- Solus

#### Manual Installation

If you prefer to install manually or the automated script doesn't work:

##### Linux (Ubuntu/Debian)
```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3 python3-pip python3-tk \
    pulseaudio pulseaudio-utils portaudio19-dev

# Install Python dependencies
pip3 install --user pyaudio
```

##### Linux (Arch/Manjaro)
```bash
# Install system dependencies
sudo pacman -S python python-pip tk pulseaudio portaudio python-pyaudio

# Note: PyAudio is available as a system package on Arch/Manjaro
```

##### Linux (Fedora/RHEL/CentOS)
```bash
# Install system dependencies
sudo dnf install python3 python3-pip python3-tkinter \
    pulseaudio pulseaudio-utils portaudio-devel

# Install Python dependencies
pip3 install --user pyaudio
```

##### Linux (openSUSE)
```bash
# Install system dependencies
sudo zypper install python3 python3-pip python3-tk \
    pulseaudio pulseaudio-utils portaudio-devel

# Install Python dependencies
pip3 install --user pyaudio
```

#### Python Dependencies Only

If system packages are already installed, you can install just Python dependencies:

```bash
pip install --user -r requirements.txt
```

Or install manually:
```bash
pip install --user pyaudio
```

## Usage

### Graphical Interface (GUI)

Both server and client have graphical interfaces for easy use.

#### Starting the Server GUI

On the machine where you want the virtual microphone to appear:

```bash
cd server
python3 server_gui.py
```

Or use the launcher script:
```bash
./start-server-gui.sh
```

The GUI provides:
- Easy configuration of port and device name
- Start/Stop controls
- Real-time status display (server, client connection, virtual device)
- Connection logs
- Visual feedback for all operations

#### Starting the Client GUI

On the machine with the microphone you want to stream:

```bash
cd client
python3 client_gui.py
```

Or use the launcher script:
```bash
./start-client-gui.sh
```

The GUI provides:
- Server connection settings (host, port)
- Microphone device selection dropdown
- Audio settings (sample rate, channels, chunk size)
- Connect/Disconnect controls
- Real-time status and connection logs

**Note**: For GUI versions, you'll need tkinter installed:
- Debian/Ubuntu: `sudo apt-get install python3-tk`
- Arch/Manjaro: `sudo pacman -S tk`

### Command-Line Interface (CLI)

#### Starting the Server

On the machine where you want the virtual microphone to appear:

```bash
cd server
python3 server.py
```

Options:
- `--port PORT`: Specify server port (default: 5000)
- `--name NAME`: Specify virtual device name (default: YaP-Mic-Pass-Ult)
- `--volume VOLUME`: Set virtual device volume (0.0-2.0, default: 1.0)
- `--no-pulseaudio`: Disable PulseAudio virtual device (Linux only)

Example:
```bash
python3 server.py --port 5000 --name MyVirtualMic --volume 1.5
```

The server will:
1. Create a virtual audio input device named "YaP-Mic-Pass-Ult" (or your custom name)
2. Listen for client connections on the specified port
3. Stream received audio to the virtual device

**Important**: After starting the server, select the virtual device as your microphone input in your applications (Zoom, Discord, OBS, etc.).

#### Starting the Client

On the machine with the microphone you want to stream:

```bash
cd client
python3 client.py --host SERVER_IP --port 5000
```

Options:
- `--host HOST`: Server hostname or IP address (default: localhost)
- `--port PORT`: Server port (default: 5000)
- `--device INDEX`: Audio input device index (use `--list` to see available devices)
- `--rate RATE`: Sample rate in Hz (default: 44100, lower = less latency)
- `--channels N`: Number of audio channels, 1 or 2 (default: 1)
- `--chunk SIZE`: Chunk size in frames (default: 128, lower = less latency but more CPU)
- `--volume VOLUME`: Volume/gain multiplier (0.0-2.0, default: 1.0)
- `--quality QUALITY`: Quality preset: `low_latency`, `balanced` (default), or `high_quality`
- `--list`: List available audio input devices and exit

Examples:

List available microphones:
```bash
python3 client.py --list
```

Connect to a remote server:
```bash
python3 client.py --host 192.168.1.100 --port 5000
```

Use a specific microphone device:
```bash
python3 client.py --host 192.168.1.100 --device 2
```

Use low latency mode for gaming/real-time applications:
```bash
python3 client.py --host 192.168.1.100 --quality low_latency
```

Adjust volume/gain:
```bash
python3 client.py --host 192.168.1.100 --volume 1.5
```

### Complete Example

**On Server Machine** (where virtual mic will appear):
```bash
cd /path/to/YaP-Mic-Pass-Ult/server
python3 server.py
```

Output:
```
Created virtual audio source: YaP-Mic-Pass-Ult
Server listening on port 5000
Waiting for client connection...
```

**On Client Machine** (with microphone):
```bash
cd /path/to/YaP-Mic-Pass-Ult/client
python3 client.py --host SERVER_IP --port 5000
```

After connection, the server will stream audio to the virtual device, which you can then select in any application.

## How It Works

1. **Client**: 
   - Captures audio from the microphone using PyAudio
   - Applies volume/gain adjustment if specified
   - Sends configuration (sample rate, channels, chunk size, quality preset) to server
   - Continuously streams raw PCM audio data over TCP with low-latency optimizations

2. **Server**:
   - Creates a PulseAudio pipe-source module (virtual input device)
   - Configures virtual device volume if specified
   - Opens a named pipe (FIFO) for audio data
   - Receives audio stream from client
   - Writes audio data to the pipe, which PulseAudio reads and makes available as a virtual microphone
   - Uses adaptive buffering based on quality preset for optimal performance

## Troubleshooting

### "PulseAudio not found" or "pactl: command not found"
- Install PulseAudio: `sudo apt-get install pulseaudio pulseaudio-utils` (Debian/Ubuntu)
- Make sure PulseAudio is running: `pulseaudio --check -v`

### "Port already in use"
- Change the port with `--port` option
- Check what's using the port: `sudo netstat -tulpn | grep 5000`

### "Could not connect to server"
- Make sure server is running
- Check firewall settings (port 5000 needs to be open)
- Verify the hostname/IP address is correct

### "No default input device" (Client)
- Use `--list` to see available devices
- Specify a device with `--device INDEX`

### Virtual device not showing up in applications
- Make sure an application has connected to the virtual device (some apps only show active devices)
- Restart the application after starting the server
- Check PulseAudio sources: `pactl list sources short`

### Audio quality issues
- Ensure both client and server use the same sample rate (default 44100 Hz)
- Try adjusting chunk size with `--chunk` option (smaller = lower latency but more CPU)
- Use `--quality low_latency` for gaming/real-time applications (reduces latency)
- Use `--quality high_quality` for best audio quality (increases latency)
- Adjust volume with `--volume` option if audio is too quiet or too loud (0.0-2.0)

### "Connected but no audio is being transmitted"

This is a common issue with several possible causes:

**1. Virtual device not selected in an application:**
   - The server's pipe will block until an application actually selects the virtual device
   - **Solution**: Open an application (Zoom, Discord, OBS, etc.) and select "YaP-Mic-Pass-Ult" as the microphone input
   - The server will show "✓ Pipe opened successfully!" when an application connects

**2. Microphone is muted or not capturing:**
   - Check if your microphone is muted in system settings
   - Verify the microphone works: `arecord -d 5 test.wav && aplay test.wav`
   - The client will warn if it detects very low audio levels
   - **Solution**: Unmute microphone, check system audio settings, try a different microphone

**3. Microphone volume too low:**
   - Use `--volume` option to increase gain: `--volume 1.5` or `--volume 2.0`
   - Check system microphone volume levels

**4. Wrong audio device selected:**
   - Use `--list` to see available devices: `python3 client.py --list`
   - Specify the correct device: `python3 client.py --device INDEX`

**5. Server pipe blocking:**
   - The server waits for an application to connect to the virtual device
   - Check server logs - it should say "Waiting for application to connect..."
   - **Solution**: Select the virtual device in an application (this unblocks the pipe)

**6. Audio format mismatch:**
   - Ensure client and server use compatible settings
   - Try default settings first: `python3 client.py --host SERVER_IP`

**Diagnostic steps:**
```bash
# On server, check if virtual device exists:
pactl list sources short | grep YaP

# On server, check if pipe is being read:
# (Server will show "Pipe opened successfully" when an app connects)

# On client, check audio levels:
# (Client will show warnings if microphone is too quiet)

# Test microphone directly:
arecord -d 3 -f cd test.wav && aplay test.wav
```

### Connection drops
- Check network stability
- Check server logs for errors
- Restart both client and server

## Limitations

- **Windows Server**: Virtual device setup for Windows is not yet implemented. Windows users would need to use VB-Audio Virtual Cable or similar third-party tools.
- **macOS Server**: Virtual device setup for macOS is not yet implemented.
- **Latency**: Network latency depends on network conditions and distance between client and server.
- **Single Client**: The current implementation handles one client connection at a time.

## Building AppImages

Portable AppImages can be built for both the client and server applications. The AppImages are designed to work across all major Linux distributions and desktop environments (GNOME, KDE, XFCE, MATE, Cinnamon, etc.).

### Features

- **Cross-Distribution**: Works on Debian/Ubuntu, Arch/Manjaro, Fedora, openSUSE, and more
- **Desktop Integration**: Full support for GNOME, KDE Plasma, XFCE, MATE, Cinnamon, and other desktop environments
- **Icon Support**: Includes icons in all standard sizes (16x16 to 256x256) for proper display
- **AppStream Metadata**: Includes metadata for software centers and desktop integration
- **System Library Compatibility**: Automatically detects and bundles necessary audio libraries

### Prerequisites

- Python 3.6+ with pip
- PyInstaller: `pip install pyinstaller`
- appimagetool (will be downloaded automatically if not found)
- ImageMagick (optional, for icon resizing - falls back to copying if not available)

### Building

Run the build script:

```bash
./build-appimages.sh
```

This will:
1. Check for and install required dependencies (PyInstaller)
2. Download appimagetool if needed
3. Build both client and server AppImages using PyInstaller
4. Bundle necessary system libraries for audio support
5. Create desktop files compatible with all major desktop environments
6. Generate icons in all standard sizes
7. Add AppStream metadata for software center integration
8. Create portable AppImages in `build/appimages/`

### Output

After building, you'll find:
- `build/appimages/YaP-Mic-Pass-Ult-Client-<arch>.AppImage`
- `build/appimages/YaP-Mic-Pass-Ult-Server-<arch>.AppImage`

### Using AppImages

AppImages are already executable. Simply:

```bash
# Make executable (if needed)
chmod +x YaP-Mic-Pass-Ult-Client-*.AppImage
chmod +x YaP-Mic-Pass-Ult-Server-*.AppImage

# Run directly
./YaP-Mic-Pass-Ult-Client-*.AppImage
./YaP-Mic-Pass-Ult-Server-*.AppImage
```

You can also:
- **Double-click to run** (if your desktop environment supports AppImages)
- **Move to Applications directory**: `mv *.AppImage ~/Applications/`
- **Create desktop shortcuts**: Right-click → "Add to Desktop" or "Create Shortcut"
- **Integrate into application menu**: Some desktop environments automatically detect AppImages

### Desktop Environment Compatibility

The AppImages are tested and work with:
- **GNOME** (Ubuntu, Fedora, Debian)
- **KDE Plasma** (KDE Neon, openSUSE, Manjaro KDE)
- **XFCE** (Xubuntu, Manjaro XFCE)
- **MATE** (Ubuntu MATE)
- **Cinnamon** (Linux Mint)
- **LXQt** (Lubuntu, Manjaro LXQt)
- **Budgie** (Solus, Ubuntu Budgie)
- **Deepin** (Deepin Linux)

### System Requirements

**For Client AppImage:**
- Linux kernel 3.0+ (most modern distributions)
- Audio input device (microphone)
- Network connectivity to server

**For Server AppImage:**
- Linux kernel 3.0+ (most modern distributions)
- PulseAudio installed on the system (for virtual device creation)
- Network connectivity for client connections

**Note**: 
- AppImages require FUSE support on the host system. Most modern Linux distributions include this by default.
- The Server AppImage requires PulseAudio to be installed on the system (it's not bundled). Install it with:
  - Debian/Ubuntu: `sudo apt-get install pulseaudio pulseaudio-utils`
  - Arch/Manjaro: `sudo pacman -S pulseaudio`
  - Fedora: `sudo dnf install pulseaudio pulseaudio-utils`

## License

This project is provided as-is for educational and personal use.

## Notes

- The virtual device remains available as long as the server is running
- You can have multiple client connections (one at a time - disconnect one before connecting another)
- The named pipe is created in the system temp directory
- Press Ctrl+C on either client or server to stop and clean up
