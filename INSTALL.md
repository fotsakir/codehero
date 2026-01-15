# CodeHero - Installation Guide

## Requirements

- Ubuntu 24.04 LTS (minimal or server)
- Root access
- Internet connection

## Quick Installation

### 1. Upload and extract

```bash
cd /root
unzip codehero-2.62.0.zip
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

To upgrade from a previous version:

```bash
# Download and extract new version
cd /root
unzip codehero-2.62.0.zip
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
2. **Stop services**: Safely stops web and daemon services
3. **Database migrations**: Applies any pending schema changes
4. **Copy files**: Updates web, scripts, and docs
5. **Start services**: Restarts all services
6. **Verify**: Checks services are running
7. **Changelog**: Shows what changed in the new version

### Upgrade options

| Option | Description |
|--------|-------------|
| `--dry-run` | Preview changes without applying |
| `-y, --yes` | Auto-confirm all prompts |
| `-h, --help` | Show help message |

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

**Version:** 2.62.0
