#!/bin/bash
# =====================================================
# CODEHERO - Installation Script (Core)
# Version is read from VERSION file
# =====================================================
# Usage:
#   sudo ./setup.sh          (from root or with sudo)
#   sudo su -> ./setup.sh    (switch to root first)
#
# This installs the core admin panel. For development
# tools (Node.js, Java, Playwright, etc.) run:
#   sudo ./setup_devtools.sh
# =====================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Get script directory first
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Read version from VERSION file
if [ -f "${SCRIPT_DIR}/VERSION" ]; then
    VERSION=$(cat "${SCRIPT_DIR}/VERSION" | tr -d '[:space:]')
else
    VERSION="unknown"
fi

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║       CODEHERO - Core Installation              ║"
echo "║              Version ${VERSION}                              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# =====================================================
# ROOT/SUDO CHECK
# =====================================================
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run as root or with sudo${NC}"
    echo "  Option 1: sudo ./setup.sh"
    echo "  Option 2: sudo su -> ./setup.sh"
    exit 1
fi

# Already got SCRIPT_DIR at top
cd "$SCRIPT_DIR"

# =====================================================
# LOAD CONFIGURATION
# =====================================================
if [ -f "${SCRIPT_DIR}/install.conf" ]; then
    echo -e "${CYAN}Loading configuration from install.conf...${NC}"
    source "${SCRIPT_DIR}/install.conf"
else
    echo -e "${YELLOW}install.conf not found, using defaults${NC}"
fi

# Set defaults if not in config
CLAUDE_USER="${CLAUDE_USER:-claude}"
DB_HOST="${DB_HOST:-localhost}"
DB_NAME="${DB_NAME:-claude_knowledge}"
DB_USER="${DB_USER:-claude_user}"
DB_PASSWORD="${DB_PASSWORD:-claudepass123}"
MYSQL_ROOT_PASSWORD="${MYSQL_ROOT_PASSWORD:-rootpass123}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin123}"
FLASK_HOST="${FLASK_HOST:-127.0.0.1}"
FLASK_PORT="${FLASK_PORT:-5000}"
ADMIN_PORT="${ADMIN_PORT:-9453}"
PROJECTS_PORT="${PROJECTS_PORT:-9867}"
INSTALL_DIR="${INSTALL_DIR:-/opt/codehero}"
CONFIG_DIR="${CONFIG_DIR:-/etc/codehero}"
LOG_DIR="${LOG_DIR:-/var/log/codehero}"
WEB_ROOT="${WEB_ROOT:-/var/www/projects}"
APP_ROOT="${APP_ROOT:-/opt/apps}"
MAX_PARALLEL_PROJECTS="${MAX_PARALLEL_PROJECTS:-3}"
REVIEW_DEADLINE_DAYS="${REVIEW_DEADLINE_DAYS:-7}"
AUTO_REVIEW_DELAY_MINUTES="${AUTO_REVIEW_DELAY_MINUTES:-5}"
SSL_CERT="${SSL_CERT:-${CONFIG_DIR}/ssl/cert.pem}"
SSL_KEY="${SSL_KEY:-${CONFIG_DIR}/ssl/key.pem}"
ENABLE_AUTOSTART="${ENABLE_AUTOSTART:-yes}"

# Generate secret key
SECRET_KEY=$(openssl rand -hex 32)

echo ""
echo -e "${CYAN}Configuration:${NC}"
echo "  Claude User:     ${CLAUDE_USER}"
echo "  Install Dir:     ${INSTALL_DIR}"
echo "  Admin Port:      ${ADMIN_PORT}"
echo "  Projects Port:   ${PROJECTS_PORT}"
echo "  Max Workers:     ${MAX_PARALLEL_PROJECTS}"
echo ""

# =====================================================
# [1/12] CREATE CLAUDE USER
# =====================================================
echo -e "${YELLOW}[1/12] Setting up ${CLAUDE_USER} user with sudo access...${NC}"

if ! id "${CLAUDE_USER}" &>/dev/null; then
    useradd -m -s /bin/bash "${CLAUDE_USER}"
    echo -e "${GREEN}User '${CLAUDE_USER}' created${NC}"
else
    echo "User '${CLAUDE_USER}' already exists"
fi

# Ensure passwordless sudo
echo "${CLAUDE_USER} ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/${CLAUDE_USER}
chmod 440 /etc/sudoers.d/${CLAUDE_USER}
echo -e "${GREEN}Passwordless sudo configured for ${CLAUDE_USER}${NC}"

# =====================================================
# [2/12] SYSTEM DEPENDENCIES
# =====================================================
echo -e "${YELLOW}[2/12] Installing system dependencies...${NC}"
apt-get update || true
apt-get install -y python3 python3-pip openssl sudo wget curl gnupg lsb-release git || true

