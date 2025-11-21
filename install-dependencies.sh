#!/bin/bash
#
# YaP Mic Pass Ult - Dependency Installer
# This script installs all necessary dependencies for YaP Mic Pass Ult.
# Supports: Arch/Manjaro, Debian/Ubuntu, Fedora, openSUSE, and other major Linux distributions.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

print_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

echo ""
echo "=========================================="
echo "  YaP Mic Pass Ult - Dependency Installer"
echo "=========================================="
echo ""

# Safety Check: Prevent running as root
if [ "$(id -u)" -eq 0 ]; then
    print_error "Do not run this script as root or with 'sudo'."
    echo "It will ask for your password with 'sudo' when needed."
    exit 1
fi

# Check if sudo is available
if ! command -v sudo &> /dev/null; then
    print_error "sudo is not installed. Please install it first."
    exit 1
fi

# --- Section 1: Detect Distribution and Package Manager ---

print_info "Detecting Linux distribution..."

# Detect the package manager (supporting all major Linux distributions)
if command -v apt &> /dev/null; then
    PACKAGE_MANAGER="apt"
    DISTRO_FAMILY="debian"
    DISTRO_NAME="Debian/Ubuntu"
elif command -v dnf &> /dev/null; then
    PACKAGE_MANAGER="dnf"
    DISTRO_FAMILY="redhat"
    DISTRO_NAME="Fedora/RHEL/CentOS Stream"
elif command -v yum &> /dev/null; then
    PACKAGE_MANAGER="yum"
    DISTRO_FAMILY="redhat"
    DISTRO_NAME="CentOS/RHEL"
elif command -v pacman &> /dev/null; then
    PACKAGE_MANAGER="pacman"
    DISTRO_FAMILY="arch"
    DISTRO_NAME="Arch/Manjaro"
elif command -v zypper &> /dev/null; then
    PACKAGE_MANAGER="zypper"
    DISTRO_FAMILY="suse"
    DISTRO_NAME="openSUSE/SLE"
elif command -v apk &> /dev/null; then
    PACKAGE_MANAGER="apk"
    DISTRO_FAMILY="alpine"
    DISTRO_NAME="Alpine"
elif command -v eopkg &> /dev/null; then
    PACKAGE_MANAGER="eopkg"
    DISTRO_FAMILY="solus"
    DISTRO_NAME="Solus"
else
    print_error "Could not detect a supported package manager."
    echo "Supported managers: apt (Debian/Ubuntu), dnf/yum (Fedora/RHEL), pacman (Arch/Manjaro),"
    echo "                    zypper (openSUSE), apk (Alpine), eopkg (Solus)"
    exit 1
fi

print_success "Detected: $DISTRO_NAME (using $PACKAGE_MANAGER)"

# --- Section 2: Update Package Lists ---

print_info "Updating package lists..."

if [ "$PACKAGE_MANAGER" == "apt" ]; then
    sudo apt update -qq
elif [ "$PACKAGE_MANAGER" == "dnf" ]; then
    sudo dnf check-update -q || [[ $? -eq 100 ]]
elif [ "$PACKAGE_MANAGER" == "yum" ]; then
    sudo yum check-update -q || [[ $? -eq 100 ]]
elif [ "$PACKAGE_MANAGER" == "pacman" ]; then
    sudo pacman -Sy --noconfirm
elif [ "$PACKAGE_MANAGER" == "zypper" ]; then
    sudo zypper refresh -q
elif [ "$PACKAGE_MANAGER" == "apk" ]; then
    sudo apk update
elif [ "$PACKAGE_MANAGER" == "eopkg" ]; then
    sudo eopkg update-repo
fi

print_success "Package lists updated"

# --- Section 3: Define Required Packages ---

print_info "Defining required packages for $DISTRO_NAME..."

# Define packages for each distribution
if [ "$PACKAGE_MANAGER" == "apt" ]; then
    # Debian, Ubuntu, Mint, Pop!_OS, Elementary OS, etc.
    PYTHON3_PKG="python3"
    PYTHON3_PIP_PKG="python3-pip"
    PYTHON3_TK_PKG="python3-tk"
    PULSEAUDIO_PKG="pulseaudio"
    PULSEAUDIO_UTILS_PKG="pulseaudio-utils"
    PORTAUDIO_DEV_PKG="portaudio19-dev"
    PYTHON3_PYAUDIO_PKG="python3-pyaudio"
    INSTALL_CMD="sudo apt install -y"
