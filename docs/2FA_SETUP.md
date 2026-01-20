# Two-Factor Authentication (2FA) Setup

CodeHero supports optional Two-Factor Authentication using Google Authenticator or any TOTP-compatible app.

## Features

- **TOTP-based 2FA** - Works with Google Authenticator, Authy, Microsoft Authenticator, etc.
- **Account Lockout** - Automatic lockout after 5 failed login attempts (30 min)
- **Remember Device** - Skip 2FA on trusted devices until end of month
- **Terminal Management** - Enable/disable 2FA from command line

---

## Quick Start

### 1. Enable 2FA

```bash
sudo /opt/codehero/scripts/manage-2fa.sh
```

Select option **1. Enable 2FA**

### 2. Scan QR Code

A QR code will appear in the terminal. Scan it with your authenticator app:

- **Google Authenticator** (Android/iOS)
- **Authy** (Android/iOS/Desktop)
- **Microsoft Authenticator** (Android/iOS)

Or manually enter the secret code shown below the QR.

### 3. Verify Setup

Enter the 6-digit code from your authenticator app to verify:

```
Enter 6-digit code to verify: 482910

✓ 2FA enabled successfully!
```

### 4. Login with 2FA

Next time you login:

1. Enter username and password
2. Enter the 6-digit code from your authenticator
3. (Optional) Check "Remember this device" to skip 2FA until end of month

---

## Management Commands

### Interactive Menu

```bash
sudo /opt/codehero/scripts/manage-2fa.sh
```

```
┌─────────────────────────────────────────┐
│  CodeHero 2FA Management                │
├─────────────────────────────────────────┤
│  Status: OFF                            │
├─────────────────────────────────────────┤
│  1. Enable 2FA (show QR code)           │
│  2. Disable 2FA                         │
│  3. Reset 2FA (new QR code)             │
│  4. Unlock account                      │
│  5. Show status                         │
│  6. Exit                                │
└─────────────────────────────────────────┘
```

### Direct Commands

```bash
# Enable 2FA
sudo /opt/codehero/scripts/manage-2fa.sh enable

# Disable 2FA
sudo /opt/codehero/scripts/manage-2fa.sh disable

# Reset 2FA (generate new QR code)
sudo /opt/codehero/scripts/manage-2fa.sh reset

# Unlock account after failed attempts
sudo /opt/codehero/scripts/manage-2fa.sh unlock

# Show current status
sudo /opt/codehero/scripts/manage-2fa.sh status
```

---

## Account Lockout

If you enter the wrong password **5 times**, the account locks for **30 minutes**.

### Check Status

```bash
sudo /opt/codehero/scripts/manage-2fa.sh status
```

```
CodeHero Authentication Status
==================================================

  2FA Status:      Enabled ✓
  Account Status:  Locked (unlocks in 25 min)
  Failed Attempts: 5/5
```

### Unlock Manually

```bash
sudo /opt/codehero/scripts/manage-2fa.sh unlock
```

```
✓ Account unlocked.
Failed attempts reset to 0.
```

---

## Remember Device

When logging in with 2FA, you can check **"Remember this device"**:

- The device is trusted until the **end of the current month**
- No 2FA code required for subsequent logins
- Automatically expires and requires 2FA again next month

### How it Works

1. Login with username + password
2. Enter 2FA code
3. Check "Remember this device"
4. Click Verify

A secure cookie is set that expires at month end.

---

## Lost Access to Authenticator?

If you lose your phone or can't access your authenticator app:

### Option 1: Reset via Terminal

SSH into the server and run:

```bash
sudo /opt/codehero/scripts/manage-2fa.sh disable
```

Then re-enable and scan a new QR code.

### Option 2: Disable 2FA

```bash
sudo /opt/codehero/scripts/manage-2fa.sh disable
```

You can now login with just username and password.

---

## Security Recommendations

1. **Enable 2FA** - Adds an extra layer of security
2. **Use a reputable authenticator app** - Google Authenticator, Authy, etc.
3. **Don't share your secret** - The QR code/secret is sensitive
4. **Backup your authenticator** - Some apps support cloud backup
5. **Use strong passwords** - 2FA is not a substitute for good passwords

---

## Troubleshooting

### "Invalid code" error

- Make sure your phone's time is correct (TOTP is time-based)
- Wait for a new code if current one is about to expire
- Verify you're using the correct authenticator entry

### Account locked

```bash
sudo /opt/codehero/scripts/manage-2fa.sh unlock
```

### QR code not scanning

Enter the secret code manually in your authenticator app:
- Select "Enter manually" or "Add account"
- Account name: `admin`
- Secret key: (the code shown below QR)
- Type: Time-based (TOTP)

### Reset everything

```bash
# Disable 2FA
sudo /opt/codehero/scripts/manage-2fa.sh disable

# Unlock account
sudo /opt/codehero/scripts/manage-2fa.sh unlock

# Re-enable fresh
sudo /opt/codehero/scripts/manage-2fa.sh enable
```
