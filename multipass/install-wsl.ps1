# Fotios Claude System - WSL2 Installer
# Run this script as Administrator (Right-click > Run as Administrator)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Fotios Claude System - WSL2 Setup      " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Please run this script as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if WSL is installed
Write-Host "[1/4] Checking WSL status..." -ForegroundColor Yellow
$wslInstalled = $false
try {
    $wslStatus = wsl --status 2>&1
    if ($LASTEXITCODE -eq 0) {
        $wslInstalled = $true
        Write-Host "      WSL is installed." -ForegroundColor Green
    }
} catch {}

if (-not $wslInstalled) {
    Write-Host "      WSL not found. Installing WSL2..." -ForegroundColor Yellow
    Write-Host "      This may require a RESTART." -ForegroundColor Red
    wsl --install --no-distribution
    Write-Host ""
    Write-Host "      WSL2 installed. Please RESTART your computer," -ForegroundColor Yellow
    Write-Host "      then run this script again." -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 0
}

# Check if Ubuntu-24.04 is installed
Write-Host "[2/4] Checking for Ubuntu 24.04..." -ForegroundColor Yellow
$ubuntuInstalled = $false
$distros = wsl --list --quiet 2>$null
if ($distros -match "Ubuntu-24.04") {
    $ubuntuInstalled = $true
    Write-Host "      Ubuntu 24.04 is already installed." -ForegroundColor Green
}

if (-not $ubuntuInstalled) {
    Write-Host "      Installing Ubuntu 24.04..." -ForegroundColor Yellow
    wsl --install -d Ubuntu-24.04 --no-launch
    Write-Host "      Ubuntu 24.04 installed!" -ForegroundColor Green
}

# Initialize Ubuntu with root as default user (skip user creation prompt)
Write-Host "[3/4] Initializing Ubuntu..." -ForegroundColor Yellow

# Use --exec to bypass the interactive OOBE (first-run user creation)
# This runs the command directly without starting an interactive shell
Write-Host "      Configuring root as default user..." -ForegroundColor Gray

# First, try to configure wsl.conf using --exec (bypasses OOBE)
# Enable systemd and set root as default user
$configResult = wsl -d Ubuntu-24.04 --exec /bin/bash -c "echo -e '[boot]\nsystemd=true\n\n[user]\ndefault=root' > /etc/wsl.conf" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Note: First-time initialization..." -ForegroundColor Gray
}

# Terminate to apply the wsl.conf settings
wsl --terminate Ubuntu-24.04 2>$null
Start-Sleep -Seconds 3

# Now it should work with root as default
Write-Host "      Testing connection..." -ForegroundColor Gray
$testResult = wsl -d Ubuntu-24.04 --exec /bin/bash -c "whoami" 2>&1
if ($testResult -match "root") {
    Write-Host "      Ubuntu ready! (running as root)" -ForegroundColor Green
} else {
    # Fallback: try with -u root
    wsl -d Ubuntu-24.04 -u root --exec /bin/bash -c "echo -e '[boot]\nsystemd=true\n\n[user]\ndefault=root' > /etc/wsl.conf" 2>$null
    wsl --terminate Ubuntu-24.04 2>$null
    Start-Sleep -Seconds 2
    Write-Host "      Ubuntu ready!" -ForegroundColor Green
}

# Run the installation inside WSL
Write-Host "[4/4] Installing Fotios Claude System inside WSL..." -ForegroundColor Yellow
Write-Host "      This takes about 10-15 minutes..." -ForegroundColor Gray
Write-Host ""

# Create install script file and copy to WSL
$installScriptContent = @"
#!/bin/bash
set -e
cd /root
echo "Updating packages..."
apt-get update
apt-get install -y unzip wget net-tools curl
echo "Downloading latest release..."
LATEST_URL=`$(curl -s https://api.github.com/repos/fotsakir/codehero/releases/latest | grep "browser_download_url.*zip" | cut -d '"' -f 4)
wget -q "`$LATEST_URL" -O fotios-claude-system.zip
rm -rf fotios-claude-system
unzip -q fotios-claude-system.zip
cd fotios-claude-system
chmod +x setup.sh
echo "Running setup..."
./setup.sh
echo "done" > /root/install-complete
"@

