# Installation with Multipass (macOS & Linux)

Complete guide to install codehero using Multipass virtual machines.

## Table of Contents

- [What is Multipass?](#what-is-multipass)
- [Requirements](#requirements)
- [Quick Install](#quick-install)
  - [macOS](#macos)
  - [Linux](#linux)
- [Manual Installation](#manual-installation)
- [After Installation](#after-installation)
- [Daily Usage](#daily-usage)
- [Troubleshooting](#troubleshooting)
  - [macOS Issues](#macos-issues)
  - [Linux Issues](#linux-issues)

---

## What is Multipass?

Multipass is a free tool from Canonical (makers of Ubuntu) that creates lightweight Ubuntu virtual machines with a single command. It's:

- **Simple** - One command to create a VM
- **Fast** - Uses native hypervisors (HyperKit/QEMU on macOS, KVM/LXD on Linux)
- **Free** - Open source, no license needed
- **Cross-platform** - Works on macOS and Linux

---

## Requirements

| | Minimum | Recommended |
|---|---------|-------------|
| RAM | 8GB total (6GB for VM) | 16GB total |
| Disk | 70GB free | 100GB free |
| CPU | 2 cores | 4+ cores |

### macOS Requirements

- macOS 10.15 (Catalina) or newer
- Intel or Apple Silicon (M1/M2/M3/M4)
- Homebrew (installed automatically if missing)

### Linux Requirements

- Ubuntu 18.04+, Debian 10+, Fedora 32+, or similar
- Snap support (installed automatically if missing)
- KVM support recommended (check: `egrep -c '(vmx|svm)' /proc/cpuinfo` > 0)

---

## Quick Install

### macOS

#### Option 1: One-Line Install (Terminal)

```bash
curl -sL https://raw.githubusercontent.com/fotsakir/codehero/main/multipass/install-macos.command | bash
```

#### Option 2: Download and Double-Click

1. Download: [install-macos.command](https://raw.githubusercontent.com/fotsakir/codehero/main/multipass/install-macos.command)
2. Double-click the file
3. If macOS blocks it: **System Settings** → **Privacy & Security** → **Allow**
4. Enter your password when prompted (for sudo)

#### What Happens

1. Installs Homebrew (if not installed)
2. Installs Multipass via Homebrew
3. Starts the Multipass daemon
4. Downloads Ubuntu 24.04 image
5. Creates VM with 6GB RAM, 64GB disk, 4 CPUs
6. Installs codehero inside VM
7. Creates desktop shortcuts

**Installation time:** 15-25 minutes (depending on internet speed)

---

### Linux

#### One-Line Install

```bash
curl -sL https://raw.githubusercontent.com/fotsakir/codehero/main/multipass/install-linux.sh | bash
```

#### What Happens

1. Installs Snap (if not installed)
2. Installs Multipass via Snap
3. Downloads Ubuntu 24.04 image
4. Creates VM with 6GB RAM, 64GB disk, 4 CPUs
5. Installs codehero inside VM
6. Creates desktop shortcuts

**Installation time:** 15-25 minutes

---

## Manual Installation

If you prefer step-by-step control:

### Step 1: Install Multipass

**macOS:**
```bash
brew install --cask multipass
```

**Ubuntu/Debian:**
```bash
sudo snap install multipass
```

**Fedora:**
```bash
sudo dnf install snapd
sudo ln -s /var/lib/snapd/snap /snap
sudo snap install multipass
```

**Arch Linux:**
```bash
sudo pacman -S snapd
sudo systemctl enable --now snapd.socket
sudo snap install multipass
```

### Step 2: Verify Installation

```bash
multipass version
multipass list
```

### Step 3: Download Configuration

```bash
curl -sL https://raw.githubusercontent.com/fotsakir/codehero/main/multipass/cloud-init.yaml -o /tmp/cloud-init.yaml
```

### Step 4: Create the VM

```bash
multipass launch 24.04 \
  --name claude-dev \
  --memory 6G \
  --disk 64G \
  --cpus 4 \
  --timeout 1800 \
  --cloud-init /tmp/cloud-init.yaml
```

This takes 15-20 minutes. The cloud-init configuration automatically:
- Updates the system
- Installs all dependencies
- Downloads and installs codehero
- Configures services

### Step 5: Check Installation Progress

```bash
# Watch installation logs
multipass exec claude-dev -- tail -f /var/log/cloud-init-output.log

# Check if complete
multipass exec claude-dev -- cat /root/install-complete
# Should show: done
```

### Step 6: Get IP Address

```bash
multipass exec claude-dev -- hostname -I
```

---

## After Installation

### Access the Dashboard

Open your browser:

```
https://YOUR_VM_IP:9453
```

Replace `YOUR_VM_IP` with the IP from the previous step (e.g., `https://192.168.64.5:9453`)

### Default Login

- **Username**: `admin`
- **Password**: `admin123`

### Security Warning

You'll see a browser security warning (self-signed certificate). This is normal:

- **Chrome**: Click "Advanced" → "Proceed to site"
- **Firefox**: Click "Advanced" → "Accept the Risk and Continue"
- **Safari**: Click "Show Details" → "visit this website"

### Change Passwords (Important!)

```bash
multipass shell claude-dev
sudo /opt/fotios-claude/scripts/change-passwords.sh
```

### Activate Claude Code

1. Open the dashboard
2. Click "Activate Claude" in the header
3. Follow the prompts

Or via terminal:
```bash
multipass shell claude-dev
su - claude
claude
```

---

## Daily Usage

### Start the VM

```bash
multipass start claude-dev
```

### Stop the VM

```bash
multipass stop claude-dev
```

### Check VM Status

```bash
multipass list
```

Output example:
```
Name                    State             IPv4             Image
claude-dev              Running           192.168.64.5     Ubuntu 24.04 LTS
```

### Open VM Terminal

```bash
multipass shell claude-dev
```

### Get Current IP Address

```bash
multipass exec claude-dev -- hostname -I
```

### View VM Details

```bash
multipass info claude-dev
```

### Restart VM

```bash
multipass restart claude-dev
```

---

## VM Management

### Increase Resources

```bash
# Stop VM first
multipass stop claude-dev

# Increase memory to 8GB
multipass set local.claude-dev.memory=8G

# Increase CPUs to 8
multipass set local.claude-dev.cpus=8

# Start VM
multipass start claude-dev
```

### Delete the VM (Uninstall)

```bash
# Delete VM
multipass delete claude-dev

# Purge (permanently remove)
multipass purge
```

### Create Snapshot (Backup)

```bash
# Stop VM
multipass stop claude-dev

# Create snapshot
multipass snapshot claude-dev --name backup-$(date +%Y%m%d)

# List snapshots
multipass snapshot list claude-dev
```

### Restore from Snapshot

```bash
multipass restore claude-dev.backup-20240115
```

---

## Desktop Shortcuts

The installer creates these on your Desktop:

### macOS

- **Claude AI Developer.webloc** - Opens dashboard in browser
- **Start Claude VM.command** - Starts VM and opens dashboard

### Linux

- **claude-ai-developer.desktop** - Opens dashboard
- **start-claude-vm.sh** - Starts VM and opens dashboard

---

## Troubleshooting

### macOS Issues

#### "failed to open file multipass_root_cert.pem"

The Multipass daemon hasn't started. Fix:

```bash
# Start the daemon
sudo launchctl load /Library/LaunchDaemons/com.canonical.multipassd.plist

# Wait 10 seconds
sleep 10

# Test
multipass list
```

If still failing:
```bash
# Restart daemon
sudo launchctl unload /Library/LaunchDaemons/com.canonical.multipassd.plist
sudo launchctl load /Library/LaunchDaemons/com.canonical.multipassd.plist
sleep 15
multipass list
```

#### "Operation not permitted" on Apple Silicon

Allow Multipass in System Settings:
1. **System Settings** → **Privacy & Security** → **Full Disk Access**
2. Add **multipassd**
3. Restart Multipass:
   ```bash
   brew services restart multipass
   ```

#### VM Creation Stuck

Check logs:
```bash
# Multipass logs
cat /Library/Logs/Multipass/multipassd.log | tail -50

# Cloud-init logs (if VM started)
multipass exec claude-dev -- cat /var/log/cloud-init-output.log
```

#### Network Issues on macOS

```bash
# Check VM network
multipass exec claude-dev -- ip addr

# Try restarting
multipass restart claude-dev
```

---

### Linux Issues

#### "Cannot connect to the Multipass socket"

```bash
# Check service status
sudo snap services multipass

# Restart service
sudo snap restart multipass
```

#### "launch failed: KVM is required"

Enable KVM:
```bash
# Check if KVM is available
egrep -c '(vmx|svm)' /proc/cpuinfo

# If 0, enable in BIOS (VT-x for Intel, AMD-V for AMD)

# Install KVM
sudo apt install qemu-kvm libvirt-daemon-system
sudo usermod -aG kvm $USER
# Log out and back in
```

Or use LXD instead:
```bash
multipass set local.driver=lxd
```

#### "Not enough disk space"

```bash
# Check space
df -h

# Clean old images
multipass purge
```

#### Snap Permission Issues

```bash
# Connect interfaces
sudo snap connect multipass:lxd lxd
sudo snap connect multipass:libvirt
```

---

### General Issues

#### Can't Access Dashboard

1. **Check VM is running:**
   ```bash
   multipass list
   ```

2. **Check services inside VM:**
   ```bash
   multipass exec claude-dev -- systemctl status fotios-claude-web
   ```

3. **Start services if needed:**
   ```bash
   multipass exec claude-dev -- sudo systemctl start mysql lshttpd fotios-claude-web fotios-claude-daemon
   ```

4. **Check IP:**
   ```bash
   multipass exec claude-dev -- hostname -I
   ```

#### Installation Incomplete

Check if setup finished:
```bash
multipass exec claude-dev -- cat /root/install-complete
```

If empty, check logs:
```bash
multipass exec claude-dev -- tail -100 /var/log/cloud-init-output.log
```

#### VM Won't Start

```bash
# Check status
multipass info claude-dev

# Try recovery
multipass recover claude-dev

# If corrupted, recreate
multipass delete claude-dev --purge
# Run installer again
```

---

## Quick Reference - Get IP Address

The most common task after installation:

```bash
# Get VM IP address
multipass exec claude-dev -- hostname -I

# Example output: 192.168.64.5
# Dashboard URL: https://192.168.64.5:9453
```

**Tip:** The IP may change after VM restart. Always check with the command above.

---

## Command Reference

| Task | Command |
|------|---------|
| **Get IP address** | `multipass exec claude-dev -- hostname -I` |
| List VMs | `multipass list` |
| Start VM | `multipass start claude-dev` |
| Stop VM | `multipass stop claude-dev` |
| Restart VM | `multipass restart claude-dev` |
| Open shell | `multipass shell claude-dev` |
| Run command | `multipass exec claude-dev -- <command>` |
| VM info | `multipass info claude-dev` |
| Delete VM | `multipass delete claude-dev --purge` |
| View logs | `multipass exec claude-dev -- journalctl -u fotios-claude-web` |

---

## Multipass vs WSL2 vs Traditional VM

| Feature | Multipass | WSL2 | Traditional VM |
|---------|-----------|------|----------------|
| Platform | macOS, Linux, Windows | Windows only | All |
| Setup time | 15-20 min | 10-15 min | 30-60 min |
| Resource usage | Medium | Low | High |
| Isolation | Full VM | Shared kernel | Full VM |
| Networking | Separate IP | Windows IP | Configurable |
| Best for | macOS/Linux | Windows | Maximum control |

**Recommendations:**
- **Windows users**: Use [WSL2](WSL_INSTALL.md) (lighter weight)
- **macOS users**: Use Multipass
- **Linux users**: Use Multipass or [direct installation](../INSTALL.md)

---

*Need help? Open an issue at [GitHub](https://github.com/fotsakir/codehero/issues)*
