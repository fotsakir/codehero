# CodeHero Multi-User System Plan

**Version:** 2.77.0 (planned)
**Date:** 2026-01-20

## Overview

Προσθήκη multi-user system με:
- Πολλαπλοί χρήστες (όλοι βλέπουν όλα)
- Μόνο ο admin δημιουργεί users
- IP blocking μετά από 5 αποτυχημένες προσπάθειες
- Υποχρεωτικό 2FA με Google Authenticator

---

## 1. Database Schema

### 1.1 Users Table

```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'user') DEFAULT 'user',
    totp_secret VARCHAR(32) DEFAULT NULL,
    totp_enabled BOOLEAN DEFAULT FALSE,  -- Admin enables per user
    must_change_password BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    created_by INT DEFAULT NULL,
    last_login TIMESTAMP NULL,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);
```

### 1.2 Login Attempts Table

```sql
CREATE TABLE login_attempts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    ip_address VARCHAR(45) NOT NULL,
    username VARCHAR(50) DEFAULT NULL,
    success BOOLEAN DEFAULT FALSE,
    attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_ip_time (ip_address, attempted_at),
    INDEX idx_username (username)
);
```

### 1.3 Blocked IPs Table

```sql
CREATE TABLE blocked_ips (
    ip_address VARCHAR(45) PRIMARY KEY,
    blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    blocked_until TIMESTAMP NOT NULL,
    reason VARCHAR(100) DEFAULT 'Too many failed login attempts',
    failed_attempts INT DEFAULT 5
);
```

### 1.4 User Sessions Table (optional, για tracking)

```sql
CREATE TABLE user_sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    session_token VARCHAR(64) UNIQUE NOT NULL,
    ip_address VARCHAR(45),
    user_agent VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_token (session_token),
    INDEX idx_expires (expires_at)
);
```

---

## 2. Security Settings

### 2.1 Password Policy

| Setting | Value |
|---------|-------|
| Minimum length | 8 characters |
| Require uppercase | Yes |
| Require lowercase | Yes |
| Require number | Yes |
| Require special char | Optional |
| Hash algorithm | bcrypt (cost 12) |

### 2.2 IP Blocking Policy

| Setting | Value |
|---------|-------|
| Max failed attempts | 5 |
| Time window | 15 minutes |
| Block duration | 30 minutes |
| Auto-unblock | Yes (after duration) |

### 2.3 2FA Settings

| Setting | Value |
|---------|-------|
| Algorithm | TOTP (RFC 6238) |
| Library | pyotp |
| Digits | 6 |
| Interval | 30 seconds |
| Default | **Disabled** |
| Enabled by | Admin only (per user) |
| Issuer name | "CodeHero" |

---

## 3. User Flows

### 3.1 Login Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                         LOGIN FLOW                               │
└─────────────────────────────────────────────────────────────────┘

1. User visits /login
         │
         ▼
2. Check IP blocked? ──────Yes──────► Show "IP blocked" message
         │                            (με χρόνο που απομένει)
         No
         │
         ▼
3. User enters username + password
         │
         ▼
4. Validate credentials ───Failed───► Log attempt
         │                            │
         │                            ▼
         │                      5 attempts in 15min?
         │                            │
         │                      Yes───► Block IP 30min
         │                            │
         │                      No────► Show "Invalid credentials"
         │
         Success
         │
         ▼
5. 2FA enabled for user? ──No───────► Skip to step 8
         │
         Yes
         │
         ▼
6. 2FA setup done? ────────No───────► Redirect to /setup-2fa
         │
         Yes
         │
         ▼
7. Show 2FA code input
         │
         ▼
8. Validate TOTP code ────Failed────► Show "Invalid code"
         │                            (δεν μετράει στο IP blocking)
         │
         Success
         │
         ▼
9. Must change password? ──Yes──────► Redirect to /change-password
         │
         No
         │
         ▼
