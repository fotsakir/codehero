#!/bin/bash
# CodeHero - macOS Installer
# Double-click this file to run

set -e

echo ""
echo "=========================================="
echo "  CodeHero - macOS Setup                 "
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

    # Start the Multipass daemon
    echo "      Starting Multipass daemon..."
    sudo launchctl load /Library/LaunchDaemons/com.canonical.multipassd.plist 2>/dev/null || true

    # Wait for daemon to be ready
    echo "      Waiting for daemon to initialize..."
    DAEMON_READY=false
    for i in {1..30}; do
        if multipass list &>/dev/null; then
            DAEMON_READY=true
            break
        fi
        sleep 2
    done

    if [ "$DAEMON_READY" = false ]; then
        echo "      Restarting daemon..."
        sudo launchctl unload /Library/LaunchDaemons/com.canonical.multipassd.plist 2>/dev/null || true
        sleep 2
        sudo launchctl load /Library/LaunchDaemons/com.canonical.multipassd.plist
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

# Create desktop shortcut (webloc file)
DESKTOP_PATH="$HOME/Desktop"

cat > "$DESKTOP_PATH/Claude AI Developer.webloc" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>URL</key>
    <string>https://$IP:9453</string>
</dict>
</plist>
EOF
echo "Desktop shortcut created: Claude AI Developer.webloc"

# Create start VM script
cat > "$DESKTOP_PATH/Start Claude VM.command" << 'SCRIPT'
#!/bin/bash
echo "Starting Claude AI Developer VM..."
multipass start claude-dev
echo ""
echo "VM started! Opening dashboard..."
sleep 3
SCRIPT
echo "IP=\$(multipass exec claude-dev -- hostname -I | awk '{print \$1}')" >> "$DESKTOP_PATH/Start Claude VM.command"
echo "open \"https://\$IP:9453\"" >> "$DESKTOP_PATH/Start Claude VM.command"
chmod +x "$DESKTOP_PATH/Start Claude VM.command"
echo "Desktop shortcut created: Start Claude VM.command"

echo ""

# Ask to open browser
read -p "Open dashboard in browser? (y/n): " open_browser
if [[ "$open_browser" == "y" ]]; then
    open "https://$IP:9453"
fi

echo ""
echo "Press Enter to close this window..."
read
