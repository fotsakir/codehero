# CodeHero - Installation Guide

## Requirements

- Ubuntu 24.04 LTS (minimal or server)
- Root access
- Internet connection

## Quick Installation

### 1. Upload and extract

```bash
cd /root
unzip codehero-2.73.2.zip
cd codehero
```

### 2. (Optional) Edit configuration

```bash
nano install.conf
```

Default credentials (change after installation):
| Setting | Default |
|---------|---------|
| ADMIN_USER | admin |
| ADMIN_PASSWORD | admin123 |
| DB_PASSWORD | claudepass123 |
| MYSQL_ROOT_PASSWORD | rootpass123 |

### 3. Run setup

```bash
chmod +x setup.sh
./setup.sh
```

This installs:
- MySQL database
- Nginx web server with PHP-FPM
- Python/Flask web application
- Claude Code CLI
- Claude daemon service
- System user `claude`

### 4. Login to Claude Code

```bash
su - claude
claude
```

Follow the prompts to login with:
- **API Key** - For developers with Anthropic API access
- **Max Subscription** - For Claude Max subscribers

### 5. (Optional) Install additional environments

Run these scripts based on what you need:

| Script | Purpose | What it installs |
|--------|---------|------------------|
| `setup_devtools.sh` | Development tools | Node.js 22, Java (GraalVM 24), multimedia (ffmpeg, ImageMagick, tesseract) |
| `setup_android.sh` | Android development | Docker, Redroid emulator, ws-scrcpy, ADB, Flutter, Gradle |
| `setup_windows.sh` | Windows/.NET development | .NET 8 SDK, PowerShell 7, Wine, Mono, NuGet |
| `setup_lsp.sh` | Code Editor LSP | Language servers for Python, JS/TS, PHP, Java, C#, Kotlin, HTML/CSS |

```bash
# Development tools (Node.js, Java, multimedia)
sudo /opt/codehero/scripts/setup_devtools.sh

# Android development (emulator + mobile frameworks)
sudo /opt/codehero/scripts/setup_android.sh

# Windows/.NET development
sudo /opt/codehero/scripts/setup_windows.sh

# Code Editor LSP (optional - for autocomplete, hover docs, etc.)
sudo /opt/codehero/scripts/setup_lsp.sh
```

**Android Emulator**: After running `setup_android.sh`, access at `https://YOUR_IP:8443`

## Access Points

After installation:

| Service | URL |
|---------|-----|
| Admin Panel | https://YOUR_IP:9453 |
| Web Projects | https://YOUR_IP:9867 |

## Post-Installation

### Change passwords

```bash
sudo /opt/codehero/scripts/change-passwords.sh
```

### Check services

```bash
systemctl status codehero-web codehero-daemon mysql nginx php8.3-fpm
```

### Restart services

```bash
sudo systemctl restart codehero-web codehero-daemon
```

## Upgrading

### Method 1: Admin Panel (Recommended)

1. Open Dashboard in browser
2. Click the green "Update Available" badge when shown
3. Click "Install Update"
4. Watch real-time console output
5. Page reloads automatically on success

**If upgrade fails:** Click "Ask AI to fix the problem" - AI will analyze the error and suggest fixes with one-click execution.

### Method 2: Command Line

```bash
# Download and extract new version
cd /root
wget https://github.com/fotsakir/codehero/releases/latest/download/codehero-2.73.2.zip
unzip codehero-2.73.2.zip
cd codehero

# Preview what will change (recommended)
sudo ./upgrade.sh --dry-run

# Run the upgrade
sudo ./upgrade.sh

# Or skip confirmation prompts
sudo ./upgrade.sh -y
```

### What the upgrade does

1. **Backup**: Creates automatic backup in `/var/backups/codehero/`
2. **Stop services**: Safely stops daemon service
3. **Copy files**: Updates web, scripts, docs, and upgrades
4. **Version upgrades**: Runs pending scripts from `upgrades/` folder
   - Only runs scripts for versions between current and new
   - Tracks applied upgrades (won't run twice)
5. **Database migrations**: Applies pending SQL migrations
6. **Restart services**: Restarts all services and reloads nginx
7. **Verify**: Checks services are running
8. **Changelog**: Shows what changed in the new version

### Upgrade options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without applying |
| `-y, --yes` | Auto-confirm all prompts |
| `-h, --help` | Show help message |

### Modular Upgrade System

The upgrade system uses individual scripts for each version:

```
upgrades/
├── 2.42.0.sh    # Multimedia tools
├── 2.60.4.sh    # Permission fixes
├── 2.61.0.sh    # Claude CLI install
├── 2.61.2.sh    # Systemd service fixes
├── 2.63.0.sh    # OpenLiteSpeed → Nginx migration
├── 2.65.0.sh    # phpMyAdmin integration
└── _always.sh   # Runs every upgrade (permissions)
```

When upgrading from 2.60.0 to 2.72.7, the system automatically runs: `2.60.4.sh` → `2.61.0.sh` → `2.61.2.sh` → `2.63.0.sh` → `2.65.0.sh`

### Creating custom upgrade scripts

For version X.Y.Z, create `upgrades/X.Y.Z.sh`:

```bash
#!/bin/bash
log_info() { echo -e "\033[0;36m[X.Y.Z]\033[0m $1"; }

log_info "Installing new package..."
apt-get install -y some-package || true
```

## Uninstallation

```bash
cd /root/codehero
chmod +x uninstall.sh
./uninstall.sh
```

## Troubleshooting

### Services not starting

```bash
journalctl -u codehero-web -n 50
journalctl -u codehero-daemon -n 50
```

### Database connection issues

```bash
mysql -u claude_user -p claude_knowledge
```

### Claude Code not found

```bash
su - claude
which claude
# If not found, reinstall:
curl -fsSL https://claude.ai/install.sh | sh
```

---

**Version:** 2.73.2
