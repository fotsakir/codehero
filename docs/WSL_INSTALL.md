# Windows Installation with WSL2

Complete guide to install Claude-AI-developer on Windows using WSL2 (Windows Subsystem for Linux).

## Table of Contents

- [What is WSL2?](#what-is-wsl2)
- [Requirements](#requirements)
- [Quick Install (Recommended)](#quick-install-recommended)
- [Manual Installation](#manual-installation)
- [After Installation](#after-installation)
- [Daily Usage](#daily-usage)
- [Troubleshooting](#troubleshooting)

---

## What is WSL2?

WSL2 (Windows Subsystem for Linux 2) lets you run a real Linux environment directly on Windows, without the overhead of a traditional virtual machine. It's:

- **Fast** - Near-native Linux performance
- **Integrated** - Access Windows files from Linux and vice versa
- **Built-in** - Part of Windows 10/11, no extra software needed
- **Lightweight** - Uses less resources than a full VM

---

## Requirements

| | Minimum | Recommended |
|---|---------|-------------|
| Windows | Windows 10 (build 19041+) or Windows 11 | Windows 11 |
| RAM | 4GB | 8GB+ |
| Disk | 20GB free | 40GB free |
| CPU | 64-bit with virtualization | Multi-core |

### Check Windows Version

Press `Win + R`, type `winver` and press Enter. You need:
- Windows 10 version 2004 or higher (Build 19041+)
- Windows 11 (any version)

---

## Quick Install (Recommended)

### One-Line Install

Open **PowerShell as Administrator** and run:

```powershell
irm https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/install-wsl.ps1 | iex
```

### What the Installer Does

1. Checks if WSL is installed (installs if needed)
2. Installs Ubuntu 24.04
3. Configures systemd (required for services)
4. Downloads and installs Claude-AI-developer
5. Starts all services
6. Creates desktop shortcuts

### Installation Time

- **First time (WSL not installed)**: May require restart, then 15-20 minutes
- **WSL already installed**: 10-15 minutes

---

## Manual Installation

If you prefer to install step by step:

### Step 1: Enable WSL

Open **PowerShell as Administrator**:

```powershell
# Install WSL with Ubuntu
wsl --install -d Ubuntu-24.04
```

**Restart your computer** when prompted.

### Step 2: Configure WSL

After restart, open **PowerShell as Administrator**:

```powershell
# Open Ubuntu
wsl -d Ubuntu-24.04
```

On first launch, you'll be asked to create a username and password. Create them and remember them.

### Step 3: Enable Systemd

Inside WSL (Ubuntu terminal):

```bash
# Switch to root
sudo su

# Enable systemd
echo -e '[boot]\nsystemd=true\n\n[user]\ndefault=root' > /etc/wsl.conf

# Exit
exit
exit
```

Back in PowerShell:

```powershell
# Restart WSL to apply changes
wsl --shutdown

# Wait 5 seconds, then start again
wsl -d Ubuntu-24.04
```

### Step 4: Install Claude-AI-developer

Inside WSL (now running as root):

```bash
# Update packages
apt-get update
apt-get install -y unzip wget curl

# Download latest release
cd /root
wget https://github.com/fotsakir/Claude-AI-developer/releases/latest/download/fotios-claude-system-2.52.0.zip

# Extract and install
unzip fotios-claude-system-2.52.0.zip
cd fotios-claude-system
chmod +x setup.sh
./setup.sh
```

Wait 10-15 minutes for installation to complete.

### Step 5: Get IP Address

```bash
hostname -I
```

Note the IP address (e.g., `172.25.123.45`)

---

## After Installation

### Access the Dashboard

Open your browser and go to:

```
https://YOUR_IP:9453
```

Replace `YOUR_IP` with the IP from `hostname -I` (e.g., `https://172.25.123.45:9453`)

### Default Login

- **Username**: `admin`
- **Password**: `admin123`

### Change Passwords (Important!)

Inside WSL:

```bash
/opt/fotios-claude/scripts/change-passwords.sh
```

### Activate Claude Code

1. Open the dashboard
2. Click "Activate Claude" in the header
3. Follow the prompts to login with your Anthropic account

Or via terminal:
```bash
su - claude
claude
# Follow the login prompts
```

---

## Daily Usage

### Start Services

The services start automatically when you open WSL. If they're not running:

**PowerShell:**
```powershell
wsl -d Ubuntu-24.04 --exec systemctl start mysql lshttpd fotios-claude-web fotios-claude-daemon
```

**Or inside WSL:**
```bash
systemctl start mysql lshttpd fotios-claude-web fotios-claude-daemon
```

### Check Services Status

```bash
systemctl status fotios-claude-web fotios-claude-daemon
```

### Get IP Address

The IP may change after restart. Get current IP:

**PowerShell:**
```powershell
wsl -d Ubuntu-24.04 --exec hostname -I
```

**Or inside WSL:**
```bash
hostname -I
```

### Open WSL Terminal

```powershell
wsl -d Ubuntu-24.04
```

### Shutdown WSL

```powershell
wsl --shutdown
```

### List Installed Distros

```powershell
wsl --list --verbose
```

---

## Desktop Shortcuts

The installer creates these shortcuts on your Desktop:

### Claude AI Developer (WSL).bat

Double-click to:
1. Start services
2. Get current IP
3. Open dashboard in browser

### Claude Dashboard (WSL).url

Direct link to dashboard (uses IP from installation time - may be outdated)

---

## File Access

### Access WSL Files from Windows

In File Explorer, go to:
```
\\wsl$\Ubuntu-24.04
```

Or type in the address bar:
```
\\wsl$\Ubuntu-24.04\root
```

### Access Windows Files from WSL

```bash
# Your Windows C: drive
cd /mnt/c

# Your Windows user folder
cd /mnt/c/Users/YourUsername
```

---

## Troubleshooting

### "systemctl" not working / "System has not been booted with systemd"

Systemd is not enabled. Fix:

```bash
# Inside WSL
echo -e '[boot]\nsystemd=true' >> /etc/wsl.conf
exit
```

Then in PowerShell:
```powershell
wsl --shutdown
wsl -d Ubuntu-24.04
```

### Can't Access Dashboard

1. **Check services are running:**
   ```bash
   systemctl status fotios-claude-web
   ```

2. **Check IP address:**
   ```bash
   hostname -I
   ```

3. **Start services if needed:**
   ```bash
   systemctl start mysql lshttpd fotios-claude-web fotios-claude-daemon
   ```

4. **Check firewall** (Windows may block):
   - Allow the connection when Windows Firewall prompts
   - Or manually add rule for port 9453

### WSL Won't Start

```powershell
# Check status
wsl --status

# Update WSL
wsl --update

# Restart WSL service
net stop LxssManager
net start LxssManager
```

### "Virtual Machine Platform" Error

Enable in PowerShell (Admin):
```powershell
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
```

Then restart your computer.

### IP Address Changes After Restart

This is normal. Get the new IP:
```powershell
wsl -d Ubuntu-24.04 --exec hostname -I
```

Use the `.bat` shortcut which always gets the current IP.

### Delete and Reinstall WSL Distro

```powershell
# Remove the distro completely
wsl --unregister Ubuntu-24.04

# Install fresh
wsl --install -d Ubuntu-24.04
```

### Services Won't Start

Check logs:
```bash
journalctl -u fotios-claude-web -n 50
journalctl -u fotios-claude-daemon -n 50
```

---

## WSL vs Multipass

| Feature | WSL2 | Multipass |
|---------|------|-----------|
| Platform | Windows only | Windows, macOS, Linux |
| Resource usage | Lower | Higher (full VM) |
| Setup complexity | Easy | Easy |
| File sharing | Native Windows integration | Separate mount required |
| Networking | Shared with Windows | Separate IP |
| Best for | Windows users | Cross-platform |

**Recommendation:**
- **Windows users**: Use WSL2 (lighter, better integrated)
- **macOS/Linux users**: Use Multipass

---

## Quick Reference - Get IP Address

The most common task after installation:

**From PowerShell:**
```powershell
wsl -d Ubuntu-24.04 --exec hostname -I
```

**From inside WSL:**
```bash
hostname -I
```

**Example output:** `172.25.123.45`
**Dashboard URL:** `https://172.25.123.45:9453`

**Tip:** The IP may change after restart. Always check with the command above.

---

## Useful Commands Reference

| Task | Command (PowerShell) |
|------|---------|
| **Get IP address** | `wsl -d Ubuntu-24.04 --exec hostname -I` |
| Open Ubuntu | `wsl -d Ubuntu-24.04` |
| Shutdown WSL | `wsl --shutdown` |
| Start services | `wsl -d Ubuntu-24.04 --exec systemctl start fotios-claude-web` |
| Check services | `wsl -d Ubuntu-24.04 --exec systemctl status fotios-claude-web` |
| List distros | `wsl --list --verbose` |
| Remove distro | `wsl --unregister Ubuntu-24.04` |
| Update WSL | `wsl --update` |

---

*Need help? Open an issue at [GitHub](https://github.com/fotsakir/Claude-AI-developer/issues)*
