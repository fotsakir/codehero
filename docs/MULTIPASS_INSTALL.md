# One-Click Installation with Multipass

The easiest way to install Claude-AI-developer on any computer (Windows, macOS, or Linux).

## What is Multipass?

Multipass is a free tool from Ubuntu that creates virtual machines with a single command. No complex setup required.

---

## Quick Install (Recommended)

### Windows

1. **Download the installer**: [install-windows.ps1](https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/install-windows.ps1)
2. **Right-click** the file → **Run with PowerShell** (as Administrator)
3. Wait 15-20 minutes
4. Done! Open the dashboard URL shown

### macOS

1. **Download the installer**: [install-macos.command](https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/install-macos.command)
2. **Double-click** the file
3. If blocked: System Settings → Privacy & Security → Allow
4. Wait 15-20 minutes
5. Done! Open the dashboard URL shown

### Linux

```bash
curl -sL https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/install-linux.sh | bash
```

---

## Manual Installation

If you prefer to run commands manually:

### Step 1: Install Multipass

**Windows:**
```powershell
winget install Canonical.Multipass
```

**macOS:**
```bash
brew install --cask multipass
```

**Linux:**
```bash
sudo snap install multipass
```

### Step 2: Create the VM

```bash
# Download configuration
curl -sL https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/cloud-init.yaml -o cloud-init.yaml

# Create VM (takes 15-20 minutes)
multipass launch 24.04 --name claude-dev --memory 4G --disk 40G --cpus 2 --cloud-init cloud-init.yaml
```

### Step 3: Get the Dashboard URL

```bash
# Get VM IP address
multipass exec claude-dev -- hostname -I

# Output example: 192.168.64.5
# Dashboard URL: https://192.168.64.5:9453
```

---

## After Installation

### Access the Dashboard

Open in your browser: `https://YOUR_VM_IP:9453`

**Default login:**
- Username: `admin`
- Password: `admin123`

### Change Passwords (Important!)

Open the **Web Terminal** from the dashboard menu, or SSH into the VM:

```bash
multipass shell claude-dev
sudo /opt/fotios-claude/scripts/change-passwords.sh
```

### Access the VM Terminal

```bash
multipass shell claude-dev
```

### Activate Claude Code

1. Open the dashboard
2. Click the "Activate Claude" button in the header
3. Follow the prompts to login with your Anthropic account

Or via terminal:
```bash
multipass shell claude-dev
su - claude
claude
# Follow the login prompts
```

---

## VM Management

### Start/Stop the VM

```bash
# Stop VM (saves resources)
multipass stop claude-dev

# Start VM
multipass start claude-dev
```

### Delete the VM

```bash
multipass delete claude-dev --purge
```

### List all VMs

```bash
multipass list
```

---

## Troubleshooting

### Can't access dashboard

1. Make sure VM is running: `multipass list`
2. Get the IP: `multipass exec claude-dev -- hostname -I`
3. Try: `https://IP:9453` (note: HTTPS, not HTTP)

### Installation seems stuck

The installation takes 15-20 minutes. Check progress:
```bash
multipass exec claude-dev -- tail -f /var/log/cloud-init-output.log
```

### VM won't start

```bash
# Check status
multipass info claude-dev

# Try restarting Multipass service
# Windows: Restart "Multipass" service
# macOS: brew services restart multipass
# Linux: sudo snap restart multipass
```

### Need more resources

Stop the VM and modify:
```bash
multipass stop claude-dev
multipass set local.claude-dev.memory=8G
multipass set local.claude-dev.cpus=4
multipass start claude-dev
```

---

## Requirements

| | Minimum | Recommended |
|---|---------|-------------|
| RAM | 4GB free | 8GB free |
| Disk | 45GB free | 60GB free |
| CPU | 2 cores | 4 cores |

**Supported OS:**
- Windows 10/11 (Pro, Enterprise, Education, or Home with WSL2)
- macOS 10.15+ (Intel or Apple Silicon)
- Linux (Ubuntu, Debian, Fedora, CentOS, etc.)

---

## Why Multipass?

| Traditional VM | Multipass |
|----------------|-----------|
| Download ISO | Not needed |
| Configure VM settings | Automatic |
| Install OS manually | Automatic |
| Run setup scripts | Automatic |
| 30-60 minutes | 15-20 minutes |

---

*Need help? Open an issue at [GitHub](https://github.com/fotsakir/Claude-AI-developer/issues)*
