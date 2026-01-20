# Claude Instructions - CodeHero

**READ THIS BEFORE MAKING ANY CHANGES**

## Project Structure

```
/home/claude/codehero/    <- LOCAL SOURCE (make changes here)
/opt/codehero/                   <- LOCAL PRODUCTION (installed files)
/home/claude/codehero-X.Y.Z.zip  <- BACKUPS (DON'T DELETE!)
```

### Remote Server (Optional)
```
The remote server is not always available.
User will provide IP/credentials when needed.
Production path: /opt/codehero/
```

## Workflow for Changes

### 1. Make changes in SOURCE
```
/home/claude/codehero/
```

### 2. Copy to PRODUCTION
```bash
sudo cp /home/claude/codehero/web/app.py /opt/codehero/web/
sudo cp /home/claude/codehero/scripts/claude-daemon.py /opt/codehero/scripts/
sudo cp -r /home/claude/codehero/web/templates/* /opt/codehero/web/templates/
sudo cp /home/claude/codehero/scripts/*.sh /opt/codehero/scripts/
```

### 3. Copy to REMOTE PRODUCTION (when remote server is available)
```bash
# User will provide IP and PASSWORD
sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no /home/claude/codehero/web/app.py root@REMOTE_IP:/opt/codehero/web/
sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no /home/claude/codehero/scripts/claude-daemon.py root@REMOTE_IP:/opt/codehero/scripts/
sshpass -p 'PASSWORD' scp -o StrictHostKeyChecking=no -r /home/claude/codehero/web/templates/* root@REMOTE_IP:/opt/codehero/web/templates/
```

### 4. Restart services (ALWAYS!) - Both Local and Remote
**IMPORTANT:** Always restart services after ANY change - otherwise changes won't be visible!
```bash
# Local
sudo systemctl restart codehero-web codehero-daemon

# Remote (when available)
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "systemctl restart codehero-web codehero-daemon"
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
zip -r codehero-X.Y.Z.zip codehero -x "*.pyc" -x "*__pycache__*" -x "*.git*"
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
gh release create vX.Y.Z /home/claude/codehero-X.Y.Z.zip --title "vX.Y.Z - Description" --notes "Release notes here"
```

## New Release Checklist (FOLLOW THIS ORDER!)

**"κάνε νέα έκδοση X.Y.Z"** = Βήματα 1-5 ΜΟΝΟ (preparation, NO commit)
**"κάνε νέα έκδοση X.Y.Z με commit"** = ΟΛΑ τα βήματα (1-8) + ΠΑΝΤΑ update local zip

### Step 1: Update VERSION
```bash
echo "X.Y.Z" > /home/claude/codehero/VERSION
```

### Step 2: Update Documentation Files
```bash
# README.md - Update badge version AND zip filename
# INSTALL.md - Update zip filename AND footer version
# docs/index.html - Update softwareVersion AND zip filename
# Use "replace all" for zip filename changes
```

### Step 3: Update CHANGELOG.md
Add new entry at the TOP with:
- `## [X.Y.Z] - YYYY-MM-DD`
- `### Added` / `### Improved` / `### Fixed` sections

### Step 4: Check Database (IMPORTANT!)
**Migration:** Αν έχεις κάνει αλλαγές στη βάση, φτιάξε migration file:
```bash
# Check if migration exists
ls database/migrations/X.Y.Z_*.sql
# If not, create one for DB changes
```

**Schema:** Έλεγξε ότι το schema.sql έχει ΟΛΑ τα νέα columns/tables για fresh install:
```bash
# Search for new columns in schema
grep "new_column_name" database/schema.sql
# If missing, ADD them to schema.sql!
```

⚠️ **ΠΡΟΣΟΧΗ:** Migration = για upgrades, Schema = για νέες εγκαταστάσεις. ΠΡΕΠΕΙ να είναι in sync!

### Step 5: Copy to Production
```bash
sudo cp /home/claude/codehero/VERSION /opt/codehero/
sudo cp /home/claude/codehero/CHANGELOG.md /opt/codehero/
sudo cp /home/claude/codehero/README.md /opt/codehero/
sudo cp /home/claude/codehero/INSTALL.md /opt/codehero/
sudo cp -r /home/claude/codehero/docs/* /opt/codehero/docs/
sudo cp /home/claude/codehero/database/schema.sql /opt/codehero/database/
sudo cp /home/claude/codehero/database/migrations/*.sql /opt/codehero/database/migrations/ 2>/dev/null || true
```

**--- STOP HERE αν ΔΕΝ είπε "με commit" ---**

### Step 6: Create ZIP (don't delete old ones!)
```bash
cd /home/claude
zip -r codehero-X.Y.Z.zip codehero -x "*.pyc" -x "*__pycache__*" -x "*.git*"
```

### Step 7: Git Commit, Tag, Push
```bash
git add -A
git commit -m "Release vX.Y.Z - Short Description"
git tag -a vX.Y.Z -m "Release vX.Y.Z - Short Description"
git push origin main
git push origin vX.Y.Z
```

### Step 8: Create GitHub Release
```bash
gh release create vX.Y.Z /home/claude/codehero-X.Y.Z.zip \
  --title "vX.Y.Z - Short Description" \
  --notes "## What's New

### Added
- Feature 1
- Feature 2

## Upgrade
\`\`\`bash
cd /root
wget https://github.com/fotsakir/codehero/releases/latest/download/codehero-X.Y.Z.zip
unzip codehero-X.Y.Z.zip
cd codehero
sudo ./upgrade.sh
\`\`\`"
```

---

## Service Names (IMPORTANT!)

The correct names are:
- `codehero-web` (NOT fotios-web)
- `codehero-daemon` (NOT fotios-daemon)

## Check Sync (Local Source vs Local Prod vs Remote Prod)

```bash
# Local Source vs Local Production
diff /home/claude/codehero/web/app.py /opt/codehero/web/app.py
diff /home/claude/codehero/scripts/claude-daemon.py /opt/codehero/scripts/claude-daemon.py

# Local Source vs Remote Production (when remote available)
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "cat /opt/codehero/web/app.py" | diff /home/claude/codehero/web/app.py -
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "cat /opt/codehero/scripts/claude-daemon.py" | diff /home/claude/codehero/scripts/claude-daemon.py -
```

## Check Services

```bash
# Local
systemctl status codehero-web codehero-daemon

# Remote (when available)
sshpass -p 'PASSWORD' ssh -o StrictHostKeyChecking=no root@REMOTE_IP "systemctl is-active codehero-web codehero-daemon"
```

## Version History

The zip files are BACKUPS. Keep them all:
- codehero-2.20.0.zip
- codehero-2.21.0.zip
- ... etc

## Files that must be SYNCED

| Source | Production |
|--------|------------|
| web/app.py | /opt/codehero/web/app.py |
| scripts/claude-daemon.py | /opt/codehero/scripts/claude-daemon.py |
| scripts/change-passwords.sh | /opt/codehero/scripts/change-passwords.sh |
| web/templates/*.html | /opt/codehero/web/templates/*.html |

## After Reboot

Check that services are running:
```bash
systemctl status codehero-web codehero-daemon mysql nginx php8.3-fpm
```

## Detailed Development Notes

For comprehensive development guide, database info, common tasks, and tips:
```
/home/claude/codehero/CLAUDE_DEV_NOTES.md
```

## Project Template

For helping users design projects:
```
/home/claude/PROJECT_TEMPLATE.md
```

---
**Last updated:** 2026-01-20
**Version:** 2.77.0