# Write script to temp file
$tempScript = "$env:TEMP\wsl-install.sh"
$installScriptContent | Out-File -FilePath $tempScript -Encoding utf8 -NoNewline

# Convert to Unix line endings and copy to WSL (use --exec to bypass OOBE)
$wslPath = wsl -d Ubuntu-24.04 --exec /bin/bash -c "wslpath -u '$tempScript'"
wsl -d Ubuntu-24.04 --exec /bin/bash -c "cat '$wslPath' | tr -d '\r' > /root/install-fotios.sh && chmod +x /root/install-fotios.sh && /root/install-fotios.sh"

# Cleanup
Remove-Item $tempScript -Force -ErrorAction SilentlyContinue

# Get IP address
Write-Host ""
Write-Host "      Getting IP address..." -ForegroundColor Gray
$ip = wsl -d Ubuntu-24.04 --exec hostname -I 2>$null | ForEach-Object { $_.Split()[0] }

if (-not $ip) {
    $ip = "[Run: wsl hostname -I]"
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  ACCESS POINTS:" -ForegroundColor Yellow
Write-Host "  Dashboard:    https://${ip}:9453" -ForegroundColor Cyan
Write-Host "  Web Projects: https://${ip}:9867" -ForegroundColor Cyan
Write-Host ""
Write-Host "  LOGIN:" -ForegroundColor Yellow
Write-Host "  Username:  admin" -ForegroundColor White
Write-Host "  Password:  admin123" -ForegroundColor White
Write-Host ""
Write-Host "  WSL COMMANDS:" -ForegroundColor Yellow
Write-Host "  Open terminal:  wsl -d Ubuntu-24.04" -ForegroundColor White
Write-Host "  Stop WSL:       wsl --shutdown" -ForegroundColor White
Write-Host "  Start services: wsl -d Ubuntu-24.04 --exec systemctl start fotios-claude-web fotios-claude-daemon" -ForegroundColor White
Write-Host ""
Write-Host "  CHANGE PASSWORDS:" -ForegroundColor Red
Write-Host "  wsl -d Ubuntu-24.04 --exec /opt/fotios-claude/scripts/change-passwords.sh" -ForegroundColor White
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Create desktop shortcuts
$desktopPath = [Environment]::GetFolderPath("Desktop")

# Create batch file that starts services and opens browser
$batchPath = Join-Path $desktopPath "Claude AI Developer (WSL).bat"
$batchContent = @"
@echo off
title Claude AI Developer (WSL)
echo.
echo ========================================
echo   Claude AI Developer (WSL)
echo ========================================
echo.
echo Starting services...
wsl -d Ubuntu-24.04 --exec /bin/bash -c "systemctl start mysql lshttpd fotios-claude-web fotios-claude-daemon" 2>nul

echo Getting IP address...
for /f "tokens=1" %%a in ('wsl -d Ubuntu-24.04 --exec hostname -I 2^>nul') do set IP=%%a

if "%IP%"=="" (
    echo ERROR: Could not get IP address
    echo Make sure WSL is running: wsl -d Ubuntu-24.04
    pause
    exit /b 1
)

echo.
echo Dashboard: https://%IP%:9453
echo.
echo Opening browser...
start https://%IP%:9453
echo.
echo Press any key to close...
pause >nul
"@
$batchContent | Out-File -FilePath $batchPath -Encoding ascii
Write-Host "Desktop shortcut created: Claude AI Developer (WSL).bat" -ForegroundColor Green

# Also create URL shortcut if we have valid IP
if ($ip -match "^\d+\.\d+\.\d+\.\d+$") {
    $urlPath = Join-Path $desktopPath "Claude Dashboard (WSL).url"
    $urlContent = @"
[InternetShortcut]
URL=https://${ip}:9453
IconIndex=0
"@
    $urlContent | Out-File -FilePath $urlPath -Encoding ascii
    Write-Host "Desktop shortcut created: Claude Dashboard (WSL).url" -ForegroundColor Green
}

Write-Host ""

# Open browser
$openBrowser = Read-Host "Open dashboard in browser? (y/n)"
if ($openBrowser -eq 'y') {
    Start-Process "https://${ip}:9453"
}

Read-Host "Press Enter to exit"
