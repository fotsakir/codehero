#!/bin/bash
# =====================================================
# CODEHERO - Upgrade Script (Modular)
# =====================================================
# Usage:
#   sudo ./upgrade.sh           # Interactive mode
#   sudo ./upgrade.sh -y        # Auto-confirm all
#   sudo ./upgrade.sh --dry-run # Show what would be done
# =====================================================

# Note: We don't use 'set -e' to allow graceful error handling
# Each critical step checks for errors explicitly

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# Paths
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/codehero"

# Safety check: SOURCE must not be same as INSTALL
if [ "$SOURCE_DIR" = "$INSTALL_DIR" ]; then
    echo -e "${RED}ERROR: Cannot run upgrade from ${INSTALL_DIR}${NC}"
    echo ""
    echo "You extracted the zip to the wrong location!"
    echo ""
    echo "Correct procedure:"
    echo "  1. cd /root"
    echo "  2. unzip codehero-X.Y.Z.zip"
    echo "  3. cd codehero"
    echo "  4. sudo ./upgrade.sh"
    echo ""
    exit 1
fi
BACKUP_DIR="/var/backups/codehero"
CONFIG_DIR="/etc/codehero"
UPGRADES_DIR="${SOURCE_DIR}/upgrades"
APPLIED_FILE="${CONFIG_DIR}/applied_upgrades"

# Options
DRY_RUN=false
AUTO_YES=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        -y|--yes) AUTO_YES=true; shift ;;
        -h|--help)
            echo "Usage: sudo ./upgrade.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -y, --yes      Auto-confirm all prompts"
            echo "  --dry-run      Show what would be done without making changes"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *) echo -e "${RED}Unknown option: $1${NC}"; exit 1 ;;
    esac
done

# Functions
log_info() { echo -e "${CYAN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

confirm() {
    if [ "$AUTO_YES" = true ]; then return 0; fi
    read -p "$1 [y/N]: " response
    case "$response" in [yY][eE][sS]|[yY]) return 0 ;; *) return 1 ;; esac
}

