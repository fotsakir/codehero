#!/bin/bash
# =====================================================
# FOTIOS CLAUDE SYSTEM - Installation Script
# Version is read from VERSION file
# =====================================================
# Usage:
#   sudo ./setup.sh          (from root or with sudo)
#   sudo su -> ./setup.sh    (switch to root first)
#
# Configuration:
#   Edit install.conf before running to customize
#   passwords, ports, and directories.
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
echo "║       FOTIOS CLAUDE SYSTEM - Installation                 ║"
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
OLS_ADMIN_USER="${OLS_ADMIN_USER:-admin}"
OLS_ADMIN_PASSWORD="${OLS_ADMIN_PASSWORD:-123456}"
FLASK_HOST="${FLASK_HOST:-127.0.0.1}"
FLASK_PORT="${FLASK_PORT:-5000}"
ADMIN_PORT="${ADMIN_PORT:-9453}"
PROJECTS_PORT="${PROJECTS_PORT:-9867}"
OLS_WEBADMIN_PORT="${OLS_WEBADMIN_PORT:-7080}"
INSTALL_DIR="${INSTALL_DIR:-/opt/fotios-claude}"
CONFIG_DIR="${CONFIG_DIR:-/etc/fotios-claude}"
LOG_DIR="${LOG_DIR:-/var/log/fotios-claude}"
WEB_ROOT="${WEB_ROOT:-/var/www/projects}"
APP_ROOT="${APP_ROOT:-/opt/apps}"
MAX_PARALLEL_PROJECTS="${MAX_PARALLEL_PROJECTS:-3}"
REVIEW_DEADLINE_DAYS="${REVIEW_DEADLINE_DAYS:-7}"
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
# [1/14] CREATE CLAUDE USER
# =====================================================
echo -e "${YELLOW}[1/14] Setting up ${CLAUDE_USER} user with sudo access...${NC}"

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
# [2/14] SYSTEM DEPENDENCIES
# =====================================================
echo -e "${YELLOW}[2/14] Installing system dependencies...${NC}"
apt-get update || true
apt-get install -y python3 python3-pip openssl sudo wget curl gnupg lsb-release git || true

# Multimedia & Processing Tools (for AI capabilities)
echo "Installing multimedia tools..."
apt-get install -y ffmpeg imagemagick tesseract-ocr tesseract-ocr-eng tesseract-ocr-ell \
    poppler-utils ghostscript sox mediainfo webp optipng jpegoptim \
    librsvg2-bin libvips-tools qpdf || true

# Python multimedia libraries
pip3 install --ignore-installed Pillow opencv-python-headless pydub pytesseract pdf2image --break-system-packages 2>&1 || \
pip3 install --ignore-installed Pillow opencv-python-headless pydub pytesseract pdf2image 2>&1 || true

# =====================================================
# [3/14] MYSQL
# =====================================================
echo -e "${YELLOW}[3/14] Setting up MySQL...${NC}"

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
# [4/14] OPENLITESPEED
# =====================================================
echo -e "${YELLOW}[4/14] Setting up OpenLiteSpeed...${NC}"

if [ -d /usr/local/lsws ] && [ -f /usr/local/lsws/bin/lshttpd ]; then
    echo "OpenLiteSpeed already installed"
else
    if [ ! -f /etc/apt/sources.list.d/lst_debian_repo.list ]; then
        wget -qO - https://repo.litespeed.sh | bash || true
    fi
    apt-get install -y openlitespeed || true
fi

# =====================================================
# [5/14] LSPHP
# =====================================================
echo -e "${YELLOW}[5/14] Installing LSPHP (PHP 8.3 + 8.4)...${NC}"

if [ ! -f /usr/local/lsws/lsphp83/bin/lsphp ]; then
    apt-get install -y lsphp83 lsphp83-common lsphp83-mysql lsphp83-curl lsphp83-intl lsphp83-opcache lsphp83-redis lsphp83-imagick || true
fi

if [ ! -f /usr/local/lsws/lsphp84/bin/lsphp ]; then
    apt-get install -y lsphp84 lsphp84-common lsphp84-mysql lsphp84-curl lsphp84-intl lsphp84-opcache lsphp84-redis lsphp84-imagick || true