elif [ "$PACKAGE_MANAGER" == "dnf" ]; then
    # Fedora, CentOS Stream, RHEL 8+
    PYTHON3_PKG="python3"
    PYTHON3_PIP_PKG="python3-pip"
    PYTHON3_TK_PKG="python3-tkinter"
    PULSEAUDIO_PKG="pulseaudio"
    PULSEAUDIO_UTILS_PKG="pulseaudio-utils"
    PORTAUDIO_DEV_PKG="portaudio-devel"
    PYTHON3_PYAUDIO_PKG=""  # Not available in Fedora repos, use pip
    INSTALL_CMD="sudo dnf install -y"
elif [ "$PACKAGE_MANAGER" == "yum" ]; then
    # CentOS 7, RHEL 7, older Fedora
    PYTHON3_PKG="python3"
    PYTHON3_PIP_PKG="python3-pip"
    PYTHON3_TK_PKG="python3-tkinter"
    PULSEAUDIO_PKG="pulseaudio"
    PULSEAUDIO_UTILS_PKG="pulseaudio-utils"
    PORTAUDIO_DEV_PKG="portaudio-devel"
    PYTHON3_PYAUDIO_PKG=""  # Not available, use pip
    INSTALL_CMD="sudo yum install -y"
elif [ "$PACKAGE_MANAGER" == "pacman" ]; then
    # Arch Linux, Manjaro, EndeavourOS, Garuda, etc.
    PYTHON3_PKG="python"
    PYTHON3_PIP_PKG="python-pip"
    PYTHON3_TK_PKG="tk"
    PULSEAUDIO_PKG="pulseaudio"
    PULSEAUDIO_UTILS_PKG="pulseaudio"  # Included in pulseaudio
    PORTAUDIO_DEV_PKG="portaudio"
    PYTHON3_PYAUDIO_PKG="python-pyaudio"
    INSTALL_CMD="sudo pacman -S --noconfirm"
elif [ "$PACKAGE_MANAGER" == "zypper" ]; then
    # openSUSE, SUSE Linux Enterprise
    PYTHON3_PKG="python3"
    PYTHON3_PIP_PKG="python3-pip"
    PYTHON3_TK_PKG="python3-tk"
    PULSEAUDIO_PKG="pulseaudio"
    PULSEAUDIO_UTILS_PKG="pulseaudio-utils"
    PORTAUDIO_DEV_PKG="portaudio-devel"
    PYTHON3_PYAUDIO_PKG=""  # Use pip
    INSTALL_CMD="sudo zypper install -y"
elif [ "$PACKAGE_MANAGER" == "apk" ]; then
    # Alpine Linux
    PYTHON3_PKG="python3"
    PYTHON3_PIP_PKG="py3-pip"
    PYTHON3_TK_PKG="py3-tkinter"
    PULSEAUDIO_PKG="pulseaudio"
    PULSEAUDIO_UTILS_PKG="pulseaudio-utils"
    PORTAUDIO_DEV_PKG="portaudio-dev"
    PYTHON3_PYAUDIO_PKG=""  # Use pip
    INSTALL_CMD="sudo apk add"
elif [ "$PACKAGE_MANAGER" == "eopkg" ]; then
    # Solus
    PYTHON3_PKG="python3"
    PYTHON3_PIP_PKG="python3-pip"
    PYTHON3_TK_PKG="python3-tkinter"
    PULSEAUDIO_PKG="pulseaudio"
    PULSEAUDIO_UTILS_PKG="pulseaudio-utils"
    PORTAUDIO_DEV_PKG="portaudio-devel"
    PYTHON3_PYAUDIO_PKG=""  # Use pip
    INSTALL_CMD="sudo eopkg install -y"
fi

# --- Section 4: Check Existing Installations ---

print_info "Checking for existing installations..."

# Check for Python 3
PYTHON3_INSTALLED=false
if command -v python3 &> /dev/null; then
    PYTHON3_VERSION=$(python3 --version 2>/dev/null || echo "unknown")
    print_success "Python 3 found: $PYTHON3_VERSION"
    PYTHON3_INSTALLED=true
elif command -v python &> /dev/null && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON3_VERSION=$(python --version 2>/dev/null || echo "unknown")
    print_success "Python 3 found: $PYTHON3_VERSION"
    PYTHON3_INSTALLED=true
else
    print_warning "Python 3 not found - will install"
fi

# Check for pip
PIP_INSTALLED=false
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
    PIP_VERSION=$(pip3 --version 2>/dev/null || pip --version 2>/dev/null || echo "unknown")
    print_success "pip found: $PIP_VERSION"
    PIP_INSTALLED=true
else
    print_warning "pip not found - will install"
fi

