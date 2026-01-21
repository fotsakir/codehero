#!/bin/bash
#
# CodeHero Services Restart Script
# Restarts all CodeHero services (nginx, web, daemon, php-fpm, mysql)
#
# Usage:
#   sudo ./restart_codehero_services.sh           # Restart all
#   sudo ./restart_codehero_services.sh --status  # Check status only
#   sudo ./restart_codehero_services.sh --stop    # Stop all
#   sudo ./restart_codehero_services.sh --start   # Start all
#

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Services to manage
SERVICES=(
    "mysql"
    "php8.3-fpm"
    "nginx"
    "codehero-web"
    "codehero-daemon"
)

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "This script must be run as root (sudo)"
        exit 1
    fi
}

# Get service status
get_status() {
    local service="$1"
    if systemctl is-active "$service" &>/dev/null; then
        echo -e "${GREEN}running${NC}"
    else
        echo -e "${RED}stopped${NC}"
    fi
}

# Show status of all services
show_status() {
    echo
    echo -e "${CYAN}========================================${NC}"
    echo -e "${CYAN}       CodeHero Services Status         ${NC}"
    echo -e "${CYAN}========================================${NC}"
    echo
    printf "%-20s %s\n" "SERVICE" "STATUS"
    echo "----------------------------------------"

    for service in "${SERVICES[@]}"; do
        if systemctl list-unit-files "$service.service" &>/dev/null; then
            printf "%-20s %s\n" "$service" "$(get_status $service)"
        else
            printf "%-20s %s\n" "$service" "${YELLOW}not installed${NC}"
        fi
    done
    echo
}

# Restart all services
restart_all() {
    echo
    echo -e "${CYAN}Restarting CodeHero services...${NC}"
    echo

    for service in "${SERVICES[@]}"; do
        if systemctl list-unit-files "$service.service" &>/dev/null 2>&1; then
            printf "%-20s " "$service"
            if systemctl restart "$service" 2>/dev/null; then
                echo -e "${GREEN}restarted${NC}"
            else
                echo -e "${RED}failed${NC}"
            fi
        fi
    done

    echo
    log_success "All services restarted"
    echo
    show_status
}

# Stop all services
stop_all() {
    echo
    echo -e "${CYAN}Stopping CodeHero services...${NC}"
    echo

    # Stop in reverse order
    for ((i=${#SERVICES[@]}-1; i>=0; i--)); do
        service="${SERVICES[$i]}"
        if systemctl list-unit-files "$service.service" &>/dev/null 2>&1; then
            printf "%-20s " "$service"
            if systemctl stop "$service" 2>/dev/null; then
                echo -e "${YELLOW}stopped${NC}"
            else
                echo -e "${RED}failed${NC}"
            fi
        fi
    done

    echo
    log_success "All services stopped"
}

# Start all services
start_all() {
    echo
    echo -e "${CYAN}Starting CodeHero services...${NC}"
    echo

    for service in "${SERVICES[@]}"; do
        if systemctl list-unit-files "$service.service" &>/dev/null 2>&1; then
            printf "%-20s " "$service"
            if systemctl start "$service" 2>/dev/null; then
                echo -e "${GREEN}started${NC}"
            else
                echo -e "${RED}failed${NC}"
            fi
        fi
    done

    echo
    log_success "All services started"
    echo
    show_status
}

# Show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  (no option)    Restart all CodeHero services"
    echo "  --status       Show status of all services"
    echo "  --stop         Stop all services"
    echo "  --start        Start all services"
    echo "  -h, --help     Show this help"
    echo
    echo "Services managed:"
    for service in "${SERVICES[@]}"; do
        echo "  - $service"
    done
}

# Main
main() {
    check_root

    case "${1:-}" in
        --status)
            show_status
            ;;
        --stop)
            stop_all
            ;;
        --start)
            start_all
            ;;
        -h|--help)
            show_usage
            ;;
        "")
            restart_all
            ;;
        *)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
