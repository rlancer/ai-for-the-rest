# Setup script for new user environment
# Run in classic PowerShell (not PowerShell Core)

Write-Host "Setting up your development environment..." -ForegroundColor Cyan

# Set execution policy for current user (ignore if already set by group policy)
Write-Host "`nSetting execution policy..." -ForegroundColor Yellow
try {
    Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force -ErrorAction Stop
} catch {
    Write-Host "  Execution policy already configured (current: $(Get-ExecutionPolicy))" -ForegroundColor Gray
}

# Install Scoop
Write-Host "`nInstalling Scoop..." -ForegroundColor Yellow
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression

# Refresh PATH to include scoop
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# Install git first (required for adding buckets)
Write-Host "`nInstalling git (required for buckets)..." -ForegroundColor Yellow
scoop install git 2>&1 | Write-Host
if ($LASTEXITCODE -ne 0) {
    Write-Host "  WARNING: git install may have failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
}

# Add required buckets
Write-Host "`nAdding Scoop buckets..." -ForegroundColor Yellow
Write-Host "  Adding extras bucket..." -ForegroundColor Gray
scoop bucket add extras 2>&1 | Write-Host
Write-Host "  Adding nerd-fonts bucket..." -ForegroundColor Gray
scoop bucket add nerd-fonts 2>&1 | Write-Host

# Install remaining packages
Write-Host "`nInstalling packages..." -ForegroundColor Yellow

$packages = @(
    "7zip",
    "antigravity",
    "duckdb",
    "Hack-NF",
    "innounp",
    "mise",
    "pwsh",
    "slack",
    "starship",
    "touch",
    "vcredist2022",
    "which",
    "windows-terminal"
)

foreach ($package in $packages) {
    Write-Host "Installing $package..." -ForegroundColor Gray
    scoop install $package 2>&1 | Write-Host
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  WARNING: $package install may have failed" -ForegroundColor Red
    }
}

# Refresh PATH to include newly installed tools (mise, etc.)
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# Install bun via mise
Write-Host "`nInstalling bun via mise..." -ForegroundColor Yellow
mise use -g bun@latest 2>&1 | Write-Host

# Add mise shims to PATH for current session
$miseDataDir = if ($env:MISE_DATA_DIR) { $env:MISE_DATA_DIR } else { "$env:LOCALAPPDATA\mise" }
$env:PATH = "$miseDataDir\shims;$env:PATH"

# Configure mise to use bun for npm packages
Write-Host "`nConfiguring mise to use bun backend..." -ForegroundColor Yellow
mise settings set npm.bun true 2>&1 | Write-Host

# Install Claude Code via mise (uses bun backend)
Write-Host "`nInstalling Claude Code..." -ForegroundColor Yellow
mise use -g npm:@anthropic-ai/claude-code 2>&1 | Write-Host

Write-Host "`nSetup complete!" -ForegroundColor Green