10. Create session, redirect to /dashboard
```

### 3.2 2FA Setup Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                       2FA SETUP FLOW                             │
└─────────────────────────────────────────────────────────────────┘

1. Generate TOTP secret (32 chars base32)
         │
         ▼
2. Create provisioning URI
   otpauth://totp/CodeHero:{username}?secret={secret}&issuer=CodeHero
         │
         ▼
3. Generate QR code (qrcode library)
         │
         ▼
4. Display to user:
   ┌─────────────────────────────────────┐
   │  Scan this QR code with            │
   │  Google Authenticator              │
   │                                    │
   │       ┌─────────────┐              │
   │       │ [QR CODE]   │              │
   │       └─────────────┘              │
   │                                    │
   │  Or enter manually:                │
   │  JBSW Y3DP EHPK 3PXP               │
   │                                    │
   │  Enter 6-digit code: [______]      │
   │                                    │
   │           [Verify]                 │
   └─────────────────────────────────────┘
         │
         ▼
5. User scans QR, enters code
         │
         ▼
6. Verify code matches ────Failed────► Show "Invalid code, try again"
         │
         Success
         │
         ▼
7. Save totp_secret to database
         │
         ▼
8. Redirect to dashboard
```

### 3.3 Admin Creates User Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    ADMIN CREATE USER FLOW                        │
└─────────────────────────────────────────────────────────────────┘

1. Admin goes to Settings → Users
         │
         ▼
2. Clicks [+ New User]
         │
         ▼
3. Fills form:
   ┌─────────────────────────────────────┐
   │  Create New User                   │
   │                                    │
   │  Username: [________________]      │
   │  Role:     [User ▼]                │
   │            - User                  │
   │            - Admin                 │
   │                                    │
   │  ☐ Enable 2FA (user must setup)    │
   │                                    │
   │  [Cancel]  [Create User]           │
   └─────────────────────────────────────┘
         │
         ▼
4. System generates temporary password
         │
         ▼
5. Show to admin:
   ┌─────────────────────────────────────┐
   │  ✓ User created!                   │
   │                                    │
   │  Username: developer1              │
   │  Temporary password: TempP@ss#847  │
   │  2FA: Disabled                     │
   │                                    │
   │  ⚠️ Ο χρήστης πρέπει να αλλάξει    │
   │  τον κωδικό στο πρώτο login.       │
   │                                    │
   │  [Copy credentials]  [Close]       │
   └─────────────────────────────────────┘
         │
         ▼
6. New user logs in:
   - Enters temp password
   - Forced to change password
   - If 2FA enabled → Setup 2FA
   - Ready!
```

---

## 4. Admin UI

### 4.1 User Management Page

```
┌─────────────────────────────────────────────────────────────────┐
│  Settings › User Management                      [+ New User]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ Username     │ Role   │ 2FA      │ Status   │ Last Login │ Actions│
│  ├─────────────────────────────────────────────────────────────┤│
│  │ admin        │ Admin  │ [ON]  ✓  │ Active   │ 5 min ago  │ [···] ││
│  │ developer1   │ User   │ [ON]  ✓  │ Active   │ 2 hours    │ [···] ││
│  │ developer2   │ User   │ [OFF]    │ Active   │ Never      │ [···] ││
│  │ tester       │ User   │ [ON]  ⚠  │ Active   │ Never      │ [···] ││
│  │ olduser      │ User   │ [OFF]    │ Disabled │ 30 days    │ [···] ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  2FA Status:                                                    │
│    [ON] ✓ = Enabled + Setup complete                            │
│    [ON] ⚠ = Enabled but not setup yet (pending)                 │
│    [OFF]  = Disabled                                            │
│                                                                 │
│  [···] Actions menu:                                            │
│    • Edit User                                                  │
│    • Reset Password                                             │
│    • Enable 2FA / Disable 2FA  ← Admin toggle                   │
│    • Reset 2FA (if enabled)                                     │
│    • Disable / Enable user                                      │
│    • Delete (με confirmation)                                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Blocked IPs Page

