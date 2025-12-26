# Test wrapper for setup.ps1
$ErrorActionPreference = 'Continue'
$transcriptFile = "C:\Users\WDAGUtilityAccount\Desktop\setup-transcript.txt"

# Start transcript to capture ALL output
Start-Transcript -Path $transcriptFile -Force

Write-Host "Starting setup.ps1 test..."
Write-Host "PowerShell Version: $($PSVersionTable.PSVersion)"

# Wait for network connectivity
Write-Host "
Waiting for network..." -ForegroundColor Yellow
$maxAttempts = 30
$attempt = 0
while ($attempt -lt $maxAttempts) {
    $attempt++
    try {
        $null = Resolve-DnsName "github.com" -ErrorAction Stop
        Write-Host "  Network ready (attempt $attempt)" -ForegroundColor Green
        break
    } catch {
        Write-Host "  Waiting for network... (attempt $attempt/$maxAttempts)" -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}
if ($attempt -eq $maxAttempts) {
    Write-Host "  WARNING: Network may not be available" -ForegroundColor Red
}

# Disable Windows Defender for faster extraction
Write-Host "
Configuring Windows Defender..." -ForegroundColor Yellow

# Try multiple methods to speed up extraction
$defenderDisabled = $false

# Method 1: Try to disable via registry (works even if service not started)
try {
    Write-Host "  Disabling via registry..." -ForegroundColor Gray
    $defenderKey = "HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender"
    $rtpKey = "HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection"
    if (-not (Test-Path $defenderKey)) { New-Item -Path $defenderKey -Force | Out-Null }
    if (-not (Test-Path $rtpKey)) { New-Item -Path $rtpKey -Force | Out-Null }
    Set-ItemProperty -Path $defenderKey -Name "DisableAntiSpyware" -Value 1 -Type DWord -Force -ErrorAction Stop
    Set-ItemProperty -Path $rtpKey -Name "DisableRealtimeMonitoring" -Value 1 -Type DWord -Force -ErrorAction Stop
    Write-Host "  Registry method: SUCCESS" -ForegroundColor Green
    $defenderDisabled = $true
} catch {
    Write-Host "  Registry method: FAILED - $($_.Exception.Message)" -ForegroundColor Red
}

# Method 2: Try Set-MpPreference (may need service running)
if (-not $defenderDisabled) {
    try {
        Write-Host "  Trying Set-MpPreference..." -ForegroundColor Gray
        Set-MpPreference -DisableRealtimeMonitoring $true -ErrorAction Stop
        Write-Host "  Set-MpPreference: SUCCESS" -ForegroundColor Green
        $defenderDisabled = $true
    } catch {
        Write-Host "  Set-MpPreference: FAILED - $($_.Exception.Message)" -ForegroundColor Red
    }
}

# Method 3: Add exclusions for scoop paths
try {
    Write-Host "  Adding path exclusions..." -ForegroundColor Gray
    Add-MpPreference -ExclusionPath "C:\Users\WDAGUtilityAccount\scoop" -ErrorAction SilentlyContinue
    Add-MpPreference -ExclusionPath "C:\Users\WDAGUtilityAccount\AppData\Local\Temp" -ErrorAction SilentlyContinue
    Add-MpPreference -ExclusionPath "C:\TestFiles" -ErrorAction SilentlyContinue
    Write-Host "  Path exclusions: ADDED" -ForegroundColor Green
} catch {
    Write-Host "  Path exclusions: FAILED" -ForegroundColor Red
}

if ($defenderDisabled) {
    Write-Host "  Windows Defender: DISABLED (faster extraction)" -ForegroundColor Green
} else {
    Write-Host "  Windows Defender: Could not fully disable (extraction may be slower)" -ForegroundColor Yellow
}
Write-Host ""

try {
    # Dot-source the setup script so it runs in this session
    . "C:\TestFiles\scripts\setup.ps1"
    Write-Host "Setup script completed successfully!"
} catch {
    Write-Host "ERROR: $_"
    Write-Host $_.ScriptStackTrace
}

# Verify installations
Write-Host "
=== Verification ==="

Write-Host "Checking scoop..."
if (Get-Command scoop -ErrorAction SilentlyContinue) {
    Write-Host "  scoop: INSTALLED"
    Write-Host "  Installed packages:"
    scoop list
} else {
    Write-Host "  scoop: NOT FOUND"
}

Write-Host "
Checking mise..."
if (Get-Command mise -ErrorAction SilentlyContinue) {
    Write-Host "  mise: INSTALLED"
    mise list
} else {
    Write-Host "  mise: NOT FOUND"
}

Write-Host "
Checking bun..."
if (Get-Command bun -ErrorAction SilentlyContinue) {
    Write-Host "  bun: INSTALLED ($(bun --version))"
} else {
    Write-Host "  bun: NOT FOUND"
}

Write-Host "
Checking claude..."
if (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Host "  claude: INSTALLED"
} else {
    Write-Host "  claude: NOT FOUND"
}

Write-Host "
=== Test Complete ==="

Stop-Transcript

Write-Host "Transcript saved to: $transcriptFile"

# Keep window open
Read-Host "
Press Enter to close"
