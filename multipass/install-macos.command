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
echo "[1/6] Checking for Multipass..."
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

# Setup SSH key for VM
echo "[2/6] Setting up SSH key for VM access..."
SSH_KEY_PATH="$HOME/.ssh/codehero_vm"

if [ -f "$SSH_KEY_PATH" ]; then
    echo "      SSH key already exists at $SSH_KEY_PATH"
else
    echo "      Generating new SSH key..."
    ssh-keygen -t rsa -b 4096 -f "$SSH_KEY_PATH" -N "" -C "codehero-vm-$(date +%Y%m%d)"
    echo "      SSH key created: $SSH_KEY_PATH"
fi

# Add to ssh-agent
echo "      Adding key to ssh-agent..."
eval "$(ssh-agent -s)" > /dev/null
ssh-add "$SSH_KEY_PATH" 2>/dev/null || true
echo "      Key added to ssh-agent."

# Read the public key
SSH_PUB_KEY=$(cat "${SSH_KEY_PATH}.pub")
echo "      Public key ready for VM."

# Download cloud-init and inject SSH key
echo "[3/6] Preparing VM configuration..."
CLOUD_INIT_URL="https://raw.githubusercontent.com/fotsakir/codehero/main/multipass/cloud-init.yaml"
CLOUD_INIT_PATH="/tmp/cloud-init.yaml"

# Download the template
curl -sL "$CLOUD_INIT_URL" -o "$CLOUD_INIT_PATH"

# Replace the placeholder with actual SSH key (both occurrences)
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS sed syntax
    sed -i '' "s|PASTE_YOUR_SSH_PUBLIC_KEY_HERE|${SSH_PUB_KEY}|g" "$CLOUD_INIT_PATH"
else
    # Linux sed syntax
    sed -i "s|PASTE_YOUR_SSH_PUBLIC_KEY_HERE|${SSH_PUB_KEY}|g" "$CLOUD_INIT_PATH"
fi

echo "      Configuration ready with SSH key."

# Check if VM already exists
echo "[4/6] Checking for existing VM..."
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
echo "[5/6] Creating VM and installing software..."
echo "      - Name: claude-dev"
echo "      - Memory: 4GB"
echo "      - Disk: 64GB"
echo "      - CPUs: 2"
echo "      - OS: Ubuntu 24.04 LTS"
echo ""

# Launch VM (this will wait for cloud-init to complete)
echo "[6/6] Installing software (this takes 15-25 minutes)..."
echo ""
echo "      ┌─────────────────────────────────────────────────────┐"
echo "      │  TIP: To see live installation progress, open a    │"
echo "      │  NEW terminal window and run:                      │"
echo "      │                                                    │"
echo "      │  multipass shell claude-dev                        │"
echo "      │  tail -f /var/log/cloud-init-output.log            │"
echo "      └─────────────────────────────────────────────────────┘"
echo ""
echo "      Please wait..."
echo ""

if ! multipass launch 24.04 --name claude-dev --memory 4G --disk 64G --cpus 2 --timeout 3600 --cloud-init "$CLOUD_INIT_PATH"; then
    echo ""
    echo "ERROR: VM creation failed!"
    echo "Try running: multipass delete claude-dev --purge"
    echo "Then run this script again."
    exit 1
fi

echo ""
echo "Installation complete!"

# Get IP address
IP=$(multipass exec claude-dev -- hostname -I | awk '{print $1}')

# Setup SSH config for easy connection
echo ""
echo "Setting up SSH configuration..."
SSH_CONFIG_FILE="$HOME/.ssh/config"
SSH_CONFIG_ENTRY="# CodeHero VM
Host codehero
    HostName $IP
    User claude
    IdentityFile $SSH_KEY_PATH
    StrictHostKeyChecking no
    UserKnownHostsFile=/dev/null
"

# Check if entry already exists
if grep -q "Host codehero" "$SSH_CONFIG_FILE" 2>/dev/null; then
    # Remove old entry
    sed -i '' '/# CodeHero VM/,/UserKnownHostsFile=\/dev\/null/d' "$SSH_CONFIG_FILE" 2>/dev/null || true
fi

# Add new entry
echo "$SSH_CONFIG_ENTRY" >> "$SSH_CONFIG_FILE"
chmod 600 "$SSH_CONFIG_FILE"

echo "SSH configuration added!"

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
echo "  SSH ACCESS:"
echo "  Connect:      ssh codehero"
echo "  Or:           ssh claude@$IP"
echo "  VS Code:      Use 'Remote-SSH' extension with host 'codehero'"
echo ""
echo "  VM COMMANDS:"
echo "  Start VM:     multipass start claude-dev"
echo "  Stop VM:      multipass stop claude-dev"
echo "  VM Shell:     multipass shell claude-dev"
echo "  VM Status:    multipass list"
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

# Create SSH connection script
cat > "$DESKTOP_PATH/SSH to Claude VM.command" << 'EOF'
#!/bin/bash
echo "Connecting to Claude AI Developer VM..."
echo ""
ssh codehero
EOF
chmod +x "$DESKTOP_PATH/SSH to Claude VM.command"
echo "Desktop shortcut created: SSH to Claude VM.command"

echo ""

# Ask to open browser
read -p "Open dashboard in browser? (y/n): " open_browser
if [[ "$open_browser" == "y" ]]; then
    open "https://$IP:9453"
fi

echo ""
echo "Press Enter to close this window..."
read