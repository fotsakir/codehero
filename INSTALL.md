# Fotios Claude System - Installation Guide

## Requirements

- Ubuntu 24.04 LTS (minimal or server)
- Root access
- Internet connection

## Quick Installation

### 1. Upload and extract

```bash
cd /root
unzip fotios-claude-system-2.51.0.zip
cd fotios-claude-system
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
- OpenLiteSpeed web server
- Python/Flask web application
- Claude daemon service
- System user `claude`

### 4. Install Claude Code CLI

```bash
/opt/fotios-claude/scripts/install-claude-code.sh
```

### 5. Login to Claude Code

```bash
su - claude
claude
```

Follow the prompts to login with:
- **API Key** - For developers with Anthropic API access
- **Max Subscription** - For Claude Max subscribers

## Access Points

After installation:

| Service | URL |
|---------|-----|
| Admin Panel | https://YOUR_IP:9453 |
| Web Projects | https://YOUR_IP:9867 |
| OLS WebAdmin | https://YOUR_IP:7080 |

## Post-Installation

### Change passwords

```bash
sudo /opt/fotios-claude/scripts/change-passwords.sh
```

### Check services

```bash
systemctl status fotios-claude-web fotios-claude-daemon mysql lshttpd
```

### Restart services

```bash
sudo systemctl restart fotios-claude-web fotios-claude-daemon
```

## Upgrading

To upgrade from a previous version:

```bash
# Download and extract new version
cd /root
unzip fotios-claude-system-2.51.0.zip
cd fotios-claude-system

# Preview what will change (recommended)
sudo ./upgrade.sh --dry-run

# Run the upgrade
sudo ./upgrade.sh

# Or skip confirmation prompts
sudo ./upgrade.sh -y
```

### What the upgrade does

1. **Backup**: Creates automatic backup in `/var/backups/fotios-claude/`
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
cd /root/fotios-claude-system
chmod +x uninstall.sh
./uninstall.sh
```

## Troubleshooting

### Services not starting

```bash
journalctl -u fotios-claude-web -n 50
journalctl -u fotios-claude-daemon -n 50
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

**Version:** 2.47.0
