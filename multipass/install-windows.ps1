# CodeHero - Windows Installer
# Run this script as Administrator (Right-click > Run as Administrator)

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  CodeHero - Windows Setup               " -ForegroundColor Cyan
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
Write-Host "[1/7] Checking Windows edition..." -ForegroundColor Yellow
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
    Write-Host "[2/7] Checking for VirtualBox..." -ForegroundColor Yellow
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
Write-Host "[3/7] Checking for Multipass..." -ForegroundColor Yellow
$multipass = Get-Command multipass -ErrorAction SilentlyContinue
$freshInstall = $false

if (-not $multipass) {
    Write-Host "      Multipass not found. Installing..." -ForegroundColor Yellow
    $freshInstall = $true

    # If we need VirtualBox, create config BEFORE installing Multipass
    if ($needsVirtualBox) {
        Write-Host "      Pre-configuring VirtualBox driver..." -ForegroundColor Gray
        $configDir = "C:\ProgramData\Multipass\data\multipassd"
        New-Item -ItemType Directory -Path $configDir -Force -ErrorAction SilentlyContinue | Out-Null
        @"
[General]
driver=virtualbox
"@ | Out-File -FilePath "$configDir\multipassd.conf" -Encoding utf8 -Force
    }

    # Download latest Multipass from GitHub releases
    Write-Host "      Getting latest Multipass version..." -ForegroundColor Gray
    try {
        $releases = Invoke-RestMethod -Uri "https://api.github.com/repos/canonical/multipass/releases/latest"
        $version = $releases.tag_name -replace '^v', ''
        $asset = $releases.assets | Where-Object { $_.name -match "multipass.*win.*exe$" } | Select-Object -First 1
        if ($asset) {
            $installerUrl = $asset.browser_download_url
            Write-Host "      Downloading Multipass $version..." -ForegroundColor Gray
        } else {
            throw "No installer found"
        }
    } catch {
        Write-Host "      Using default download URL..." -ForegroundColor Gray
        $installerUrl = "https://multipass.run/download/windows"
    }

    $installerPath = "$env:TEMP\multipass-installer.exe"
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
    Write-Host "      Running installer..." -ForegroundColor Gray
    Start-Process -FilePath $installerPath -ArgumentList "/S" -Wait
    Remove-Item $installerPath -Force -ErrorAction SilentlyContinue

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")

    Write-Host "      Multipass installed!" -ForegroundColor Green

    # Stop service immediately after install (before it tries to use wrong driver)
    Write-Host "      Stopping service to apply configuration..." -ForegroundColor Gray
    Start-Sleep -Seconds 3
    Stop-Service Multipass -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

} else {
    Write-Host "      Multipass is already installed." -ForegroundColor Green
}

