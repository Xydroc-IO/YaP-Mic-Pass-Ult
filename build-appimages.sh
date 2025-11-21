#!/bin/bash
# Build AppImages for YaP Mic Pass Ult Client and Server
# This script creates portable AppImages compatible with all major Linux distributions
# including Arch, Manjaro, Linux Mint, XFCE, and other desktop environments

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  YaP Mic Pass Ult - Universal AppImage Builder       ║${NC}"
echo -e "${GREEN}║  Compatible with Arch, Manjaro, Linux Mint, XFCE    ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
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

# Function to find and bundle system libraries for cross-distro compatibility
find_system_libs() {
    local lib_name="$1"
    local search_paths=(
        "/usr/lib"
        "/usr/lib64"
        "/usr/lib/x86_64-linux-gnu"
        "/usr/lib/i386-linux-gnu"
        "/lib"
        "/lib64"
        "/lib/x86_64-linux-gnu"
        "/usr/local/lib"
    )
    
    for path in "${search_paths[@]}"; do
        if [ -f "$path/$lib_name" ]; then
            echo "$path/$lib_name"
            return 0
        fi
    done
    
    # Try using ldconfig
    local found=$(ldconfig -p 2>/dev/null | grep -oP "(?<= => )/.*/$lib_name" | head -1)
    if [ -n "$found" ] && [ -f "$found" ]; then
        echo "$found"
        return 0
    fi
    
    return 1
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

# Create build directory
BUILD_DIR="$SCRIPT_DIR/build"
APPIMAGE_DIR="$BUILD_DIR/appimages"
mkdir -p "$BUILD_DIR" "$APPIMAGE_DIR"

# Function to build AppImage for a component
build_appimage() {
    local COMPONENT="$1"  # "client" or "server"
    local COMPONENT_NAME="$(echo "$COMPONENT" | tr '[:lower:]' '[:upper:]')"
    local APP_NAME="YaP-Mic-Pass-Ult-${COMPONENT_NAME}"
    local EXE_NAME="yap-mic-pass-ult-${COMPONENT}"
    local SPEC_FILE="${COMPONENT}.spec"
    local APPDIR="$BUILD_DIR/${APP_NAME}.AppDir"
    
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}Building ${COMPONENT_NAME} AppImage...${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    # Clean previous builds
    rm -rf "$APPDIR"
    rm -rf "$SCRIPT_DIR/dist" "$SCRIPT_DIR/build/${COMPONENT}"
    mkdir -p "$APPDIR"
    
    # Build with PyInstaller
    echo -e "${BLUE}Running PyInstaller for ${COMPONENT}...${NC}"
    cd "$SCRIPT_DIR"
    pyinstaller --clean --noconfirm "$SPEC_FILE"
    
    # Check if build succeeded
    # PyInstaller with EXE() creates a single executable file, not a directory
    local EXE_FILE="$SCRIPT_DIR/dist/${EXE_NAME}"
    if [ ! -f "$EXE_FILE" ]; then
        echo -e "${RED}✗ PyInstaller build failed for ${COMPONENT}${NC}"
        echo -e "${RED}   Expected executable not found: $EXE_FILE${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ PyInstaller build completed${NC}"
    
    # Create AppDir structure
    mkdir -p "$APPDIR/usr/bin"
    mkdir -p "$APPDIR/usr/lib"
    mkdir -p "$APPDIR/usr/share/applications"
    mkdir -p "$APPDIR/usr/share/icons/hicolor/256x256/apps"
    
    # Copy PyInstaller executable
    echo -e "${BLUE}Copying executable to AppDir...${NC}"
    cp "$EXE_FILE" "$APPDIR/usr/bin/"
    chmod +x "$APPDIR/usr/bin/${EXE_NAME}"
    
    # Note: PyInstaller should bundle most required libraries
    # We rely on system libraries for maximum compatibility across distributions
    echo -e "${BLUE}Preparing AppDir structure...${NC}"
    
    # Create AppRun script with environment setup for cross-distro compatibility
    echo -e "${BLUE}Creating AppRun script...${NC}"
    cat > "$APPDIR/AppRun" << 'APPRUN_EOF'
#!/bin/bash
# AppRun script with cross-distro compatibility
# Compatible with Arch, Manjaro, Linux Mint, XFCE, and all major Linux distributions

HERE="$(dirname "$(readlink -f "${0}")")"

# Set up library paths - prioritize bundled libs, then system libs
# This ensures compatibility across different distributions
export LD_LIBRARY_PATH="${HERE}/usr/lib:${LD_LIBRARY_PATH}"

# Add common library paths for different distributions
# Arch/Manjaro typically use /usr/lib
# Debian/Ubuntu/Mint use /usr/lib/x86_64-linux-gnu
# Fedora uses /usr/lib64
for lib_path in /usr/lib/x86_64-linux-gnu /usr/lib64 /usr/lib /lib/x86_64-linux-gnu /lib64 /lib; do
    if [ -d "$lib_path" ]; then
        export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}:${lib_path}"
    fi
done

# Set up Python path
export PYTHONPATH="${HERE}/usr/bin:${PYTHONPATH}"

# Set up environment for different desktop environments (XFCE, GNOME, KDE, etc.)
export XDG_DATA_DIRS="${HERE}/usr/share:${XDG_DATA_DIRS}:/usr/share:/usr/local/share"
export XDG_CONFIG_DIRS="${HERE}/usr/etc/xdg:${XDG_CONFIG_DIRS}:/etc/xdg"

# Ensure PulseAudio can find modules (important for Arch/Manjaro)
# PulseAudio module paths vary by distribution
for pulse_path in /usr/lib/pulse /usr/lib64/pulse /usr/lib/x86_64-linux-gnu/pulse; do
    if [ -d "$pulse_path" ]; then
        export PULSE_MODULE_PATH="${PULSE_MODULE_PATH}:${pulse_path}"
    fi
done

# Set up TCL/TK paths for tkinter (critical for GUI)
# Try bundled first, then system locations
if [ -d "${HERE}/usr/lib" ]; then
    for tcl_lib in "${HERE}/usr/lib"/libtcl*.so*; do
        if [ -f "$tcl_lib" ]; then
            # Try to find corresponding TCL library directory
            for tcl_dir in "${HERE}/usr/lib/tcl"* /usr/lib/tcl* /usr/lib64/tcl* /usr/share/tcl*; do
                if [ -d "$tcl_dir" ] && [ -f "$tcl_dir/init.tcl" ]; then
                    export TCL_LIBRARY="$tcl_dir"
                    break 2
                fi
            done
        fi
    done
    for tk_lib in "${HERE}/usr/lib"/libtk*.so*; do
        if [ -f "$tk_lib" ]; then
            # Try to find corresponding TK library directory
            for tk_dir in "${HERE}/usr/lib/tk"* /usr/lib/tk* /usr/lib64/tk* /usr/share/tk*; do
                if [ -d "$tk_dir" ] && [ -f "$tk_dir/init.tcl" ]; then
                    export TK_LIBRARY="$tk_dir"
                    break 2
                fi
            done
        fi
    done
fi

# Fallback to system TCL/TK if not found above
# This handles different package naming across distributions
if [ -z "$TCL_LIBRARY" ]; then
    # Common TCL locations across distributions
    for tcl_path in /usr/lib/tcl* /usr/lib64/tcl* /usr/share/tcl* /usr/lib/tcl*/*.*; do
        if [ -d "$tcl_path" ] && [ -f "$tcl_path/init.tcl" ]; then
            export TCL_LIBRARY="$tcl_path"
            break
        fi
    done
fi

if [ -z "$TK_LIBRARY" ]; then
    # Common TK locations across distributions
    for tk_path in /usr/lib/tk* /usr/lib64/tk* /usr/share/tk* /usr/lib/tk*/*.*; do
        if [ -d "$tk_path" ] && [ -f "$tk_path/init.tcl" ]; then
            export TK_LIBRARY="$tk_path"
            break
        fi
    done
fi

# Ensure PATH includes common binary locations
export PATH="${HERE}/usr/bin:${PATH}:/usr/bin:/usr/local/bin"

# Execute the application
exec "${HERE}/usr/bin/APP_EXECUTABLE" "$@"
APPRUN_EOF
    
    # Replace APP_EXECUTABLE with actual executable name
    sed -i "s|APP_EXECUTABLE|${EXE_NAME}|g" "$APPDIR/AppRun"
    chmod +x "$APPDIR/AppRun"
    
    # Create desktop file
    local DESKTOP_NAME="YaP Mic Pass Ult ${COMPONENT_NAME}"
    local DESKTOP_COMMENT=""
    if [ "$COMPONENT" = "client" ]; then
        DESKTOP_COMMENT="Stream microphone audio to a remote server"
    else
        DESKTOP_COMMENT="Receive and stream microphone audio as a virtual input device"
    fi
    
    cat > "$APPDIR/${APP_NAME}.desktop" << EOF
[Desktop Entry]
Type=Application
Name=${DESKTOP_NAME}
GenericName=Microphone Stream ${COMPONENT_NAME}
Comment=${DESKTOP_COMMENT}
Exec=${EXE_NAME}
Icon=${EXE_NAME}
Categories=AudioVideo;Audio;Network;
Terminal=false
StartupNotify=true
MimeType=
EOF
    
    # Copy icon
    local icon_source=""
    if [ -f "$SCRIPT_DIR/icons/yapmicpassult.png" ]; then
        icon_source="$SCRIPT_DIR/icons/yapmicpassult.png"
    elif [ -f "$SCRIPT_DIR/icons/icon.png" ]; then
        icon_source="$SCRIPT_DIR/icons/icon.png"
    fi
    
    if [ -n "$icon_source" ]; then
        cp "$icon_source" "$APPDIR/${EXE_NAME}.png"
        cp "$icon_source" "$APPDIR/usr/share/icons/hicolor/256x256/apps/${EXE_NAME}.png"
        echo -e "${GREEN}✓ Icon copied${NC}"
    else
        echo -e "${YELLOW}⚠ Warning: icon not found${NC}"
    fi
    
    # Build AppImage
    echo -e "${BLUE}Creating ${COMPONENT_NAME} AppImage...${NC}"
    mkdir -p "$APPIMAGE_DIR"
    cd "$BUILD_DIR"
    ARCH="$(uname -m)"
    
    # Build AppImage (suppress warnings about desktop file and appstream)
    $APPIMAGETOOL_PATH "$APPDIR" "$APPIMAGE_DIR/${APP_NAME}-${ARCH}.AppImage" 2>&1 | \
        grep -vE "(desktop file is missing|appstreamcli|WARNING)" || true
    
    if [ -f "$APPIMAGE_DIR/${APP_NAME}-${ARCH}.AppImage" ]; then
        chmod +x "$APPIMAGE_DIR/${APP_NAME}-${ARCH}.AppImage"
        echo -e "${GREEN}✓ ${COMPONENT_NAME} AppImage created successfully!${NC}"
        echo -e "  ${BLUE}Location:${NC} $APPIMAGE_DIR/${APP_NAME}-${ARCH}.AppImage"
    else
        echo -e "${RED}✗ Failed to create ${COMPONENT_NAME} AppImage${NC}"
        exit 1
    fi
    
    # Clean up PyInstaller files
    rm -rf "$SCRIPT_DIR/dist"
    rm -rf "$SCRIPT_DIR/build/${COMPONENT}"
}

