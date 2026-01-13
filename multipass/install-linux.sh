#!/bin/bash
# CodeHero - Linux Installer
# Run: chmod +x install-linux.sh && ./install-linux.sh

set -e

echo ""
echo "=========================================="
echo "  CodeHero - Linux Setup                 "
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

    # Wait for multipassd service to be ready
    echo "      Waiting for Multipass daemon to start..."
    sleep 5

    # Check if multipass is working
    DAEMON_READY=false
    for i in {1..30}; do
        if multipass list &>/dev/null; then
            DAEMON_READY=true
            break
        fi
        sleep 2
    done

    if [ "$DAEMON_READY" = false ]; then
        echo "      Restarting Multipass service..."
        sudo snap restart multipass
        sleep 10
    fi

    echo "      Daemon ready!"
else
    echo "      Multipass is already installed."
fi

# Download cloud-init
echo "[2/5] Downloading configuration..."
CLOUD_INIT_URL="https://raw.githubusercontent.com/fotsakir/codehero/main/multipass/cloud-init.yaml"
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
echo "[4/5] Creating VM and installing software..."
echo "      - Name: claude-dev"
echo "      - Memory: 4GB"
echo "      - Disk: 64GB"
echo "      - CPUs: 2"
echo "      - OS: Ubuntu 24.04 LTS"
echo ""

# Launch VM in background so we can show progress
# Using conservative resources for compatibility
multipass launch 24.04 --name claude-dev --memory 4G --disk 64G --cpus 2 --timeout 3600 --cloud-init "$CLOUD_INIT_PATH" &
LAUNCH_PID=$!

# Wait for VM to be running
echo "      Waiting for VM to start..."
while ! multipass list 2>/dev/null | grep -q "claude-dev.*Running"; do
    sleep 3
done
echo "      VM started!"
echo ""

# Show progress by displaying last lines periodically
echo "[5/5] Installing software (15-20 minutes)..."
echo ""

# Just tail -f the log - it will keep running until we kill it
multipass exec claude-dev -- tail -f /var/log/cloud-init-output.log 2>/dev/null &
TAIL_PID=$!

# Wait for the launch process to complete (means cloud-init is done)
wait $LAUNCH_PID
LAUNCH_EXIT=$?

# Kill the tail
kill $TAIL_PID 2>/dev/null
wait $TAIL_PID 2>/dev/null

if [ $LAUNCH_EXIT -ne 0 ]; then
    echo ""
    echo "ERROR: VM creation failed!"
    exit 1
fi

echo ""
echo "Installation complete!"

# Get IP address
IP=$(multipass exec claude-dev -- hostname -I | awk '{print $1}')

# Cleanup
rm -f "$CLOUD_INIT_PATH"

echo ""
echo "=========================================="
echo "  VM Created Successfully!"
echo "=========================================="
echo ""
echo "  IMPORTANT: Software is still installing inside the VM!"
echo "  This takes 10-15 minutes. Wait before accessing the dashboard."
echo ""
echo "  To check installation progress:"
echo "    multipass shell claude-dev"
echo "    tail -f /var/log/cloud-init-output.log"
echo ""
echo "  ACCESS POINTS (available after setup completes):"
echo "  Dashboard:    https://$IP:9453"
echo "  Web Projects: https://$IP:9867"
echo ""
echo "  LOGIN:"
echo "  Username:  admin"
echo "  Password:  admin123"
echo ""
echo "  VM COMMANDS:"
echo "  Start VM:   multipass start claude-dev"
echo "  Stop VM:    multipass stop claude-dev"
echo "  VM Shell:   multipass shell claude-dev"
echo "  VM Status:  multipass list"
echo ""
echo "  CHANGE PASSWORDS (after setup completes):"
echo "  sudo /opt/codehero/scripts/change-passwords.sh"
echo ""
echo "=========================================="
echo ""

# Create desktop shortcut (.desktop file)
DESKTOP_PATH="$HOME/Desktop"
mkdir -p "$DESKTOP_PATH"

cat > "$DESKTOP_PATH/claude-ai-developer.desktop" << EOF
[Desktop Entry]
Version=1.0
Type=Link
Name=Claude AI Developer
Comment=Open Claude AI Developer Dashboard
Icon=web-browser
URL=https://$IP:9453
EOF
chmod +x "$DESKTOP_PATH/claude-ai-developer.desktop"
echo "Desktop shortcut created: claude-ai-developer.desktop"

# Create start VM script
cat > "$DESKTOP_PATH/start-claude-vm.sh" << 'SCRIPT'
#!/bin/bash
echo "Starting Claude AI Developer VM..."
multipass start claude-dev
echo ""
echo "VM started! Opening dashboard..."
sleep 3
IP=$(multipass exec claude-dev -- hostname -I | awk '{print $1}')
xdg-open "https://$IP:9453" 2>/dev/null || echo "Open browser: https://$IP:9453"
SCRIPT
chmod +x "$DESKTOP_PATH/start-claude-vm.sh"
echo "Desktop shortcut created: start-claude-vm.sh"

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
