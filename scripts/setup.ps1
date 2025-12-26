# Setup script for new user environment (Windows)
# Run in classic PowerShell (not PowerShell Core)

$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path $scriptRoot -Parent
$configPath = Join-Path $repoRoot "config\config.json"

# Load configuration
if (-not (Test-Path $configPath)) {
    Write-Host "ERROR: config.json not found at $configPath" -ForegroundColor Red
    exit 1
}

$config = Get-Content $configPath -Raw | ConvertFrom-Json

Write-Host "Setting up your development environment..." -ForegroundColor Cyan

# Set execution policy for current user (ignore if already set by group policy)
Write-Host "`nSetting execution policy..." -ForegroundColor Yellow
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction Stop
} catch {
    Write-Host "  Execution policy already configured (current: $(Get-ExecutionPolicy))" -ForegroundColor Gray
}

# Install Scoop (if not already installed)
Write-Host "`nInstalling Scoop..." -ForegroundColor Yellow
if (Get-Command scoop -ErrorAction SilentlyContinue) {
    Write-Host "  Scoop already installed" -ForegroundColor Gray
} else {
    Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression
}

# Refresh PATH to include scoop
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# Install git (required for adding buckets)
Write-Host "`nInstalling git (required for buckets)..." -ForegroundColor Yellow
if (scoop list git 2>$null | Select-String "git") {
    Write-Host "  git already installed" -ForegroundColor Gray
} else {
    scoop install git 2>&1 | Write-Host
}

# Add required buckets from config
Write-Host "`nAdding Scoop buckets..." -ForegroundColor Yellow
$buckets = scoop bucket list 2>$null

foreach ($bucket in $config.buckets.scoop) {
    if ($buckets | Select-String $bucket) {
        Write-Host "  $bucket bucket already added" -ForegroundColor Gray
    } else {
        Write-Host "  Adding $bucket bucket..." -ForegroundColor Gray
        scoop bucket add $bucket 2>&1 | Write-Host
    }
}

# Build package list from config
$packages = @()
$packages += $config.packages.common.scoop
$packages += $config.packages.windows.scoop
$packages += $config.packages.fonts.scoop

# Install packages
Write-Host "`nInstalling packages..." -ForegroundColor Yellow

# Get list of installed packages once
$installedPackages = scoop list 2>$null | Out-String

foreach ($package in $packages) {
    if ($installedPackages -match "(?m)^\s*$package\s") {
        Write-Host "  $package already installed" -ForegroundColor Gray
    } else {
        Write-Host "  Installing $package..." -ForegroundColor Gray
        scoop install $package 2>&1 | Write-Host
    }
}

# Refresh PATH to include newly installed tools (mise, etc.)
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# Install mise tools from config
Write-Host "`nInstalling mise tools..." -ForegroundColor Yellow
foreach ($tool in $config.mise_tools) {
    $toolName = $tool -replace "@.*", ""
    if (mise list $toolName 2>$null | Select-String $toolName) {
        Write-Host "  $toolName already installed via mise" -ForegroundColor Gray
    } else {
        Write-Host "  Installing $tool..." -ForegroundColor Gray
        mise use -g $tool 2>&1 | Write-Host
    }
}

# Add mise shims to PATH for current session
$miseDataDir = if ($env:MISE_DATA_DIR) { $env:MISE_DATA_DIR } else { "$env:LOCALAPPDATA\mise" }
$env:PATH = "$miseDataDir\shims;$env:PATH"

# Install bun global packages from config
Write-Host "`nInstalling bun global packages..." -ForegroundColor Yellow

foreach ($pkg in $config.bun_global) {
    # Extract command name from package (last part after /)
    $cmdName = ($pkg -split "/")[-1]
    if (Get-Command $cmdName -ErrorAction SilentlyContinue) {
        Write-Host "  $pkg already installed" -ForegroundColor Gray
    } else {
        Write-Host "  Installing $pkg..." -ForegroundColor Gray
        bun install -g $pkg 2>&1 | Write-Host
    }
}

# Configure PowerShell profile for mise and starship
Write-Host "`nConfiguring PowerShell profile..." -ForegroundColor Yellow

$profileContent = @'
# Initialize mise
Invoke-Expression (& mise activate pwsh)

# Initialize starship prompt
Invoke-Expression (&starship init powershell)
'@

# Configure for PowerShell Core (pwsh)
$pwshProfileDir = "$env:USERPROFILE\Documents\PowerShell"
$pwshProfile = "$pwshProfileDir\Microsoft.PowerShell_profile.ps1"

if (-not (Test-Path $pwshProfileDir)) {
    New-Item -ItemType Directory -Path $pwshProfileDir -Force | Out-Null
}

if (-not (Test-Path $pwshProfile)) {
    $profileContent | Out-File -FilePath $pwshProfile -Encoding UTF8
    Write-Host "  Created PowerShell Core profile" -ForegroundColor Gray
} elseif (-not (Select-String -Path $pwshProfile -Pattern "starship init" -Quiet)) {
    Add-Content -Path $pwshProfile -Value "`n$profileContent"
    Write-Host "  Updated PowerShell Core profile" -ForegroundColor Gray
} else {
    Write-Host "  PowerShell Core profile already configured" -ForegroundColor Gray
}

# Configure for Windows PowerShell
$winPsProfileDir = "$env:USERPROFILE\Documents\WindowsPowerShell"
$winPsProfile = "$winPsProfileDir\Microsoft.PowerShell_profile.ps1"

if (-not (Test-Path $winPsProfileDir)) {
    New-Item -ItemType Directory -Path $winPsProfileDir -Force | Out-Null
}

if (-not (Test-Path $winPsProfile)) {
    $profileContent | Out-File -FilePath $winPsProfile -Encoding UTF8
    Write-Host "  Created Windows PowerShell profile" -ForegroundColor Gray
} elseif (-not (Select-String -Path $winPsProfile -Pattern "starship init" -Quiet)) {
    Add-Content -Path $winPsProfile -Value "`n$profileContent"
    Write-Host "  Updated Windows PowerShell profile" -ForegroundColor Gray
} else {
    Write-Host "  Windows PowerShell profile already configured" -ForegroundColor Gray
}

Write-Host "`nSetup complete!" -ForegroundColor Green
