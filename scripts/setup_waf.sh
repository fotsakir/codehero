#!/bin/bash
# =====================================================
# CodeHero WAF Setup - ModSecurity with OWASP CRS
# =====================================================
# Installs and configures ModSecurity Web Application Firewall
# for Nginx with OWASP Core Rule Set (CRS) protection
#
# Protection includes:
# - SQL Injection
# - Cross-Site Scripting (XSS)
# - Local/Remote File Inclusion
# - Command Injection
# - And many more OWASP Top 10 attacks
# =====================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${CYAN}[WAF]${NC} $1"; }
log_success() { echo -e "${GREEN}[WAF]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WAF]${NC} $1"; }
log_error() { echo -e "${RED}[WAF]${NC} $1"; }

# Check root
if [ "$EUID" -ne 0 ]; then
    log_error "Please run as root (sudo $0)"
    exit 1
fi

echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     CodeHero WAF Setup - ModSecurity + OWASP CRS          ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  This will install:                                       ║"
echo "║  • ModSecurity 3.x for Nginx                              ║"
echo "║  • OWASP Core Rule Set (CRS) 3.3.5                        ║"
echo "║  • Custom CodeHero exclusions                             ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# =====================================================
# STEP 1: Install ModSecurity
# =====================================================
log_info "Installing ModSecurity and OWASP CRS..."

apt-get update -qq
apt-get install -y libmodsecurity3 libnginx-mod-http-modsecurity >/dev/null 2>&1

if ! dpkg -l | grep -q "libmodsecurity3"; then
    log_error "Failed to install ModSecurity"
    exit 1
fi

log_success "ModSecurity installed"

# =====================================================
# STEP 2: Copy base configuration
# =====================================================
log_info "Configuring ModSecurity..."

# Copy sample config if not exists
if [ ! -f /etc/modsecurity/modsecurity.conf ]; then
    cp /usr/share/nginx/docs/modsecurity/modsecurity.conf /etc/modsecurity/
fi

# Copy unicode mapping
if [ ! -f /etc/modsecurity/unicode.mapping ]; then
    cp /usr/share/nginx/docs/modsecurity/unicode.mapping /etc/modsecurity/
fi

# Enable blocking mode (change from DetectionOnly to On)
sed -i 's/SecRuleEngine DetectionOnly/SecRuleEngine On/' /etc/modsecurity/modsecurity.conf

log_success "Base configuration ready"

# =====================================================
# STEP 3: Create main config with OWASP CRS
# =====================================================
log_info "Creating main configuration with OWASP CRS..."

cat > /etc/modsecurity/main.conf << 'EOF'
# =====================================================
# ModSecurity Main Configuration for CodeHero
# =====================================================
# Includes base config and OWASP CRS rules
# Custom exclusions for CodeHero functionality

# Base ModSecurity config
Include /etc/modsecurity/modsecurity.conf

# Unicode mapping
SecUnicodeMapFile /etc/modsecurity/unicode.mapping 20127