# Check for tkinter
TK_INSTALLED=false
if python3 -c "import tkinter" 2>/dev/null || python -c "import tkinter" 2>/dev/null; then
    print_success "tkinter found (GUI support available)"
    TK_INSTALLED=true
else
    print_warning "tkinter not found - GUI will not work"
fi

# Check for PulseAudio
PULSEAUDIO_INSTALLED=false
if command -v pactl &> /dev/null; then
    PULSEAUDIO_VERSION=$(pactl --version 2>/dev/null || echo "unknown")
    print_success "PulseAudio found: $PULSEAUDIO_VERSION"
    PULSEAUDIO_INSTALLED=true
else
    print_warning "PulseAudio not found - will install (required for server)"
fi

# Check for PortAudio development libraries
PORTAUDIO_DEV_INSTALLED=false
if pkg-config --exists portaudio-2.0 2>/dev/null || \
   [ -f /usr/include/portaudio.h ] 2>/dev/null || \
   [ -f /usr/local/include/portaudio.h ] 2>/dev/null; then
    print_success "PortAudio development libraries found"
    PORTAUDIO_DEV_INSTALLED=true
else
    print_warning "PortAudio development libraries not found - will install (required for PyAudio)"
fi

# Check for PyAudio
PYAUDIO_INSTALLED=false
if python3 -c "import pyaudio" 2>/dev/null || python -c "import pyaudio" 2>/dev/null; then
    PYAUDIO_VERSION=$(python3 -c "import pyaudio; print(pyaudio.__version__)" 2>/dev/null || \
                     python -c "import pyaudio; print(pyaudio.__version__)" 2>/dev/null || echo "unknown")
    print_success "PyAudio found: $PYAUDIO_VERSION"
    PYAUDIO_INSTALLED=true
else
    print_warning "PyAudio not found - will install"
fi

# Check for Pillow (for icon support in GUI)
PILLOW_INSTALLED=false
if python3 -c "import PIL" 2>/dev/null || python -c "import PIL" 2>/dev/null; then
    PILLOW_VERSION=$(python3 -c "import PIL; print(PIL.__version__)" 2>/dev/null || \
                    python -c "import PIL; print(PIL.__version__)" 2>/dev/null || echo "unknown")
    print_success "Pillow found: $PILLOW_VERSION (icon support available)"
    PILLOW_INSTALLED=true
else
    print_warning "Pillow not found - will install (required for GUI icons)"
fi

# Check for pystray (for system tray support)
PYSTRAY_INSTALLED=false
if python3 -c "import pystray" 2>/dev/null || python -c "import pystray" 2>/dev/null; then
    PYSTRAY_VERSION=$(python3 -c "import pystray; print(pystray.__version__)" 2>/dev/null || \
                     python -c "import pystray; print(pystray.__version__)" 2>/dev/null || echo "unknown")
    print_success "pystray found: $PYSTRAY_VERSION (system tray support available)"
    PYSTRAY_INSTALLED=true
else
    print_warning "pystray not found - will install (required for minimize to tray)"
fi

# --- Section 5: Install Missing System Packages ---

print_info "Installing missing system packages..."

PACKAGES_TO_INSTALL=""

# Python 3
if [ "$PYTHON3_INSTALLED" = false ]; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $PYTHON3_PKG"
    # Also install pip if Python wasn't installed
    if [ -n "$PYTHON3_PIP_PKG" ]; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $PYTHON3_PIP_PKG"
    fi
elif [ "$PIP_INSTALLED" = false ] && [ -n "$PYTHON3_PIP_PKG" ]; then
    # Python is installed but pip is missing
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $PYTHON3_PIP_PKG"
fi

# tkinter
if [ "$TK_INSTALLED" = false ] && [ -n "$PYTHON3_TK_PKG" ]; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $PYTHON3_TK_PKG"
fi

# PulseAudio
if [ "$PULSEAUDIO_INSTALLED" = false ]; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $PULSEAUDIO_PKG"
    if [ -n "$PULSEAUDIO_UTILS_PKG" ] && [ "$PULSEAUDIO_UTILS_PKG" != "$PULSEAUDIO_PKG" ]; then
        PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $PULSEAUDIO_UTILS_PKG"
    fi
fi

# PortAudio development libraries
if [ "$PORTAUDIO_DEV_INSTALLED" = false ] && [ -n "$PORTAUDIO_DEV_PKG" ]; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $PORTAUDIO_DEV_PKG"
fi

# PyAudio (if available as system package)
if [ "$PYAUDIO_INSTALLED" = false ] && [ -n "$PYTHON3_PYAUDIO_PKG" ]; then
    PACKAGES_TO_INSTALL="$PACKAGES_TO_INSTALL $PYTHON3_PYAUDIO_PKG"