```
┌─────────────────────────────────────────────────────────────────┐
│  Settings › Blocked IPs                                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │ IP Address      │ Blocked At        │ Until          │      ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ 192.168.1.50    │ 2026-01-20 16:00  │ 16:30 (10 min) │ [Unblock]│
│  │ 10.0.0.15       │ 2026-01-20 15:45  │ 16:15 (expired)│ [Remove] │
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  ℹ️ IPs ξεμπλοκάρονται αυτόματα μετά από 30 λεπτά.              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.3 Navigation (Admin)

```
Sidebar:
├── 📊 Dashboard
├── 📁 Projects
├── 🎫 Tickets
├── 💻 Console
├── 📜 History
├── ⚙️ Settings
│   ├── 👥 Users           ← NEW (admin only)
│   ├── 🚫 Blocked IPs     ← NEW (admin only)
│   ├── 📦 Packages
│   └── ℹ️ System Info
└── 🚪 Logout (username)   ← Shows current user
```

---

## 5. Command Line Tools

### 5.1 User Admin Script

**Location:** `/opt/codehero/scripts/user-admin.sh`

#### Interactive Mode

```bash
sudo /opt/codehero/scripts/user-admin.sh

┌─────────────────────────────────────────┐
│  CodeHero User Administration           │
├─────────────────────────────────────────┤
│  1. List users                          │
│  2. Reset password                      │
│  3. Enable/Disable 2FA                  │
│  4. Reset 2FA secret                    │
│  5. Reset all (password + 2FA)          │
│  6. Enable/Disable user                 │
│  7. Unblock IP address                  │
│  8. List blocked IPs                    │
│  9. Exit                                │
└─────────────────────────────────────────┘

Select option: _
```

#### Direct Commands

```bash
# List all users
sudo /opt/codehero/scripts/user-admin.sh list
# Output:
# ID  Username     Role   2FA       Status    Last Login
# 1   admin        Admin  ON ✓      Active    2026-01-20 15:30
# 2   developer1   User   ON ✓      Active    2026-01-20 14:00
# 3   developer2   User   OFF       Active    Never
# 4   tester       User   ON ⚠      Active    Never  (pending setup)

# Reset password
sudo /opt/codehero/scripts/user-admin.sh reset-password <username>
# Output:
# ✓ Password reset for 'admin'
# New temporary password: TempP@ss#293
# User must change password on next login.

# Enable 2FA for user
sudo /opt/codehero/scripts/user-admin.sh enable-2fa <username>
# Output:
# ✓ 2FA enabled for 'developer2'
# User must setup 2FA on next login.

# Disable 2FA for user
sudo /opt/codehero/scripts/user-admin.sh disable-2fa <username>
# Output:
# ✓ 2FA disabled for 'developer1'
# 2FA secret cleared.

# Reset 2FA secret (keep enabled, clear secret for re-setup)
sudo /opt/codehero/scripts/user-admin.sh reset-2fa <username>
# Output:
# ✓ 2FA secret reset for 'admin'
# User must setup 2FA again on next login.

# Reset all (password + disable 2FA)
sudo /opt/codehero/scripts/user-admin.sh reset-all <username>
# Output:
# ✓ Password reset for 'admin'
# New temporary password: TempP@ss#517
# ✓ 2FA disabled for 'admin'
# User must change password on next login.

# Disable user
sudo /opt/codehero/scripts/user-admin.sh disable <username>
# Output:
# ✓ User 'developer1' disabled.

# Enable user
sudo /opt/codehero/scripts/user-admin.sh enable <username>
# Output:
# ✓ User 'developer1' enabled.

# Unblock IP
sudo /opt/codehero/scripts/user-admin.sh unblock-ip <ip_address>
# Output:
# ✓ IP 192.168.1.50 unblocked.

