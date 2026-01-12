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

# Check if Multipass is installed
Write-Host "[1/5] Checking for Multipass..." -ForegroundColor Yellow
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

# Download cloud-init
Write-Host "[2/5] Downloading configuration..." -ForegroundColor Yellow
$cloudInitUrl = "https://raw.githubusercontent.com/fotsakir/Claude-AI-developer/main/multipass/cloud-init.yaml"
$cloudInitPath = "$env:TEMP\cloud-init.yaml"
Invoke-WebRequest -Uri $cloudInitUrl -OutFile $cloudInitPath
Write-Host "      Done." -ForegroundColor Green

# Check if VM already exists
Write-Host "[3/5] Checking for existing VM..." -ForegroundColor Yellow
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
Write-Host "[4/5] Creating VM (this takes 15-20 minutes)..." -ForegroundColor Yellow
Write-Host "      - Name: claude-dev" -ForegroundColor Gray
Write-Host "      - Memory: 4GB" -ForegroundColor Gray
Write-Host "      - Disk: 40GB" -ForegroundColor Gray
Write-Host "      - OS: Ubuntu 24.04 LTS" -ForegroundColor Gray
Write-Host ""
Write-Host "      Please wait..." -ForegroundColor Gray

multipass launch 24.04 --name claude-dev --memory 4G --disk 40G --cpus 2 --cloud-init $cloudInitPath

# Wait for cloud-init to complete
Write-Host "[5/5] Waiting for installation to complete..." -ForegroundColor Yellow
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
Write-Host "  Dashboard: https://${ip}:9453" -ForegroundColor Cyan
Write-Host "  Username:  admin" -ForegroundColor White
Write-Host "  Password:  admin123" -ForegroundColor White
Write-Host ""
Write-Host "  To access VM terminal:" -ForegroundColor Yellow
Write-Host "  multipass shell claude-dev" -ForegroundColor White
Write-Host ""
Write-Host "  IMPORTANT: Change passwords after login!" -ForegroundColor Red
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Open browser
$openBrowser = Read-Host "Open dashboard in browser? (y/n)"
if ($openBrowser -eq 'y') {
    Start-Process "https://${ip}:9453"
}

Read-Host "Press Enter to exit"