fi

mkdir -p /usr/local/lsws/fcgi-bin
ln -sf /usr/local/lsws/lsphp83/bin/lsphp /usr/local/lsws/fcgi-bin/lsphp83 2>/dev/null || true
ln -sf /usr/local/lsws/lsphp84/bin/lsphp /usr/local/lsws/fcgi-bin/lsphp84 2>/dev/null || true
ln -sf /usr/local/lsws/lsphp83/bin/lsphp /usr/local/lsws/fcgi-bin/lsphp 2>/dev/null || true

# =====================================================
# [6/14] PYTHON PACKAGES
# =====================================================
echo -e "${YELLOW}[6/14] Installing Python packages...${NC}"
pip3 install --ignore-installed flask flask-socketio flask-cors mysql-connector-python bcrypt eventlet --break-system-packages 2>&1 || \
pip3 install --ignore-installed flask flask-socketio flask-cors mysql-connector-python bcrypt eventlet 2>&1 || true

# Playwright and its system dependencies
echo "Installing Playwright dependencies..."
apt-get install -y --no-install-recommends \
    libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libatspi2.0-0t64 \
    libcairo2 libcups2t64 libdbus-1-3 libdrm2 libgbm1 libglib2.0-0t64 \
    libnspr4 libnss3 libpango-1.0-0 libx11-6 libxcb1 libxcomposite1 \
    libxdamage1 libxext6 libxfixes3 libxkbcommon0 libxrandr2 xvfb \
    fonts-noto-color-emoji fonts-unifont libfontconfig1 libfreetype6 \
    xfonts-cyrillic xfonts-scalable fonts-liberation fonts-ipafont-gothic \
    fonts-wqy-zenhei fonts-tlwg-loma-otf fonts-freefont-ttf 2>/dev/null || true

pip3 install --ignore-installed playwright --break-system-packages 2>&1 || pip3 install --ignore-installed playwright 2>&1 || true
su - ${CLAUDE_USER} -c "playwright install chromium" 2>/dev/null || playwright install chromium 2>/dev/null || true

# =====================================================
# [7/14] NODE.JS
# =====================================================
echo -e "${YELLOW}[7/14] Installing Node.js...${NC}"
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_22.x 2>/dev/null | bash - || true
    apt-get install -y nodejs || true
fi
node --version 2>/dev/null && echo "Node.js ready" || echo "Node.js skipped"

# =====================================================
# [8/14] GRAALVM (Java)
# =====================================================
echo -e "${YELLOW}[8/14] Installing GraalVM...${NC}"
GRAALVM_DIR="/opt/graalvm"
if [ ! -f "$GRAALVM_DIR/bin/java" ]; then
    cd /tmp
    if curl -fsSL "https://download.oracle.com/graalvm/24/latest/graalvm-jdk-24_linux-x64_bin.tar.gz" -o graalvm.tar.gz 2>/dev/null; then
        mkdir -p $GRAALVM_DIR
        tar -xzf graalvm.tar.gz -C $GRAALVM_DIR --strip-components=1 || true
        rm -f graalvm.tar.gz

        cat > /etc/profile.d/graalvm.sh << 'EOF'
export GRAALVM_HOME=/opt/graalvm
export JAVA_HOME=$GRAALVM_HOME
export PATH=$GRAALVM_HOME/bin:$PATH
EOF
        ln -sf $GRAALVM_DIR/bin/java /usr/local/bin/java 2>/dev/null || true
        ln -sf $GRAALVM_DIR/bin/javac /usr/local/bin/javac 2>/dev/null || true
    fi
fi
java --version 2>/dev/null | head -1 || echo "Java skipped"

