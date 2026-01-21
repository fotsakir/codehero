#!/usr/bin/env python3
"""
CodeHero 2FA Management Helper
Handles TOTP setup, verification, and account unlock
"""

import sys
import os
import argparse
import mysql.connector
from datetime import datetime, timedelta

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pyotp
    import qrcode
    DEPS_AVAILABLE = True
except ImportError:
    DEPS_AVAILABLE = False

# ANSI colors
GREEN = '\033[0;32m'
RED = '\033[0;31m'
YELLOW = '\033[0;33m'
CYAN = '\033[0;36m'
RESET = '\033[0m'
BOLD = '\033[1m'

def get_db_connection():
    """Get database connection using config credentials."""
    db_password = None

    # Try /etc/codehero/mysql.conf first (production)
    mysql_conf = '/etc/codehero/mysql.conf'
    if os.path.exists(mysql_conf):
        with open(mysql_conf, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('DB_PASSWORD='):
                    db_password = line.split('=', 1)[1].strip('"\'')
                    break

    # Fallback to install.conf
    if not db_password:
        for config_path in ['/opt/codehero/install.conf', '/home/claude/codehero/install.conf']:
            if os.path.exists(config_path):
                with open(config_path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('DB_PASSWORD='):
                            db_password = line.split('=', 1)[1].strip('"\'')
                            break
                if db_password:
                    break

    # Default fallback
    if not db_password:
        db_password = 'claudepass123'

    return mysql.connector.connect(
        host='localhost',
        user='claude_user',
        password=db_password,
        database='claude_knowledge'
    )

def get_auth_settings():
    """Get current auth settings from database."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM auth_settings WHERE id = 1")
    result = cursor.fetchone()
    cursor.close()
    conn.close()

    if not result:
        # Initialize if not exists
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT IGNORE INTO auth_settings (id) VALUES (1)")
        conn.commit()
        cursor.close()
        conn.close()
        return {'id': 1, 'failed_attempts': 0, 'locked_until': None, 'totp_secret': None, 'totp_enabled': False}

    return result

def update_auth_settings(**kwargs):
    """Update auth settings in database."""
    conn = get_db_connection()
    cursor = conn.cursor()

    set_clauses = []
    values = []
    for key, value in kwargs.items():
        set_clauses.append(f"{key} = %s")
        values.append(value)

    query = f"UPDATE auth_settings SET {', '.join(set_clauses)} WHERE id = 1"
    cursor.execute(query, values)
    conn.commit()
    cursor.close()
    conn.close()

def show_status():
    """Show current 2FA and account status."""
    settings = get_auth_settings()

    print(f"\n{CYAN}{'='*50}{RESET}")
    print(f"{BOLD}CodeHero Authentication Status{RESET}")
    print(f"{CYAN}{'='*50}{RESET}\n")

    # 2FA Status
    if settings['totp_enabled']:
        if settings['totp_secret']:
            print(f"  2FA Status:      {GREEN}Enabled ✓{RESET}")
        else:
            print(f"  2FA Status:      {YELLOW}Enabled (pending setup){RESET}")
    else:
        print(f"  2FA Status:      {YELLOW}Disabled{RESET}")

    # Account lock status
    if settings['locked_until']:
        lock_time = settings['locked_until']
        if isinstance(lock_time, str):
            lock_time = datetime.fromisoformat(lock_time)

        if lock_time > datetime.now():
            remaining = lock_time - datetime.now()
            mins = int(remaining.total_seconds() / 60)
            print(f"  Account Status:  {RED}Locked (unlocks in {mins} min){RESET}")
        else:
            print(f"  Account Status:  {GREEN}Active{RESET}")
    else:
        print(f"  Account Status:  {GREEN}Active{RESET}")

    # Failed attempts
    print(f"  Failed Attempts: {settings['failed_attempts']}/5")
    print()

def enable_2fa():
    """Enable 2FA and show QR code for setup."""
    if not DEPS_AVAILABLE:
        print(f"{RED}Error: Required packages not installed.{RESET}")
        print(f"Run: pip install pyotp qrcode")
        return False

    settings = get_auth_settings()

    if settings['totp_enabled'] and settings['totp_secret']:
        print(f"{YELLOW}2FA is already enabled.{RESET}")
        print("Use 'reset' to generate a new QR code, or 'disable' first.")
        return False

    # Generate new secret
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)

    # Create provisioning URI
    uri = totp.provisioning_uri(name="admin", issuer_name="CodeHero")

    # Show QR code in terminal
    print(f"\n{CYAN}{'='*50}{RESET}")
    print(f"{BOLD}Scan this QR code with Google Authenticator:{RESET}")
    print(f"{CYAN}{'='*50}{RESET}\n")

    # Generate QR code for terminal
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=1,
        border=2,
    )
    qr.add_data(uri)
    qr.make(fit=True)

    # Print QR to terminal
    qr.print_ascii(invert=True)

    print(f"\n{CYAN}Or enter this code manually:{RESET}")
    # Format secret in groups of 4 for readability
    formatted_secret = ' '.join([secret[i:i+4] for i in range(0, len(secret), 4)])
    print(f"\n  {BOLD}{formatted_secret}{RESET}\n")

    # Verify the code
    print(f"{YELLOW}Enter the 6-digit code from your authenticator to verify:{RESET}")
    code = input("Code: ").strip()

    if totp.verify(code):
        # Save to database
        update_auth_settings(totp_secret=secret, totp_enabled=True)
        print(f"\n{GREEN}✓ 2FA enabled successfully!{RESET}")
        print("You will now need to enter a code when logging in.\n")
        return True
    else:
        print(f"\n{RED}✗ Invalid code. 2FA not enabled.{RESET}")
        print("Please try again.\n")
        return False

def disable_2fa():
    """Disable 2FA."""
    settings = get_auth_settings()

    if not settings['totp_enabled']:
        print(f"{YELLOW}2FA is already disabled.{RESET}")
        return True

    # Confirm
    print(f"{YELLOW}Are you sure you want to disable 2FA? (yes/no){RESET}")
    confirm = input().strip().lower()

    if confirm in ['yes', 'y']:
        update_auth_settings(totp_secret=None, totp_enabled=False)
        print(f"\n{GREEN}✓ 2FA disabled.{RESET}")
        print("You can now login with just username and password.\n")
        return True
    else:
        print("Cancelled.")
        return False

def reset_2fa():
    """Reset 2FA secret and generate new QR code."""
    settings = get_auth_settings()

    if not settings['totp_enabled']:
        print(f"{YELLOW}2FA is not enabled. Use 'enable' instead.{RESET}")
        return False

    # Confirm
    print(f"{YELLOW}This will generate a new QR code. Your old authenticator entry will stop working.{RESET}")
    print(f"{YELLOW}Continue? (yes/no){RESET}")
    confirm = input().strip().lower()

    if confirm in ['yes', 'y']:
        # Clear secret and re-run enable
        update_auth_settings(totp_secret=None)
        return enable_2fa()
    else:
        print("Cancelled.")
        return False

def unlock_account():
    """Unlock the account and reset failed attempts."""
    update_auth_settings(failed_attempts=0, locked_until=None)
    print(f"\n{GREEN}✓ Account unlocked.{RESET}")
    print("Failed attempts reset to 0.\n")
    return True

def verify_code(code):
    """Verify a TOTP code (used by web app)."""
    settings = get_auth_settings()

    if not settings['totp_enabled'] or not settings['totp_secret']:
        print("2FA not enabled")
        return False

    totp = pyotp.TOTP(settings['totp_secret'])
    if totp.verify(code):
        print("valid")
        return True
    else:
        print("invalid")
        return False

def interactive_menu():
    """Show interactive menu."""
    while True:
        settings = get_auth_settings()

        print(f"\n{CYAN}┌─────────────────────────────────────────┐{RESET}")
        print(f"{CYAN}│{RESET}  {BOLD}CodeHero 2FA Management{RESET}                {CYAN}│{RESET}")
        print(f"{CYAN}├─────────────────────────────────────────┤{RESET}")

        # Show current status
        if settings['totp_enabled'] and settings['totp_secret']:
            status = f"{GREEN}ON ✓{RESET}"
        elif settings['totp_enabled']:
            status = f"{YELLOW}ON (pending){RESET}"
        else:
            status = f"{YELLOW}OFF{RESET}"
        print(f"{CYAN}│{RESET}  Status: {status}                          {CYAN}│{RESET}")

        print(f"{CYAN}├─────────────────────────────────────────┤{RESET}")
        print(f"{CYAN}│{RESET}  1. Enable 2FA (show QR code)           {CYAN}│{RESET}")
        print(f"{CYAN}│{RESET}  2. Disable 2FA                         {CYAN}│{RESET}")
        print(f"{CYAN}│{RESET}  3. Reset 2FA (new QR code)             {CYAN}│{RESET}")
        print(f"{CYAN}│{RESET}  4. Unlock account                      {CYAN}│{RESET}")
        print(f"{CYAN}│{RESET}  5. Show status                         {CYAN}│{RESET}")
        print(f"{CYAN}│{RESET}  6. Exit                                {CYAN}│{RESET}")
        print(f"{CYAN}└─────────────────────────────────────────┘{RESET}")

        choice = input("\nSelect option: ").strip()

        if choice == '1':
            enable_2fa()
        elif choice == '2':
            disable_2fa()
        elif choice == '3':
            reset_2fa()
        elif choice == '4':
            unlock_account()
        elif choice == '5':
            show_status()
        elif choice == '6':
            print("Bye!")
            break
        else:
            print(f"{RED}Invalid option.{RESET}")

def main():
    parser = argparse.ArgumentParser(description='CodeHero 2FA Management')
    parser.add_argument('command', nargs='?', default='menu',
                        choices=['menu', 'enable', 'disable', 'reset', 'unlock', 'status', 'verify'],
                        help='Command to run')
    parser.add_argument('--code', help='TOTP code for verification')

    args = parser.parse_args()

    if args.command == 'menu':
        if not DEPS_AVAILABLE:
            print(f"{RED}Error: Required packages not installed.{RESET}")
            print(f"Run: pip install pyotp qrcode")
            sys.exit(1)
        interactive_menu()
    elif args.command == 'enable':
        enable_2fa()
    elif args.command == 'disable':
        disable_2fa()
    elif args.command == 'reset':
        reset_2fa()
    elif args.command == 'unlock':
        unlock_account()
    elif args.command == 'status':
        show_status()
    elif args.command == 'verify':
        if not args.code:
            print("Error: --code required for verify")
            sys.exit(1)
        verify_code(args.code)

if __name__ == '__main__':
    main()
