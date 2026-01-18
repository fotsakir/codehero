#!/bin/bash
# Always runs during upgrade (permissions, cleanup)
# This script runs LAST, after all version-specific upgrades

log_info() { echo -e "\033[0;36m[ALWAYS]\033[0m $1"; }

CLAUDE_USER="claude"
INSTALL_DIR="/opt/codehero"

# Fix ownership of key directories
log_info "Fixing permissions..."

# Log directory
mkdir -p /var/log/codehero
chown -R ${CLAUDE_USER}:${CLAUDE_USER} /var/log/codehero 2>/dev/null || true

# Runtime directory
mkdir -p /var/run/codehero
chown -R ${CLAUDE_USER}:${CLAUDE_USER} /var/run/codehero 2>/dev/null || true

# Projects directory
if [ -d "/var/www/projects" ]; then
    chown -R ${CLAUDE_USER}:${CLAUDE_USER} /var/www/projects 2>/dev/null || true
    chmod 2775 /var/www/projects 2>/dev/null || true
fi

# Apps directory
if [ -d "/opt/apps" ]; then
    chown -R ${CLAUDE_USER}:${CLAUDE_USER} /opt/apps 2>/dev/null || true
    chmod 2775 /opt/apps 2>/dev/null || true
fi

# Make scripts executable
chmod +x ${INSTALL_DIR}/scripts/*.sh 2>/dev/null || true

log_info "Permissions fixed"

# Ensure AUTO_REVIEW_DELAY_MINUTES is in system.conf (added in 2.72.0)
CONFIG_FILE="/etc/codehero/system.conf"
if [ -f "$CONFIG_FILE" ] && ! grep -q "AUTO_REVIEW_DELAY_MINUTES" "$CONFIG_FILE"; then
    log_info "Adding AUTO_REVIEW_DELAY_MINUTES to config..."
    echo "AUTO_REVIEW_DELAY_MINUTES=5" >> "$CONFIG_FILE"
fi