# List blocked IPs
sudo /opt/codehero/scripts/user-admin.sh blocked
# Output:
# IP Address       Blocked Until         Reason
# 192.168.1.50     2026-01-20 16:30     5 failed attempts
# 10.0.0.15        2026-01-20 16:15     5 failed attempts
```

### 5.2 Python Helper Script

**Location:** `/opt/codehero/scripts/user_admin.py`

Το shell script καλεί αυτό το Python script για database operations:

```python
#!/usr/bin/env python3
"""CodeHero User Administration Helper"""

import sys
import bcrypt
import secrets
import string
import mysql.connector
from pathlib import Path

def generate_temp_password(length=12):
    """Generate a secure temporary password."""
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def hash_password(password):
    """Hash password with bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(12)).decode()

def reset_password(username):
    """Reset user's password to a temporary one."""
    temp_password = generate_temp_password()
    hashed = hash_password(temp_password)
    # Update database...
    return temp_password

def reset_2fa(username):
    """Clear user's TOTP secret."""
    # UPDATE users SET totp_secret = NULL WHERE username = ?
    pass

def unblock_ip(ip_address):
    """Remove IP from blocked list."""
    # DELETE FROM blocked_ips WHERE ip_address = ?
    pass

# ... etc
```

---

## 6. Migration Plan

### 6.1 For Existing Installations (Upgrade)

**Migration script:** `database/migrations/2.77.0_multi_user.sql`

```sql
-- Create tables
CREATE TABLE IF NOT EXISTS users (...);
CREATE TABLE IF NOT EXISTS login_attempts (...);
CREATE TABLE IF NOT EXISTS blocked_ips (...);

-- Migrate existing admin from install.conf
-- This is done by the upgrade script (2.77.0.sh), not SQL
```

**Upgrade script:** `upgrades/2.77.0.sh`

```bash
#!/bin/bash
log_info() { echo -e "\033[0;36m[2.77.0]\033[0m $1"; }

log_info "Migrating to multi-user system..."

# Read current credentials from install.conf
source /opt/codehero/install.conf

# Create admin user in database
python3 /opt/codehero/scripts/user_admin.py migrate-admin \
    --username "$ADMIN_USER" \
    --password "$ADMIN_PASSWORD"

log_info "Admin user migrated to database"
log_info "2FA setup will be required on next login"
```

### 6.2 For Fresh Installations

**setup.sh** modifications:

```bash
# After database creation, create admin user
python3 /opt/codehero/scripts/user_admin.py create-admin \
    --username "$ADMIN_USER" \
    --password "$ADMIN_PASSWORD"
