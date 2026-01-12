#!/bin/bash
# Fotios Claude System - macOS Installer
# Double-click this file to run

set -e

echo ""
echo "=========================================="
echo "  Fotios Claude System - macOS Setup     "
echo "=========================================="
echo ""

# Check if Multipass is installed
echo "[1/5] Checking for Multipass..."
if ! command -v multipass &> /dev/null; then
    echo "      Multipass not found. Installing..."

    # Check if Homebrew is installed
    if command -v brew &> /dev/null; then
        echo "      Using Homebrew to install Multipass..."
        brew install --cask multipass
    else
        echo "      Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

        # Add Homebrew to PATH for Apple Silicon
        if [[ $(uname -m) == "arm64" ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi

        echo "      Now installing Multipass..."
        brew install --cask multipass
    fi

    echo "      Multipass installed!"
else
    echo "      Multipass is already installed."
fi

# Download cloud-init
echo "[2/5] Downloading configuration..."
CLOUD_INIT_URL="https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/cloud-init.yaml"
CLOUD_INIT_PATH="/tmp/cloud-init.yaml"
curl -sL "$CLOUD_INIT_URL" -o "$CLOUD_INIT_PATH"
echo "      Done."

# Check if VM already exists
echo "[3/5] Checking for existing VM..."
if multipass list --format csv | grep -q "claude-dev"; then
    echo "      VM 'claude-dev' already exists!"
    read -p "      Delete and recreate? (y/n): " response
    if [[ "$response" == "y" ]]; then
        echo "      Deleting existing VM..."
        multipass delete claude-dev --purge
    else
        echo "      Keeping existing VM. Exiting."
        exit 0
    fi
fi

# Create VM
echo "[4/5] Creating VM (this takes 15-20 minutes)..."
echo "      - Name: claude-dev"
echo "      - Memory: 4GB"
echo "      - Disk: 40GB"
echo "      - OS: Ubuntu 24.04 LTS"
echo ""
echo "      Please wait..."

multipass launch 24.04 --name claude-dev --memory 4G --disk 40G --cpus 2 --cloud-init "$CLOUD_INIT_PATH"

# Wait for cloud-init to complete
echo "[5/5] Waiting for installation to complete..."
echo "      This may take 10-15 more minutes..."

MAX_WAIT=1200  # 20 minutes
WAITED=0
INTERVAL=30

while [ $WAITED -lt $MAX_WAIT ]; do
    sleep $INTERVAL
    WAITED=$((WAITED + INTERVAL))

    # Check if install completed
    INSTALL_STATUS=$(multipass exec claude-dev -- cat /root/install-complete 2>/dev/null || echo "")
    if [ "$INSTALL_STATUS" == "done" ]; then
        break
    fi

    # Check if services are running
    WEB_STATUS=$(multipass exec claude-dev -- systemctl is-active fotios-claude-web 2>/dev/null || echo "inactive")
    if [ "$WEB_STATUS" == "active" ]; then
        break
    fi

    MINUTES=$((WAITED / 60))
    echo "      Still installing... ($MINUTES minutes elapsed)"
done

# Get IP address
IP=$(multipass exec claude-dev -- hostname -I | awk '{print $1}')

# Cleanup
rm -f "$CLOUD_INIT_PATH"

echo ""
echo "=========================================="
echo "  Installation Complete!"
echo "=========================================="
echo ""
echo "  ACCESS POINTS:"
echo "  Dashboard:    https://$IP:9453"
echo "  Web Projects: https://$IP:9867"
echo "  OLS Admin:    https://$IP:7080"
echo ""
echo "  LOGIN:"
echo "  Username:  admin"
echo "  Password:  admin123"
echo ""
echo "  VM TERMINAL:"
echo "  multipass shell claude-dev"
echo ""
echo "  CHANGE PASSWORDS (via Web Terminal or SSH):"
echo "  sudo /opt/fotios-claude/scripts/change-passwords.sh"
echo ""
echo "=========================================="
echo ""

# Ask to open browser
read -p "Open dashboard in browser? (y/n): " open_browser
if [[ "$open_browser" == "y" ]]; then
    open "https://$IP:9453"
fi

echo ""
echo "Press Enter to close this window..."
read