# =====================================================
# [3/12] DISABLE AUTOMATIC UPDATES
# =====================================================
echo -e "${YELLOW}[3/12] Disabling automatic updates...${NC}"

systemctl stop unattended-upgrades 2>/dev/null || true
systemctl disable unattended-upgrades 2>/dev/null || true
systemctl stop apt-daily.timer 2>/dev/null || true
systemctl disable apt-daily.timer 2>/dev/null || true
systemctl stop apt-daily-upgrade.timer 2>/dev/null || true
systemctl disable apt-daily-upgrade.timer 2>/dev/null || true

cat > /etc/apt/apt.conf.d/20auto-upgrades << 'APTEOF'
APT::Periodic::Update-Package-Lists "0";
APT::Periodic::Unattended-Upgrade "0";
APT::Periodic::Download-Upgradeable-Packages "0";
APT::Periodic::AutocleanInterval "0";
APTEOF

echo -e "${GREEN}Automatic updates disabled${NC}"

# =====================================================
# [4/12] MYSQL
# =====================================================
echo -e "${YELLOW}[4/12] Setting up MySQL...${NC}"

if command -v mysql &> /dev/null; then
    echo "MySQL already installed"
else
    # Add MySQL repository
    if [ ! -f /etc/apt/sources.list.d/mysql.list ]; then
        cd /tmp
        wget -q https://dev.mysql.com/get/mysql-apt-config_0.8.32-1_all.deb || true
        if [ -f mysql-apt-config_0.8.32-1_all.deb ]; then
            DEBIAN_FRONTEND=noninteractive dpkg -i mysql-apt-config_0.8.32-1_all.deb || true
            apt-get update || true
            rm -f mysql-apt-config_0.8.32-1_all.deb
        fi
    fi
    DEBIAN_FRONTEND=noninteractive apt-get install -y mysql-server || true
fi

# =====================================================
# [5/12] NGINX & PHP-FPM
# =====================================================
echo -e "${YELLOW}[5/12] Setting up Nginx & PHP-FPM...${NC}"

if command -v nginx &> /dev/null; then
    echo "Nginx already installed"
else
    apt-get install -y nginx || true
fi

if [ ! -f /var/run/php/php8.3-fpm.sock ] && ! dpkg -l | grep -q php8.3-fpm; then
    apt-get install -y php8.3-fpm php8.3-mysql php8.3-curl php8.3-intl \
        php8.3-opcache php8.3-redis php8.3-imagick php8.3-sqlite3 php8.3-imap \
        php8.3-apcu php8.3-igbinary php8.3-tidy php8.3-pgsql php8.3-cli || true
fi

# Install phpMyAdmin for database management
echo "  Installing phpMyAdmin..."
if ! dpkg -l | grep -q phpmyadmin; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y phpmyadmin || true
fi

# Configure phpMyAdmin signon authentication for auto-login (only if phpMyAdmin installed)
if [ -d /usr/share/phpmyadmin ]; then
    echo "  Configuring phpMyAdmin signon..."
    cat > /usr/share/phpmyadmin/signon.php << 'PMASIGNON' || true
<?php
/**
 * CodeHero phpMyAdmin Single Sign-On Script
 * Auto-login with project database credentials
 */
session_name('PMA_signon');
session_start();

// Get credentials from query parameters (base64 encoded for safety)
$user = isset($_GET['u']) ? base64_decode($_GET['u']) : '';
$pass = isset($_GET['p']) ? base64_decode($_GET['p']) : '';
$db = isset($_GET['db']) ? base64_decode($_GET['db']) : '';

if (empty($user)) {
    die('Missing credentials');
}

// Store credentials in session for phpMyAdmin
$_SESSION['PMA_single_signon_user'] = $user;
$_SESSION['PMA_single_signon_password'] = $pass;
$_SESSION['PMA_single_signon_host'] = 'localhost';

// Redirect to phpMyAdmin with selected database
$redirect = 'index.php';
if (!empty($db)) {
    $redirect .= '?db=' . urlencode($db);
}

header('Location: ' . $redirect);
exit;
PMASIGNON

    mkdir -p /etc/phpmyadmin/conf.d || true
    cat > /etc/phpmyadmin/conf.d/codehero-signon.php << 'PMACONFIG' || true
<?php
/**
 * CodeHero phpMyAdmin Single Sign-On Configuration
 */

// Override default server config to use signon auth
$cfg['Servers'][1]['auth_type'] = 'signon';
$cfg['Servers'][1]['SignonSession'] = 'PMA_signon';
$cfg['Servers'][1]['SignonURL'] = '/signon.php';
$cfg['Servers'][1]['LogoutURL'] = '/';
PMACONFIG
else
    echo "  phpMyAdmin not installed, skipping signon config"
fi

