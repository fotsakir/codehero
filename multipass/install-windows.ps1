# Fotios Claude System - Windows Installer
# Run this script as Administrator (Right-click > Run as Administrator)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Fotios Claude System - Windows Setup   " -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: Please run this script as Administrator!" -ForegroundColor Red
    Write-Host "Right-click the script and select 'Run as Administrator'" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if Hyper-V is available (Windows Pro/Enterprise) or need VirtualBox (Windows Home)
Write-Host "[1/6] Checking Windows edition..." -ForegroundColor Yellow
$hyperv = Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -ErrorAction SilentlyContinue
$needsVirtualBox = $false

if (-not $hyperv -or $hyperv.State -ne "Enabled") {
    # Check if this is Windows Home (no Hyper-V support)
    $edition = (Get-WmiObject -Class Win32_OperatingSystem).Caption
    if ($edition -match "Home") {
        Write-Host "      Windows Home detected - will use VirtualBox" -ForegroundColor Yellow
        $needsVirtualBox = $true
    } else {
        Write-Host "      Hyper-V not enabled. Enabling..." -ForegroundColor Yellow
        try {
            Enable-WindowsOptionalFeature -Online -FeatureName Microsoft-Hyper-V -All -NoRestart -ErrorAction Stop
            Write-Host "      Hyper-V enabled. Please RESTART and run this script again." -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 0
        } catch {
            Write-Host "      Could not enable Hyper-V - will use VirtualBox" -ForegroundColor Yellow
            $needsVirtualBox = $true
        }
    }
} else {
    Write-Host "      Hyper-V is available." -ForegroundColor Green
}

# Install VirtualBox if needed (Windows Home)
if ($needsVirtualBox) {
    Write-Host "[2/6] Checking for VirtualBox..." -ForegroundColor Yellow
    $vbox = Get-Command VBoxManage -ErrorAction SilentlyContinue

    if (-not $vbox) {
        Write-Host "      VirtualBox not found. Installing..." -ForegroundColor Yellow
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if ($winget) {
            winget install -e --id Oracle.VirtualBox --accept-package-agreements --accept-source-agreements
        } else {
            Write-Host "      Please install VirtualBox manually from: https://www.virtualbox.org/wiki/Downloads" -ForegroundColor Red
            Read-Host "Press Enter after installing VirtualBox"
        }
        # Refresh PATH
        $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    } else {
        Write-Host "      VirtualBox is installed." -ForegroundColor Green
    }
}

# Check if Multipass is installed
Write-Host "[3/6] Checking for Multipass..." -ForegroundColor Yellow
$multipass = Get-Command multipass -ErrorAction SilentlyContinue

if (-not $multipass) {
    Write-Host "      Multipass not found. Installing..." -ForegroundColor Yellow

    # Check if winget is available
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($winget) {
        Write-Host "      Using winget to install Multipass..." -ForegroundColor Gray
        winget install -e --id Canonical.Multipass --accept-package-agreements --accept-source-agreements
    } else {
        Write-Host "      Downloading Multipass installer..." -ForegroundColor Gray
        $installerUrl = "https://multipass.run/download/windows"
        $installerPath = "$env:TEMP\multipass-installer.exe"
        Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
        Write-Host "      Running installer..." -ForegroundColor Gray
        Start-Process -FilePath $installerPath -Wait
        Remove-Item $installerPath -Force
    }

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    Write-Host "      Multipass installed!" -ForegroundColor Green
} else {
    Write-Host "      Multipass is already installed." -ForegroundColor Green
}

