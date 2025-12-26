# Setup script for new user environment (Windows)
# Works in both Windows PowerShell and PowerShell 7+
# Can be run via: irm https://raw.githubusercontent.com/rlancer/dangerous-ai/main/scripts/setup.ps1 | iex

# Helper function to run commands and display output without stderr causing error formatting
# Uses cmd /c to bypass PowerShell's stderr-to-error conversion
function Invoke-CommandWithOutput {
    param([string]$Command)
    cmd /c "$Command 2>&1" | Write-Host
}

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
    Write-Host "  Execution policy already configured" -ForegroundColor Gray
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
    Invoke-CommandWithOutput "scoop install git"
}

# Add required buckets from config
Write-Host "`nAdding Scoop buckets..." -ForegroundColor Yellow
$buckets = scoop bucket list 2>$null

foreach ($bucket in $config.buckets.scoop) {
    if ($buckets | Select-String $bucket) {
        Write-Host "  $bucket bucket already added" -ForegroundColor Gray
    } else {
        Write-Host "  Adding $bucket bucket..." -ForegroundColor Gray
        Invoke-CommandWithOutput "scoop bucket add $bucket"
    }
}

# Build package list from config
$packages = @()
$packages += $config.packages.common.scoop
$packages += $config.packages.windows.scoop
$packages += $config.packages.fonts.scoop

# Install packages
Write-Host "`nInstalling packages..." -ForegroundColor Yellow

# Get list of installed packages once (as array of names)
$installedApps = (scoop list 2>$null | Where-Object { $_.Name }).Name

foreach ($package in $packages) {
    if ($installedApps -contains $package) {
        Write-Host "  $package already installed" -ForegroundColor Gray
    } else {
        Write-Host "  Installing $package..." -ForegroundColor Gray
        Invoke-CommandWithOutput "scoop install $package"
    }
}

# Refresh PATH to include newly installed tools (mise, etc.)
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# Install bun via scoop (using pwsh since legacy PowerShell can't install bun directly)
Write-Host "`nInstalling bun..." -ForegroundColor Yellow
if (scoop list bun 2>$null | Select-String "bun") {
    $bunVersion = bun --version 2>$null
    Write-Host "  bun already installed ($bunVersion)" -ForegroundColor Gray
} else {
    Write-Host "  Installing via scoop (using pwsh)..." -ForegroundColor Gray
    Invoke-CommandWithOutput "pwsh -Command `"scoop install bun`""
    # Refresh PATH to include bun
    $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
}

# Check for old native bun installer (conflicts with scoop bun)
$nativeBunPath = "$env:USERPROFILE\.bun\bin\bun.exe"
if (Test-Path $nativeBunPath) {
    Write-Host "`nFound bun installed via native installer at ~/.bun/bin" -ForegroundColor Yellow
    Write-Host "  Scoop bun is now preferred. The native bun.exe can be removed." -ForegroundColor Gray
    Write-Host "  (Global packages in ~/.bun will be preserved)" -ForegroundColor Gray
    $response = Read-Host "  Remove native bun.exe? (Y/n)"
    if ($null -eq $response -or $response -eq "" -or $response -match "^[Yy]") {
        Remove-Item -Force $nativeBunPath -ErrorAction SilentlyContinue
        Write-Host "  Removed native bun.exe" -ForegroundColor Green
    } else {
        Write-Host "  Keeping native bun (may cause PATH conflicts)" -ForegroundColor Yellow
    }
}

# Check if bun is installed or configured via mise (conflicts with scoop bun)
$miseBunInstalled = mise list bun 2>$null | Where-Object { $_ -notmatch "\(missing\)" }
$miseBunConfigured = mise list bun 2>$null | Where-Object { $_ -match "\(missing\)" }
if ($miseBunInstalled -or $miseBunConfigured) {
    if ($miseBunInstalled) {
        Write-Host "`nFound bun installed via mise." -ForegroundColor Yellow
    } else {
        Write-Host "`nFound bun configured in mise (not yet installed)." -ForegroundColor Yellow
    }
    Write-Host "  Scoop bun is preferred to avoid version conflicts." -ForegroundColor Gray
    $response = Read-Host "  Remove bun from mise? (Y/n)"
    if ($null -eq $response -or $response -eq "" -or $response -match "^[Yy]") {
        if ($miseBunInstalled) {
            mise uninstall bun 2>&1 | Out-Null
        }
        # Remove bun from mise global config
        $miseConfigPath = "$env:USERPROFILE\.config\mise\config.toml"
        if (Test-Path $miseConfigPath) {
            $content = Get-Content $miseConfigPath | Where-Object { $_ -notmatch '^\s*bun\s*=' }
            $content | Set-Content $miseConfigPath
        }
        Write-Host "  Removed bun from mise" -ForegroundColor Green
    } else {
        Write-Host "  Keeping mise bun (may cause conflicts)" -ForegroundColor Yellow
    }
}

# Install mise tools from config
$miseTools = @($config.mise_tools | Where-Object { $_ })
if ($miseTools.Count -gt 0) {
    Write-Host "`nInstalling mise tools..." -ForegroundColor Yellow
    foreach ($tool in $miseTools) {
        $toolName = $tool -replace "@.*", ""
        # Check if actually installed (not just in config as "missing")
        $installed = mise list $toolName 2>$null | Where-Object { $_ -notmatch "\(missing\)" }
        if ($installed) {
            Write-Host "  $toolName already installed via mise" -ForegroundColor Gray
        } else {
            Write-Host "  Installing $tool..." -ForegroundColor Gray
            Invoke-CommandWithOutput "mise use -g $tool"
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
        Invoke-CommandWithOutput "bun install -g $pkg"
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
bun pm ls -g 2>$null | ForEach-Object { Write-Host "  $_" -ForegroundColor Gray }

Write-Host "`nSetup complete!" -ForegroundColor Green
