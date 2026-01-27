# Setup script for new user environment (Windows)
# Works in both Windows PowerShell and PowerShell 7+
# Can be run via: irm https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/scripts/setup.ps1 | iex

# Set UTF-8 encoding for proper character display (especially in legacy PowerShell)
[console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

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
        $configUrl = "https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/config/config.json"
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
    # Skip prompts in CI environments
    if ($env:CI -or $env:GITHUB_ACTIONS) {
        Write-Host "  Skipping removal (CI environment)" -ForegroundColor Gray
    } else {
        $response = Read-Host "  Remove native bun.exe? (Y/n)"
        if ($null -eq $response -or $response -eq "" -or $response -match "^[Yy]") {
            Remove-Item -Force $nativeBunPath -ErrorAction SilentlyContinue
            Write-Host "  Removed native bun.exe" -ForegroundColor Green
        } else {
            Write-Host "  Keeping native bun (may cause PATH conflicts)" -ForegroundColor Yellow
        }
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
    # Skip prompts in CI environments
    if ($env:CI -or $env:GITHUB_ACTIONS) {
        Write-Host "  Skipping removal (CI environment)" -ForegroundColor Gray
    } else {
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
}

# Install Claude Code using native installer (must run in same PowerShell context as Scoop)
Write-Host "`nInstalling Claude Code..." -ForegroundColor Yellow

# Claude Code installs to ~/.local/bin - ensure it's in PATH for this session
$localBin = Join-Path $env:USERPROFILE ".local\bin"
if ($env:PATH -notlike "*$localBin*") {
    $env:PATH = "$localBin;$env:PATH"
}

if (Get-Command claude -ErrorAction SilentlyContinue) {
    $claudeVersion = claude --version 2>$null
    Write-Host "  Claude Code already installed ($claudeVersion)" -ForegroundColor Gray
} else {
    Write-Host "  Installing via official installer..." -ForegroundColor Gray
    try {
        Invoke-RestMethod -Uri https://claude.ai/install.ps1 | Invoke-Expression
        # Refresh PATH from environment (in case installer modified it) + ensure ~/.local/bin is included
        $env:PATH = "$localBin;" + [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")
        Write-Host "  Claude Code installed successfully" -ForegroundColor Green
    } catch {
        Write-Host "  Failed to install Claude Code: $_" -ForegroundColor Red
    }
}

# Set CLAUDE_CODE_GIT_BASH_PATH to Scoop's git bash (required for Claude Code on Windows)
$gitBashPath = Join-Path $env:USERPROFILE "scoop\apps\git\current\bin\bash.exe"
if (Test-Path $gitBashPath) {
    $currentGitBashPath = [System.Environment]::GetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", "User")
    if ($currentGitBashPath -ne $gitBashPath) {
        [System.Environment]::SetEnvironmentVariable("CLAUDE_CODE_GIT_BASH_PATH", $gitBashPath, "User")
        $env:CLAUDE_CODE_GIT_BASH_PATH = $gitBashPath
        Write-Host "  Set CLAUDE_CODE_GIT_BASH_PATH to $gitBashPath" -ForegroundColor Green
    } else {
        Write-Host "  CLAUDE_CODE_GIT_BASH_PATH already configured" -ForegroundColor Gray
    }
} else {
    Write-Host "  Warning: Git bash not found at expected Scoop path" -ForegroundColor Yellow
}

# Show scoop packages summary
Write-Host "`n=== Bootstrap Summary ===" -ForegroundColor Cyan
Write-Host "`nScoop packages:" -ForegroundColor Yellow
$scoopApps = scoop list 2>$null | Where-Object { $_.Name }
foreach ($app in $scoopApps) {
    Write-Host "  $($app.Name) $($app.Version)" -ForegroundColor Gray
}

# Hand off to TypeScript for the rest of setup
Write-Host "`n=== Continuing with bun... ===" -ForegroundColor Cyan

# Always copy setup.ts and config to temp directory to avoid permission issues
# (Windows Sandbox and other restricted environments can't run directly from mapped folders)
$tempDir = Join-Path $env:TEMP "ai-setup"
if (-not (Test-Path $tempDir)) {
    New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
}

$setupTsPath = Join-Path $tempDir "setup.ts"
$configDir = Join-Path $tempDir "config"
if (-not (Test-Path $configDir)) {
    New-Item -ItemType Directory -Path $configDir -Force | Out-Null
}

if ($PSScriptRoot) {
    # Running from a file on disk - copy files to temp
    $sourceTs = Join-Path $PSScriptRoot "setup.ts"
    $sourceConfig = Join-Path (Split-Path $PSScriptRoot -Parent) "config\config.json"

    Copy-Item -Path $sourceTs -Destination $setupTsPath -Force
    Copy-Item -Path $sourceConfig -Destination (Join-Path $configDir "config.json") -Force
} else {
    # Running via irm | iex - download files to temp
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/scripts/setup.ts" -OutFile $setupTsPath
    Invoke-WebRequest -Uri "https://raw.githubusercontent.com/rlancer/ai-for-the-rest/main/config/config.json" -OutFile (Join-Path $configDir "config.json")
}

# Run the TypeScript setup script from temp
bun run $setupTsPath