# =====================================================
# [9/14] MYSQL DATABASE SETUP
# =====================================================
echo -e "${YELLOW}[9/14] Configuring MySQL database...${NC}"

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
        # Just ensure user has access
        $MYSQL_CMD -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';" 2>/dev/null || true
        $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';" 2>/dev/null || true
        # Grant ability to create databases for projects (auto-database feature)
        $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON *.* TO '${DB_USER}'@'localhost' WITH GRANT OPTION;" 2>/dev/null || true
        $MYSQL_CMD -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    else
        echo "Creating new database..."
        $MYSQL_CMD -e "CREATE DATABASE IF NOT EXISTS ${DB_NAME};" 2>/dev/null || true
        $MYSQL_CMD -e "CREATE USER IF NOT EXISTS '${DB_USER}'@'localhost' IDENTIFIED BY '${DB_PASSWORD}';" 2>/dev/null || true
        $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON ${DB_NAME}.* TO '${DB_USER}'@'localhost';" 2>/dev/null || true
        # Grant ability to create databases for projects (auto-database feature)
        $MYSQL_CMD -e "GRANT ALL PRIVILEGES ON *.* TO '${DB_USER}'@'localhost' WITH GRANT OPTION;" 2>/dev/null || true
        $MYSQL_CMD -e "FLUSH PRIVILEGES;" 2>/dev/null || true

        # Import schema only for NEW database
        if [ -f "${SCRIPT_DIR}/database/schema.sql" ]; then
            $MYSQL_CMD ${DB_NAME} < "${SCRIPT_DIR}/database/schema.sql" 2>/dev/null || true
            echo "Database schema imported"

            # Update admin password from install.conf (schema has default hash)
            ADMIN_HASH=$(python3 -c "import bcrypt; print(bcrypt.hashpw('${ADMIN_PASSWORD}'.encode(), bcrypt.gensalt()).decode())" 2>/dev/null)
            if [ -n "$ADMIN_HASH" ]; then
                $MYSQL_CMD ${DB_NAME} -e "UPDATE developers SET username='${ADMIN_USER}', password_hash='${ADMIN_HASH}' WHERE id=1;" 2>/dev/null || true
                echo "Admin credentials set from install.conf"
            fi
        fi
    fi
    echo -e "${GREEN}Database configured (with CREATE DATABASE privileges)${NC}"
else
    echo -e "${RED}WARNING: Could not configure MySQL automatically${NC}"
fi

# =====================================================
# [10/14] SSL CERTIFICATE
# =====================================================
echo -e "${YELLOW}[10/14] Generating SSL certificate...${NC}"
mkdir -p ${CONFIG_DIR}/ssl

if [ -f "${SSL_CERT}" ] && [ -f "${SSL_KEY}" ]; then
    echo "SSL certificate already exists"
else
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "${SSL_KEY}" \
        -out "${SSL_CERT}" \
        -subj "/C=GR/ST=Athens/L=Athens/O=Fotios/CN=fotios-claude" 2>/dev/null || true
    chmod 600 "${SSL_KEY}"
    chmod 644 "${SSL_CERT}"
    echo "SSL certificate generated"
fi

# =====================================================
# [11/14] DIRECTORIES & FILES
# =====================================================
echo -e "${YELLOW}[11/14] Setting up directories and copying files...${NC}"

# Create directories
mkdir -p ${WEB_ROOT}
mkdir -p ${APP_ROOT}
mkdir -p ${INSTALL_DIR}/scripts
mkdir -p ${INSTALL_DIR}/web/templates
mkdir -p ${LOG_DIR}
mkdir -p /var/run/fotios-claude
mkdir -p /var/backups/fotios-claude

# Create tmpfiles.d config so /var/run/fotios-claude persists across reboots
cat > /etc/tmpfiles.d/fotios-claude.conf << TMPEOF
# Create runtime directory for Fotios Claude System
d /var/run/fotios-claude 0755 ${CLAUDE_USER} ${CLAUDE_USER} -
TMPEOF

# Copy application files
echo "Copying files to ${INSTALL_DIR}..."
cp "${SCRIPT_DIR}/scripts/"*.py ${INSTALL_DIR}/scripts/ 2>/dev/null || true
cp "${SCRIPT_DIR}/scripts/"*.sh ${INSTALL_DIR}/scripts/ 2>/dev/null || true
cp "${SCRIPT_DIR}/web/app.py" ${INSTALL_DIR}/web/ 2>/dev/null || true
cp "${SCRIPT_DIR}/web/templates/"*.html ${INSTALL_DIR}/web/templates/ 2>/dev/null || true

# Copy config files for Claude (global context, knowledge base, templates)
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
echo "  Documentation and knowledge files copied"