# =====================================================
# [6/12] PYTHON PACKAGES
# =====================================================
echo -e "${YELLOW}[6/12] Installing Python packages...${NC}"
pip3 install --ignore-installed flask flask-socketio flask-cors mysql-connector-python bcrypt eventlet pyotp qrcode pillow --break-system-packages 2>&1 || \
pip3 install --ignore-installed flask flask-socketio flask-cors mysql-connector-python bcrypt eventlet pyotp qrcode pillow 2>&1 || true

# Playwright (browser automation for visual verification)
echo "  Installing Playwright browser dependencies..."
apt-get install -y --no-install-recommends \
    libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libatspi2.0-0t64 \
    libcairo2 libcups2t64 libdbus-1-3 libdrm2 libgbm1 libglib2.0-0t64 \
    libnspr4 libnss3 libpango-1.0-0 libx11-6 libxcb1 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 xvfb \
    fonts-noto-color-emoji fonts-unifont libfontconfig1 libfreetype6 \
    xfonts-cyrillic xfonts-scalable fonts-liberation fonts-ipafont-gothic \
    fonts-wqy-zenhei fonts-tlwg-loma-otf fonts-freefont-ttf 2>/dev/null || true

echo "  Installing Playwright Python package..."
pip3 install --ignore-installed playwright --break-system-packages 2>&1 || \
pip3 install --ignore-installed playwright 2>&1 || true

echo "  Installing Chromium browser for Playwright..."
su - ${CLAUDE_USER} -c "playwright install chromium" 2>/dev/null || \
playwright install chromium 2>/dev/null || true

if su - ${CLAUDE_USER} -c "python3 -c 'from playwright.sync_api import sync_playwright'" 2>/dev/null; then
    echo -e "${GREEN}  ✓ Playwright installed${NC}"
else
    echo -e "${YELLOW}  ⚠ Playwright may need manual setup: playwright install chromium${NC}"
fi

# =====================================================
# [7/12] CLAUDE CODE CLI
# =====================================================
echo -e "${YELLOW}[7/12] Installing Claude Code CLI...${NC}"

# Install for claude user
su - ${CLAUDE_USER} -c 'curl -fsSL https://claude.ai/install.sh | bash' 2>/dev/null || true

# Add to PATH if not already
if ! su - ${CLAUDE_USER} -c 'grep -q "\.local/bin" ~/.bashrc' 2>/dev/null; then
    su - ${CLAUDE_USER} -c 'echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> ~/.bashrc'
fi

# Check if installed
if su - ${CLAUDE_USER} -c 'which claude' &>/dev/null; then
    CLAUDE_VERSION=$(su - ${CLAUDE_USER} -c 'claude --version 2>/dev/null' | head -1)
    echo -e "${GREEN}  ✓ Claude Code CLI installed: ${CLAUDE_VERSION}${NC}"
else
    echo -e "${YELLOW}  ⚠ Claude Code CLI not found - install manually later${NC}"
    echo "    Run as ${CLAUDE_USER}: curl -fsSL https://claude.ai/install.sh | bash"
fi

# Configure MCP Server for Claude Code
echo "  Configuring MCP server for Claude Code..."
CLAUDE_CONFIG="/home/${CLAUDE_USER}/.claude.json"

# Create or update .claude.json with MCP server config
if [ -f "${CLAUDE_CONFIG}" ]; then
    # Config exists - add MCP servers if not present
    if ! grep -q '"mcpServers"' "${CLAUDE_CONFIG}" 2>/dev/null; then
        # Add mcpServers to existing config (before last closing brace)
        python3 << PYEOF
import json
with open('${CLAUDE_CONFIG}', 'r') as f:
    config = json.load(f)
config['mcpServers'] = {
    'codehero': {
        'type': 'stdio',
        'command': 'python3',
        'args': ['${INSTALL_DIR}/scripts/mcp_server.py'],
        'env': {}
    }
}
with open('${CLAUDE_CONFIG}', 'w') as f:
    json.dump(config, f, indent=2)
PYEOF
        echo -e "${GREEN}  ✓ MCP server added to existing config${NC}"
    else
        echo "  MCP server already configured"
    fi
else
    # Create new config with MCP servers
    cat > "${CLAUDE_CONFIG}" << MCPEOF
{
  "mcpServers": {
    "codehero": {
      "type": "stdio",
      "command": "python3",
      "args": ["${INSTALL_DIR}/scripts/mcp_server.py"],
      "env": {}
    }
  }
}
MCPEOF
    echo -e "${GREEN}  ✓ MCP config created${NC}"
fi

chown ${CLAUDE_USER}:${CLAUDE_USER} "${CLAUDE_CONFIG}"
chmod 644 "${CLAUDE_CONFIG}"

