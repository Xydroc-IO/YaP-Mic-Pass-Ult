#!/bin/bash
# Build AppImages for YaP Mic Pass Ult Client and Server
# This script creates portable AppImages for both applications

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  YaP Mic Pass Ult - AppImage Builder  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""

# Function to check dependencies
check_dependency() {
    if ! command -v "$1" &> /dev/null; then
        echo -e "${RED}✗ Error: $1 is not installed.${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Found: $1${NC}"
    return 0
}

# Function to download appimagetool
download_appimagetool() {
    echo -e "${BLUE}Downloading appimagetool...${NC}"
    ARCH="$(uname -m)"
    
    if [ "$ARCH" = "x86_64" ]; then
        URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-x86_64.AppImage"
    elif [ "$ARCH" = "aarch64" ]; then
        URL="https://github.com/AppImage/AppImageKit/releases/download/continuous/appimagetool-aarch64.AppImage"
    else
        echo -e "${YELLOW}Warning: Architecture $ARCH may not be supported${NC}"
        URL="https://github.com/AppImage/AppImageKit/releases/download/13/appimagetool-${ARCH}.AppImage"
    fi
    
    if wget -q --show-progress "$URL" -O appimagetool.AppImage 2>/dev/null || \
       curl -L --progress-bar "$URL" -o appimagetool.AppImage 2>/dev/null; then
        chmod +x appimagetool.AppImage
        echo -e "${GREEN}✓ Downloaded appimagetool${NC}"
        echo "./appimagetool.AppImage"
    else
        echo -e "${RED}✗ Failed to download appimagetool${NC}"
        echo "Please download it manually from: https://github.com/AppImage/AppImageKit/releases"
        exit 1
    fi
}

# Check for required tools
echo -e "${BLUE}Checking dependencies...${NC}"
MISSING_DEPS=0

check_dependency python3 || MISSING_DEPS=1
check_dependency pip3 || MISSING_DEPS=1

if [ $MISSING_DEPS -eq 1 ]; then
    echo -e "${RED}Please install missing dependencies and try again.${NC}"
    exit 1
fi

# Check for PyInstaller
echo ""
echo -e "${BLUE}Checking PyInstaller...${NC}"
if ! python3 -c "import PyInstaller" 2>/dev/null; then
    echo -e "${YELLOW}PyInstaller not found. Installing...${NC}"
    pip3 install --user pyinstaller 2>/dev/null || \
    pip3 install --break-system-packages pyinstaller 2>/dev/null || \
    pip3 install pyinstaller
    echo -e "${GREEN}✓ PyInstaller installed${NC}"
else
    echo -e "${GREEN}✓ PyInstaller found${NC}"
fi

# Check for appimagetool
echo ""
echo -e "${BLUE}Checking appimagetool...${NC}"
APPIMAGETOOL_PATH=""
if command -v appimagetool &> /dev/null; then
    APPIMAGETOOL_PATH="appimagetool"
    echo -e "${GREEN}✓ Found appimagetool in PATH${NC}"
elif [ -f "appimagetool.AppImage" ]; then
    chmod +x appimagetool.AppImage
    APPIMAGETOOL_PATH="./appimagetool.AppImage"
    echo -e "${GREEN}✓ Found appimagetool.AppImage${NC}"
else
    APPIMAGETOOL_PATH=$(download_appimagetool)
fi