```

---

## 7. Dependencies

### 7.1 New Python Packages

```
bcrypt>=4.0.0      # Password hashing
pyotp>=2.8.0       # TOTP (2FA)
qrcode>=7.4.0      # QR code generation
Pillow>=10.0.0     # Image handling for QR codes
```

### 7.2 Installation

```bash
pip install bcrypt pyotp qrcode Pillow
```

---

## 8. Files to Create/Modify

### 8.1 New Files

| File | Description |
|------|-------------|
| `database/migrations/2.77.0_multi_user.sql` | Database schema |
| `upgrades/2.77.0.sh` | Upgrade script |
| `scripts/user-admin.sh` | CLI user management (shell wrapper) |
| `scripts/user_admin.py` | CLI user management (Python) |
| `web/templates/login_2fa.html` | 2FA code input page |
| `web/templates/setup_2fa.html` | 2FA setup with QR code |
| `web/templates/change_password.html` | Password change page |
| `web/templates/users.html` | User management page (admin) |
| `web/templates/blocked_ips.html` | Blocked IPs page (admin) |

### 8.2 Modified Files

| File | Changes |
|------|---------|
| `web/app.py` | Auth logic, new routes, 2FA, IP blocking |
| `web/templates/dashboard.html` | Show current user, logout link |
| `web/templates/login.html` | Update design, show block message |
| `database/schema.sql` | Add new tables |
| `setup.sh` | Install new dependencies, create admin |

---

## 9. API Routes

### 9.1 Authentication Routes

| Route | Method | Description |
|-------|--------|-------------|
| `/login` | GET/POST | Login page |
| `/login/2fa` | GET/POST | 2FA verification |
| `/setup-2fa` | GET/POST | 2FA setup (QR) |
| `/change-password` | GET/POST | Change password |
| `/logout` | GET | Logout |

### 9.2 Admin Routes (require admin role)

| Route | Method | Description |
|-------|--------|-------------|
| `/admin/users` | GET | List users |
| `/admin/users/create` | POST | Create user |
| `/admin/users/<id>/edit` | POST | Edit user |
| `/admin/users/<id>/reset-password` | POST | Reset password |
| `/admin/users/<id>/enable-2fa` | POST | Enable 2FA |
| `/admin/users/<id>/disable-2fa` | POST | Disable 2FA |
| `/admin/users/<id>/reset-2fa` | POST | Reset 2FA secret |
| `/admin/users/<id>/toggle-active` | POST | Enable/disable user |
| `/admin/users/<id>/delete` | POST | Delete user |
| `/admin/blocked-ips` | GET | List blocked IPs |
| `/admin/blocked-ips/<ip>/unblock` | POST | Unblock IP |

---

## 10. Security Considerations

### 10.1 Session Security

- Session cookie: `HttpOnly`, `Secure`, `SameSite=Strict`
- Session timeout: 24 hours (configurable)
- Session invalidation on password change

### 10.2 Password Security

- Never store plain text
- Use bcrypt with cost 12
- Enforce password policy
- Prevent password reuse (optional, future)

### 10.3 2FA Security

- TOTP secrets stored encrypted (optional, future)
- Rate limit 2FA attempts (5 per minute)
- Backup codes (optional, future)

### 10.4 IP Blocking

- Use X-Forwarded-For header (behind proxy)
- Whitelist localhost (127.0.0.1, ::1)
- Log all blocks for audit

---

## 11. Testing Checklist

### Authentication
- [ ] Login with correct credentials (no 2FA)
- [ ] Login with correct credentials (with 2FA)
- [ ] Login with wrong password (5x → block)
- [ ] Login after IP blocked
- [ ] 2FA setup flow (when enabled by admin)
- [ ] 2FA login flow
- [ ] 2FA with wrong code
- [ ] Login without 2FA when disabled
- [ ] Password change (forced)
- [ ] Password change (voluntary)

### Admin UI
- [ ] Admin: Create user (without 2FA)
- [ ] Admin: Create user (with 2FA enabled)
- [ ] Admin: Reset password
- [ ] Admin: Enable 2FA for user
- [ ] Admin: Disable 2FA for user
- [ ] Admin: Reset 2FA secret
- [ ] Admin: Disable user
- [ ] Admin: Enable user
- [ ] Admin: Delete user
- [ ] Admin: View blocked IPs
- [ ] Admin: Unblock IP

### CLI Tools
- [ ] CLI: list users
- [ ] CLI: reset-password
- [ ] CLI: enable-2fa
- [ ] CLI: disable-2fa
- [ ] CLI: reset-2fa
- [ ] CLI: reset-all
- [ ] CLI: disable user
- [ ] CLI: enable user
- [ ] CLI: unblock-ip
- [ ] CLI: list blocked IPs

### Installation
- [ ] Upgrade from previous version
- [ ] Fresh installation

---

## 12. Timeline

| Phase | Tasks | Estimate |
|-------|-------|----------|
| 1 | Database schema, migrations | Day 1 |
| 2 | Backend auth logic, 2FA | Day 1-2 |
| 3 | Login/2FA templates | Day 2 |
| 4 | Admin UI (users, blocked IPs) | Day 2-3 |
| 5 | CLI tools | Day 3 |
| 6 | Testing, bug fixes | Day 3-4 |
| 7 | Documentation | Day 4 |

---

**Status:** Planning
**Next step:** User approval, then implementation