# Also create project-level CLAUDE.md for Claude Code
CLAUDE_HOME_MD="/home/${CLAUDE_USER}/CLAUDE.md"
cat > "${CLAUDE_HOME_MD}" << 'CLAUDEMDEOF'
# CodeHero Assistant

You are the CodeHero platform assistant. You help users manage their projects and development tasks.

## Your Tools

You have special tools to manage the platform. **Use them proactively when users ask about projects or tickets!**

| Tool | What it does | When to use |
|------|--------------|-------------|
| `codehero_list_projects` | Shows all projects | "What projects do I have?", "Show me my projects" |
| `codehero_get_project` | Gets project details | "Tell me about project X" |
| `codehero_create_project` | Creates a new project | "Create a project" |
| `codehero_list_tickets` | Shows tickets | "What tickets are open?" |
| `codehero_get_ticket` | Gets ticket details | "Show ticket X" |
| `codehero_create_ticket` | Creates a ticket | "Create a ticket" |
| `codehero_update_ticket` | Updates a ticket | "Close ticket X" |
| `codehero_kill_switch` | Stop a running ticket | "Stop ticket X", "Kill switch" |
| `codehero_dashboard_stats` | Platform overview | "Give me a summary" |

## Execution Modes

Tickets can run in two modes:
- **autonomous** - Full access, no permission prompts (default)
- **supervised** - Asks for user approval before write/edit/bash operations

When creating tickets, ask: **"Supervised or autonomous?"**

Use `execution_mode` parameter in `codehero_create_ticket`:
```
execution_mode: "supervised"  // or "autonomous" or omit to inherit from project
```

## Relaxed Mode

When creating multiple tickets, ask: **"Relaxed or strict?"**

| User says | Set `deps_include_awaiting` to |
|-----------|-------------------------------|
| "relaxed" | `true` |
| "strict" or nothing | `false` (default) |

**Simple rule:** "relaxed" → `true`, "strict" → `false`

## How to Help Users

1. **When user asks about projects** → Use `codehero_list_projects` first
2. **When user wants to create something** → Use `codehero_create_project` or `codehero_create_ticket`
3. **When user asks about status** → Use `codehero_dashboard_stats`
4. **When creating tickets** → Ask: "Supervised or autonomous?"
5. **When creating multiple tickets** → Ask: "Relaxed or strict?"

## Project Paths

**IMPORTANT:** Always use the correct default paths when creating projects:

| Project Type | Default Path |
|--------------|--------------|
| `web` (PHP, HTML) | `/var/www/projects/{project_name}` |
| `app`, `api`, `cli`, `library` | `/opt/apps/{project_name}` |

Use `web_path` for web projects and `app_path` for app projects:
```
web_path: "/var/www/projects/myproject"   // for web/PHP projects
app_path: "/opt/apps/myproject"           // for app/api/node projects
```

**Example:**
- PHP e-shop → `web_path: "/var/www/projects/eshop"`
- Node.js API → `app_path: "/opt/apps/myapi"`
- React Native app → `app_path: "/opt/apps/myapp"`

## Example Conversations

**User:** "Show me my projects"
**You:** Use `codehero_list_projects` and show results nicely

**User:** "Create an e-shop project with PHP"
**You:** Use `codehero_create_project` with name="E-Shop", project_type="web", tech_stack="php", web_path="/var/www/projects/eshop"

**User:** "Add a ticket to create login page"
**You:** First ask "Supervised or autonomous?", then use `codehero_create_ticket` with the chosen `execution_mode`

**User:** "Create a ticket to add dark mode, supervised"
**You:** Use `codehero_create_ticket` with `execution_mode: "supervised"`

## Language

Users may speak Greek or English. Respond in the same language they use.
CLAUDEMDEOF

chown ${CLAUDE_USER}:${CLAUDE_USER} "${CLAUDE_HOME_MD}"
chmod 644 "${CLAUDE_HOME_MD}"
echo -e "${GREEN}  ✓ CLAUDE.md created in home folder${NC}"

# =====================================================
# [8/12] MYSQL DATABASE SETUP
# =====================================================
echo -e "${YELLOW}[8/12] Configuring MySQL database...${NC}"

mkdir -p ${CONFIG_DIR}
systemctl start mysql 2>/dev/null || service mysql start || true
sleep 3

# Try to connect to MySQL
MYSQL_CONNECTED=false
MYSQL_CMD=""

# Method 1: Socket auth
if mysql -e "SELECT 1" 2>/dev/null; then
    MYSQL_CMD="mysql"
    MYSQL_CONNECTED=true
    mysql -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASSWORD}';" 2>/dev/null || true
    mysql -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    MYSQL_CMD="mysql -u root -p${MYSQL_ROOT_PASSWORD}"
fi