fi

if [ -n "$PACKAGES_TO_INSTALL" ]; then
    print_info "Installing system packages: $PACKAGES_TO_INSTALL"
    set +e  # Temporarily disable exit on error
    $INSTALL_CMD $PACKAGES_TO_INSTALL
    INSTALL_EXIT_CODE=$?
    set -e  # Re-enable exit on error
    
    if [ $INSTALL_EXIT_CODE -ne 0 ]; then
        print_error "Failed to install some packages (exit code: $INSTALL_EXIT_CODE)"
        echo "Please install manually:"
        echo "  $PACKAGES_TO_INSTALL"
        exit 1
    fi
    
    print_success "System packages installed successfully"
else
    print_success "All required system packages are already installed"
fi

# --- Section 6: Install Python Packages via pip ---

print_info "Installing Python packages via pip..."

# Determine pip command
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    print_error "pip is not available. Cannot install Python packages."
    exit 1
fi

# Install PyAudio via pip if not installed
if [ "$PYAUDIO_INSTALLED" = false ]; then
    print_info "Installing PyAudio via pip..."
    # Use --break-system-packages flag for modern Python installations
    $PIP_CMD install --user --break-system-packages pyaudio
    if [ $? -eq 0 ]; then
        print_success "PyAudio installed successfully"
    else
        print_warning "Failed to install PyAudio via pip. You may need to:"
        echo "  1. Ensure PortAudio development libraries are installed"
        echo "  2. Try: $PIP_CMD install --user --break-system-packages pyaudio"
    fi
fi

# Install Pillow via pip if not installed
if [ "$PILLOW_INSTALLED" = false ]; then
    print_info "Installing Pillow via pip..."
    # Use --break-system-packages flag for modern Python installations
    $PIP_CMD install --user --break-system-packages Pillow
    if [ $? -eq 0 ]; then
        print_success "Pillow installed successfully"
    else
        print_warning "Failed to install Pillow via pip."
        echo "  Try: $PIP_CMD install --user --break-system-packages Pillow"
    fi
fi

# Install pystray via pip if not installed
if [ "$PYSTRAY_INSTALLED" = false ]; then
    print_info "Installing pystray via pip..."
    # Use --break-system-packages flag for modern Python installations
    $PIP_CMD install --user --break-system-packages pystray
    if [ $? -eq 0 ]; then
        print_success "pystray installed successfully"
    else
        print_warning "Failed to install pystray via pip."
        echo "  Try: $PIP_CMD install --user --break-system-packages pystray"
    fi
fi

# Verify Python package installations
echo ""
print_info "Verifying Python packages..."

if python3 -c "import pyaudio" 2>/dev/null || python -c "import pyaudio" 2>/dev/null; then
    print_success "PyAudio is available"
else
    print_warning "PyAudio verification failed. GUI may still work but audio streaming may fail."
fi

if python3 -c "import PIL" 2>/dev/null || python -c "import PIL" 2>/dev/null; then
    print_success "Pillow is available (icon support enabled)"
else
    print_warning "Pillow not available - GUI icons may not display"
fi

if python3 -c "import pystray" 2>/dev/null || python -c "import pystray" 2>/dev/null; then
    print_success "pystray is available (system tray support enabled)"
else
    print_warning "pystray not available - minimize to tray will not work"
fi

# --- Section 7: Verify All Installations ---

echo ""
print_info "Verifying all installations..."

VERIFY_FAILED=0

# Verify Python 3
if command -v python3 &> /dev/null; then
    PYTHON3_VERSION=$(python3 --version 2>/dev/null || echo "unknown")
    print_success "Python 3: $PYTHON3_VERSION"
elif command -v python &> /dev/null && python --version 2>&1 | grep -q "Python 3"; then
    PYTHON3_VERSION=$(python --version 2>/dev/null || echo "unknown")
    print_success "Python 3: $PYTHON3_VERSION"
else
    print_error "Python 3 verification failed"
    VERIFY_FAILED=1
fi

# Verify pip
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
    PIP_VERSION=$(pip3 --version 2>/dev/null || pip --version 2>/dev/null || echo "unknown")
    print_success "pip: $PIP_VERSION"
else
    print_warning "pip not found (but may not be critical)"
fi

# Verify tkinter
if python3 -c "import tkinter" 2>/dev/null || python -c "import tkinter" 2>/dev/null; then
    print_success "tkinter: Available (GUI support enabled)"
else
    print_warning "tkinter: Not available (GUI will not work)"
    echo "  Install: $PYTHON3_TK_PKG"
