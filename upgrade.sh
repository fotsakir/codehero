#!/bin/bash
# =====================================================
# FOTIOS CLAUDE SYSTEM - Upgrade Script
# =====================================================
# Usage:
#   sudo ./upgrade.sh           # Interactive mode
#   sudo ./upgrade.sh -y        # Auto-confirm all
#   sudo ./upgrade.sh --dry-run # Show what would be done
# =====================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BLUE='\033[0;34m'
NC='\033[0m'

# Paths
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/fotios-claude"
BACKUP_DIR="/var/backups/fotios-claude"
CONFIG_DIR="/etc/fotios-claude"

# Options
DRY_RUN=false
AUTO_YES=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        -h|--help)
            echo "Usage: sudo ./upgrade.sh [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -y, --yes      Auto-confirm all prompts"
            echo "  --dry-run      Show what would be done without making changes"
            echo "  -h, --help     Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Functions
log_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_dry() {
    echo -e "${BLUE}[DRY-RUN]${NC} Would: $1"
}

confirm() {
    if [ "$AUTO_YES" = true ]; then
        return 0
    fi
    read -p "$1 [y/N]: " response
    case "$response" in
        [yY][eE][sS]|[yY]) return 0 ;;
        *) return 1 ;;
    esac
}

version_compare() {
    # Returns: 0 if equal, 1 if $1 > $2, 2 if $1 < $2
    if [ "$1" = "$2" ]; then
        return 0
    fi
    local IFS=.
    local i ver1=($1) ver2=($2)
    for ((i=0; i<${#ver1[@]}; i++)); do
        if [ -z "${ver2[i]}" ]; then
            return 1
        fi
        if ((10#${ver1[i]} > 10#${ver2[i]})); then
            return 1
        fi
        if ((10#${ver1[i]} < 10#${ver2[i]})); then
            return 2
        fi
    done
    return 0
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
echo "║         FOTIOS CLAUDE SYSTEM - Upgrade Script             ║"
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
    log_error "Fotios Claude is not installed at $INSTALL_DIR"
    log_info "Please run setup.sh for fresh installation"
    exit 1
fi

# Get versions
NEW_VERSION=$(cat "${SOURCE_DIR}/VERSION" 2>/dev/null || echo "0.0.0")
CURRENT_VERSION=$(cat "${INSTALL_DIR}/VERSION" 2>/dev/null || echo "0.0.0")

echo -e "Current version: ${YELLOW}${CURRENT_VERSION}${NC}"
echo -e "New version:     ${GREEN}${NEW_VERSION}${NC}"
echo ""

# Compare versions
set +e
version_compare "$NEW_VERSION" "$CURRENT_VERSION"
VCOMP=$?
set -e
case $VCOMP in
    0)
        log_warning "Versions are the same. Nothing to upgrade."
        if ! confirm "Continue anyway?"; then
            exit 0
        fi
        ;;
    2)
        log_warning "New version ($NEW_VERSION) is older than current ($CURRENT_VERSION)"
        if ! confirm "Downgrade?"; then
            exit 0
        fi
        ;;
esac

# Show what will be upgraded
echo -e "${CYAN}=== Upgrade Summary ===${NC}"
echo ""

# Check for file changes
log_info "Files to be updated:"
CHANGED_FILES=0
for dir in web scripts docs; do
    if [ -d "${SOURCE_DIR}/${dir}" ]; then
        while IFS= read -r -d '' file; do
            rel_path="${file#$SOURCE_DIR/}"
            target="${INSTALL_DIR}/${rel_path}"
            if [ -f "$target" ]; then
                if ! diff -q "$file" "$target" > /dev/null 2>&1; then
                    echo "  [MODIFIED] $rel_path"
                    CHANGED_FILES=$((CHANGED_FILES + 1))
                fi
            else
                echo "  [NEW] $rel_path"
                CHANGED_FILES=$((CHANGED_FILES + 1))
            fi
        done < <(find "${SOURCE_DIR}/${dir}" -type f -print0)
    fi
done

if [ $CHANGED_FILES -eq 0 ]; then
    echo "  (no file changes detected)"
fi
echo ""

# Check for migrations
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

if [ -d "$MIGRATIONS_DIR" ]; then
    for migration in $(ls -1 "${MIGRATIONS_DIR}"/*.sql 2>/dev/null | sort -V); do
        migration_name=$(basename "$migration" .sql)
        # Check if already applied
        applied=$(run_sql "SELECT version FROM schema_migrations WHERE version='${migration_name}';" 2>/dev/null | tail -1)
        if [ -z "$applied" ]; then
            echo "  [PENDING] $migration_name"
            PENDING_MIGRATIONS+=("$migration")
        fi
    done
fi

if [ ${#PENDING_MIGRATIONS[@]} -eq 0 ]; then
    echo "  (no pending migrations)"
fi
echo ""

# Confirm upgrade
if [ "$DRY_RUN" = true ]; then
    echo -e "${BLUE}=== Dry-run complete ===${NC}"
    echo "Run without --dry-run to apply changes."
    exit 0
fi

if ! confirm "Proceed with upgrade?"; then
    log_info "Upgrade cancelled."
    exit 0
fi

echo ""
echo -e "${CYAN}=== Starting Upgrade ===${NC}"
echo ""

# Step 1: Create backup
BACKUP_NAME="fotios-claude-${CURRENT_VERSION}-$(date +%Y%m%d_%H%M%S)"
log_info "Creating backup: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
mkdir -p "$BACKUP_DIR"
tar -czf "${BACKUP_DIR}/${BACKUP_NAME}.tar.gz" -C /opt fotios-claude 2>/dev/null
log_success "Backup created"

# Step 2: Stop services
log_info "Stopping services..."
systemctl stop fotios-claude-web 2>/dev/null || true
systemctl stop fotios-claude-daemon 2>/dev/null || true
sleep 2
log_success "Services stopped"

# Step 3: Apply database migrations
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
            systemctl start fotios-claude-daemon 2>/dev/null || true
            systemctl start fotios-claude-web 2>/dev/null || true
            exit 1
        fi
    done
    log_success "All migrations applied"
fi

# Step 4: Copy files
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

# Config files (knowledge base, templates)
if [ -d "${SOURCE_DIR}/config" ]; then
    mkdir -p "${INSTALL_DIR}/config"
    cp "${SOURCE_DIR}/config/"*.md "${INSTALL_DIR}/config/" 2>/dev/null || true
    cp "${SOURCE_DIR}/config/"*.md "${CONFIG_DIR}/" 2>/dev/null || true
    echo "  Copied config files (knowledge base, templates)"
fi

# VERSION, CHANGELOG, and documentation
cp "${SOURCE_DIR}/VERSION" "${INSTALL_DIR}/"
cp "${SOURCE_DIR}/CHANGELOG.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/README.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/CLAUDE_OPERATIONS.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/CLAUDE_DEV_NOTES.md" "${INSTALL_DIR}/" 2>/dev/null || true
cp "${SOURCE_DIR}/CLAUDE.md" "${INSTALL_DIR}/" 2>/dev/null || true

log_success "Files copied"

# Step 5: Start services
log_info "Starting services..."
systemctl start fotios-claude-daemon
sleep 1
systemctl start fotios-claude-web
sleep 2
log_success "Services started"

# Step 6: Verify
log_info "Verifying services..."
VERIFY_OK=true

if systemctl is-active --quiet fotios-claude-web; then
    echo -e "  fotios-claude-web:    ${GREEN}running${NC}"
else
    echo -e "  fotios-claude-web:    ${RED}not running${NC}"
    VERIFY_OK=false
fi

if systemctl is-active --quiet fotios-claude-daemon; then
    echo -e "  fotios-claude-daemon: ${GREEN}running${NC}"
else
    echo -e "  fotios-claude-daemon: ${RED}not running${NC}"
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
    # Extract changelog for this version (between ## [version] markers)
    sed -n "/^## \[${NEW_VERSION}\]/,/^## \[/p" "${SOURCE_DIR}/CHANGELOG.md" | head -n -1 | tail -n +2
else
    echo "See CHANGELOG.md for details"
fi

echo ""
echo -e "${GREEN}Upgrade from ${CURRENT_VERSION} to ${NEW_VERSION} complete!${NC}"
echo ""
echo "Backup saved to: ${BACKUP_DIR}/${BACKUP_NAME}.tar.gz"