# Configure Multipass to use VirtualBox if needed
if ($needsVirtualBox) {
    Write-Host "      Configuring Multipass to use VirtualBox..." -ForegroundColor Yellow

    # Stop service completely
    Write-Host "      Stopping Multipass service..." -ForegroundColor Gray
    Stop-Service Multipass -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3

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

# Setup SSH key for VM
Write-Host "[4/7] Setting up SSH key for VM access..." -ForegroundColor Yellow
$sshDir = "$env:USERPROFILE\.ssh"
$sshKeyPath = "$sshDir\codehero_vm"

# Ensure .ssh directory exists
if (-not (Test-Path $sshDir)) {
    New-Item -ItemType Directory -Path $sshDir -Force | Out-Null
}

if (Test-Path $sshKeyPath) {
    Write-Host "      SSH key already exists at $sshKeyPath" -ForegroundColor Green
} else {
    Write-Host "      Generating new SSH key..." -ForegroundColor Gray
    
    # Use ssh-keygen (available in Windows 10+)
    $sshKeygen = Get-Command ssh-keygen -ErrorAction SilentlyContinue
    if ($sshKeygen) {
        & ssh-keygen -t rsa -b 4096 -f $sshKeyPath -N '""' -C "codehero-vm-$(Get-Date -Format 'yyyyMMdd')" | Out-Null
        Write-Host "      SSH key created: $sshKeyPath" -ForegroundColor Green
    } else {
        Write-Host "      ERROR: ssh-keygen not found. OpenSSH may not be installed." -ForegroundColor Red
        Write-Host "      Install OpenSSH Client from Windows Settings > Apps > Optional Features" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Start ssh-agent and add key
Write-Host "      Adding key to ssh-agent..." -ForegroundColor Gray
$sshAgent = Get-Service ssh-agent -ErrorAction SilentlyContinue
if ($sshAgent) {
    if ($sshAgent.Status -ne 'Running') {
        Set-Service ssh-agent -StartupType Manual
        Start-Service ssh-agent
    }
    & ssh-add $sshKeyPath 2>&1 | Out-Null
    Write-Host "      Key added to ssh-agent." -ForegroundColor Green
} else {
    Write-Host "      Warning: ssh-agent service not available" -ForegroundColor Yellow
}

# Read the public key
$sshPubKey = Get-Content "${sshKeyPath}.pub" -Raw
$sshPubKey = $sshPubKey.Trim()
Write-Host "      Public key ready for VM." -ForegroundColor Green

# Download cloud-init and inject SSH key
Write-Host "[5/7] Preparing VM configuration..." -ForegroundColor Yellow
$cloudInitUrl = "https://raw.githubusercontent.com/fotsakir/codehero/main/multipass/cloud-init.yaml"
$cloudInitPath = "$env:TEMP\cloud-init.yaml"

# Download the template
Invoke-WebRequest -Uri $cloudInitUrl -OutFile $cloudInitPath

# Replace the placeholder with actual SSH key (both occurrences)
$cloudInitContent = Get-Content $cloudInitPath -Raw
$cloudInitContent = $cloudInitContent -replace 'PASTE_YOUR_SSH_PUBLIC_KEY_HERE', $sshPubKey
$cloudInitContent | Out-File -FilePath $cloudInitPath -Encoding utf8 -NoNewline

Write-Host "      Configuration ready with SSH key." -ForegroundColor Green

# Check if VM already exists
Write-Host "[6/7] Checking for existing VM..." -ForegroundColor Yellow
$ErrorActionPreference = "SilentlyContinue"
$existingVm = & multipass list --format csv 2>&1 | Select-String "claude-dev"
$ErrorActionPreference = "Stop"

if ($existingVm) {
    Write-Host "      VM 'claude-dev' already exists!" -ForegroundColor Yellow
    $response = Read-Host "      Delete and recreate? (y/n)"
    if ($response -eq 'y') {
        Write-Host "      Deleting existing VM..." -ForegroundColor Gray
        & multipass delete claude-dev --purge 2>$null
        Start-Sleep -Seconds 3
    } else {
        Write-Host "      Keeping existing VM. Exiting." -ForegroundColor Yellow
        exit 0
    }
} else {
    Write-Host "      No existing VM found." -ForegroundColor Green
}

# Create VM
Write-Host "[7/7] Creating VM (this takes 15-20 minutes)..." -ForegroundColor Yellow
Write-Host "      - Name: claude-dev" -ForegroundColor Gray
Write-Host "      - Memory: 6GB" -ForegroundColor Gray
Write-Host "      - Disk: 64GB" -ForegroundColor Gray
Write-Host "      - OS: Ubuntu 24.04 LTS" -ForegroundColor Gray
Write-Host ""
Write-Host "      Please wait..." -ForegroundColor Gray

multipass launch 24.04 --name claude-dev --memory 6G --disk 64G --cpus 4 --timeout 1800 --cloud-init $cloudInitPath

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
    $webRunning = & multipass exec claude-dev -- systemctl is-active codehero-web 2>$null
    if ($LASTEXITCODE -eq 0 -and $webRunning -match "active") {
        break
    }

    $minutes = [math]::Floor($waited / 60)
    Write-Host "      Still installing... ($minutes minutes elapsed)" -ForegroundColor Gray
}

# Get IP address (try multiple methods with timeout)
$ip = ""
Write-Host "      Getting VM IP address..." -ForegroundColor Gray

# Method 1: multipass list (fastest, most reliable)
try {
    $job = Start-Job -ScriptBlock { multipass list --format csv 2>$null }
    $completed = Wait-Job $job -Timeout 15
    if ($completed) {
        $listOutput = Receive-Job $job
        foreach ($line in $listOutput) {
            if ($line -match "^claude-dev,\w+,(\d+\.\d+\.\d+\.\d+)") {
                $ip = $matches[1]
                break
            }
        }
    }
    Remove-Job $job -Force -ErrorAction SilentlyContinue
} catch {}

# Method 2: multipass info
if (-not $ip) {
    try {
        $job = Start-Job -ScriptBlock { multipass info claude-dev 2>$null }
        $completed = Wait-Job $job -Timeout 15
        if ($completed) {
            $infoOutput = Receive-Job $job
            foreach ($line in $infoOutput) {
                if ($line -match "IPv4:\s*(\d+\.\d+\.\d+\.\d+)") {
                    $ip = $matches[1]
                    break
                }
            }
        }
        Remove-Job $job -Force -ErrorAction SilentlyContinue
    } catch {}
}

# Fallback message
if (-not $ip) {
    $ip = "[RUN: multipass list]"
    Write-Host ""
    Write-Host "  NOTE: Could not auto-detect IP. Run this command to find it:" -ForegroundColor Yellow
    Write-Host "  multipass list" -ForegroundColor White
    Write-Host ""
}

# Setup SSH config for easy connection
Write-Host ""
Write-Host "Setting up SSH configuration..." -ForegroundColor Yellow
$sshConfigFile = "$sshDir\config"

$sshConfigEntry = @"
# CodeHero VM
Host codehero
    HostName $ip
    User claude
    IdentityFile $sshKeyPath
    StrictHostKeyChecking no
    UserKnownHostsFile=NUL
"@

# Check if config file exists and if entry already exists
if (Test-Path $sshConfigFile) {
    $configContent = Get-Content $sshConfigFile -Raw
    if ($configContent -match "# CodeHero VM") {
        # Remove old entry
        $configContent = $configContent -replace "(?ms)# CodeHero VM.*?UserKnownHostsFile=NUL\r?\n?", ""
        $configContent | Out-File -FilePath $sshConfigFile -Encoding utf8 -NoNewline
    }
}

# Add new entry
Add-Content -Path $sshConfigFile -Value "`n$sshConfigEntry" -Encoding utf8
Write-Host "SSH configuration added!" -ForegroundColor Green

# Cleanup
Remove-Item $cloudInitPath -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host "  VM Created Successfully!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  IMPORTANT: Software is still installing inside the VM!" -ForegroundColor Yellow
Write-Host "  This takes 10-15 minutes. Wait before accessing the dashboard." -ForegroundColor Yellow
Write-Host ""
Write-Host "  To check installation progress:" -ForegroundColor Cyan
Write-Host "    multipass shell claude-dev" -ForegroundColor White
Write-Host "    tail -f /var/log/cloud-init-output.log" -ForegroundColor White
Write-Host ""
Write-Host "  ACCESS POINTS (available after setup completes):" -ForegroundColor Yellow
Write-Host "  Dashboard:    https://${ip}:9453" -ForegroundColor Cyan
Write-Host "  Web Projects: https://${ip}:9867" -ForegroundColor Cyan
Write-Host ""
Write-Host "  LOGIN:" -ForegroundColor Yellow
Write-Host "  Username:  admin" -ForegroundColor White
Write-Host "  Password:  admin123" -ForegroundColor White
Write-Host ""
Write-Host "  SSH ACCESS:" -ForegroundColor Yellow
Write-Host "  Connect:      ssh codehero" -ForegroundColor White
Write-Host "  Or:           ssh claude@$ip" -ForegroundColor White
Write-Host "  VS Code:      Use 'Remote-SSH' extension with host 'codehero'" -ForegroundColor White
Write-Host ""
Write-Host "  VM COMMANDS:" -ForegroundColor Yellow
Write-Host "  Start VM:     multipass start claude-dev" -ForegroundColor White
Write-Host "  Stop VM:      multipass stop claude-dev" -ForegroundColor White
Write-Host "  VM Shell:     multipass shell claude-dev" -ForegroundColor White
Write-Host "  VM Status:    multipass list" -ForegroundColor White
Write-Host ""
Write-Host "  CHANGE PASSWORDS (after setup completes):" -ForegroundColor Red
Write-Host "  sudo /opt/codehero/scripts/change-passwords.sh" -ForegroundColor White
Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""

# Create desktop shortcuts
$desktopPath = [Environment]::GetFolderPath("Desktop")

# Create a smart batch file that gets IP dynamically
$startVmPath = Join-Path $desktopPath "Claude AI Developer.bat"
$startVmContent = @"
@echo off
title Claude AI Developer
echo.
echo ========================================
echo   Claude AI Developer
echo ========================================
echo.

REM Check if VM is running
multipass list 2>nul | findstr /C:"claude-dev" | findstr /C:"Running" >nul
if %ERRORLEVEL% NEQ 0 (
    echo Starting VM...
    multipass start claude-dev
    echo Waiting for VM to boot...
    timeout /t 15 /nobreak >nul
)

REM Ensure services are running inside VM
echo Checking services...
multipass exec claude-dev -- sudo systemctl start codehero-web 2>nul
multipass exec claude-dev -- sudo systemctl start codehero-daemon 2>nul

REM Get IP address
for /f "tokens=3 delims=," %%a in ('multipass list --format csv 2^>nul ^| findstr /C:"claude-dev"') do set IP=%%a

if "%IP%"=="" (
    echo ERROR: Could not get VM IP address
    echo Run: multipass list
    pause
    exit /b 1
)

echo.
echo Dashboard: https://%IP%:9453
echo.
echo Opening browser...
start https://%IP%:9453
echo.
echo Press any key to close this window...
pause >nul
"@
$startVmContent | Out-File -FilePath $startVmPath -Encoding ascii
Write-Host "Desktop shortcut created: Claude AI Developer.bat" -ForegroundColor Green

# Create SSH connection batch file
$sshVmPath = Join-Path $desktopPath "SSH to Claude VM.bat"
$sshVmContent = @"
@echo off
title SSH to Claude AI Developer VM
echo.
echo Connecting to Claude AI Developer VM...
echo.

REM Check if VM is running
multipass list 2>nul | findstr /C:"claude-dev" | findstr /C:"Running" >nul
if %ERRORLEVEL% NEQ 0 (
    echo VM is not running. Starting...
    multipass start claude-dev
    timeout /t 10 /nobreak >nul
)

ssh codehero
"@
$sshVmContent | Out-File -FilePath $sshVmPath -Encoding ascii
Write-Host "Desktop shortcut created: SSH to Claude VM.bat" -ForegroundColor Green

# Only create URL shortcut if we have a valid IP
if ($ip -match "^\d+\.\d+\.\d+\.\d+$") {
    $shortcutPath = Join-Path $desktopPath "Claude Dashboard.url"
    $shortcutContent = @"
[InternetShortcut]
URL=https://${ip}:9453
IconIndex=0
"@
    $shortcutContent | Out-File -FilePath $shortcutPath -Encoding ascii
    Write-Host "Desktop shortcut created: Claude Dashboard.url" -ForegroundColor Green
}

Write-Host ""

# Open browser
$openBrowser = Read-Host "Open dashboard in browser? (y/n)"
if ($openBrowser -eq 'y') {
    Start-Process "https://${ip}:9453"
}

Read-Host "Press Enter to exit"