# OWASP Core Rule Set
Include /etc/modsecurity/crs/crs-setup.conf
Include /etc/modsecurity/crs/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf
Include /usr/share/modsecurity-crs/rules/*.conf
Include /etc/modsecurity/crs/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf

# =====================================================
# CodeHero Custom Exclusions (prevent false positives)
# =====================================================

# Allow WebSocket connections (Socket.IO)
SecRule REQUEST_URI "@beginsWith /socket.io/" \
    "id:1001,phase:1,pass,nolog,ctl:ruleEngine=Off"

# Allow terminal/console connections (contains shell commands)
SecRule REQUEST_URI "@beginsWith /terminal" \
    "id:1002,phase:1,pass,nolog,ctl:ruleEngine=Off"
SecRule REQUEST_URI "@beginsWith /console" \
    "id:1003,phase:1,pass,nolog,ctl:ruleEngine=Off"

# Allow Claude Assistant (may contain code snippets)
SecRule REQUEST_URI "@beginsWith /claude-assistant" \
    "id:1004,phase:1,pass,nolog,ctl:ruleEngine=Off"

# Allow Monaco editor static files
SecRule REQUEST_URI "@beginsWith /static/monaco" \
    "id:1005,phase:1,pass,nolog,ctl:ruleEngine=Off"

# Allow file uploads with relaxed rules
SecRule REQUEST_URI "@endsWith /upload" \
    "id:1006,phase:1,pass,nolog,ctl:ruleRemoveById=920420"

# Allow API endpoints with relaxed JSON rules
SecRule REQUEST_URI "@beginsWith /api/" \
    "id:1007,phase:1,pass,nolog,ctl:ruleRemoveById=920170"
SecRule REQUEST_URI "@beginsWith /api/" \
    "id:1008,phase:1,pass,nolog,ctl:ruleRemoveById=942100"

# Allow ticket chat (may contain code)
SecRule REQUEST_URI "@contains /ticket/" \
    "id:1009,phase:1,pass,nolog,ctl:ruleRemoveById=942100"
SecRule REQUEST_URI "@contains /send_message" \
    "id:1010,phase:1,pass,nolog,ctl:ruleRemoveById=942100"

# Allow editor save (contains code)
SecRule REQUEST_URI "@contains /save_file" \
    "id:1011,phase:1,pass,nolog,ctl:ruleEngine=Off"
SecRule REQUEST_URI "@contains /editor/" \
    "id:1012,phase:1,pass,nolog,ctl:ruleEngine=Off"

# Allow database operations in phpMyAdmin
SecRule REQUEST_URI "@contains phpmyadmin" \
    "id:1013,phase:1,pass,nolog,ctl:ruleRemoveById=942100"
SecRule REQUEST_URI "@contains /db/" \
    "id:1014,phase:1,pass,nolog,ctl:ruleRemoveById=942100"
EOF

log_success "Main configuration created"

# =====================================================
# STEP 4: Add ModSecurity to Nginx configs
# =====================================================
log_info "Enabling ModSecurity in Nginx..."

# Function to add modsecurity to a config file
add_modsecurity_to_config() {
    local config_file="$1"
    local config_name=$(basename "$config_file")

    if [ ! -f "$config_file" ]; then
        log_warning "Config not found: $config_name"
        return
    fi

    # Check if already configured
    if grep -q "modsecurity on" "$config_file"; then
        log_info "ModSecurity already enabled in $config_name"
        return
    fi

    # Add modsecurity after the first server_name line
    sed -i '/server_name _;/a\
\
    # ModSecurity WAF\
    modsecurity on;\
    modsecurity_rules_file /etc/modsecurity/main.conf;' "$config_file"

    log_success "Added to $config_name"
}

# Add to all CodeHero configs
add_modsecurity_to_config "/etc/nginx/sites-available/codehero-admin"
add_modsecurity_to_config "/etc/nginx/sites-available/codehero-projects"
add_modsecurity_to_config "/etc/nginx/sites-available/codehero-phpmyadmin"

# =====================================================
# STEP 5: Test and restart Nginx
# =====================================================
log_info "Testing Nginx configuration..."

if nginx -t 2>&1 | grep -q "successful"; then
    log_success "Nginx configuration valid"

    log_info "Restarting Nginx..."
    systemctl restart nginx

    if systemctl is-active --quiet nginx; then
        log_success "Nginx restarted successfully"
    else
        log_error "Nginx failed to start!"
        exit 1
    fi
else
    log_error "Nginx configuration test failed!"
    nginx -t
    exit 1
fi

# =====================================================
# STEP 6: Verify installation
# =====================================================
echo ""
log_info "Verifying ModSecurity..."

# Count loaded rules
rules_count=$(nginx -t 2>&1 | grep -o "rules loaded.*" | grep -o "[0-9]*" | head -1)
if [ -n "$rules_count" ]; then
    log_success "$rules_count rules loaded"
fi

# Test with XSS payload
echo ""
log_info "Testing WAF with XSS payload..."
response=$(curl -k -s -o /dev/null -w "%{http_code}" "https://127.0.0.1:9453/?test=<script>alert(1)</script>" 2>/dev/null || echo "000")

if [ "$response" = "403" ]; then
    log_success "XSS attack blocked (HTTP 403)"
else
    log_warning "XSS test returned HTTP $response (expected 403)"
fi

# =====================================================
# DONE
# =====================================================
echo ""
echo "╔═══════════════════════════════════════════════════════════╗"
echo "║              ModSecurity WAF Installed!                   ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  Protection enabled for:                                  ║"
echo "║  • Admin Panel (port 9453)                                ║"
echo "║  • Web Projects (port 9867)                               ║"
echo "║  • phpMyAdmin (port 9454)                                 ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  Logs: /var/log/nginx/*-error.log                         ║"
echo "║  Config: /etc/modsecurity/main.conf                       ║"
echo "╠═══════════════════════════════════════════════════════════╣"
echo "║  To disable: Edit Nginx configs, remove modsecurity lines ║"
echo "║  To tune: Edit /etc/modsecurity/main.conf                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""