# Configure Multipass to use VirtualBox if needed
if ($needsVirtualBox) {
    Write-Host "      Configuring Multipass to use VirtualBox..." -ForegroundColor Yellow

    # Stop service completely
    Write-Host "      Stopping Multipass service..." -ForegroundColor Gray
    Stop-Service Multipass -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 5

    # Write driver setting directly to config file (bypasses socket issue)
    Write-Host "      Writing VirtualBox driver to config..." -ForegroundColor Gray
    $configDir = "C:\ProgramData\Multipass\data"
    $configFile = "$configDir\multipassd\multipassd.conf"

    # Create directory if needed
    New-Item -ItemType Directory -Path "$configDir\multipassd" -Force -ErrorAction SilentlyContinue | Out-Null

    # Write config
    @"
[General]
driver=virtualbox
"@ | Out-File -FilePath $configFile -Encoding utf8 -Force

    Write-Host "      Config written to: $configFile" -ForegroundColor Gray

    # Start service
    Write-Host "      Starting Multipass service..." -ForegroundColor Gray
    Start-Service Multipass -ErrorAction SilentlyContinue

    # Wait longer for VirtualBox initialization
    Write-Host "      Waiting for VirtualBox initialization (30 seconds)..." -ForegroundColor Gray
    Start-Sleep -Seconds 30

    # Test connection with retries
    Write-Host "      Testing Multipass connection..." -ForegroundColor Gray
    $maxRetries = 5
    $retryCount = 0
    $connected = $false

    while ($retryCount -lt $maxRetries -and -not $connected) {
        $retryCount++
        $testResult = & multipass list 2>&1
        if ($testResult -match "No instances found" -or $testResult -match "Name") {
            Write-Host "      Multipass connection OK!" -ForegroundColor Green
            $connected = $true
        } else {
            Write-Host "      Retry $retryCount/$maxRetries - waiting 10 more seconds..." -ForegroundColor Yellow
            Start-Sleep -Seconds 10
        }
    }

    if (-not $connected) {
        Write-Host "      ERROR: Could not connect to Multipass" -ForegroundColor Red
        Write-Host "      Please try:" -ForegroundColor Yellow
        Write-Host "        1. Restart your computer" -ForegroundColor White
        Write-Host "        2. Run this script again" -ForegroundColor White
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Download cloud-init
Write-Host "[4/6] Downloading configuration..." -ForegroundColor Yellow
$cloudInitUrl = "https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/cloud-init.yaml"
$cloudInitPath = "$env:TEMP\cloud-init.yaml"
Invoke-WebRequest -Uri $cloudInitUrl -OutFile $cloudInitPath
Write-Host "      Done." -ForegroundColor Green

# Check if VM already exists
Write-Host "[5/6] Checking for existing VM..." -ForegroundColor Yellow
$existingVm = multipass list --format csv | Select-String "claude-dev"
if ($existingVm) {
    Write-Host "      VM 'claude-dev' already exists!" -ForegroundColor Yellow
    $response = Read-Host "      Delete and recreate? (y/n)"
    if ($response -eq 'y') {
        Write-Host "      Deleting existing VM..." -ForegroundColor Gray
        multipass delete claude-dev --purge
    } else {
        Write-Host "      Keeping existing VM. Exiting." -ForegroundColor Yellow
        exit 0
    }
}

# Create VM
Write-Host "[6/6] Creating VM (this takes 15-20 minutes)..." -ForegroundColor Yellow
Write-Host "      - Name: claude-dev" -ForegroundColor Gray
Write-Host "      - Memory: 4GB" -ForegroundColor Gray
Write-Host "      - Disk: 40GB" -ForegroundColor Gray
Write-Host "      - OS: Ubuntu 24.04 LTS" -ForegroundColor Gray
Write-Host ""
Write-Host "      Please wait..." -ForegroundColor Gray

multipass launch 24.04 --name claude-dev --memory 4G --disk 40G --cpus 2 --timeout 1800 --cloud-init $cloudInitPath

# Wait for cloud-init to complete
Write-Host "      Waiting for installation to complete..." -ForegroundColor Yellow
Write-Host "      This may take 10-15 more minutes..." -ForegroundColor Gray

# Poll for completion
$maxWait = 1200  # 20 minutes
$waited = 0
$interval = 30

$ErrorActionPreference = "SilentlyContinue"

while ($waited -lt $maxWait) {
    Start-Sleep -Seconds $interval
    $waited += $interval

    # Check if install completed
    $status = & multipass exec claude-dev -- cat /root/install-complete 2>$null
    if ($LASTEXITCODE -eq 0 -and $status -match "done") {
        break
    }

    # Check if services are running
    $webRunning = & multipass exec claude-dev -- systemctl is-active fotios-claude-web 2>$null
    if ($LASTEXITCODE -eq 0 -and $webRunning -match "active") {
        break
    }

    $minutes = [math]::Floor($waited / 60)
    Write-Host "      Still installing... ($minutes minutes elapsed)" -ForegroundColor Gray
}

$ErrorActionPreference = "Stop"

# Get IP address
$ip = multipass exec claude-dev -- hostname -I | ForEach-Object { $_.Split()[0] }

# Cleanup
Remove-Item $cloudInitPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  Installation Complete!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  ACCESS POINTS:" -ForegroundColor Yellow
Write-Host "  Dashboard:    https://${ip}:9453" -ForegroundColor Cyan
Write-Host "  Web Projects: https://${ip}:9867" -ForegroundColor Cyan
Write-Host "  OLS Admin:    https://${ip}:7080" -ForegroundColor Cyan
Write-Host ""
Write-Host "  LOGIN:" -ForegroundColor Yellow
Write-Host "  Username:  admin" -ForegroundColor White
Write-Host "  Password:  admin123" -ForegroundColor White
Write-Host ""
Write-Host "  VM TERMINAL:" -ForegroundColor Yellow
Write-Host "  multipass shell claude-dev" -ForegroundColor White
Write-Host ""
Write-Host "  CHANGE PASSWORDS (via Web Terminal or SSH):" -ForegroundColor Red
Write-Host "  sudo /opt/fotios-claude/scripts/change-passwords.sh" -ForegroundColor White
Write-Host ""
Write-Host "  DAILY USAGE:" -ForegroundColor Yellow
Write-Host "  Start VM:   multipass start claude-dev" -ForegroundColor White
Write-Host "  Stop VM:    multipass stop claude-dev" -ForegroundColor White
Write-Host "  VM Status:  multipass list" -ForegroundColor White
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Create desktop shortcut
$desktopPath = [Environment]::GetFolderPath("Desktop")
$shortcutPath = Join-Path $desktopPath "Claude AI Developer.url"

$shortcutContent = @"
[InternetShortcut]
URL=https://${ip}:9453
IconIndex=0
"@

$shortcutContent | Out-File -FilePath $shortcutPath -Encoding ascii
Write-Host "Desktop shortcut created: Claude AI Developer" -ForegroundColor Green

# Also create a batch file to start the VM
$startVmPath = Join-Path $desktopPath "Start Claude VM.bat"
$startVmContent = @"
@echo off
echo Starting Claude AI Developer VM...
multipass start claude-dev
echo.
echo VM started! Opening dashboard...
timeout /t 5 /nobreak >nul
start https://${ip}:9453
"@
$startVmContent | Out-File -FilePath $startVmPath -Encoding ascii
Write-Host "Desktop shortcut created: Start Claude VM" -ForegroundColor Green

Write-Host ""

# Open browser
$openBrowser = Read-Host "Open dashboard in browser? (y/n)"
if ($openBrowser -eq 'y') {
    Start-Process "https://${ip}:9453"
}

Read-Host "Press Enter to exit"
