#!/bin/bash
#
# CodeHero Domain & SSL Setup Script
# Configures domains with Let's Encrypt SSL for CodeHero services
#
# Usage:
#   Interactive:    sudo ./setup_domain.sh
#   Admin SSL:      sudo ./setup_domain.sh --admin --domain example.com --port 9453
#   WebApps SSL:    sudo ./setup_domain.sh --webapps --domain example.com --port 9867
#   Password:       sudo ./setup_domain.sh --webapps --password
#   Renew:          sudo ./setup_domain.sh --renew
#   Status:         sudo ./setup_domain.sh --status
#   Revert:         sudo ./setup_domain.sh --revert
#

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration paths
CONFIG_DIR="/etc/codehero"
DOMAINS_CONF="$CONFIG_DIR/domains.conf"
SSL_DIR="$CONFIG_DIR/ssl"
HTPASSWD_FILE="$CONFIG_DIR/.htpasswd"
BACKUP_DIR="/var/backups/codehero/domain"
NGINX_SITES="/etc/nginx/sites-available"
NGINX_SNIPPETS="/etc/nginx/snippets"
AUTH_SNIPPET="$NGINX_SNIPPETS/codehero-webapps-auth.conf"

# Default ports
DEFAULT_ADMIN_PORT="9453"
DEFAULT_WEBAPPS_PORT="9867"

# Default whitelist for password bypass
DEFAULT_WHITELIST="127.0.0.1,::1,192.168.0.0/16,10.0.0.0/8"

