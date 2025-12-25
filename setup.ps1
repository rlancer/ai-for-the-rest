# Setup script for new user environment
# Run in classic PowerShell (not PowerShell Core)

Write-Host "Setting up your development environment..." -ForegroundColor Cyan

# Set execution policy for current user
Write-Host "`nSetting execution policy..." -ForegroundColor Yellow
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force

# Install Scoop
Write-Host "`nInstalling Scoop..." -ForegroundColor Yellow
Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression

# Refresh PATH to include scoop
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# Install git first (required for adding buckets)
Write-Host "`nInstalling git (required for buckets)..." -ForegroundColor Yellow
scoop install git

# Add required buckets
Write-Host "`nAdding Scoop buckets..." -ForegroundColor Yellow
scoop bucket add extras
scoop bucket add nerd-fonts

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
    scoop install $package
}

# Refresh PATH to include newly installed tools (mise, etc.)
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "User") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "Machine")

# Install bun via mise
Write-Host "`nInstalling bun via mise..." -ForegroundColor Yellow
mise use -g bun@latest

# Add mise shims to PATH for current session
$miseDataDir = if ($env:MISE_DATA_DIR) { $env:MISE_DATA_DIR } else { "$env:LOCALAPPDATA\mise" }
$env:PATH = "$miseDataDir\shims;$env:PATH"

# Configure mise to use bun for npm packages
Write-Host "`nConfiguring mise to use bun backend..." -ForegroundColor Yellow
mise settings set npm.bun true

# Install Claude Code via mise (uses bun backend)
Write-Host "`nInstalling Claude Code..." -ForegroundColor Yellow
mise use -g npm:@anthropic-ai/claude-code

Write-Host "`nSetup complete!" -ForegroundColor Green