# Method 2: Password auth
if [ "$MYSQL_CONNECTED" = false ]; then
    if mysql -u root -p"${MYSQL_ROOT_PASSWORD}" -e "SELECT 1" 2>/dev/null; then
        MYSQL_CMD="mysql -u root -p${MYSQL_ROOT_PASSWORD}"
        MYSQL_CONNECTED=true
    fi
fi

# Method 3: debian-sys-maint
if [ "$MYSQL_CONNECTED" = false ] && [ -f /etc/mysql/debian.cnf ]; then
    if mysql --defaults-file=/etc/mysql/debian.cnf -e "SELECT 1" 2>/dev/null; then
        mysql --defaults-file=/etc/mysql/debian.cnf -e "ALTER USER 'root'@'localhost' IDENTIFIED WITH mysql_native_password BY '${MYSQL_ROOT_PASSWORD}';" 2>/dev/null || true
        MYSQL_CMD="mysql -u root -p${MYSQL_ROOT_PASSWORD}"
        MYSQL_CONNECTED=true
    fi
fi

if [ "$MYSQL_CONNECTED" = true ]; then
    # Check if database already exists
    DB_EXISTS=$($MYSQL_CMD -N -e "SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME='${DB_NAME}'" 2>/dev/null)

    if [ "$DB_EXISTS" = "1" ]; then
        echo -e "${GREEN}Database '${DB_NAME}' already exists - keeping existing data${NC}"
        $MYSQL_CMD -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';" 2>/dev/null || true
        $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';" 2>/dev/null || true
        $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON *.* TO '${DB_USER}'@'localhost' WITH GRANT OPTION;" 2>/dev/null || true
        $MYSQL_CMD -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    else
        echo "Creating new database..."
        $MYSQL_CMD -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};" 2>/dev/null || true
        $MYSQL_CMD -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';" 2>/dev/null || true
        $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';" 2>/dev/null || true
        $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON *.* TO '${DB_USER}'@'localhost' WITH GRANT OPTION;" 2>/dev/null || true
        $MYSQL_CMD -e "FLUSH PRIVILEGES;" 2>/dev/null || true

        # Import schema only for NEW database
        if [ -f "${SCRIPT_DIR}/database/schema.sql" ]; then
            $MYSQL_CMD ${DB_NAME} < "${SCRIPT_DIR}/database/schema.sql" 2>/dev/null || true
            echo "Database schema imported"

            ADMIN_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw('${ADMIN_PASSWORD}'.encode(), bcrypt.gensalt()).decode())" 2>/dev/null)
            if [ -n "$ADMIN_HASH" ]; then
                $MYSQL_CMD ${DB_NAME} -e "UPDATE developers SET username='${ADMIN_USER}', password_hash='${ADMIN_HASH}' WHERE id=1;" 2>/dev/null || true
                echo "Admin credentials set from install.conf"
            fi
        fi
    fi
    echo -e "${GREEN}Database configured${NC}"
else
    echo -e "${RED}WARNING: Could not configure MySQL automatically${NC}"
fi

# =====================================================
# [9/12] SSL CERTIFICATE
# =====================================================
echo -e "${YELLOW}[9/12] Generating SSL certificate...${NC}"
mkdir -p ${CONFIG_DIR}/ssl

if [ -f "${SSL_CERT}" ] && [ -f "${SSL_KEY}" ]; then
    echo "SSL certificate already exists"
else
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${SSL_KEY}" \
        -out "${SSL_CERT}" \
        -subj "/C=GR/ST=Athens/L=Athens/O=CodeHero/CN=codehero" 2>/dev/null || true
    chmod 600 "${SSL_KEY}"
    chmod 644 "${SSL_CERT}"
    echo "SSL certificate generated"
fi

# =====================================================
# [10/12] DIRECTORIES & FILES
# =====================================================
echo -e "${YELLOW}[10/12] Setting up directories and copying files...${NC}"

# Create directories
mkdir -p ${WEB_ROOT}
mkdir -p ${APP_ROOT}
mkdir -p ${INSTALL_DIR}/scripts
mkdir -p ${INSTALL_DIR}/web/templates
mkdir -p ${INSTALL_DIR}/web/static
mkdir -p ${INSTALL_DIR}/references
mkdir -p ${LOG_DIR}
mkdir -p /var/run/codehero
mkdir -p /var/backups/codehero
mkdir -p /var/backups/codehero/deleted-projects

# Create tmpfiles.d config
cat > /etc/tmpfiles.d/codehero.conf << TMPEOF
d /var/run/codehero 0755 ${CLAUDE_USER} ${CLAUDE_USER} -
TMPEOF