# Logging
log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Install required dependencies
install_dependencies() {
    local missing_packages=()

    log_info "Checking required packages..."

    # Check certbot
    if ! command -v certbot &> /dev/null; then
        missing_packages+=("certbot" "python3-certbot-nginx")
    fi

    # Check htpasswd (apache2-utils)
    if ! command -v htpasswd &> /dev/null; then
        missing_packages+=("apache2-utils")
    fi

    # Check openssl
    if ! command -v openssl &> /dev/null; then
        missing_packages+=("openssl")
    fi

    # Check curl (for testing)
    if ! command -v curl &> /dev/null; then
        missing_packages+=("curl")
    fi

    # Install if needed
    if [ ${#missing_packages[@]} -gt 0 ]; then
        log_info "Installing missing packages: ${missing_packages[*]}"
        # Ignore apt update errors (e.g., expired GPG keys for non-essential repos)
        apt-get update -qq 2>/dev/null || true
        apt-get install -y "${missing_packages[@]}" || {
            log_warn "Some packages may have failed to install. Trying without update..."
            apt-get install -y "${missing_packages[@]}" 2>/dev/null || true
        }
        log_success "Dependencies check completed"
    else
        log_success "All dependencies already installed"
    fi

    # Ensure directories exist
    mkdir -p "$CONFIG_DIR" "$SSL_DIR" "$BACKUP_DIR" "$NGINX_SNIPPETS"
    mkdir -p /etc/nginx/codehero-dotnet 2>/dev/null || true
}

# Check root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (sudo)"
        exit 1
    fi
}

# Load configuration
load_config() {
    if [ -f "$DOMAINS_CONF" ]; then
        source "$DOMAINS_CONF"
    fi
}

# Save configuration
save_config() {
    cat > "$DOMAINS_CONF" << EOF
# CodeHero Domain Configuration
# Generated: $(date)

# Admin Panel
ADMIN_DOMAIN="${ADMIN_DOMAIN:-}"
ADMIN_PORT="${ADMIN_PORT:-$DEFAULT_ADMIN_PORT}"
ADMIN_SSL_TYPE="${ADMIN_SSL_TYPE:-self-signed}"
ADMIN_SSL_CERT="${ADMIN_SSL_CERT:-$SSL_DIR/cert.pem}"
ADMIN_SSL_KEY="${ADMIN_SSL_KEY:-$SSL_DIR/key.pem}"

# Web Apps
WEBAPPS_DOMAIN="${WEBAPPS_DOMAIN:-}"
WEBAPPS_PORT="${WEBAPPS_PORT:-$DEFAULT_WEBAPPS_PORT}"
WEBAPPS_SSL_TYPE="${WEBAPPS_SSL_TYPE:-self-signed}"
WEBAPPS_SSL_CERT="${WEBAPPS_SSL_CERT:-$SSL_DIR/cert.pem}"
WEBAPPS_SSL_KEY="${WEBAPPS_SSL_KEY:-$SSL_DIR/key.pem}"
WEBAPPS_AUTH_ENABLED="${WEBAPPS_AUTH_ENABLED:-false}"
WEBAPPS_AUTH_WHITELIST="${WEBAPPS_AUTH_WHITELIST:-$DEFAULT_WHITELIST}"

# Auto-renewal
AUTO_RENEW_ENABLED="${AUTO_RENEW_ENABLED:-true}"
LETSENCRYPT_EMAIL="${LETSENCRYPT_EMAIL:-}"
EOF
    chmod 600 "$DOMAINS_CONF"
    log_success "Configuration saved to $DOMAINS_CONF"
}

# Create backup
create_backup() {
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$timestamp"

    mkdir -p "$backup_path"

    # Backup nginx configs
    cp -f "$NGINX_SITES/codehero-admin" "$backup_path/" 2>/dev/null || true
    cp -f "$NGINX_SITES/codehero-projects" "$backup_path/" 2>/dev/null || true
    cp -f "$AUTH_SNIPPET" "$backup_path/" 2>/dev/null || true
    cp -f "$DOMAINS_CONF" "$backup_path/" 2>/dev/null || true

    echo "$backup_path"
}

# Restore from backup
restore_backup() {
    local backup_path="$1"

    if [ -d "$backup_path" ]; then
        cp -f "$backup_path/codehero-admin" "$NGINX_SITES/" 2>/dev/null || true
        cp -f "$backup_path/codehero-projects" "$NGINX_SITES/" 2>/dev/null || true
        cp -f "$backup_path/codehero-webapps-auth.conf" "$AUTH_SNIPPET" 2>/dev/null || true
        cp -f "$backup_path/domains.conf" "$DOMAINS_CONF" 2>/dev/null || true
        log_success "Restored from backup: $backup_path"
    else
        log_error "Backup not found: $backup_path"
    fi
}

# Test and reload nginx
test_and_reload_nginx() {
    log_info "Testing nginx configuration..."
    if nginx -t 2>&1; then
        log_info "Reloading nginx..."
        systemctl reload nginx
        log_success "Nginx reloaded successfully"
        return 0
    else
        log_error "Nginx configuration test failed!"
        return 1
    fi
}

# Restart all CodeHero services
restart_services() {
    log_info "Restarting CodeHero services..."

    # Restart nginx
    systemctl restart nginx 2>/dev/null && log_success "nginx restarted" || log_warn "nginx restart failed"

    # Restart codehero services if they exist
    if systemctl is-enabled codehero-web &>/dev/null; then
        systemctl restart codehero-web 2>/dev/null && log_success "codehero-web restarted" || log_warn "codehero-web restart failed"
    fi

    if systemctl is-enabled codehero-daemon &>/dev/null; then
        systemctl restart codehero-daemon 2>/dev/null && log_success "codehero-daemon restarted" || log_warn "codehero-daemon restart failed"
    fi
}

# Check if certbot is installed
check_certbot() {
    # Verify certbot is available (should be installed by install_dependencies)
    if ! command -v certbot &> /dev/null; then
        log_error "Certbot not found. Running install_dependencies..."
        install_dependencies
    fi
}

# Get Let's Encrypt certificate
get_letsencrypt_cert() {
    local domain="$1"
    local email="$2"

    check_certbot

    log_info "Obtaining Let's Encrypt certificate for $domain..."

    # Stop nginx temporarily for standalone mode
    systemctl stop nginx

    if certbot certonly --standalone -d "$domain" --email "$email" --agree-tos --non-interactive; then
        systemctl start nginx
        log_success "Certificate obtained for $domain"
        return 0
    else
        systemctl start nginx
        log_error "Failed to obtain certificate for $domain"
        return 1
    fi
}

# Get certificate paths
get_cert_paths() {
    local domain="$1"
    local cert_dir="/etc/letsencrypt/live/$domain"

    if [ -d "$cert_dir" ]; then
        echo "$cert_dir/fullchain.pem:$cert_dir/privkey.pem"
    else
        echo ""
    fi
}

# Check certificate expiry
check_cert_expiry() {
    local cert_file="$1"

    if [ -f "$cert_file" ]; then
        local expiry=$(openssl x509 -enddate -noout -in "$cert_file" 2>/dev/null | cut -d= -f2)
        local expiry_epoch=$(date -d "$expiry" +%s 2>/dev/null || echo 0)
        local now_epoch=$(date +%s)
        local days_left=$(( (expiry_epoch - now_epoch) / 86400 ))

        echo "$days_left"
    else
        echo "-1"
    fi
}

# Create auth snippet for web apps
create_auth_snippet() {
    local whitelist="$1"

    mkdir -p "$NGINX_SNIPPETS"

    cat > "$AUTH_SNIPPET" << 'EOF'
# CodeHero Web Apps Authentication
# Password required for external IPs, bypassed for local/LAN

satisfy any;

# Localhost
allow 127.0.0.1;
allow ::1;

EOF

    # Add whitelist IPs
    IFS=',' read -ra IPS <<< "$whitelist"
    for ip in "${IPS[@]}"; do
        ip=$(echo "$ip" | xargs)  # Trim whitespace
        if [ "$ip" != "127.0.0.1" ] && [ "$ip" != "::1" ]; then
            echo "allow $ip;" >> "$AUTH_SNIPPET"
        fi
    done

    cat >> "$AUTH_SNIPPET" << 'EOF'

# External IPs require password
deny all;
auth_basic "CodeHero Web Apps";
auth_basic_user_file /etc/codehero/.htpasswd;
EOF

    log_success "Auth snippet created: $AUTH_SNIPPET"
}

# Setup password protection
setup_password() {
    local username="${1:-admin}"
    local password="$2"

    if [ -z "$password" ]; then
        read -sp "Enter password for web apps: " password
        echo
        read -sp "Confirm password: " password2
        echo

        if [ "$password" != "$password2" ]; then
            log_error "Passwords don't match!"
            return 1
        fi
    fi

    # Install htpasswd if not available
    if ! command -v htpasswd &> /dev/null; then
        apt-get install -y apache2-utils
    fi

    htpasswd -bc "$HTPASSWD_FILE" "$username" "$password"
    chmod 600 "$HTPASSWD_FILE"

    log_success "Password set for user: $username"
}

# Update admin nginx config
update_admin_config() {
    local domain="$1"
    local port="$2"
    local ssl_cert="$3"
    local ssl_key="$4"

    # server_name: always include _ (catch-all for IP) plus domain if provided
    local server_name="_"
    if [ -n "$domain" ]; then
        server_name="_ $domain"
    fi

    cat > "$NGINX_SITES/codehero-admin" << EOF
# CodeHero Admin Panel
# Port: $port (HTTPS)
# Domain: ${domain:-IP-only}
# Reverse proxy to Flask (127.0.0.1:5000)

server {
    listen $port ssl http2;
    listen [::]:$port ssl http2;

    # ModSecurity WAF
    modsecurity on;
    modsecurity_rules_file /etc/modsecurity/main.conf;
    server_name $server_name;

    # SSL Configuration
    ssl_certificate $ssl_cert;
    ssl_certificate_key $ssl_key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Logging
    access_log /var/log/nginx/codehero-admin-access.log;
    error_log /var/log/nginx/codehero-admin-error.log;

    # Large uploads (for file manager)
    client_max_body_size 500M;

    # Flask Proxy - Main application
    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Socket.io WebSocket support
    location /socket.io {
        proxy_pass http://127.0.0.1:5000;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 86400s;
    }

    # ws-scrcpy Android emulator proxy (with path stripping!)
    location /android/ {
        proxy_pass https://127.0.0.1:8443/;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_ssl_verify off;
        proxy_read_timeout 86400s;
    }

    # ws-scrcpy without trailing slash (redirect)
    location = /android {
        return 301 /android/;
    }
}
EOF

    log_success "Admin nginx config updated"
}

# Update webapps nginx config
update_webapps_config() {
    local domain="$1"
    local port="$2"
    local ssl_cert="$3"
    local ssl_key="$4"
    local auth_enabled="$5"

    # server_name: always include _ (catch-all for IP) plus domain if provided
    local server_name="_"
    if [ -n "$domain" ]; then
        server_name="_ $domain"
    fi

    local auth_include=""
    if [ "$auth_enabled" = "true" ]; then
        auth_include="include $AUTH_SNIPPET;"
    fi

    cat > "$NGINX_SITES/codehero-projects" << EOF
# CodeHero Web Projects
# Port: $port (HTTPS)
# Domain: ${domain:-IP-only}
# Static files + PHP from /var/www/projects

server {
    listen $port ssl http2;
    listen [::]:$port ssl http2;

    # ModSecurity WAF
    modsecurity on;
    modsecurity_rules_file /etc/modsecurity/main.conf;
    server_name $server_name;

    # SSL Configuration
    ssl_certificate $ssl_cert;
    ssl_certificate_key $ssl_key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Document root
    root /var/www/projects;
    index index.html index.php;

    # Logging
    access_log /var/log/nginx/codehero-projects-access.log;
    error_log /var/log/nginx/codehero-projects-error.log;

    # Large uploads
    client_max_body_size 500M;

    # Gzip compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript;

    # Authentication (if enabled)
    $auth_include

    # Main location
    location / {
        try_files \$uri \$uri/ /index.php?\$query_string;
    }

    # PHP files
    location ~ \.php$ {
        fastcgi_pass unix:/var/run/php/php8.3-fpm.sock;
        fastcgi_param SCRIPT_FILENAME \$realpath_root\$fastcgi_script_name;
        include fastcgi_params;
        fastcgi_read_timeout 300s;
    }

    # Deny access to .htaccess files (security)
    location ~ /\.ht {
        deny all;
    }

    # Static file caching
    location ~* \.(jpg|jpeg|png|gif|ico|css|js|woff|woff2|ttf|svg)$ {
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # Include .NET project proxy configs
    include /etc/nginx/codehero-dotnet/*.conf;
}
EOF

    log_success "WebApps nginx config updated"
}

# Configure admin panel domain
configure_admin() {
    local domain="$1"
    local port="${2:-$DEFAULT_ADMIN_PORT}"
    local email="$3"

    log_info "Configuring Admin Panel..."
    echo

    # Get current values
    load_config

    # Interactive if no domain provided
    if [ -z "$domain" ]; then
        echo -e "${CYAN}[Admin Panel Configuration]${NC}"
        if [ -n "$ADMIN_DOMAIN" ]; then
            echo "Current: https://$ADMIN_DOMAIN:$ADMIN_PORT ($ADMIN_SSL_TYPE)"
        else
            echo "Current: https://IP:$ADMIN_PORT (self-signed)"
        fi
        echo

        read -p "Enter domain (or leave empty for IP-only): " domain
        read -p "Enter port [$port]: " input_port
        port="${input_port:-$port}"
    fi

    local ssl_cert="$SSL_DIR/cert.pem"
    local ssl_key="$SSL_DIR/key.pem"
    local ssl_type="self-signed"

    if [ -n "$domain" ]; then
        # Get Let's Encrypt cert
        if [ -z "$email" ]; then
            read -p "Email for Let's Encrypt: " email
        fi

        # Create backup
        local backup=$(create_backup)
        log_info "Backup created: $backup"

        if get_letsencrypt_cert "$domain" "$email"; then
            local cert_paths=$(get_cert_paths "$domain")
            ssl_cert=$(echo "$cert_paths" | cut -d: -f1)
            ssl_key=$(echo "$cert_paths" | cut -d: -f2)
            ssl_type="letsencrypt"
            LETSENCRYPT_EMAIL="$email"
        else
            log_error "Failed to get certificate. Reverting..."
            restore_backup "$backup"
            return 1
        fi
    fi

    # Update config
    ADMIN_DOMAIN="$domain"
    ADMIN_PORT="$port"
    ADMIN_SSL_CERT="$ssl_cert"
    ADMIN_SSL_KEY="$ssl_key"
    ADMIN_SSL_TYPE="$ssl_type"

    # Update nginx
    update_admin_config "$domain" "$port" "$ssl_cert" "$ssl_key"

    # Test and reload
    if test_and_reload_nginx; then
        save_config
        restart_services
        echo
        if [ -n "$domain" ]; then
            log_success "Admin Panel configured on port $port"
            log_info "  Access via IP:     https://IP:$port"
            log_info "  Access via domain: https://$domain:$port"
        else
            log_success "Admin Panel configured: https://IP:$port (self-signed)"
        fi
    else
        log_error "Configuration failed. Check nginx error log."
        return 1
    fi
}

# Configure web apps domain
configure_webapps() {
    local domain="$1"
    local port="${2:-$DEFAULT_WEBAPPS_PORT}"
    local email="$3"
    local enable_auth="$4"

    log_info "Configuring Web Apps..."
    echo

    # Get current values
    load_config

    # Interactive if no domain provided
    if [ -z "$domain" ]; then
        echo -e "${CYAN}[Web Apps Configuration]${NC}"
        if [ -n "$WEBAPPS_DOMAIN" ]; then
            echo "Current: https://$WEBAPPS_DOMAIN:$WEBAPPS_PORT ($WEBAPPS_SSL_TYPE)"
        else
            echo "Current: https://IP:$WEBAPPS_PORT (self-signed)"
        fi
        echo

        # Offer same domain as admin if available
        if [ -n "$ADMIN_DOMAIN" ]; then
            read -p "Use same domain as Admin ($ADMIN_DOMAIN)? [Y/n]: " same_domain
            if [ "${same_domain,,}" != "n" ]; then
                domain="$ADMIN_DOMAIN"
            fi
        fi

        if [ -z "$domain" ]; then
            read -p "Enter domain (or leave empty for IP-only): " domain
        fi

        read -p "Enter port [$port]: " input_port
        port="${input_port:-$port}"

        # Ask about password protection
        if [ -z "$enable_auth" ]; then
            read -p "Enable password protection for external IPs? [Y/n]: " enable_auth_input
            if [ "${enable_auth_input,,}" != "n" ]; then
                enable_auth="true"
            else
                enable_auth="false"
            fi
        fi
    fi

    local ssl_cert="$SSL_DIR/cert.pem"
    local ssl_key="$SSL_DIR/key.pem"
    local ssl_type="self-signed"

    if [ -n "$domain" ]; then
        # Check if we already have a cert for this domain
        local existing_paths=$(get_cert_paths "$domain")

        if [ -n "$existing_paths" ]; then
            ssl_cert=$(echo "$existing_paths" | cut -d: -f1)
            ssl_key=$(echo "$existing_paths" | cut -d: -f2)
            ssl_type="letsencrypt"
            log_info "Using existing certificate for $domain"
        else
            # Get Let's Encrypt cert
            if [ -z "$email" ]; then
                if [ -n "$LETSENCRYPT_EMAIL" ]; then
                    email="$LETSENCRYPT_EMAIL"
                else
                    read -p "Email for Let's Encrypt: " email
                fi
            fi

            # Create backup
            local backup=$(create_backup)
            log_info "Backup created: $backup"

            if get_letsencrypt_cert "$domain" "$email"; then
                local cert_paths=$(get_cert_paths "$domain")
                ssl_cert=$(echo "$cert_paths" | cut -d: -f1)
                ssl_key=$(echo "$cert_paths" | cut -d: -f2)
                ssl_type="letsencrypt"
                LETSENCRYPT_EMAIL="$email"
            else
                log_error "Failed to get certificate. Reverting..."
                restore_backup "$backup"
                return 1
            fi
        fi
    fi

    # Setup password if enabled
    if [ "$enable_auth" = "true" ]; then
        if [ ! -f "$HTPASSWD_FILE" ]; then
            setup_password "admin"
        fi
        create_auth_snippet "${WEBAPPS_AUTH_WHITELIST:-$DEFAULT_WHITELIST}"
    fi

    # Update config
    WEBAPPS_DOMAIN="$domain"
    WEBAPPS_PORT="$port"
    WEBAPPS_SSL_CERT="$ssl_cert"
    WEBAPPS_SSL_KEY="$ssl_key"
    WEBAPPS_SSL_TYPE="$ssl_type"
    WEBAPPS_AUTH_ENABLED="$enable_auth"

    # Update nginx
    update_webapps_config "$domain" "$port" "$ssl_cert" "$ssl_key" "$enable_auth"

    # Test and reload
    if test_and_reload_nginx; then
        save_config
        restart_services
        echo
        if [ -n "$domain" ]; then
            log_success "Web Apps configured on port $port"
            log_info "  Access via IP:     https://IP:$port"
            log_info "  Access via domain: https://$domain:$port"
        else
            log_success "Web Apps configured: https://IP:$port (self-signed)"
        fi
        if [ "$enable_auth" = "true" ]; then
            log_success "Password protection enabled (external IPs only)"
        fi
    else
        log_error "Configuration failed. Check nginx error log."
        return 1
    fi
}

# Configure password protection only
configure_password() {
    local enable="$1"
    local whitelist="$2"

    load_config

    if [ "$enable" = "true" ] || [ "$enable" = "on" ]; then
        # Setup password
        if [ ! -f "$HTPASSWD_FILE" ]; then
            setup_password "admin"
        else
            read -p "Password file exists. Update password? [y/N]: " update_pw
            if [ "${update_pw,,}" = "y" ]; then
                setup_password "admin"
            fi
        fi

        # Create auth snippet
        create_auth_snippet "${whitelist:-$WEBAPPS_AUTH_WHITELIST:-$DEFAULT_WHITELIST}"

        WEBAPPS_AUTH_ENABLED="true"
        if [ -n "$whitelist" ]; then
            WEBAPPS_AUTH_WHITELIST="$whitelist"
        fi
    else
        WEBAPPS_AUTH_ENABLED="false"
    fi

    # Update nginx config
    update_webapps_config "$WEBAPPS_DOMAIN" "$WEBAPPS_PORT" "$WEBAPPS_SSL_CERT" "$WEBAPPS_SSL_KEY" "$WEBAPPS_AUTH_ENABLED"

    if test_and_reload_nginx; then
        save_config
        restart_services
        if [ "$WEBAPPS_AUTH_ENABLED" = "true" ]; then
            log_success "Password protection enabled"
        else
            log_success "Password protection disabled"
        fi
    fi
}

# Renew SSL certificates
renew_ssl() {
    local domain="$1"

    check_certbot

    echo -e "${CYAN}Checking certificates...${NC}"
    echo

    printf "%-25s %-15s %s\n" "Domain" "Expires" "Status"
    echo "----------------------------------------"

    local certs_to_renew=()

    # Check admin cert
    if [ -n "$ADMIN_DOMAIN" ] && [ "$ADMIN_SSL_TYPE" = "letsencrypt" ]; then
        local days=$(check_cert_expiry "$ADMIN_SSL_CERT")
        local status="OK"
        if [ "$days" -lt 30 ]; then
            status="NEEDS RENEWAL"
            certs_to_renew+=("$ADMIN_DOMAIN")
        fi
        printf "%-25s %-15s %s\n" "$ADMIN_DOMAIN" "${days} days" "$status"
    fi

    # Check webapps cert (if different domain)
    if [ -n "$WEBAPPS_DOMAIN" ] && [ "$WEBAPPS_SSL_TYPE" = "letsencrypt" ]; then
        if [ "$WEBAPPS_DOMAIN" != "$ADMIN_DOMAIN" ]; then
            local days=$(check_cert_expiry "$WEBAPPS_SSL_CERT")
            local status="OK"
            if [ "$days" -lt 30 ]; then
                status="NEEDS RENEWAL"
                certs_to_renew+=("$WEBAPPS_DOMAIN")
            fi
            printf "%-25s %-15s %s\n" "$WEBAPPS_DOMAIN" "${days} days" "$status"
        fi
    fi

    echo

    # Filter to specific domain if provided
    if [ -n "$domain" ]; then
        certs_to_renew=("$domain")
    fi

    if [ ${#certs_to_renew[@]} -eq 0 ]; then
        log_info "All certificates are up to date"
        return 0
    fi

    read -p "Renew certificates now? [y/N]: " confirm
    if [ "${confirm,,}" != "y" ]; then
        return 0
    fi

    # Stop nginx for standalone renewal
    systemctl stop nginx

    for cert_domain in "${certs_to_renew[@]}"; do
        log_info "Renewing $cert_domain..."
        if certbot renew --cert-name "$cert_domain" --standalone; then
            log_success "Certificate renewed: $cert_domain"
        else
            log_error "Failed to renew: $cert_domain"
        fi
    done

    systemctl start nginx
    log_success "Nginx restarted"
}

# Configure auto-renewal
setup_auto_renew() {
    local enable="$1"

    if [ "$enable" = "on" ] || [ "$enable" = "true" ]; then
        # Enable certbot timer
        systemctl enable certbot.timer
        systemctl start certbot.timer
        AUTO_RENEW_ENABLED="true"
        log_success "Auto-renewal enabled"
    elif [ "$enable" = "off" ] || [ "$enable" = "false" ]; then
        systemctl stop certbot.timer
        systemctl disable certbot.timer
        AUTO_RENEW_ENABLED="false"
        log_success "Auto-renewal disabled"
    else
        # Show status
        echo -e "${CYAN}Auto-renewal Status:${NC}"
        if systemctl is-active certbot.timer &>/dev/null; then
            echo "Status: ENABLED"
            systemctl status certbot.timer --no-pager
        else
            echo "Status: DISABLED"
        fi
    fi

    save_config
}

# Show current status
show_status() {
    load_config

    echo
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}       CodeHero Domain & SSL Status         ${NC}"
    echo -e "${CYAN}============================================${NC}"
    echo

    echo -e "${YELLOW}Admin Panel:${NC}"
    echo "  Port: $ADMIN_PORT"
    if [ -n "$ADMIN_DOMAIN" ]; then
        echo "  URLs: https://IP:$ADMIN_PORT"
        echo "        https://$ADMIN_DOMAIN:$ADMIN_PORT"
        echo "  SSL:  $ADMIN_SSL_TYPE"
        if [ "$ADMIN_SSL_TYPE" = "letsencrypt" ]; then
            local days=$(check_cert_expiry "$ADMIN_SSL_CERT")
            echo "  Cert: Expires in $days days"
        fi
    else
        echo "  URL:  https://IP:$ADMIN_PORT"
        echo "  SSL:  self-signed"
    fi
    echo

    echo -e "${YELLOW}Web Apps:${NC}"
    echo "  Port: $WEBAPPS_PORT"
    if [ -n "$WEBAPPS_DOMAIN" ]; then
        echo "  URLs: https://IP:$WEBAPPS_PORT"
        echo "        https://$WEBAPPS_DOMAIN:$WEBAPPS_PORT"
        echo "  SSL:  $WEBAPPS_SSL_TYPE"
        if [ "$WEBAPPS_SSL_TYPE" = "letsencrypt" ]; then
            local days=$(check_cert_expiry "$WEBAPPS_SSL_CERT")
            echo "  Cert: Expires in $days days"
        fi
    else
        echo "  URL:  https://IP:$WEBAPPS_PORT"
        echo "  SSL:  self-signed"
    fi
    echo "  Auth: ${WEBAPPS_AUTH_ENABLED:-false}"
    if [ "$WEBAPPS_AUTH_ENABLED" = "true" ]; then
        echo "  Whitelist: ${WEBAPPS_AUTH_WHITELIST:-$DEFAULT_WHITELIST}"
    fi
    echo

    echo -e "${YELLOW}Auto-renewal:${NC}"
    if systemctl is-active certbot.timer &>/dev/null; then
        echo "  Status: ENABLED"
    else
        echo "  Status: DISABLED"
    fi
    echo
}

# Revert to self-signed certificates
revert_ssl() {
    local target="$1"

    load_config

    echo -e "${YELLOW}Reverting to self-signed certificates...${NC}"

    # Create backup first
    local backup=$(create_backup)
    log_info "Backup created: $backup"

    if [ "$target" = "admin" ] || [ -z "$target" ]; then
        ADMIN_DOMAIN=""
        ADMIN_SSL_CERT="$SSL_DIR/cert.pem"
        ADMIN_SSL_KEY="$SSL_DIR/key.pem"
        ADMIN_SSL_TYPE="self-signed"
        update_admin_config "" "$ADMIN_PORT" "$ADMIN_SSL_CERT" "$ADMIN_SSL_KEY"
        log_success "Admin Panel reverted to self-signed"
    fi

    if [ "$target" = "webapps" ] || [ -z "$target" ]; then
        WEBAPPS_DOMAIN=""
        WEBAPPS_SSL_CERT="$SSL_DIR/cert.pem"
        WEBAPPS_SSL_KEY="$SSL_DIR/key.pem"
        WEBAPPS_SSL_TYPE="self-signed"
        update_webapps_config "" "$WEBAPPS_PORT" "$WEBAPPS_SSL_CERT" "$WEBAPPS_SSL_KEY" "$WEBAPPS_AUTH_ENABLED"
        log_success "Web Apps reverted to self-signed"
    fi

    if test_and_reload_nginx; then
        save_config
        restart_services
        log_success "Reverted to self-signed certificates"
    else
        log_error "Failed to reload nginx. Restoring backup..."
        restore_backup "$backup"
        test_and_reload_nginx
    fi
}

# Interactive menu
show_menu() {
    while true; do
        clear
        echo
        echo -e "${CYAN}=======================================================${NC}"
        echo -e "${CYAN}           CODEHERO - Domain & SSL Setup               ${NC}"
        echo -e "${CYAN}=======================================================${NC}"
        echo
        echo "What would you like to configure?"
        echo
        echo "  1) Admin Panel domain & SSL"
        echo "  2) Web Apps domain & SSL"
        echo "  3) Web Apps password protection"
        echo "  4) Renew SSL certificates"
        echo "  5) Auto-renewal settings"
        echo "  6) Show current status"
        echo "  7) Revert to self-signed certificates"
        echo "  0) Exit"
        echo
        read -p "Choice [0-7]: " choice

        case $choice in
            1) configure_admin; read -p "Press Enter to continue..." ;;
            2) configure_webapps; read -p "Press Enter to continue..." ;;
            3)
                read -p "Enable password protection? [y/n]: " enable_pw
                if [ "${enable_pw,,}" = "y" ]; then
                    configure_password "true"
                else
                    configure_password "false"
                fi
                read -p "Press Enter to continue..."
                ;;
            4) renew_ssl; read -p "Press Enter to continue..." ;;
            5)
                echo
                echo "Auto-renewal options:"
                echo "  1) Enable auto-renewal"
                echo "  2) Disable auto-renewal"
                echo "  3) Check status"
                read -p "Choice [1-3]: " ar_choice
                case $ar_choice in
                    1) setup_auto_renew "on" ;;
                    2) setup_auto_renew "off" ;;
                    3) setup_auto_renew "" ;;
                esac
                read -p "Press Enter to continue..."
                ;;
            6) show_status; read -p "Press Enter to continue..." ;;
            7)
                echo
                echo "Revert options:"
                echo "  1) Revert Admin Panel"
                echo "  2) Revert Web Apps"
                echo "  3) Revert both"
                read -p "Choice [1-3]: " rv_choice
                case $rv_choice in
                    1) revert_ssl "admin" ;;
                    2) revert_ssl "webapps" ;;
                    3) revert_ssl "" ;;
                esac
                read -p "Press Enter to continue..."
                ;;
            0) echo "Goodbye!"; exit 0 ;;
            *) echo "Invalid choice"; sleep 1 ;;
        esac
    done
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  --admin              Configure admin panel"
    echo "  --webapps            Configure web apps"
    echo "  --domain DOMAIN      Domain name"
    echo "  --port PORT          Port number"
    echo "  --email EMAIL        Let's Encrypt email"
    echo "  --password           Enable/configure password protection"
    echo "  --no-password        Disable password protection"
    echo "  --whitelist IPS      Comma-separated IPs to whitelist"
    echo "  --renew              Renew SSL certificates"
    echo "  --renew-status       Check renewal status"
    echo "  --auto-renew on|off  Enable/disable auto-renewal"
    echo "  --status             Show current configuration"
    echo "  --revert [admin|webapps]  Revert to self-signed"
    echo "  -h, --help           Show this help"
    echo
    echo "Examples:"
    echo "  $0                                          # Interactive mode"
    echo "  $0 --admin --domain example.com --port 9453"
    echo "  $0 --webapps --domain example.com --password"
    echo "  $0 --renew"
    echo "  $0 --status"
}

# Parse command line arguments
main() {
    check_root
    install_dependencies
    load_config

    local mode=""
    local domain=""
    local port=""
    local email=""
    local password_action=""
    local whitelist=""
    local auto_renew=""
    local revert_target=""

    # No arguments = interactive mode
    if [ $# -eq 0 ]; then
        show_menu
        exit 0
    fi

    while [ $# -gt 0 ]; do
        case $1 in
            --admin)
                mode="admin"
                ;;
            --webapps)
                mode="webapps"
                ;;
            --domain)
                domain="$2"
                shift
                ;;
            --port)
                port="$2"
                shift
                ;;
            --email)
                email="$2"
                shift
                ;;
            --password)
                password_action="enable"
                ;;
            --no-password)
                password_action="disable"
                ;;
            --whitelist)
                whitelist="$2"
                shift
                ;;
            --renew)
                mode="renew"
                ;;
            --renew-status)
                setup_auto_renew ""
                exit 0
                ;;
            --auto-renew)
                auto_renew="$2"
                shift
                ;;
            --status)
                show_status
                exit 0
                ;;
            --revert)
                mode="revert"
                if [ -n "$2" ] && [[ ! "$2" =~ ^-- ]]; then
                    revert_target="$2"
                    shift
                fi
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
        shift
    done

    # Handle auto-renewal
    if [ -n "$auto_renew" ]; then
        setup_auto_renew "$auto_renew"
        exit 0
    fi

    # Execute based on mode
    case $mode in
        admin)
            configure_admin "$domain" "$port" "$email"
            ;;
        webapps)
            if [ -n "$password_action" ]; then
                if [ "$password_action" = "enable" ]; then
                    configure_webapps "$domain" "$port" "$email" "true"
                else
                    configure_webapps "$domain" "$port" "$email" "false"
                fi
            else
                configure_webapps "$domain" "$port" "$email"
            fi
            ;;
        renew)
            renew_ssl "$domain"
            ;;
        revert)
            revert_ssl "$revert_target"
            ;;
        "")
            # Password action without mode
            if [ "$password_action" = "enable" ]; then
                configure_password "true" "$whitelist"
            elif [ "$password_action" = "disable" ]; then
                configure_password "false"
            else
                show_usage
            fi
            ;;
    esac
}

# Run main
main "$@"
