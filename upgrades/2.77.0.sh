#!/bin/bash
# Upgrade to version 2.77.0
# Installs 2FA dependencies and runs migration

log_info() { echo -e "\033[0;36m[2.77.0]\033[0m $1"; }
log_success() { echo -e "\033[0;32m[2.77.0]\033[0m $1"; }
log_warning() { echo -e "\033[1;33m[2.77.0]\033[0m $1"; }

# Install 2FA Python packages
log_info "Installing 2FA dependencies (pyotp, qrcode, pillow)..."
pip3 install --quiet pyotp qrcode pillow --break-system-packages 2>/dev/null || \
pip3 install --quiet pyotp qrcode pillow 2>/dev/null || true

# Verify installation
if python3 -c "import pyotp, qrcode" 2>/dev/null; then
    log_success "2FA packages installed"
else
    log_warning "2FA packages may need manual installation: pip3 install pyotp qrcode pillow"
fi

# Run database migration
MIGRATION_FILE="/opt/codehero/database/migrations/2.77.0_auth_2fa.sql"
if [ -f "$MIGRATION_FILE" ]; then
    log_info "Running 2FA database migration..."

    # Get database credentials
    if [ -f /etc/codehero/system.conf ]; then
        source /etc/codehero/system.conf
    fi

    DB_USER="${DB_USER:-claude_user}"
    DB_PASSWORD="${DB_PASSWORD:-}"
    DB_NAME="${DB_NAME:-claude_knowledge}"

    if [ -n "$DB_PASSWORD" ]; then
        mysql -u "$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < "$MIGRATION_FILE" 2>/dev/null && \
            log_success "Database migration completed" || \
            log_warning "Migration may have already been applied"
    else
        log_warning "Could not find database credentials - run migration manually"
    fi
else
    log_warning "Migration file not found: $MIGRATION_FILE"
fi

log_success "2.77.0 upgrade complete"
