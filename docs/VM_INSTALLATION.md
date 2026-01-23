# VM Installation Guide

Step-by-step guide to install codehero on a Virtual Machine.

> **Quick Links:**
> - **Windows users**: See [WSL2 Installation](WSL_INSTALL.md) (recommended) or [Multipass](MULTIPASS_INSTALL.md)
> - **macOS/Linux users**: See [Multipass Installation](MULTIPASS_INSTALL.md) (automated)

## Table of Contents

- [Requirements](#requirements)
- [Step 1: Download Ubuntu](#step-1-download-ubuntu)
- [Step 2: Create Virtual Machine](#step-2-create-virtual-machine)
  - [VMware (Windows/macOS)](#vmware-workstation--fusion)
  - [Hyper-V (Windows)](#hyper-v-windows)
  - [VirtualBox (Windows/macOS)](#virtualbox-windowsmacos)
  - [UTM (macOS)](#utm-macos)
  - [Parallels (macOS)](#parallels-macos)
- [Step 3: Install Ubuntu](#step-3-install-ubuntu)
- [Step 4: Install codehero](#step-4-install-claude-ai-developer)
- [Step 5: Access the Dashboard](#step-5-access-the-dashboard)
- [How to Find Your VM's IP Address](#how-to-find-your-vms-ip-address)
- [Start, Stop & Delete VMs](#start-stop--delete-vms)

---

## Requirements

- **RAM**: Minimum 4GB (8GB recommended)
- **Disk**: Minimum 25GB free space
- **CPU**: 2+ cores
- **Network**: Internet connection

---

## Step 1: Download Ubuntu

1. Go to: https://ubuntu.com/download/server
2. Download **Ubuntu Server 24.04 LTS**
3. Save the ISO file (approximately 2.5GB)

> **Tip**: You can also use Ubuntu Desktop 24.04 if you prefer a graphical interface.

---

## Step 2: Create Virtual Machine

Choose your virtualization platform below:

---

### VMware Workstation / Fusion

**VMware Workstation** (Windows) or **VMware Fusion** (macOS)

#### Download VMware

- **Windows**: Download [VMware Workstation Player](https://www.vmware.com/products/workstation-player.html) (free for personal use)
- **macOS**: Download [VMware Fusion](https://www.vmware.com/products/fusion.html)

#### Create VM

1. Open VMware and click **Create a New Virtual Machine**
2. Select **Installer disc image file (ISO)** and browse to the Ubuntu ISO
3. Configure VM:
   - **Name**: `claude-ai-developer`
   - **Disk size**: 40 GB (Store as single file)
   - **Memory**: 4096 MB (or more)
   - **Processors**: 2
4. Click **Finish** to create the VM
5. Start the VM and proceed to [Install Ubuntu](#step-3-install-ubuntu)

---

### Hyper-V (Windows)

Hyper-V is built into Windows 10/11 Pro, Enterprise, and Education editions.

#### Enable Hyper-V

1. Press **Windows + R**, type `optionalfeatures` and press Enter
2. In the Windows Features window, check:
   - **Hyper-V** (expand and check all sub-items)
   - **Virtual Machine Platform**
   - **Windows Hypervisor Platform**
3. Click **OK** and wait for installation
4. **Restart your computer** when prompted

> **Note**: Hyper-V is not available on Windows Home edition. Use VirtualBox instead.

#### Alternative: Enable via PowerShell (Run as Administrator)

```powershell
Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All
```

#### Create VM in Hyper-V

1. Open **Hyper-V Manager** (search in Start menu)
2. Right-click your computer name → **New** → **Virtual Machine**
3. Click **Next** on the wizard
4. **Name**: `claude-ai-developer` → Next
5. **Generation**: Select **Generation 2** → Next
6. **Memory**: 4096 MB, uncheck "Dynamic Memory" → Next
7. **Networking**: Select your network adapter (e.g., "Default Switch") → Next
8. **Virtual Hard Disk**: Create new, 40 GB → Next
9. **Installation Options**: Select "Install from bootable image file" and browse to Ubuntu ISO → Next
10. Click **Finish**

#### Configure VM for Ubuntu

Before starting the VM:

1. Right-click the VM → **Settings**
2. Go to **Security** → Uncheck **Enable Secure Boot** (important for Ubuntu)
3. Go to **Processor** → Set **Number of virtual processors** to 2
4. Click **OK**

#### Start the VM

1. Right-click the VM → **Connect**
2. Click **Start**
3. Proceed to [Install Ubuntu](#step-3-install-ubuntu)

---

### VirtualBox (Windows/macOS)

VirtualBox is free and works on both Windows and macOS.

#### Download VirtualBox

1. Go to: https://www.virtualbox.org/wiki/Downloads
2. Download the version for your operating system:
   - **Windows**: "Windows hosts"
   - **macOS**: "macOS / Intel hosts" or "macOS / ARM hosts" (for M1/M2/M3)
3. Install VirtualBox with default settings

#### Create VM

1. Open VirtualBox and click **New**
2. Configure:
   - **Name**: `claude-ai-developer`
   - **Folder**: (leave default)
   - **ISO Image**: Browse and select the Ubuntu ISO
   - Check **Skip Unattended Installation**
3. Click **Next**
4. **Hardware**:
   - **Base Memory**: 4096 MB
   - **Processors**: 2
5. Click **Next**
6. **Virtual Hard Disk**:
   - Select **Create a Virtual Hard Disk Now**
   - **Size**: 40 GB
7. Click **Next** → **Finish**

#### Network Configuration

1. Select the VM and click **Settings**
2. Go to **Network** → **Adapter 1**
3. Change "Attached to" from "NAT" to **Bridged Adapter**
4. Select your network adapter from the dropdown
5. Click **OK**

> **Why Bridged?** This gives the VM its own IP address on your network, making it easy to access from your browser.

#### Start the VM

1. Select the VM and click **Start**
2. Proceed to [Install Ubuntu](#step-3-install-ubuntu)

---

### UTM (macOS)

UTM is ideal for Apple Silicon Macs (M1/M2/M3/M4).

#### Download UTM

1. Go to: https://mac.getutm.app/
2. Download UTM (free from the website, paid on App Store)
3. Install by dragging to Applications

#### Download Ubuntu for ARM

For Apple Silicon Macs, you need the ARM version:

1. Go to: https://ubuntu.com/download/server/arm
2. Download **Ubuntu Server 24.04 LTS for ARM**

#### Create VM

1. Open UTM and click **Create a New Virtual Machine**
2. Select **Virtualize**
3. Select **Linux**
4. Click **Browse** and select the Ubuntu ARM ISO
5. Configure:
   - **Memory**: 4096 MB
   - **CPU Cores**: 2
6. Click **Next**
7. **Storage**: 40 GB → Next
8. **Shared Directory**: Skip → Next
9. **Name**: `claude-ai-developer`
10. Click **Save**

#### Network Configuration

1. Right-click the VM → **Edit**
2. Go to **Network**
3. Change "Network Mode" to **Bridged (Advanced)**
4. Click **Save**

#### Start the VM

1. Click **Play** button
2. Proceed to [Install Ubuntu](#step-3-install-ubuntu)

---

### Parallels (macOS)

Parallels Desktop is the easiest option for Mac but requires a paid license.

#### Download Parallels

1. Go to: https://www.parallels.com/products/desktop/
2. Download and install Parallels Desktop

#### Create VM

1. Open Parallels and click **+** to create new VM
2. Select **Install Windows or another OS from a DVD or image file**
3. Click **Continue**
4. Select **Choose Manually** and browse to Ubuntu ISO
5. Parallels will detect Ubuntu Linux
6. Configure:
   - **Name**: `claude-ai-developer`
   - Check **Customize settings before installation**
7. Click **Create**

#### Configure VM

1. In the Configuration window:
   - **Hardware** → **CPU & Memory**:
     - Processors: 2
     - Memory: 4096 MB
   - **Hardware** → **Hard Disk**: 40 GB
   - **Hardware** → **Network**:
     - Source: **Bridged Network** → Default Adapter
2. Close Configuration
3. Click **Continue** to start installation
4. Proceed to [Install Ubuntu](#step-3-install-ubuntu)

---

## Step 3: Install Ubuntu

These steps are the same for all VM platforms.

### Boot from ISO

1. When the VM starts, you'll see the Ubuntu boot menu
2. Select **Try or Install Ubuntu Server** and press Enter

### Installation Wizard

1. **Language**: Select your language → Enter

2. **Keyboard**: Select your keyboard layout → Done

3. **Type of Install**: Select **Ubuntu Server** → Done

4. **Network**:
   - Ubuntu should automatically detect your network
   - Note the IP address shown (e.g., `192.168.1.100`)
   - Select **Done**

5. **Proxy**: Leave empty → Done

6. **Mirror**: Leave default → Done

7. **Storage**:
   - Select **Use an entire disk**
   - Select the virtual disk
   - Select **Done** → **Done** → **Continue** (to confirm)

8. **Profile Setup**:
   - **Your name**: `Claude Admin`
   - **Server name**: `claude-server`
   - **Username**: `claude`
   - **Password**: Choose a password (remember it!)
   - Select **Done**

9. **Ubuntu Pro**: Select **Skip for now** → Continue

10. **SSH Setup**:
    - Check **Install OpenSSH server**
    - Select **Done**

11. **Featured Snaps**: Don't select anything → Done

12. Wait for installation to complete (5-10 minutes)

13. When you see **Installation complete!**, select **Reboot Now**

14. When prompted to "remove installation medium", just press Enter

### First Login

1. Wait for the login prompt
2. Enter your username: `claude`
3. Enter your password

---

## Step 4: Install codehero

Now you're logged into Ubuntu. Run these commands one by one:

### Install Required Tools

```bash
sudo apt update
sudo apt install -y unzip wget net-tools
```

### Find Your IP Address

```bash
ifconfig
```

Look for `inet` under `eth0` or `ens33` - that's your IP address (e.g., `192.168.1.100`)

> **Write down this IP!** You'll need it to access the dashboard.

### Download and Install

```bash
# Switch to root
sudo su
# Enter your password when prompted

# Go to root folder
cd /root

# Download the latest release
wget https://github.com/fotsakir/codehero/releases/latest/download/codehero-2.81.0.zip

# Extract
unzip codehero-2.81.0.zip

# Enter the folder
cd codehero

# Run the installer
chmod +x setup.sh
./setup.sh
```

### Installation Process

The installer will:
1. Install MySQL, Nginx, PHP-FPM, Python, and all dependencies
2. Configure the database
3. Set up the web interface
4. Create system services

This takes approximately **10-15 minutes**.

When finished, you'll see the access credentials on screen.

### Install Claude Code CLI

After setup completes:

```bash
/opt/codehero/scripts/install-claude-code.sh
```

Follow the prompts to authenticate with your Anthropic account.

---

## Step 5: Access the Dashboard

Open a web browser on your computer (not inside the VM) and go to:

```
https://YOUR_VM_IP:9453
```

Replace `YOUR_VM_IP` with the IP address you noted earlier (e.g., `https://192.168.1.100:9453`)

### Default Login

- **Username**: `admin`
- **Password**: `admin123`

> **Important**: Change the default passwords after first login:
> ```bash
> sudo /opt/codehero/scripts/change-passwords.sh
> ```

### Browser Security Warning

You'll see a security warning because of the self-signed SSL certificate. This is normal:

- **Chrome**: Click "Advanced" → "Proceed to site"
- **Firefox**: Click "Advanced" → "Accept the Risk and Continue"
- **Safari**: Click "Show Details" → "visit this website"
- **Edge**: Click "Advanced" → "Continue to site"

---

## How to Find Your VM's IP Address

After installation, you need the VM's IP to access the dashboard. Here's how to find it for each platform:

### WSL2 (Windows)

**From PowerShell:**
```powershell
wsl -d Ubuntu-24.04 --exec hostname -I
```

**From inside WSL:**
```bash
hostname -I
```

---

### Multipass (macOS/Linux)

```bash
multipass exec claude-dev -- hostname -I
```

Or check the list:
```bash
multipass list
```

---

### VirtualBox / VMware / Hyper-V / UTM / Parallels

**Inside the VM terminal:**
```bash
hostname -I
```

Or with more details:
```bash
ip addr show
```

Look for the IP under `eth0`, `ens33`, or `enp0s3` (e.g., `192.168.1.100`)

---

### Quick Tip

The IP may change after VM restart. Always check with the commands above before accessing the dashboard.

**Dashboard URL format:** `https://YOUR_IP:9453`

---

## Start, Stop & Delete VMs

### WSL2 (Windows)

| Action | Command (PowerShell) |
|--------|----------------------|
| **Start** | `wsl -d Ubuntu-24.04` |
| **Stop** | `wsl --terminate Ubuntu-24.04` |
| **Stop all WSL** | `wsl --shutdown` |
| **Delete/Uninstall** | `wsl --unregister Ubuntu-24.04` |
| **List distros** | `wsl --list --verbose` |

---

### Multipass (macOS/Linux)

| Action | Command |
|--------|---------|
| **Start** | `multipass start claude-dev` |
| **Stop** | `multipass stop claude-dev` |
| **Restart** | `multipass restart claude-dev` |
| **Delete** | `multipass delete claude-dev` |
| **Delete permanently** | `multipass delete claude-dev --purge` |
| **List VMs** | `multipass list` |

---

### VirtualBox

**GUI:**
- **Start**: Select VM → Click "Start"
- **Stop**: Machine menu → "ACPI Shutdown" or "Power Off"
- **Delete**: Right-click VM → "Remove" → "Delete all files"

**Command line:**
```bash
# Start VM
VBoxManage startvm "claude-ai-developer"

# Stop VM (graceful)
VBoxManage controlvm "claude-ai-developer" acpipowerbutton

# Stop VM (force)
VBoxManage controlvm "claude-ai-developer" poweroff

# Delete VM
VBoxManage unregistervm "claude-ai-developer" --delete
```

---

### VMware (Workstation/Fusion)

**GUI:**
- **Start**: Select VM → Click "Power On"
- **Stop**: VM menu → "Shut Down Guest" or "Power Off"
- **Delete**: Right-click VM → "Delete from Disk"

**Command line (vmrun):**
```bash
# Start
vmrun start "/path/to/vm.vmx"

# Stop (graceful)
vmrun stop "/path/to/vm.vmx" soft

# Stop (force)
vmrun stop "/path/to/vm.vmx" hard

# Delete
vmrun deleteVM "/path/to/vm.vmx"
```

---

### Hyper-V (Windows)

**GUI (Hyper-V Manager):**
- **Start**: Right-click VM → "Start"
- **Stop**: Right-click VM → "Shut Down" or "Turn Off"
- **Delete**: Right-click VM → "Delete"

**PowerShell:**
```powershell
# Start
Start-VM -Name "claude-ai-developer"

# Stop (graceful)
Stop-VM -Name "claude-ai-developer"

# Stop (force)
Stop-VM -Name "claude-ai-developer" -Force

# Delete
Remove-VM -Name "claude-ai-developer" -Force
# Also delete virtual hard disk manually from disk
```

---

### UTM (macOS)

**GUI:**
- **Start**: Select VM → Click Play button
- **Stop**: Click Stop button or VM menu → "Stop"
- **Delete**: Right-click VM → "Delete"

---

### Parallels (macOS)

**GUI:**
- **Start**: Double-click VM or click Play
- **Stop**: Actions menu → "Shut Down" or "Stop"
- **Delete**: Right-click VM → "Remove" → "Move to Trash"

**Command line (prlctl):**
```bash
# Start
prlctl start "claude-ai-developer"

# Stop
prlctl stop "claude-ai-developer"

# Delete
prlctl delete "claude-ai-developer"
```

---

## Troubleshooting

### Can't Access Dashboard

1. **Check VM is running**: Make sure the VM hasn't shut down
2. **Verify IP address**: Run `ifconfig` inside the VM
3. **Check services**:
   ```bash
   sudo systemctl status codehero-web
   ```
4. **Check firewall**:
   ```bash
   sudo ufw status
   sudo ufw allow 9453
   ```

### Network Not Working

**VirtualBox/VMware**: Make sure network adapter is set to "Bridged"

**Hyper-V**: Make sure "Default Switch" is selected

### VM Runs Slow

- Increase RAM to 8GB
- Increase CPU cores to 4
- Enable virtualization in BIOS (VT-x / AMD-V)

### Ubuntu Installation Stuck

- Make sure you downloaded the correct ISO (ARM for M1/M2 Macs, x64 for Intel/AMD)
- Try disabling Secure Boot in VM settings

---

## Quick Reference

| Platform | Best For | Free? |
|----------|----------|-------|
| VirtualBox | Windows & Intel Mac | Yes |
| Hyper-V | Windows Pro/Enterprise | Yes (built-in) |
| VMware Player | Windows | Yes (personal use) |
| VMware Fusion | Intel Mac | Paid |
| UTM | Apple Silicon Mac | Yes |
| Parallels | Mac (easiest) | Paid |

---

## Next Steps

1. Read the [User Guide](USER_GUIDE.md) to learn how to use the dashboard
2. Create your first project
3. Submit your first ticket and watch Claude work!

---

*Need help? Open an issue at [GitHub](https://github.com/fotsakir/codehero/issues)*
