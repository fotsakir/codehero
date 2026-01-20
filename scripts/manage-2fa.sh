#!/bin/bash
#
# CodeHero 2FA Management
# Usage: sudo /opt/codehero/scripts/manage-2fa.sh [command]
#
# Commands:
#   (none)   - Interactive menu
#   enable   - Enable 2FA and show QR code
#   disable  - Disable 2FA
#   reset    - Reset 2FA (new QR code)
#   unlock   - Unlock account after failed attempts
#   status   - Show current status
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/manage_2fa.py"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root: sudo $0"
    exit 1
fi

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "Error: manage_2fa.py not found at $PYTHON_SCRIPT"
    exit 1
fi

# Check dependencies
python3 -c "import pyotp, qrcode" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Installing required packages..."
    pip3 install pyotp qrcode pillow --break-system-packages -q 2>/dev/null || \
    pip3 install pyotp qrcode pillow -q 2>/dev/null
fi

# Run Python script with arguments
python3 "$PYTHON_SCRIPT" "$@"