chmod +x ${INSTALL_DIR}/scripts/*.py 2>/dev/null || true
chmod +x ${INSTALL_DIR}/scripts/*.sh 2>/dev/null || true

# Set ownership
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${WEB_ROOT}
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${APP_ROOT}
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${INSTALL_DIR}
chown -R ${CLAUDE_USER}:${CLAUDE_USER} ${LOG_DIR}
# Pre-create log files with correct ownership (systemd creates as root otherwise)
touch ${LOG_DIR}/daemon.log ${LOG_DIR}/web.log
chown ${CLAUDE_USER}:${CLAUDE_USER} ${LOG_DIR}/daemon.log ${LOG_DIR}/web.log
chown -R ${CLAUDE_USER}:${CLAUDE_USER} /var/run/fotios-claude
chown -R ${CLAUDE_USER}:${CLAUDE_USER} /var/backups/fotios-claude
chown -R ${CLAUDE_USER}:${CLAUDE_USER} /home/${CLAUDE_USER}
chmod 2775 ${WEB_ROOT}

# Create default index
cat > ${WEB_ROOT}/index.html << 'HTMLEOF'
<!DOCTYPE html>
<html>
<head>
    <title>Fotios Claude - Projects</title>
    <style>
        body { font-family: -apple-system, sans-serif; background: #1a1a2e; color: #eee; padding: 40px; }
        h1 { color: #00d9ff; }
        .info { background: #16213e; padding: 20px; border-radius: 10px; margin-top: 20px; }
        code { background: #0d0d1a; padding: 3px 8px; border-radius: 4px; }
    </style>
</head>
<body>
    <h1>Fotios Claude - Projects</h1>
    <div class="info">
        <p>Project URL: <code>https://server:${PROJECTS_PORT}/PROJECT_CODE/</code></p>
    </div>
</body>
</html>
HTMLEOF
chown ${CLAUDE_USER}:${CLAUDE_USER} ${WEB_ROOT}/index.html

# Create symlink for CLI
ln -sf ${INSTALL_DIR}/scripts/claude-cli.py /usr/local/bin/claude-cli

# =====================================================
# [12/14] OPENLITESPEED CONFIGURATION
# =====================================================
echo -e "${YELLOW}[12/14] Configuring OpenLiteSpeed...${NC}"

cp /usr/local/lsws/conf/httpd_config.conf /usr/local/lsws/conf/httpd_config.conf.bak 2>/dev/null || true

mkdir -p /usr/local/lsws/conf/vhosts/vhost-admin
mkdir -p /usr/local/lsws/conf/vhosts/vhost-projects

cp "${SCRIPT_DIR}/openlitespeed/httpd_config.conf" /usr/local/lsws/conf/httpd_config.conf
cp "${SCRIPT_DIR}/openlitespeed/vhost-admin.conf" /usr/local/lsws/conf/vhosts/vhost-admin/vhconf.conf
cp "${SCRIPT_DIR}/openlitespeed/vhost-projects.conf" /usr/local/lsws/conf/vhosts/vhost-projects/vhconf.conf

chown -R lsadm:nogroup /usr/local/lsws/conf/
chmod -R 750 /usr/local/lsws/conf/

# Set OLS admin password
/usr/local/lsws/admin/misc/admpass.sh << OLSEOF
${OLS_ADMIN_USER}
${OLS_ADMIN_PASSWORD}
${OLS_ADMIN_PASSWORD}
OLSEOF


# =====================================================
# [13/14] CONFIGURATION FILES
# =====================================================
echo -e "${YELLOW}[13/14] Creating configuration files...${NC}"

# Main system config
cat > ${CONFIG_DIR}/system.conf << CONFEOF
# =====================================================
# Fotios Claude System Configuration
# Generated: $(date)
# Version: ${VERSION}
# =====================================================

# Database
DB_HOST=${DB_HOST}
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASSWORD}

# Flask Web Panel
WEB_HOST=${FLASK_HOST}
WEB_PORT=${FLASK_PORT}
SECRET_KEY=${SECRET_KEY}

# Ports
ADMIN_PORT=${ADMIN_PORT}
PROJECTS_PORT=${PROJECTS_PORT}

# SSL
SSL_CERT=${SSL_CERT}
SSL_KEY=${SSL_KEY}

# Directories
INSTALL_DIR=${INSTALL_DIR}
WEB_ROOT=${WEB_ROOT}
APP_ROOT=${APP_ROOT}

# Daemon Settings
MAX_PARALLEL_PROJECTS=${MAX_PARALLEL_PROJECTS}
REVIEW_DEADLINE_DAYS=${REVIEW_DEADLINE_DAYS}

# Telegram Notifications
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
# =====================================================
# FOTIOS CLAUDE SYSTEM - All Credentials
# Generated: $(date)
# =====================================================

# MySQL Root
MYSQL_ROOT_USER=root
MYSQL_ROOT_PASSWORD=${MYSQL_ROOT_PASSWORD}

# MySQL Application
MYSQL_APP_USER=${DB_USER}
MYSQL_APP_PASSWORD=${DB_PASSWORD}
MYSQL_DATABASE=${DB_NAME}

# Admin Panel (Flask) - https://IP:${ADMIN_PORT}
ADMIN_USER=${ADMIN_USER}
ADMIN_PASSWORD=${ADMIN_PASSWORD}

# OpenLiteSpeed WebAdmin - https://IP:${OLS_WEBADMIN_PORT}
OLS_ADMIN_USER=${OLS_ADMIN_USER}
OLS_ADMIN_PASSWORD=${OLS_ADMIN_PASSWORD}

# System User (passwordless sudo)
CLAUDE_USER=${CLAUDE_USER}

# =====================================================
# URLS
# =====================================================
# Admin Panel:     https://YOUR_IP:${ADMIN_PORT}
# Web Projects:    https://YOUR_IP:${PROJECTS_PORT}
# OLS WebAdmin:    https://YOUR_IP:${OLS_WEBADMIN_PORT}

# =====================================================
# FILE LOCATIONS
# =====================================================
# Application:     ${INSTALL_DIR}
# Config:          ${CONFIG_DIR}
# Logs:            ${LOG_DIR}
# Web Projects:    ${WEB_ROOT}
# App Projects:    ${APP_ROOT}
CREDEOF
chmod 600 ${CONFIG_DIR}/credentials.conf
chown root:root ${CONFIG_DIR}/credentials.conf

# =====================================================
# [14/14] SYSTEMD SERVICES
# =====================================================
echo -e "${YELLOW}[14/14] Setting up systemd services...${NC}"

# Web Service
cat > /etc/systemd/system/fotios-claude-web.service << SVCEOF
[Unit]
Description=Fotios Claude Web Interface
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
cat > /etc/systemd/system/fotios-claude-daemon.service << SVCEOF
[Unit]
Description=Fotios Claude Daemon
After=network.target mysql.service fotios-claude-web.service
Wants=mysql.service

[Service]
Type=simple
User=${CLAUDE_USER}
Group=${CLAUDE_USER}
WorkingDirectory=${INSTALL_DIR}
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
    systemctl enable fotios-claude-web 2>/dev/null || true
    systemctl enable fotios-claude-daemon 2>/dev/null || true
    systemctl enable lshttpd 2>/dev/null || true
    echo -e "${GREEN}Auto-start enabled for all services${NC}"
fi

# =====================================================
# START SERVICES
# =====================================================
echo -e "${CYAN}Starting services...${NC}"

systemctl start mysql 2>/dev/null || true
systemctl start fotios-claude-web 2>/dev/null || true
/usr/local/lsws/bin/lswsctrl stop 2>/dev/null || true
sleep 1
/usr/local/lsws/bin/lswsctrl start 2>/dev/null || true

# Start daemon
systemctl start fotios-claude-daemon 2>/dev/null || true

sleep 3

# =====================================================
# CLAUDE CODE CLI INSTALLATION
# =====================================================
echo ""
echo -e "${YELLOW}╔═══════════════════════════════════════════════════════════╗"
echo "║           CLAUDE CODE CLI                                 ║"
echo "╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Installing Claude Code CLI for user ${CLAUDE_USER}..."

# Install Claude Code CLI
if [ -f "${INSTALL_DIR}/scripts/install-claude-code.sh" ]; then
    chmod +x "${INSTALL_DIR}/scripts/install-claude-code.sh"
    # Run installation (without starting claude interactively)
    su - ${CLAUDE_USER} -c 'curl -fsSL https://claude.ai/install.sh | bash' 2>/dev/null || true
    # Add ~/.local/bin to PATH if not already there
    if ! su - ${CLAUDE_USER} -c 'grep -q "\.local/bin" ~/.bashrc' 2>/dev/null; then
        su - ${CLAUDE_USER} -c 'echo "export PATH=\"\$HOME/.local/bin:\$PATH\"" >> ~/.bashrc'
    fi
fi

# Check if installed
if su - ${CLAUDE_USER} -c 'which claude' &>/dev/null; then
    echo -e "${GREEN}Claude Code CLI installed successfully${NC}"
    CLAUDE_VERSION=$(su - ${CLAUDE_USER} -c 'claude --version 2>/dev/null' | head -1)
    echo -e "  Version: ${CYAN}${CLAUDE_VERSION}${NC}"
else
    echo -e "${YELLOW}Claude Code CLI installation skipped or failed${NC}"
    echo "  You can install manually later with:"
    echo -e "  ${CYAN}curl -fsSL https://claude.ai/install.sh | bash${NC}"
fi

echo ""
echo -e "${CYAN}Claude Activation:${NC}"
echo "  Activate Claude via the Admin Panel web interface."
echo "  Go to Admin Panel -> Click 'Activate Claude' button"
echo ""

# =====================================================
# STATUS CHECK
# =====================================================
echo ""
echo "Service Status:"
pgrep -f "app.py" > /dev/null && echo -e "  Flask Web:       ${GREEN}running${NC}" || echo -e "  Flask Web:       ${RED}not running${NC}"
pgrep -f "claude-daemon" > /dev/null && echo -e "  Daemon:          ${GREEN}running${NC}" || echo -e "  Daemon:          ${YELLOW}stopped${NC}"
pgrep -f "litespeed" > /dev/null && echo -e "  OpenLiteSpeed:   ${GREEN}running${NC}" || echo -e "  OpenLiteSpeed:   ${RED}not running${NC}"
systemctl is-active mysql > /dev/null 2>&1 && echo -e "  MySQL:           ${GREEN}running${NC}" || echo -e "  MySQL:           ${YELLOW}check status${NC}"

SERVER_IP=$(hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗"
echo "║              INSTALLATION COMPLETE!                       ║"
echo "╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}URLs:${NC}"
echo -e "  Admin Panel:     ${GREEN}https://${SERVER_IP}:${ADMIN_PORT}${NC}"
echo -e "  Web Projects:    ${GREEN}https://${SERVER_IP}:${PROJECTS_PORT}${NC}"
echo -e "  OLS WebAdmin:    ${GREEN}https://${SERVER_IP}:${OLS_WEBADMIN_PORT}${NC}"
echo ""
echo -e "${CYAN}Credentials:${NC}"
echo "  Admin Panel:     ${ADMIN_USER} / ${ADMIN_PASSWORD}"
echo "  OLS WebAdmin:    ${OLS_ADMIN_USER} / ${OLS_ADMIN_PASSWORD}"
echo "  MySQL Root:      root / ${MYSQL_ROOT_PASSWORD}"
echo "  MySQL App:       ${DB_USER} / ${DB_PASSWORD}"
echo ""
echo -e "${CYAN}System User:${NC}"
echo "  Username:        ${CLAUDE_USER}"
echo "  Sudo:            passwordless (sudo su - ${CLAUDE_USER})"
echo "  Home:            /home/${CLAUDE_USER}"
echo ""
echo -e "${CYAN}File Locations:${NC}"
echo "  Application:     ${INSTALL_DIR}"
echo "  Config:          ${CONFIG_DIR}"
echo "  Web Projects:    ${WEB_ROOT}"
echo ""
echo -e "${YELLOW}All credentials saved to:${NC}"
echo "  ${CONFIG_DIR}/credentials.conf"
echo ""
echo -e "${YELLOW}To change passwords later:${NC}"
echo "  sudo ${INSTALL_DIR}/scripts/change-passwords.sh"
echo ""
echo -e "${YELLOW}Services will auto-start on reboot.${NC}"
echo ""