fi

# Verify PulseAudio
if command -v pactl &> /dev/null; then
    PULSEAUDIO_VERSION=$(pactl --version 2>/dev/null || echo "unknown")
    print_success "PulseAudio: $PULSEAUDIO_VERSION"
else
    print_warning "PulseAudio: Not found (server will not work)"
    VERIFY_FAILED=1
fi

# Verify PyAudio
if python3 -c "import pyaudio" 2>/dev/null || python -c "import pyaudio" 2>/dev/null; then
    PYAUDIO_VERSION=$(python3 -c "import pyaudio; print(pyaudio.__version__)" 2>/dev/null || \
                     python -c "import pyaudio; print(pyaudio.__version__)" 2>/dev/null || echo "unknown")
    print_success "PyAudio: $PYAUDIO_VERSION"
else
    print_warning "PyAudio: Not available (audio streaming will not work)"
    VERIFY_FAILED=1
fi

# Verify Pillow
if python3 -c "import PIL" 2>/dev/null || python -c "import PIL" 2>/dev/null; then
    PILLOW_VERSION=$(python3 -c "import PIL; print(PIL.__version__)" 2>/dev/null || \
                    python -c "import PIL; print(PIL.__version__)" 2>/dev/null || echo "unknown")
    print_success "Pillow: $PILLOW_VERSION (icon support)"
else
    print_warning "Pillow: Not available (GUI icons may not display)"
fi

# Verify pystray
if python3 -c "import pystray" 2>/dev/null || python -c "import pystray" 2>/dev/null; then
    PYSTRAY_VERSION=$(python3 -c "import pystray; print(pystray.__version__)" 2>/dev/null || \
                     python -c "import pystray; print(pystray.__version__)" 2>/dev/null || echo "unknown")
    print_success "pystray: $PYSTRAY_VERSION (system tray support)"
else
    print_warning "pystray: Not available (minimize to tray will not work)"
fi

# --- Section 8: Check PulseAudio Service ---

echo ""
print_info "Checking PulseAudio service status..."

if systemctl --user is-active --quiet pulseaudio 2>/dev/null || pgrep -u "$USER" pulseaudio > /dev/null 2>&1; then
    print_success "PulseAudio service is running"
else
    print_warning "PulseAudio service is not running"
    echo "Attempting to start PulseAudio..."
    if systemctl --user start pulseaudio 2>/dev/null; then
        print_success "PulseAudio service started"
    elif pulseaudio --start -D 2>/dev/null; then
        print_success "PulseAudio started"
    else
        print_warning "Could not start PulseAudio automatically"
        echo "You may need to start it manually:"
        echo "  systemctl --user start pulseaudio"
        echo "  or"
        echo "  pulseaudio --start"
    fi
fi

# --- Section 9: Final Summary ---

echo ""
echo "=========================================="
if [ $VERIFY_FAILED -eq 0 ]; then
    print_success "Dependency installation complete!"
else
    print_warning "Dependency installation completed with warnings"
fi
echo "=========================================="
echo ""

echo "Installed/Verified:"
echo "  ✅ Python 3"
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
    echo "  ✅ pip"
fi
if python3 -c "import tkinter" 2>/dev/null || python -c "import tkinter" 2>/dev/null; then
    echo "  ✅ tkinter (GUI support)"
fi
if command -v pactl &> /dev/null; then
    echo "  ✅ PulseAudio (server support)"
fi
if python3 -c "import pyaudio" 2>/dev/null || python -c "import pyaudio" 2>/dev/null; then
    echo "  ✅ PyAudio (audio streaming)"
fi
if python3 -c "import PIL" 2>/dev/null || python -c "import PIL" 2>/dev/null; then
    echo "  ✅ Pillow (icon support)"
fi
if python3 -c "import pystray" 2>/dev/null || python -c "import pystray" 2>/dev/null; then
    echo "  ✅ pystray (system tray support)"
fi
echo ""

if [ $VERIFY_FAILED -eq 0 ]; then
    echo "You can now use YaP Mic Pass Ult:"
    echo ""
    echo "  Server (CLI):"
    echo "    cd server && python3 server.py"
    echo ""
    echo "  Server (GUI):"
    echo "    cd server && python3 server_gui.py"
    echo ""
    echo "  Client (CLI):"
    echo "    cd client && python3 client.py --host SERVER_IP"
    echo ""
    echo "  Client (GUI):"
    echo "    cd client && python3 client_gui.py"
    echo ""
else
    echo "⚠️  Some dependencies failed verification. Please check the output above."
    echo "You may need to install missing packages manually."
    echo ""
fi

