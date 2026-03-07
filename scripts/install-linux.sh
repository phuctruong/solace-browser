#!/bin/bash
# Solace Browser — Linux Installer
# Usage: ./install-linux.sh [path-to-binary]
#
# Installs the Solace Browser binary, creates desktop entry,
# and makes it launchable from your app menu.

set -e

BINARY="${1:-solace-browser-linux-x86_64}"
INSTALL_DIR="$HOME/.local/bin"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
DESKTOP_DIR="$HOME/.local/share/applications"
APP_NAME="solace-browser"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}☯ Solace Browser — Linux Installer${NC}"
echo ""

# Check binary exists
if [ ! -f "$BINARY" ]; then
    echo -e "${YELLOW}Binary not found: $BINARY${NC}"
    echo "Usage: ./install-linux.sh path/to/solace-browser-linux-x86_64"
    exit 1
fi

# Create directories
mkdir -p "$INSTALL_DIR" "$ICON_DIR" "$DESKTOP_DIR"

# Copy binary
echo -e "  Installing binary to ${GREEN}$INSTALL_DIR/$APP_NAME${NC}"
cp "$BINARY" "$INSTALL_DIR/$APP_NAME"
chmod +x "$INSTALL_DIR/$APP_NAME"

# Extract or download icon
ICON_SRC=""
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -f "$SCRIPT_DIR/../web/images/yinyang/yinyang-logo-256.png" ]; then
    ICON_SRC="$SCRIPT_DIR/../web/images/yinyang/yinyang-logo-256.png"
elif [ -f "$SCRIPT_DIR/../snap/local/solace-browser.png" ]; then
    ICON_SRC="$SCRIPT_DIR/../snap/local/solace-browser.png"
fi

if [ -n "$ICON_SRC" ]; then
    echo -e "  Installing icon to ${GREEN}$ICON_DIR/$APP_NAME.png${NC}"
    cp "$ICON_SRC" "$ICON_DIR/$APP_NAME.png"
else
    echo -e "  ${YELLOW}Icon not found — using text-only desktop entry${NC}"
fi

# Create desktop entry
echo -e "  Creating desktop entry at ${GREEN}$DESKTOP_DIR/$APP_NAME.desktop${NC}"
cat > "$DESKTOP_DIR/$APP_NAME.desktop" << EOF
[Desktop Entry]
Name=Solace Browser
GenericName=AI Browser
Comment=AI browser that works while you don't — Gmail, LinkedIn, 25+ apps
Exec=$INSTALL_DIR/$APP_NAME
Icon=solace-browser
Terminal=false
Type=Application
Categories=Network;WebBrowser;Utility;
Keywords=AI;browser;email;gmail;automation;assistant;
StartupWMClass=SolaceBrowser
EOF

# Update desktop database
if command -v update-desktop-database &>/dev/null; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
fi

# Ensure ~/.local/bin is in PATH
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo ""
    echo -e "${YELLOW}NOTE: Add ~/.local/bin to your PATH:${NC}"
    echo '  echo "export PATH=\$HOME/.local/bin:\$PATH" >> ~/.bashrc && source ~/.bashrc'
fi

echo ""
echo -e "${GREEN}✓ Solace Browser installed!${NC}"
echo ""
echo "  Launch from:"
echo "    • App menu: search 'Solace Browser'"
echo "    • Terminal: solace-browser"
echo "    • Browser:  http://localhost:8791"
echo ""
echo -e "  To uninstall: ${BLUE}~/.local/bin/solace-browser --uninstall${NC}"
echo "    or: rm ~/.local/bin/solace-browser ~/.local/share/applications/solace-browser.desktop"