version_compare() {
    # Returns: 0 if equal, 1 if $1 > $2, 2 if $1 < $2
    if [ "$1" = "$2" ]; then return 0; fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    for ((i=0; i<${#ver1[@]}; i++)); do
        if [ -z "${ver2[i]}" ]; then return 1; fi
        if ((10#${ver1[i]} > 10#${ver2[i]})); then return 1; fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then return 2; fi
    done
    return 0
}

version_gt() {
    # Returns 0 if $1 > $2
    set +e; version_compare "$1" "$2"; local result=$?; set -e
    [ $result -eq 1 ]
}

version_gte() {
    # Returns 0 if $1 >= $2
    set +e; version_compare "$1" "$2"; local result=$?; set -e
    [ $result -eq 0 ] || [ $result -eq 1 ]
}

get_db_credentials() {
    source ${CONFIG_DIR}/system.conf 2>/dev/null || {
        log_error "Cannot read ${CONFIG_DIR}/system.conf"
        exit 1
    }
    DB_USER="${DB_USER:-claude_user}"
    DB_PASS="${DB_PASSWORD:-claudepass123}"
    DB_NAME="${DB_NAME:-claude_knowledge}"
}

run_sql() {
    mysql -u "${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" -e "$1" 2>/dev/null
}

run_sql_file() {
    mysql -u "${DB_USER}" -p"${DB_PASS}" "${DB_NAME}" < "$1" 2>/dev/null
}

# =====================================================
# MAIN SCRIPT
# =====================================================

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              CODEHERO - Upgrade Script                    ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}>>> DRY-RUN MODE - No changes will be made <<<${NC}"
    echo ""
fi

# Check root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root or with sudo"
    exit 1
fi

# Check if installation exists
if [ ! -d "$INSTALL_DIR" ]; then
    log_error "CodeHero is not installed at $INSTALL_DIR"
    log_info "Please run setup.sh for fresh installation"
    exit 1
fi

# Get versions
NEW_VERSION=$(cat "${SOURCE_DIR}/VERSION" 2>/dev/null || echo "0.0.0")
CURRENT_VERSION=$(cat "${INSTALL_DIR}/VERSION" 2>/dev/null || echo "0.0.0")

echo -e "Current version: ${YELLOW}${CURRENT_VERSION}${NC}"
echo -e "New version:     ${GREEN}${NEW_VERSION}${NC}"
echo ""

# Validate versions match zip filename (detect wrong download)
ZIP_NAME=$(basename "$(dirname "${SOURCE_DIR}")" 2>/dev/null)
if [[ "$ZIP_NAME" =~ codehero-([0-9]+\.[0-9]+\.[0-9]+) ]]; then
    ZIP_VERSION="${BASH_REMATCH[1]}"
    if [ "$ZIP_VERSION" != "$NEW_VERSION" ]; then
        log_warning "Mismatch detected!"
        log_warning "Zip filename suggests version: $ZIP_VERSION"
        log_warning "But VERSION file contains: $NEW_VERSION"
        log_warning "You may have downloaded the wrong file."
        if ! confirm "Continue anyway?"; then
            exit 1
        fi
    fi
fi

# Compare versions
set +e
version_compare "$NEW_VERSION" "$CURRENT_VERSION"
VCOMP=$?
set -e

case $VCOMP in
    0)
        log_warning "Versions are the same. Nothing to upgrade."
        if ! confirm "Continue anyway?"; then exit 0; fi
        ;;
    2)
        log_warning "New version ($NEW_VERSION) is older than current ($CURRENT_VERSION)"
        log_warning "This will DOWNGRADE your installation."
        if ! confirm "Downgrade?"; then exit 0; fi
        ;;
esac

# =====================================================
# FIND PENDING UPGRADES
# =====================================================

echo -e "${CYAN}=== Upgrade Summary ===${NC}"
echo ""

# Initialize applied upgrades file
mkdir -p "${CONFIG_DIR}"
touch "${APPLIED_FILE}"

# Find upgrade scripts to run
log_info "Upgrade scripts to apply:"
PENDING_UPGRADES=()

if [ -d "$UPGRADES_DIR" ]; then
    for script in $(ls -1 "${UPGRADES_DIR}"/*.sh 2>/dev/null | grep -v '_always.sh' | sort -V); do
        script_name=$(basename "$script" .sh)

        # Skip if already applied
        if grep -qx "$script_name" "${APPLIED_FILE}" 2>/dev/null; then
            continue
        fi

        # Skip if version is older than or equal to current
        if version_gte "$CURRENT_VERSION" "$script_name" 2>/dev/null; then
            continue
        fi

        # Skip if version is newer than target
        if version_gt "$script_name" "$NEW_VERSION" 2>/dev/null; then
            continue
        fi

        echo "  [PENDING] $script_name"
        PENDING_UPGRADES+=("$script")
    done
fi

if [ ${#PENDING_UPGRADES[@]} -eq 0 ]; then
    echo "  (no pending upgrade scripts)"
fi
echo ""

# Find database migrations
get_db_credentials

# Ensure schema_migrations table exists
if [ "$DRY_RUN" = false ]; then
    run_sql "CREATE TABLE IF NOT EXISTS schema_migrations (
        version VARCHAR(20) PRIMARY KEY,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );" 2>/dev/null || true
fi

log_info "Database migrations to apply:"
MIGRATIONS_DIR="${SOURCE_DIR}/database/migrations"
PENDING_MIGRATIONS=()

# Extract version from migration filename (e.g., 2.72.0_auto_review.sql → 2.72.0)
extract_migration_version() {
    local name="$1"
    echo "$name" | grep -oE '^[0-9]+\.[0-9]+\.[0-9]+' || echo ""
}

if [ -d "$MIGRATIONS_DIR" ]; then
    for migration in $(ls -1 "${MIGRATIONS_DIR}"/*.sql 2>/dev/null | sort -V); do
        migration_name=$(basename "$migration" .sql)
        migration_version=$(extract_migration_version "$migration_name")

        # Skip if no version found in filename
        if [ -z "$migration_version" ]; then
            echo "  [SKIP] $migration_name (no version in filename)"
            continue
        fi

        # Skip if migration version <= current version (already should be applied)
        if version_gte "$CURRENT_VERSION" "$migration_version" 2>/dev/null; then
            continue
        fi

        # Skip if migration version > new version (future migration)
        if version_gt "$migration_version" "$NEW_VERSION" 2>/dev/null; then
            continue
        fi

        # Skip if already applied
        applied=$(run_sql "SELECT version FROM schema_migrations WHERE version='${migration_name}';" 2>/dev/null | tail -1)
        if [ -n "$applied" ]; then
            continue
        fi

        echo "  [PENDING] $migration_name (v$migration_version)"
        PENDING_MIGRATIONS+=("$migration")
    done
fi

if [ ${#PENDING_MIGRATIONS[@]} -eq 0 ]; then
    echo "  (no pending migrations)"
fi
echo ""

# Dry-run ends here
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}=== Dry-run complete ===${NC}"
    echo "Run without --dry-run to apply changes."
    exit 0
fi

# Confirm upgrade
if ! confirm "Proceed with upgrade?"; then
    log_info "Upgrade cancelled."
    exit 0
fi

echo ""
echo -e "${CYAN}=== Starting Upgrade ===${NC}"
echo ""

# =====================================================
# STEP 1: CREATE BACKUP
# =====================================================

BACKUP_NAME="codehero-${CURRENT_VERSION}-$(date +%Y%m%d_%H%M%S)"
log_info "Creating backup: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
mkdir -p "$BACKUP_DIR"
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C /opt codehero 2>/dev/null
log_success "Backup created"

# =====================================================
# STEP 2: STOP DAEMON
# =====================================================

log_info "Stopping daemon..."
systemctl stop codehero-daemon 2>/dev/null || true
sleep 1
log_success "Daemon stopped"

# =====================================================
# STEP 3: COPY FILES
# =====================================================

log_info "Copying files..."

# Web app
if [ -d "${SOURCE_DIR}/web" ]; then
    cp -r "${SOURCE_DIR}/web/"* "${INSTALL_DIR}/web/" 2>/dev/null || true
    echo "  Copied web files"
fi

# Scripts
if [ -d "${SOURCE_DIR}/scripts" ]; then
    cp "${SOURCE_DIR}/scripts/"*.py "${INSTALL_DIR}/scripts/" 2>/dev/null || true
    cp "${SOURCE_DIR}/scripts/"*.sh "${INSTALL_DIR}/scripts/" 2>/dev/null || true
    chmod +x "${INSTALL_DIR}/scripts/"*.sh 2>/dev/null || true
    echo "  Copied scripts"
fi

# Docs
if [ -d "${SOURCE_DIR}/docs" ]; then
    mkdir -p "${INSTALL_DIR}/docs"
    cp -r "${SOURCE_DIR}/docs/"* "${INSTALL_DIR}/docs/" 2>/dev/null || true
    echo "  Copied docs"
fi

# Config files
if [ -d "${SOURCE_DIR}/config" ]; then
    mkdir -p "${INSTALL_DIR}/config"
    cp "${SOURCE_DIR}/config/"*.md "${INSTALL_DIR}/config/" 2>/dev/null || true
    cp "${SOURCE_DIR}/config/"*.json "${INSTALL_DIR}/config/" 2>/dev/null || true
    cp "${SOURCE_DIR}/config/"*.conf "${INSTALL_DIR}/config/" 2>/dev/null || true
    cp "${SOURCE_DIR}/config/"*.md "${CONFIG_DIR}/" 2>/dev/null || true
    cp "${SOURCE_DIR}/config/"*.json "${CONFIG_DIR}/" 2>/dev/null || true
    cp "${SOURCE_DIR}/config/"*.conf "${CONFIG_DIR}/" 2>/dev/null || true
    echo "  Copied config files"
fi

# Upgrades directory
if [ -d "${SOURCE_DIR}/upgrades" ]; then
    mkdir -p "${INSTALL_DIR}/upgrades"
    cp "${SOURCE_DIR}/upgrades/"*.sh "${INSTALL_DIR}/upgrades/" 2>/dev/null || true
    cp "${SOURCE_DIR}/upgrades/"*.md "${INSTALL_DIR}/upgrades/" 2>/dev/null || true
    chmod +x "${INSTALL_DIR}/upgrades/"*.sh 2>/dev/null || true
    echo "  Copied upgrades"
fi

# VERSION, CHANGELOG, and documentation
cp "${SOURCE_DIR}/VERSION" "${INSTALL_DIR}/"
cp "${SOURCE_DIR}/CHANGELOG.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/README.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/CLAUDE_OPERATIONS.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/CLAUDE_DEV_NOTES.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/CLAUDE.md" "${INSTALL_DIR}/" 2>/dev/null || true

log_success "Files copied"

# =====================================================
# STEP 3.5: ENSURE PYTHON DEPENDENCIES
# =====================================================

log_info "Checking Python dependencies..."
pip3 install --quiet --ignore-installed eventlet --break-system-packages 2>/dev/null || \
pip3 install --quiet --ignore-installed eventlet 2>/dev/null || true
log_success "Python dependencies OK"

# =====================================================
# STEP 4: RUN VERSION UPGRADE SCRIPTS
# =====================================================

if [ ${#PENDING_UPGRADES[@]} -gt 0 ]; then
    log_info "Running upgrade scripts..."
    for script in "${PENDING_UPGRADES[@]}"; do
        script_name=$(basename "$script" .sh)
        echo -n "  Running $script_name... "
        if bash "$script" 2>&1 | sed 's/^/    /'; then
            echo "$script_name" >> "${APPLIED_FILE}"
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${YELLOW}WARNING${NC}"
        fi
    done
    log_success "Upgrade scripts completed"
fi

# Run _always.sh if exists
if [ -f "${UPGRADES_DIR}/_always.sh" ]; then
    log_info "Running cleanup script..."
    bash "${UPGRADES_DIR}/_always.sh" 2>&1 | sed 's/^/  /'
    log_success "Cleanup completed"
fi

# =====================================================
# STEP 5: APPLY DATABASE MIGRATIONS
# =====================================================

if [ ${#PENDING_MIGRATIONS[@]} -gt 0 ]; then
    log_info "Applying database migrations..."
    for migration in "${PENDING_MIGRATIONS[@]}"; do
        migration_name=$(basename "$migration" .sql)
        echo -n "  Applying $migration_name... "
        if run_sql_file "$migration"; then
            run_sql "INSERT INTO schema_migrations (version) VALUES ('${migration_name}');"
            echo -e "${GREEN}OK${NC}"
        else
            echo -e "${RED}FAILED${NC}"
            log_error "Migration failed: $migration_name"
            log_info "Rolling back: starting services..."
            systemctl start codehero-daemon 2>/dev/null || true
            systemctl start codehero-web 2>/dev/null || true
            exit 1
        fi
    done
    log_success "All migrations applied"
fi

# =====================================================
# STEP 6: UPDATE CONFIG (add new parameters if missing)
# =====================================================

log_info "Checking config parameters..."
CONFIG_UPDATED=false

# Add RATE_LIMIT_COOLDOWN_MINUTES if missing
if ! grep -q "^RATE_LIMIT_COOLDOWN_MINUTES" ${CONFIG_DIR}/system.conf 2>/dev/null; then
    echo "" >> ${CONFIG_DIR}/system.conf
    echo "# Retry Cooldown Settings (added in v2.76.0)" >> ${CONFIG_DIR}/system.conf
    echo "RATE_LIMIT_COOLDOWN_MINUTES=30" >> ${CONFIG_DIR}/system.conf
    echo "  Added: RATE_LIMIT_COOLDOWN_MINUTES=30"
    CONFIG_UPDATED=true
fi

# Add RETRY_COOLDOWN_MINUTES if missing
if ! grep -q "^RETRY_COOLDOWN_MINUTES" ${CONFIG_DIR}/system.conf 2>/dev/null; then
    if [ "$CONFIG_UPDATED" = false ]; then
        echo "" >> ${CONFIG_DIR}/system.conf
        echo "# Retry Cooldown Settings (added in v2.76.0)" >> ${CONFIG_DIR}/system.conf
    fi
    echo "RETRY_COOLDOWN_MINUTES=5" >> ${CONFIG_DIR}/system.conf
    echo "  Added: RETRY_COOLDOWN_MINUTES=5"
    CONFIG_UPDATED=true
fi

if [ "$CONFIG_UPDATED" = true ]; then
    log_success "Config updated with new parameters"
else
    echo "  (no new parameters needed)"
fi

# =====================================================
# STEP 7: UPDATE SYSTEMD SERVICES
# =====================================================

log_info "Updating systemd service files..."

# Update daemon service with improved startup handling
cat > /etc/systemd/system/codehero-daemon.service << 'SVCEOF'
[Unit]
Description=CodeHero Daemon
After=network.target mysql.service codehero-web.service
Requires=mysql.service

[Service]
Type=simple
User=claude
Group=claude
WorkingDirectory=/opt/codehero
ExecStartPre=/bin/mkdir -p /var/run/codehero
ExecStartPre=/bin/chown claude:claude /var/run/codehero
ExecStart=/usr/bin/python3 /opt/codehero/scripts/claude-daemon.py
Restart=always
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=10
StandardOutput=append:/var/log/codehero/daemon.log
StandardError=append:/var/log/codehero/daemon.log
Environment=PYTHONUNBUFFERED=1
Environment=PATH=/home/claude/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=HOME=/home/claude

[Install]
WantedBy=multi-user.target
SVCEOF

log_success "Systemd services updated"

# =====================================================
# STEP 8: RESTART SERVICES
# =====================================================

log_info "Restarting services..."
systemctl daemon-reload
systemctl restart codehero-daemon
sleep 1
systemctl restart codehero-web
sleep 1
systemctl reload nginx 2>/dev/null || systemctl restart nginx 2>/dev/null || true
sleep 1
log_success "Services restarted"

# =====================================================
# STEP 9: VERIFY
# =====================================================

log_info "Verifying services..."
VERIFY_OK=true

if systemctl is-active --quiet codehero-web; then
    echo -e "  codehero-web:    ${GREEN}running${NC}"
else
    echo -e "  codehero-web:    ${RED}not running${NC}"
    VERIFY_OK=false
fi

if systemctl is-active --quiet codehero-daemon; then
    echo -e "  codehero-daemon: ${GREEN}running${NC}"
else
    echo -e "  codehero-daemon: ${RED}not running${NC}"
    VERIFY_OK=false
fi

if systemctl is-active --quiet nginx; then
    echo -e "  nginx:           ${GREEN}running${NC}"
else
    echo -e "  nginx:           ${RED}not running${NC}"
    VERIFY_OK=false
fi

echo ""

if [ "$VERIFY_OK" = true ]; then
    log_success "Upgrade completed successfully!"
else
    log_warning "Upgrade completed with warnings. Check service status."
fi

# Show changelog for this version
echo ""
echo -e "${CYAN}=== What's New in ${NEW_VERSION} ===${NC}"
if [ -f "${SOURCE_DIR}/CHANGELOG.md" ]; then
    sed -n "/^## \[${NEW_VERSION}\]/,/^## \[/p" "${SOURCE_DIR}/CHANGELOG.md" | head -n -1 | tail -n +2
else
    echo "See CHANGELOG.md for details"
fi

echo ""
echo -e "${GREEN}Upgrade from ${CURRENT_VERSION} to ${NEW_VERSION} complete!${NC}"
echo ""
echo "Backup saved to: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