# Function to find and copy library dependencies
copy_library_deps() {
    local lib_name="$1"
    local target_dir="$2"
    
    # Try common library paths
    for lib_path in \
        "/usr/lib/x86_64-linux-gnu/$lib_name"* \
        "/usr/lib/$lib_name"* \
        "/lib/x86_64-linux-gnu/$lib_name"* \
        "/lib/$lib_name"* \
        "/usr/local/lib/$lib_name"*; do
        if [ -f "$lib_path" ] && [ ! -L "$lib_path" ]; then
            cp "$lib_path" "$target_dir/" 2>/dev/null && echo "  Copied: $(basename "$lib_path")" && return 0
        fi
    done
    
    # Try using ldd to find dependencies
    if command -v ldd &> /dev/null; then
        for binary_path in "$target_dir/../bin" "$target_dir/../../bin"; do
            if [ -d "$binary_path" ]; then
                for binary in "$binary_path"/*; do
                    if [ -f "$binary" ] && [ -x "$binary" ]; then
                        ldd "$binary" 2>/dev/null | grep -i "$lib_name" | while read -r line; do
                            lib_file=$(echo "$line" | awk '{print $3}' | grep -i "$lib_name")
                            if [ -n "$lib_file" ] && [ -f "$lib_file" ]; then
                                cp "$lib_file" "$target_dir/" 2>/dev/null && echo "  Copied: $(basename "$lib_file")"
                            fi
                        done
                    fi
                done
            fi
        done
    fi
    return 0
}

# Create build directory
BUILD_DIR="$SCRIPT_DIR/build"
APPIMAGE_DIR="$BUILD_DIR/appimages"
mkdir -p "$BUILD_DIR" "$APPIMAGE_DIR"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Building Client AppImage...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Clean previous builds (but keep appimages directory)
rm -rf "$BUILD_DIR/YaP-Mic-Pass-Ult-Client.AppDir"
rm -rf "$SCRIPT_DIR/dist" "$SCRIPT_DIR/__pycache__"
# Keep build directory but clean AppDir
mkdir -p "$BUILD_DIR" "$APPIMAGE_DIR"
mkdir -p "$BUILD_DIR/YaP-Mic-Pass-Ult-Client.AppDir"

# Build with PyInstaller
echo -e "${BLUE}Running PyInstaller for client...${NC}"
cd "$SCRIPT_DIR"
pyinstaller --clean --noconfirm client.spec

# Check if build succeeded
if [ ! -d "$SCRIPT_DIR/dist/yap-mic-pass-ult-client" ]; then
    echo -e "${RED}✗ PyInstaller build failed for client${NC}"
    exit 1
fi

echo -e "${GREEN}✓ PyInstaller build completed${NC}"

# Create AppDir structure
CLIENT_APPDIR="$BUILD_DIR/YaP-Mic-Pass-Ult-Client.AppDir"
mkdir -p "$CLIENT_APPDIR/usr/bin"
mkdir -p "$CLIENT_APPDIR/usr/lib"
mkdir -p "$CLIENT_APPDIR/usr/share/applications"
mkdir -p "$CLIENT_APPDIR/usr/share/icons/hicolor/16x16/apps"
mkdir -p "$CLIENT_APPDIR/usr/share/icons/hicolor/32x32/apps"
mkdir -p "$CLIENT_APPDIR/usr/share/icons/hicolor/48x48/apps"
mkdir -p "$CLIENT_APPDIR/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$CLIENT_APPDIR/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$CLIENT_APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$CLIENT_APPDIR/usr/share/metainfo"

# Copy PyInstaller build
echo -e "${BLUE}Copying files to AppDir...${NC}"
cp -r "$SCRIPT_DIR/dist/yap-mic-pass-ult-client"/* "$CLIENT_APPDIR/usr/bin/"

# Copy system libraries for PyAudio and audio support
echo -e "${BLUE}Bundling system libraries...${NC}"
copy_library_deps "libportaudio" "$CLIENT_APPDIR/usr/lib" || true
copy_library_deps "libasound" "$CLIENT_APPDIR/usr/lib" || true
copy_library_deps "libpulse" "$CLIENT_APPDIR/usr/lib" || true

# Create AppRun script with library path setup
cat > "$CLIENT_APPDIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"

# Set library path for bundled libraries (prepend, don't replace)
if [ -d "${HERE}/usr/lib" ]; then
    export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
fi

# Set environment variables for desktop integration
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS}"
export XDG_DATA_HOME="${HOME}/.local/share"

# Ensure system audio libraries are still accessible
# AppImage uses system PulseAudio/ALSA, but may need bundled portaudio

# Run the application
exec "${HERE}/usr/bin/yap-mic-pass-ult-client" "$@"
EOF
chmod +x "$CLIENT_APPDIR/AppRun"

# Create comprehensive desktop file for all DEs
cat > "$CLIENT_APPDIR/YaP-Mic-Pass-Ult-Client.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=YaP Mic Pass Ult Client
GenericName=Microphone Stream Client
Comment=Stream microphone audio to a remote server over the network
Comment[en]=Stream microphone audio to a remote server over the network
Exec=yap-mic-pass-ult-client
Icon=yap-mic-pass-ult-client
Categories=AudioVideo;Audio;Network;
Keywords=audio;microphone;stream;network;client;
Terminal=false
StartupNotify=true
EOF

# Copy desktop file to proper location
cp "$CLIENT_APPDIR/YaP-Mic-Pass-Ult-Client.desktop" "$CLIENT_APPDIR/usr/share/applications/"

# Create AppStream metadata
cat > "$CLIENT_APPDIR/usr/share/metainfo/yap-mic-pass-ult-client.appdata.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>yap-mic-pass-ult-client</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>Proprietary</project_license>
  <name>YaP Mic Pass Ult Client</name>
  <summary>Stream microphone audio to a remote server</summary>
  <description>
    <p>YaP Mic Pass Ult Client captures microphone audio and streams it to a remote server over TCP.</p>
  </description>
  <categories>
    <category>AudioVideo</category>
    <category>Audio</category>
    <category>Network</category>
  </categories>
  <launchable type="desktop-id">yap-mic-pass-ult-client.desktop</launchable>
</component>
EOF

# Copy and resize icons for all standard sizes
if [ -f "$SCRIPT_DIR/icons/icon.png" ]; then
    echo -e "${BLUE}Creating icon sizes...${NC}"
    ICON_SIZES=(16 32 48 64 128 256)
    for size in "${ICON_SIZES[@]}"; do
        if command -v convert &> /dev/null; then
            convert "$SCRIPT_DIR/icons/icon.png" -resize "${size}x${size}" \
                "$CLIENT_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-client.png" 2>/dev/null || \
            cp "$SCRIPT_DIR/icons/icon.png" "$CLIENT_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-client.png"
        else
            cp "$SCRIPT_DIR/icons/icon.png" "$CLIENT_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-client.png"
        fi
    done
    cp "$SCRIPT_DIR/icons/icon.png" "$CLIENT_APPDIR/yap-mic-pass-ult-client.png"
    echo -e "${GREEN}✓ Icons created${NC}"
elif [ -f "$SCRIPT_DIR/icons/yapmicpassult.png" ]; then
    echo -e "${BLUE}Creating icon sizes...${NC}"
    ICON_SIZES=(16 32 48 64 128 256)
    for size in "${ICON_SIZES[@]}"; do
        if command -v convert &> /dev/null; then
            convert "$SCRIPT_DIR/icons/yapmicpassult.png" -resize "${size}x${size}" \
                "$CLIENT_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-client.png" 2>/dev/null || \
            cp "$SCRIPT_DIR/icons/yapmicpassult.png" "$CLIENT_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-client.png"
        else
            cp "$SCRIPT_DIR/icons/yapmicpassult.png" "$CLIENT_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-client.png"
        fi
    done
    cp "$SCRIPT_DIR/icons/yapmicpassult.png" "$CLIENT_APPDIR/yap-mic-pass-ult-client.png"
    echo -e "${GREEN}✓ Icons created${NC}"
else
    echo -e "${YELLOW}⚠ Warning: No icon found${NC}"
fi

# Build AppImage
echo -e "${BLUE}Creating Client AppImage...${NC}"
# Ensure appimages directory exists
mkdir -p "$APPIMAGE_DIR"
cd "$BUILD_DIR"
ARCH="$(uname -m)"
$APPIMAGETOOL_PATH "$CLIENT_APPDIR" "$APPIMAGE_DIR/YaP-Mic-Pass-Ult-Client-${ARCH}.AppImage" 2>&1 | grep -vE "(desktop file is missing|appstreamcli)" || true

if [ -f "$APPIMAGE_DIR/YaP-Mic-Pass-Ult-Client-${ARCH}.AppImage" ]; then
    chmod +x "$APPIMAGE_DIR/YaP-Mic-Pass-Ult-Client-${ARCH}.AppImage"
    echo -e "${GREEN}✓ Client AppImage created successfully!${NC}"
else
    echo -e "${RED}✗ Failed to create Client AppImage${NC}"
    exit 1
fi

# Clean up PyInstaller files for next build (keep appimages directory)
rm -rf "$SCRIPT_DIR/dist"

echo ""
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}Building Server AppImage...${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Clean previous builds (but keep appimages directory)
rm -rf "$BUILD_DIR/YaP-Mic-Pass-Ult-Server.AppDir"
rm -rf "$SCRIPT_DIR/dist"
# Keep build directory but clean AppDir
mkdir -p "$BUILD_DIR" "$APPIMAGE_DIR"
mkdir -p "$BUILD_DIR/YaP-Mic-Pass-Ult-Server.AppDir"

# Build with PyInstaller
echo -e "${BLUE}Running PyInstaller for server...${NC}"
cd "$SCRIPT_DIR"
pyinstaller --clean --noconfirm server.spec

# Check if build succeeded
if [ ! -d "$SCRIPT_DIR/dist/yap-mic-pass-ult-server" ]; then
    echo -e "${RED}✗ PyInstaller build failed for server${NC}"
    exit 1
fi

echo -e "${GREEN}✓ PyInstaller build completed${NC}"

# Create AppDir structure
SERVER_APPDIR="$BUILD_DIR/YaP-Mic-Pass-Ult-Server.AppDir"
mkdir -p "$SERVER_APPDIR/usr/bin"
mkdir -p "$SERVER_APPDIR/usr/lib"
mkdir -p "$SERVER_APPDIR/usr/share/applications"
mkdir -p "$SERVER_APPDIR/usr/share/icons/hicolor/16x16/apps"
mkdir -p "$SERVER_APPDIR/usr/share/icons/hicolor/32x32/apps"
mkdir -p "$SERVER_APPDIR/usr/share/icons/hicolor/48x48/apps"
mkdir -p "$SERVER_APPDIR/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$SERVER_APPDIR/usr/share/icons/hicolor/128x128/apps"
mkdir -p "$SERVER_APPDIR/usr/share/icons/hicolor/256x256/apps"
mkdir -p "$SERVER_APPDIR/usr/share/metainfo"

# Copy PyInstaller build
echo -e "${BLUE}Copying files to AppDir...${NC}"
cp -r "$SCRIPT_DIR/dist/yap-mic-pass-ult-server"/* "$SERVER_APPDIR/usr/bin/"

# Copy system libraries for PulseAudio support (server needs PulseAudio)
echo -e "${BLUE}Bundling system libraries...${NC}"
copy_library_deps "libpulse" "$SERVER_APPDIR/usr/lib" || true
copy_library_deps "libpulsecommon" "$SERVER_APPDIR/usr/lib" || true
copy_library_deps "libpulsecore" "$SERVER_APPDIR/usr/lib" || true

# Create AppRun script with library path setup
cat > "$SERVER_APPDIR/AppRun" << 'EOF'
#!/bin/bash
HERE="$(dirname "$(readlink -f "${0}")")"

# Set library path for bundled libraries (prepend, don't replace)
if [ -d "${HERE}/usr/lib" ]; then
    export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"
fi

# Set environment variables for desktop integration
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS}"
export XDG_DATA_HOME="${HOME}/.local/share"

# Ensure system PulseAudio is accessible
# AppImage uses system PulseAudio libraries

# Check for PulseAudio
if ! command -v pactl &> /dev/null; then
    echo "Warning: PulseAudio (pactl) not found. Virtual device creation may fail."
    echo "Please install PulseAudio: sudo apt-get install pulseaudio pulseaudio-utils"
    echo "  or on Arch/Manjaro: sudo pacman -S pulseaudio"
    echo "  or on Fedora: sudo dnf install pulseaudio pulseaudio-utils"
fi

# Run the application
exec "${HERE}/usr/bin/yap-mic-pass-ult-server" "$@"
EOF
chmod +x "$SERVER_APPDIR/AppRun"

# Create comprehensive desktop file for all DEs
cat > "$SERVER_APPDIR/YaP-Mic-Pass-Ult-Server.desktop" << 'EOF'
[Desktop Entry]
Version=1.0
Type=Application
Name=YaP Mic Pass Ult Server
GenericName=Microphone Stream Server
Comment=Receive and stream microphone audio as a virtual input device
Comment[en]=Receive and stream microphone audio as a virtual input device
Exec=yap-mic-pass-ult-server
Icon=yap-mic-pass-ult-server
Categories=AudioVideo;Audio;Network;
Keywords=audio;microphone;stream;server;virtual;device;pulseaudio;
Terminal=false
StartupNotify=true
EOF

# Copy desktop file to proper location
cp "$SERVER_APPDIR/YaP-Mic-Pass-Ult-Server.desktop" "$SERVER_APPDIR/usr/share/applications/"

# Create AppStream metadata
cat > "$SERVER_APPDIR/usr/share/metainfo/yap-mic-pass-ult-server.appdata.xml" << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>yap-mic-pass-ult-server</id>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>Proprietary</project_license>
  <name>YaP Mic Pass Ult Server</name>
  <summary>Receive and stream microphone audio as a virtual input device</summary>
  <description>
    <p>YaP Mic Pass Ult Server receives audio streams from clients and creates a virtual audio input device using PulseAudio, making remote microphone streaming seamless.</p>
    <p>Requires PulseAudio to be installed on the system.</p>
  </description>
  <categories>
    <category>AudioVideo</category>
    <category>Audio</category>
    <category>Network</category>
  </categories>
  <launchable type="desktop-id">yap-mic-pass-ult-server.desktop</launchable>
</component>
EOF

# Copy and resize icons for all standard sizes
if [ -f "$SCRIPT_DIR/icons/icon.png" ]; then
    echo -e "${BLUE}Creating icon sizes...${NC}"
    ICON_SIZES=(16 32 48 64 128 256)
    for size in "${ICON_SIZES[@]}"; do
        if command -v convert &> /dev/null; then
            convert "$SCRIPT_DIR/icons/icon.png" -resize "${size}x${size}" \
                "$SERVER_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-server.png" 2>/dev/null || \
            cp "$SCRIPT_DIR/icons/icon.png" "$SERVER_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-server.png"
        else
            cp "$SCRIPT_DIR/icons/icon.png" "$SERVER_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-server.png"
        fi
    done
    cp "$SCRIPT_DIR/icons/icon.png" "$SERVER_APPDIR/yap-mic-pass-ult-server.png"
    echo -e "${GREEN}✓ Icons created${NC}"
elif [ -f "$SCRIPT_DIR/icons/yapmicpassult.png" ]; then
    echo -e "${BLUE}Creating icon sizes...${NC}"
    ICON_SIZES=(16 32 48 64 128 256)
    for size in "${ICON_SIZES[@]}"; do
        if command -v convert &> /dev/null; then
            convert "$SCRIPT_DIR/icons/yapmicpassult.png" -resize "${size}x${size}" \
                "$SERVER_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-server.png" 2>/dev/null || \
            cp "$SCRIPT_DIR/icons/yapmicpassult.png" "$SERVER_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-server.png"
        else
            cp "$SCRIPT_DIR/icons/yapmicpassult.png" "$SERVER_APPDIR/usr/share/icons/hicolor/${size}x${size}/apps/yap-mic-pass-ult-server.png"
        fi
    done
    cp "$SCRIPT_DIR/icons/yapmicpassult.png" "$SERVER_APPDIR/yap-mic-pass-ult-server.png"
    echo -e "${GREEN}✓ Icons created${NC}"
else
    echo -e "${YELLOW}⚠ Warning: No icon found${NC}"
fi

# Build AppImage
echo -e "${BLUE}Creating Server AppImage...${NC}"
# Ensure appimages directory exists
mkdir -p "$APPIMAGE_DIR"
cd "$BUILD_DIR"
ARCH="$(uname -m)"
$APPIMAGETOOL_PATH "$SERVER_APPDIR" "$APPIMAGE_DIR/YaP-Mic-Pass-Ult-Server-${ARCH}.AppImage" 2>&1 | grep -vE "(desktop file is missing|appstreamcli)" || true

if [ -f "$APPIMAGE_DIR/YaP-Mic-Pass-Ult-Server-${ARCH}.AppImage" ]; then
    chmod +x "$APPIMAGE_DIR/YaP-Mic-Pass-Ult-Server-${ARCH}.AppImage"
    echo -e "${GREEN}✓ Server AppImage created successfully!${NC}"
else
    echo -e "${RED}✗ Failed to create Server AppImage${NC}"
    exit 1
fi

# Final cleanup (keep appimages directory and build artifacts)
echo ""
echo -e "${BLUE}Cleaning up...${NC}"
rm -rf "$SCRIPT_DIR/dist"
rm -f "$SCRIPT_DIR"/*.spec.bak
# Clean build directory but keep appimages
if [ -d "$BUILD_DIR" ]; then
    find "$BUILD_DIR" -mindepth 1 ! -path "$APPIMAGE_DIR*" -exec rm -rf {} + 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     AppImages Built Successfully!     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════╝${NC}"
echo ""
echo -e "${GREEN}Output files:${NC}"
echo -e "  ${BLUE}Client:${NC} $APPIMAGE_DIR/YaP-Mic-Pass-Ult-Client-${ARCH}.AppImage"
echo -e "  ${BLUE}Server:${NC} $APPIMAGE_DIR/YaP-Mic-Pass-Ult-Server-${ARCH}.AppImage"
echo ""
echo -e "${YELLOW}Note:${NC} The AppImages are already executable."
echo -e "      You can run them directly or integrate them into your system."
echo ""