# Copy application files
echo "Copying files to ${INSTALL_DIR}..."
cp "${SCRIPT_DIR}/scripts/"*.py ${INSTALL_DIR}/scripts/ 2>/dev/null || true
cp "${SCRIPT_DIR}/scripts/"*.sh ${INSTALL_DIR}/scripts/ 2>/dev/null || true
cp "${SCRIPT_DIR}/web/app.py" ${INSTALL_DIR}/web/ 2>/dev/null || true
cp "${SCRIPT_DIR}/web/templates/"*.html ${INSTALL_DIR}/web/templates/ 2>/dev/null || true
cp -r "${SCRIPT_DIR}/web/static/"* ${INSTALL_DIR}/web/static/ 2>/dev/null || true

# Copy config files
mkdir -p ${INSTALL_DIR}/config
cp "${SCRIPT_DIR}/config/"*.md ${CONFIG_DIR}/ 2>/dev/null || true
cp "${SCRIPT_DIR}/config/"*.md ${INSTALL_DIR}/config/ 2>/dev/null || true

# Copy documentation files
mkdir -p ${INSTALL_DIR}/docs
cp -r "${SCRIPT_DIR}/docs/"* ${INSTALL_DIR}/docs/ 2>/dev/null || true
cp "${SCRIPT_DIR}/CLAUDE_OPERATIONS.md" ${INSTALL_DIR}/ 2>/dev/null || true
cp "${SCRIPT_DIR}/CLAUDE_DEV_NOTES.md" ${INSTALL_DIR}/ 2>/dev/null || true
cp "${SCRIPT_DIR}/CLAUDE.md" ${INSTALL_DIR}/ 2>/dev/null || true
cp "${SCRIPT_DIR}/README.md" ${INSTALL_DIR}/ 2>/dev/null || true
cp "${SCRIPT_DIR}/CHANGELOG.md" ${INSTALL_DIR}/ 2>/dev/null || true
cp "${SCRIPT_DIR}/VERSION" ${INSTALL_DIR}/ 2>/dev/null || true