# Build both AppImages
build_appimage "client"
build_appimage "server"

# Final cleanup
echo ""
echo -e "${BLUE}Cleaning up temporary files...${NC}"
rm -rf "$SCRIPT_DIR/dist"
rm -f "$SCRIPT_DIR"/*.spec.bak
# Clean build directory but keep appimages
if [ -d "$BUILD_DIR" ]; then
    find "$BUILD_DIR" -mindepth 1 ! -path "$APPIMAGE_DIR*" -exec rm -rf {} + 2>/dev/null || true
fi

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║     AppImages Built Successfully!                     ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""
ARCH="$(uname -m)"
echo -e "${GREEN}Output files:${NC}"
echo -e "  ${BLUE}Client:${NC} $APPIMAGE_DIR/YaP-Mic-Pass-Ult-CLIENT-${ARCH}.AppImage"
echo -e "  ${BLUE}Server:${NC} $APPIMAGE_DIR/YaP-Mic-Pass-Ult-SERVER-${ARCH}.AppImage"
echo ""
echo -e "${YELLOW}Compatibility:${NC}"
echo -e "  ✓ Arch Linux / Manjaro"
echo -e "  ✓ Linux Mint / Ubuntu / Debian"
echo -e "  ✓ XFCE / GNOME / KDE / Other DEs"
echo -e "  ✓ All major Linux distributions"
echo ""
echo -e "${YELLOW}Note:${NC} The AppImages are already executable."
echo -e "      You can run them directly or integrate them into your system."
echo ""
