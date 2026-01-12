#!/bin/bash
# Fotios Claude System - Linux Installer
# Run: chmod +x install-linux.sh && ./install-linux.sh

set -e

echo ""
echo "=========================================="
echo "  Fotios Claude System - Linux Setup     "
echo "=========================================="
echo ""

# Check if running as root (not recommended for snap)
if [ "$EUID" -eq 0 ]; then
    echo "WARNING: Running as root. Snap works better as regular user."
    echo "Continue anyway? (y/n)"
    read -r response
    if [[ "$response" != "y" ]]; then
        exit 1
    fi
fi

# Check if Multipass is installed
echo "[1/5] Checking for Multipass..."
if ! command -v multipass &> /dev/null; then
    echo "      Multipass not found. Installing..."

    # Check if snap is available
    if command -v snap &> /dev/null; then
        echo "      Using snap to install Multipass..."
        sudo snap install multipass
    else
        echo "      Snap not found. Installing snapd first..."
        if command -v apt &> /dev/null; then
            sudo apt update && sudo apt install -y snapd
        elif command -v dnf &> /dev/null; then
            sudo dnf install -y snapd
            sudo systemctl enable --now snapd.socket
            sudo ln -s /var/lib/snapd/snap /snap
        elif command -v yum &> /dev/null; then
            sudo yum install -y snapd
            sudo systemctl enable --now snapd.socket
        else
            echo "ERROR: Could not find a package manager to install snap."
            echo "Please install Multipass manually: https://multipass.run/install"
            exit 1
        fi

        echo "      Now installing Multipass..."
        sudo snap install multipass
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
echo "  Dashboard: https://$IP:9453"
echo "  Username:  admin"
echo "  Password:  admin123"
echo ""
echo "  To access VM terminal:"
echo "  multipass shell claude-dev"
echo ""
echo "  IMPORTANT: Change passwords after login!"
echo ""
echo "=========================================="
echo ""

# Try to open browser
read -p "Open dashboard in browser? (y/n): " open_browser
if [[ "$open_browser" == "y" ]]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://$IP:9453" 2>/dev/null &
    elif command -v gnome-open &> /dev/null; then
        gnome-open "https://$IP:9453" 2>/dev/null &
    else
        echo "Could not open browser. Please open manually: https://$IP:9453"
    fi
fi