chmod +x ${INSTALL_DIR}/scripts/*.py 2>/dev/null || true
chmod +x ${INSTALL_DIR}/scripts/*.sh 2>/dev/null || true

# Set ownership
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${WEB_ROOT}
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${APP_ROOT}
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${INSTALL_DIR}
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${INSTALL_DIR}/references
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${LOG_DIR}
touch ${LOG_DIR}/daemon.log ${LOG_DIR}/web.log
chown ${CLAUDE_USER}:${CLAUDE_USER} ${LOG_DIR}/daemon.log ${LOG_DIR}/web.log
chown -R ${CLAUDE_USER}:${CLAUDE_USER} /var/run/codehero
chown -R ${CLAUDE_USER}:${CLAUDE_USER} /var/backups/codehero
chown -R ${CLAUDE_USER}:${CLAUDE_USER} /home/${CLAUDE_USER}
chmod 2775 ${WEB_ROOT}

# Create default index
cat > ${WEB_ROOT}/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
    <title>CodeHero - Projects</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; padding: 40px; }
        h1 { color: #00d9ff; }
        .info { background: #16213e; padding: 20px; border-radius: 10px; margin-top: 20px; }
        code { background: #0d0d1a; padding: 3px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>CodeHero - Projects</h1>
    <div class="info">
        <p>Project URL: <code>https://server:9867/PROJECT_CODE/</code></p>
    </div>
</body>
</html>
HTMLEOF
chown ${CLAUDE_USER}:${CLAUDE_USER} ${WEB_ROOT}/index.html

# Create symlink for CLI
ln -sf ${INSTALL_DIR}/scripts/claude-cli.py /usr/local/bin/claude-cli

# =====================================================
# [11/12] NGINX & CONFIGURATION FILES
# =====================================================
echo -e "${YELLOW}[11/12] Configuring Nginx and creating config files...${NC}"

# Create Nginx site configs
cat > /etc/nginx/sites-available/codehero-admin << 'NGINXADMIN'
# CodeHero Admin Panel - Port 9453 (HTTPS)
server {
    listen 9453 ssl http2;
    listen [::]:9453 ssl http2;
    server_name _;

    ssl_certificate /etc/codehero/ssl/cert.pem;
    ssl_certificate_key /etc/codehero/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    access_log /var/log/nginx/codehero-admin-access.log;
    error_log /var/log/nginx/codehero-admin-error.log;
    client_max_body_size 500M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
    }

    location /android/ {
        proxy_pass https://127.0.0.1:8443/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_ssl_verify off;
        proxy_read_timeout 86400s;
    }

    location = /android {
        return 301 /android/;
    }
}
NGINXADMIN

cat > /etc/nginx/sites-available/codehero-projects << 'NGINXPROJECTS'
# CodeHero Web Projects - Port 9867 (HTTPS)
server {
    listen 9867 ssl http2;
    listen [::]:9867 ssl http2;
    server_name _;

    ssl_certificate /etc/codehero/ssl/cert.pem;
    ssl_certificate_key /etc/codehero/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    root /var/www/projects;
    index index.html index.php;

    access_log /var/log/nginx/codehero-projects-access.log;
    error_log /var/log/nginx/codehero-projects-error.log;
    client_max_body_size 500M;

    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    location / {
        try_files $uri $uri/ /index.php?$query_string;
    }

    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.3-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $realpath_root$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_read_timeout 300s;
    }

    location ~ /\.ht {
        deny all;
    }

    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }
}
NGINXPROJECTS

# phpMyAdmin nginx configuration (port 9454) - only if phpMyAdmin installed
if [ -d /usr/share/phpmyadmin ]; then
    cat > /etc/nginx/sites-available/codehero-phpmyadmin << 'NGINXPMA' || true
# CodeHero phpMyAdmin - Database Administration
# Port: 9454 (HTTPS)

server {
    listen 9454 ssl http2;
    server_name _;

    ssl_certificate /etc/codehero/ssl/cert.pem;
    ssl_certificate_key /etc/codehero/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;

    root /usr/share/phpmyadmin;
    index index.php index.html;

    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;

    location / {
        try_files $uri $uri/ /index.php?$args;
    }

    location ~ \.php$ {
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/php8.3-fpm.sock;
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
    }

    location ~ /\.ht {
        deny all;
    }

    location /setup {
        deny all;
    }
}
NGINXPMA
    ln -sf /etc/nginx/sites-available/codehero-phpmyadmin /etc/nginx/sites-enabled/ || true
fi

# Enable sites
ln -sf /etc/nginx/sites-available/codehero-admin /etc/nginx/sites-enabled/
ln -sf /etc/nginx/sites-available/codehero-projects /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

nginx -t 2>/dev/null && echo -e "${GREEN}Nginx configuration valid${NC}" || echo -e "${RED}Nginx configuration error${NC}"

# Main system config
cat > ${CONFIG_DIR}/system.conf << CONFEOF
# CodeHero Configuration - Generated: $(date)
DB_HOST=${DB_HOST}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}
WEB_HOST=${FLASK_HOST}
WEB_PORT=${FLASK_PORT}
SECRET_KEY=${SECRET_KEY}
ADMIN_PORT=${ADMIN_PORT}
PROJECTS_PORT=${PROJECTS_PORT}
SSL_CERT=${SSL_CERT}
SSL_KEY=${SSL_KEY}
INSTALL_DIR=${INSTALL_DIR}
WEB_ROOT=${WEB_ROOT}
APP_ROOT=${APP_ROOT}
MAX_PARALLEL_PROJECTS=${MAX_PARALLEL_PROJECTS}
REVIEW_DEADLINE_DAYS=${REVIEW_DEADLINE_DAYS}
AUTO_REVIEW_DELAY_MINUTES=${AUTO_REVIEW_DELAY_MINUTES}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN:-}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID:-}
NOTIFY_TICKET_COMPLETED=${NOTIFY_TICKET_COMPLETED:-yes}
NOTIFY_AWAITING_INPUT=${NOTIFY_AWAITING_INPUT:-yes}
NOTIFY_TICKET_FAILED=${NOTIFY_TICKET_FAILED:-yes}
NOTIFY_WATCHDOG_ALERT=${NOTIFY_WATCHDOG_ALERT:-yes}
CONFEOF
chmod 644 ${CONFIG_DIR}/system.conf
chown ${CLAUDE_USER}:${CLAUDE_USER} ${CONFIG_DIR}/system.conf

# Credentials file
cat > ${CONFIG_DIR}/credentials.conf << CREDEOF
# CODEHERO Credentials - Generated: $(date)
MYSQL_ROOT_USER=root
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}
MYSQL_APP_USER=${DB_USER}
MYSQL_APP_PASSWORD=${DB_PASSWORD}
MYSQL_DATABASE=${DB_NAME}
ADMIN_USER=${ADMIN_USER}
ADMIN_PASSWORD=${ADMIN_PASSWORD}
CLAUDE_USER=${CLAUDE_USER}
# URLs: https://YOUR_IP:${ADMIN_PORT} | https://YOUR_IP:${PROJECTS_PORT}
CREDEOF
chmod 600 ${CONFIG_DIR}/credentials.conf
chown root:root ${CONFIG_DIR}/credentials.conf

# =====================================================
# [12/12] SYSTEMD SERVICES
# =====================================================
echo -e "${YELLOW}[12/12] Setting up systemd services...${NC}"

# Web Service
cat > /etc/systemd/system/codehero-web.service << SVCEOF
[Unit]
Description=CodeHero Web Interface
After=network.target mysql.service
Wants=mysql.service

[Service]
Type=simple
User=${CLAUDE_USER}
Group=${CLAUDE_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/web/app.py
ExecStopPost=/bin/bash -c 'fuser -k 5000/tcp 2>/dev/null || true'
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/web.log
StandardError=append:${LOG_DIR}/web.log
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SVCEOF

# Daemon Service
cat > /etc/systemd/system/codehero-daemon.service << SVCEOF
[Unit]
Description=CodeHero Daemon
After=network.target mysql.service codehero-web.service
Wants=mysql.service

[Service]
Type=simple
User=${CLAUDE_USER}
Group=${CLAUDE_USER}
WorkingDirectory=${INSTALL_DIR}
ExecStartPre=/bin/mkdir -p /var/run/codehero
ExecStartPre=/bin/chown ${CLAUDE_USER}:${CLAUDE_USER} /var/run/codehero
ExecStart=/usr/bin/python3 ${INSTALL_DIR}/scripts/claude-daemon.py
Restart=always
RestartSec=5
StandardOutput=append:${LOG_DIR}/daemon.log
StandardError=append:${LOG_DIR}/daemon.log
Environment=PYTHONUNBUFFERED=1
Environment=PATH=/home/${CLAUDE_USER}/.local/bin:/usr/local/bin:/usr/bin:/bin
Environment=HOME=/home/${CLAUDE_USER}

[Install]
WantedBy=multi-user.target
SVCEOF

systemctl daemon-reload

# Enable auto-start on boot
if [ "${ENABLE_AUTOSTART}" = "yes" ]; then
    systemctl enable mysql 2>/dev/null || true
    systemctl enable codehero-web 2>/dev/null || true
    systemctl enable codehero-daemon 2>/dev/null || true
    systemctl enable nginx 2>/dev/null || true
    systemctl enable php8.3-fpm 2>/dev/null || true
    echo -e "${GREEN}Auto-start enabled for all services${NC}"
fi

# =====================================================
# START SERVICES
# =====================================================
echo -e "${CYAN}Starting services...${NC}"

systemctl start mysql 2>/dev/null || true
systemctl restart php8.3-fpm 2>/dev/null || true
systemctl restart codehero-web 2>/dev/null || true
systemctl restart nginx 2>/dev/null || true
systemctl restart codehero-daemon 2>/dev/null || true

sleep 3

# =====================================================
# STATUS CHECK
# =====================================================
echo ""
echo "Service Status:"
pgrep -f "app.py" > /dev/null && echo -e "  Flask Web:       ${GREEN}running${NC}" || echo -e "  Flask Web:       ${RED}not running${NC}"
pgrep -f "claude-daemon" > /dev/null && echo -e "  Daemon:          ${GREEN}running${NC}" || echo -e "  Daemon:          ${YELLOW}stopped${NC}"
systemctl is-active nginx > /dev/null 2>&1 && echo -e "  Nginx:           ${GREEN}running${NC}" || echo -e "  Nginx:           ${RED}not running${NC}"
systemctl is-active php8.3-fpm > /dev/null 2>&1 && echo -e "  PHP-FPM:         ${GREEN}running${NC}" || echo -e "  PHP-FPM:         ${RED}not running${NC}"
systemctl is-active mysql > /dev/null 2>&1 && echo -e "  MySQL:           ${GREEN}running${NC}" || echo -e "  MySQL:           ${YELLOW}check status${NC}"
su - ${CLAUDE_USER} -c 'which claude' &>/dev/null && echo -e "  Claude CLI:      ${GREEN}installed${NC}" || echo -e "  Claude CLI:      ${YELLOW}not found${NC}"

SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗"
echo "║              CORE INSTALLATION COMPLETE!                    ║"
echo "╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}URLs:${NC}"
echo -e "  Admin Panel:     ${GREEN}https://${SERVER_IP}:${ADMIN_PORT}${NC}"
echo -e "  Web Projects:    ${GREEN}https://${SERVER_IP}:${PROJECTS_PORT}${NC}"
echo ""
echo -e "${CYAN}Credentials:${NC}"
echo "  Admin Panel:     ${ADMIN_USER} / ${ADMIN_PASSWORD}"
echo "  MySQL Root:      root / ${MYSQL_ROOT_PASSWORD}"
echo "  MySQL App:       ${DB_USER} / ${DB_PASSWORD}"
echo ""
echo -e "${CYAN}System User:${NC}"
echo "  Username:        ${CLAUDE_USER}"
echo "  Sudo:            passwordless (sudo su - ${CLAUDE_USER})"
echo ""
echo -e "${YELLOW}All credentials saved to:${NC}"
echo "  ${CONFIG_DIR}/credentials.conf"
echo ""
echo -e "${CYAN}To activate Claude Code:${NC}"
echo "  Go to Admin Panel -> Click 'Activate Claude' button"
echo ""
echo -e "${YELLOW}To install development tools (Node.js, Java, Playwright):${NC}"
echo "  sudo ./setup_devtools.sh"
echo ""
echo -e "${YELLOW}Services will auto-start on reboot.${NC}"
echo ""
