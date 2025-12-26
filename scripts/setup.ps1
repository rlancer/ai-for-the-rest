# Setup script for new user environment (Windows)
# Run in classic PowerShell (not PowerShell Core)
# Can be run via: irm https://raw.githubusercontent.com/rlancer/dangerous-ai/main/scripts/setup.ps1 | iex

# Load configuration - support both local file and remote URL execution
if ($PSScriptRoot) {
    # Running from a file on disk
    $repoRoot = Split-Path $PSScriptRoot -Parent
    $configPath = Join-Path $repoRoot "config\config.json"
    if (Test-Path $configPath) {
        $config = Get-Content $configPath -Raw | ConvertFrom-Json
    }
}

if (-not $config) {
    # Running via irm | iex or config not found - fetch from GitHub
    Write-Host "Fetching configuration from GitHub..." -ForegroundColor Yellow
    try {
        $configUrl = "https://raw.githubusercontent.com/rlancer/dangerous-ai/main/config/config.json"
        $config = Invoke-RestMethod -Uri $configUrl
    } catch {
        Write-Host "ERROR: Could not fetch config.json from $configUrl" -ForegroundColor Red
        Write-Host "  $_" -ForegroundColor Red
        exit 1
    }
}

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

# Check if bun is installed via mise (scoop version is preferred for PATH compatibility)
$miseBun = mise list bun 2>$null
if ($miseBun -match "bun") {
    Write-Host "`nFound bun installed via mise." -ForegroundColor Yellow
    Write-Host "  Scoop's bun is preferred because global packages (claude, codex, gemini)" -ForegroundColor Gray
    Write-Host "  need bun in PATH before mise activates." -ForegroundColor Gray
    $response = Read-Host "  Uninstall mise's bun? (Y/n)"
    if ($response -eq "" -or $response -match "^[Yy]") {
        mise uninstall bun 2>&1 | Write-Host
        Write-Host "  Removed mise bun" -ForegroundColor Green
    } else {
        Write-Host "  Keeping mise bun (global packages may not work correctly)" -ForegroundColor Yellow
    }
}

# Install mise tools from config
if ($config.mise_tools -and $config.mise_tools.Count -gt 0) {
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
# Add bun global bin to PATH
$bunBin = "$env:USERPROFILE\.bun\bin"
if ((Test-Path $bunBin) -and ($env:PATH -notlike "*$bunBin*")) {
    $env:PATH = "$bunBin;$env:PATH"
}

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
} else {
    $needsUpdate = $false
    if (-not (Select-String -Path $pwshProfile -Pattern "starship init" -Quiet)) {
        Add-Content -Path $pwshProfile -Value "`n$profileContent"
        Write-Host "  Updated PowerShell Core profile (added mise + starship)" -ForegroundColor Gray
        $needsUpdate = $true
    }
    if (-not (Select-String -Path $pwshProfile -Pattern "\.bun\\bin" -Quiet)) {
        $bunPathSnippet = @'

# Add bun global bin to PATH
$bunBin = "$env:USERPROFILE\.bun\bin"
if ((Test-Path $bunBin) -and ($env:PATH -notlike "*$bunBin*")) {
    $env:PATH = "$bunBin;$env:PATH"
}
'@
        Add-Content -Path $pwshProfile -Value $bunPathSnippet
        Write-Host "  Updated PowerShell Core profile (added bun PATH)" -ForegroundColor Gray
        $needsUpdate = $true
    }
    if (-not $needsUpdate) {
        Write-Host "  PowerShell Core profile already configured" -ForegroundColor Gray
    }
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
} else {
    $needsUpdate = $false
    if (-not (Select-String -Path $winPsProfile -Pattern "starship init" -Quiet)) {
        Add-Content -Path $winPsProfile -Value "`n$profileContent"
        Write-Host "  Updated Windows PowerShell profile (added mise + starship)" -ForegroundColor Gray
        $needsUpdate = $true
    }
    if (-not (Select-String -Path $winPsProfile -Pattern "\.bun\\bin" -Quiet)) {
        $bunPathSnippet = @'

# Add bun global bin to PATH
$bunBin = "$env:USERPROFILE\.bun\bin"
if ((Test-Path $bunBin) -and ($env:PATH -notlike "*$bunBin*")) {
    $env:PATH = "$bunBin;$env:PATH"
}
'@
        Add-Content -Path $winPsProfile -Value $bunPathSnippet
        Write-Host "  Updated Windows PowerShell profile (added bun PATH)" -ForegroundColor Gray
        $needsUpdate = $true
    }
    if (-not $needsUpdate) {
        Write-Host "  Windows PowerShell profile already configured" -ForegroundColor Gray
    }
}

# Show what was installed
Write-Host "`n=== Installation Summary ===" -ForegroundColor Cyan

Write-Host "`nScoop packages:" -ForegroundColor Yellow
$scoopApps = scoop list 2>$null | Where-Object { $_.Name }
foreach ($app in $scoopApps) {
    Write-Host "  $($app.Name) $($app.Version)" -ForegroundColor Gray
}

Write-Host "`nMise tools:" -ForegroundColor Yellow
mise list 2>$null | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

Write-Host "`nBun global packages:" -ForegroundColor Yellow
$bunBinDir = "$env:USERPROFILE\.bun\bin"
if (Test-Path $bunBinDir) {
    Get-ChildItem $bunBinDir -File | ForEach-Object { Write-Host "  $($_.BaseName)" -ForegroundColor Gray }
}

Write-Host "`nSetup complete!" -ForegroundColor Green
