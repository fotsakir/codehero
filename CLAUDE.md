# Claude Instructions - Fotios Claude System

**READ THIS BEFORE MAKING ANY CHANGES**

## Project Structure

```
/home/claude/fotios-claude-system/    <- LOCAL SOURCE (make changes here)
/opt/fotios-claude/                   <- LOCAL PRODUCTION (installed files)
/home/claude/fotios-claude-system-X.Y.Z.zip  <- BACKUPS (DON'T DELETE!)
```

### Remote Server (Optional)
```
The remote server is not always available.
User will provide IP/credentials when needed.
Production path: /opt/fotios-claude/
```

## Workflow for Changes

### 1. Make changes in SOURCE
```
/home/claude/fotios-claude-system/
```

### 2. Copy to PRODUCTION
```bash
sudo cp /home/claude/fotios-claude-system/web/app.py /opt/fotios-claude/web/
sudo cp /home/claude/fotios-claude-system/scripts/claude-daemon.py /opt/fotios-claude/scripts/
sudo cp -r /home/claude/fotios-claude-system/web/templates/* /opt/fotios-claude/web/templates/
sudo cp /home/claude/fotios-claude-system/scripts/*.sh /opt/fotios-claude/scripts/
```

### 3. Copy to REMOTE PRODUCTION (when remote server is available)
```bash
# User will provide IP and PASSWORD
sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no /home/claude/fotios-claude-system/web/app.py root@REMOTE_IP:/opt/fotios-claude/web/
sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no /home/claude/fotios-claude-system/scripts/claude-daemon.py root@REMOTE_IP:/opt/fotios-claude/scripts/
sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no -r /home/claude/fotios-claude-system/web/templates/* root@REMOTE_IP:/opt/fotios-claude/web/templates/
```

### 4. Restart services (ALWAYS!) - Both Local and Remote
**IMPORTANT:** Always restart services after ANY change - otherwise changes won't be visible!
```bash
# Local
sudo systemctl restart fotios-claude-web fotios-claude-daemon

# Remote (when available)
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "systemctl restart fotios-claude-web fotios-claude-daemon"
```

### 5. Update version numbers
- `VERSION` - Single source of truth for version
- `README.md` - Badge version and zip filename
- `INSTALL.md` - Zip filename and footer version
- `CHANGELOG.md` - New entry at the top

### 6. Create NEW zip (DON'T DELETE THE OLD ONE!)
```bash
cd /home/claude
# DON'T rm the old zip! It's a backup!
zip -r fotios-claude-system-X.Y.Z.zip fotios-claude-system -x "*.pyc" -x "*__pycache__*" -x "*.git*"
```

### 7. Git commit and push
```bash
git add -A
git commit -m "Release vX.Y.Z - Description"
git push origin main
```

### 8. Create tag and push
```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z - Description"
git push origin vX.Y.Z
```

### 9. Create GitHub release with zip
```bash
gh release create vX.Y.Z /home/claude/fotios-claude-system-X.Y.Z.zip --title "vX.Y.Z - Description" --notes "Release notes here"
```

## Service Names (IMPORTANT!)

The correct names are:
- `fotios-claude-web` (NOT fotios-web)
- `fotios-claude-daemon` (NOT fotios-daemon)

## Check Sync (Local Source vs Local Prod vs Remote Prod)

```bash
# Local Source vs Local Production
diff /home/claude/fotios-claude-system/web/app.py /opt/fotios-claude/web/app.py
diff /home/claude/fotios-claude-system/scripts/claude-daemon.py /opt/fotios-claude/scripts/claude-daemon.py

# Local Source vs Remote Production (when remote available)
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "cat /opt/fotios-claude/web/app.py" | diff /home/claude/fotios-claude-system/web/app.py -
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "cat /opt/fotios-claude/scripts/claude-daemon.py" | diff /home/claude/fotios-claude-system/scripts/claude-daemon.py -
```

## Check Services

```bash
# Local
systemctl status fotios-claude-web fotios-claude-daemon

# Remote (when available)
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "systemctl is-active fotios-claude-web fotios-claude-daemon"
```

## Version History

The zip files are BACKUPS. Keep them all:
- fotios-claude-system-2.20.0.zip
- fotios-claude-system-2.21.0.zip
- ... etc

## Files that must be SYNCED

| Source | Production |
|--------|------------|
| web/app.py | /opt/fotios-claude/web/app.py |
| scripts/claude-daemon.py | /opt/fotios-claude/scripts/claude-daemon.py |
| scripts/change-passwords.sh | /opt/fotios-claude/scripts/change-passwords.sh |
| web/templates/*.html | /opt/fotios-claude/web/templates/*.html |

## After Reboot

Check that services are running:
```bash
systemctl status fotios-claude-web fotios-claude-daemon mysql lshttpd
```

## Detailed Development Notes

For comprehensive development guide, database info, common tasks, and tips:
```
/home/claude/fotios-claude-system/CLAUDE_DEV_NOTES.md
```

## Project Template

For helping users design projects:
```
/home/claude/PROJECT_TEMPLATE.md
```

---
**Last updated:** 2026-01-11
**Version:** 2.32.0
