# Test script for setup.ps1 using Windows Sandbox
# Requires Windows Sandbox feature to be enabled
# Enable via: Enable-WindowsOptionalFeature -FeatureName "Containers-DisposableClientVM" -All -Online

param(
    [switch]$EnableSandbox,
    [switch]$RunTest
)

$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path $scriptRoot -Parent
$setupScript = Join-Path $repoRoot "scripts\setup.ps1"
$sandboxConfig = Join-Path $scriptRoot "test-sandbox.wsb"

if ($EnableSandbox) {
    Write-Host "Enabling Windows Sandbox feature..." -ForegroundColor Cyan
    Enable-WindowsOptionalFeature -FeatureName "Containers-DisposableClientVM" -All -Online
    Write-Host "Please restart your computer to complete the installation." -ForegroundColor Yellow
    exit
}

if ($RunTest) {
    # Check if running as admin, if not, relaunch as admin
    $isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    if (-not $isAdmin) {
        Write-Host "Relaunching as administrator..." -ForegroundColor Yellow
        $scriptPath = $MyInvocation.MyCommand.Path
        Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$scriptPath`" -RunTest"
        exit
    }

    # Create a test wrapper script that runs in the sandbox
    $testWrapper = @"
# Test wrapper for setup.ps1
`$ErrorActionPreference = 'Continue'
`$transcriptFile = "C:\Users\WDAGUtilityAccount\Desktop\setup-transcript.txt"

# Start transcript to capture ALL output
Start-Transcript -Path `$transcriptFile -Force

Write-Host "Starting setup.ps1 test..."
Write-Host "PowerShell Version: `$(`$PSVersionTable.PSVersion)"

# Wait for network connectivity
Write-Host "`nWaiting for network..." -ForegroundColor Yellow
`$maxAttempts = 30
`$attempt = 0
while (`$attempt -lt `$maxAttempts) {
    `$attempt++
    try {
        `$null = Resolve-DnsName "github.com" -ErrorAction Stop
        Write-Host "  Network ready (attempt `$attempt)" -ForegroundColor Green
        break
    } catch {
        Write-Host "  Waiting for network... (attempt `$attempt/`$maxAttempts)" -ForegroundColor Gray
        Start-Sleep -Seconds 2
    }
}
if (`$attempt -eq `$maxAttempts) {
    Write-Host "  WARNING: Network may not be available" -ForegroundColor Red
}

# Disable Windows Defender for faster extraction
Write-Host "`nConfiguring Windows Defender..." -ForegroundColor Yellow

# Try multiple methods to speed up extraction
`$defenderDisabled = `$false

# Method 1: Try to disable via registry (works even if service not started)
try {
    Write-Host "  Disabling via registry..." -ForegroundColor Gray
    `$defenderKey = "HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender"
    `$rtpKey = "HKLM:\SOFTWARE\Policies\Microsoft\Windows Defender\Real-Time Protection"
    if (-not (Test-Path `$defenderKey)) { New-Item -Path `$defenderKey -Force | Out-Null }
    if (-not (Test-Path `$rtpKey)) { New-Item -Path `$rtpKey -Force | Out-Null }
    Set-ItemProperty -Path `$defenderKey -Name "DisableAntiSpyware" -Value 1 -Type DWord -Force -ErrorAction Stop
    Set-ItemProperty -Path `$rtpKey -Name "DisableRealtimeMonitoring" -Value 1 -Type DWord -Force -ErrorAction Stop
    Write-Host "  Registry method: SUCCESS" -ForegroundColor Green
    `$defenderDisabled = `$true
} catch {
    Write-Host "  Registry method: FAILED - `$(`$_.Exception.Message)" -ForegroundColor Red
}

# Method 2: Try Set-MpPreference (may need service running)
if (-not `$defenderDisabled) {
    try {
        Write-Host "  Trying Set-MpPreference..." -ForegroundColor Gray
        Set-MpPreference -DisableRealtimeMonitoring `$true -ErrorAction Stop
        Write-Host "  Set-MpPreference: SUCCESS" -ForegroundColor Green
        `$defenderDisabled = `$true
    } catch {
        Write-Host "  Set-MpPreference: FAILED - `$(`$_.Exception.Message)" -ForegroundColor Red
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

if (`$defenderDisabled) {
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
    Write-Host "ERROR: `$_"
    Write-Host `$_.ScriptStackTrace
}

# Verify installations
Write-Host "`n=== Verification ==="

Write-Host "Checking scoop..."
if (Get-Command scoop -ErrorAction SilentlyContinue) {
    Write-Host "  scoop: INSTALLED"
    Write-Host "  Installed packages:"
    scoop list
} else {
    Write-Host "  scoop: NOT FOUND"
}

Write-Host "`nChecking mise..."
if (Get-Command mise -ErrorAction SilentlyContinue) {
    Write-Host "  mise: INSTALLED"
    mise list
} else {
    Write-Host "  mise: NOT FOUND"
}

Write-Host "`nChecking bun..."
if (Get-Command bun -ErrorAction SilentlyContinue) {
    Write-Host "  bun: INSTALLED (`$(bun --version))"
} else {
    Write-Host "  bun: NOT FOUND"
}

Write-Host "`nChecking claude..."
if (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Host "  claude: INSTALLED"
} else {
    Write-Host "  claude: NOT FOUND"
}

Write-Host "`n=== Test Complete ==="

Stop-Transcript

Write-Host "Transcript saved to: `$transcriptFile"

# Keep window open
Read-Host "`nPress Enter to close"
"@

    $wrapperPath = Join-Path $scriptRoot "test-wrapper.ps1"
    $testWrapper | Out-File -FilePath $wrapperPath -Encoding UTF8

    # Create sandbox configuration
    $sandboxXml = @"
<Configuration>
    <VGpu>Disable</VGpu>
    <MappedFolders>
        <MappedFolder>
            <HostFolder>$repoRoot</HostFolder>
            <SandboxFolder>C:\TestFiles</SandboxFolder>
            <ReadOnly>true</ReadOnly>
        </MappedFolder>
    </MappedFolders>
    <LogonCommand>
        <Command>powershell -ExecutionPolicy Bypass -Command "Set-MpPreference -DisableRealtimeMonitoring `$true; Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -NoExit -File C:\TestFiles\tests\test-wrapper.ps1'"</Command>
    </LogonCommand>
    <MemoryInMB>8192</MemoryInMB>
</Configuration>
"@

    $sandboxXml | Out-File -FilePath $sandboxConfig -Encoding UTF8

    Write-Host "Starting Windows Sandbox with test configuration..." -ForegroundColor Cyan
    Write-Host "The sandbox will:" -ForegroundColor Yellow
    Write-Host "  1. Mount this folder as C:\TestFiles (read-only)" -ForegroundColor Gray
    Write-Host "  2. Run setup.ps1 automatically" -ForegroundColor Gray
    Write-Host "  3. Verify all installations" -ForegroundColor Gray
    Write-Host "  4. Save transcript to sandbox desktop (setup-transcript.txt)" -ForegroundColor Gray
    Write-Host ""

    # Launch the sandbox
    Start-Process $sandboxConfig

    Write-Host "Sandbox launched! Watch the sandbox window for progress." -ForegroundColor Green
    Write-Host "When done, simply close the sandbox - all changes are discarded." -ForegroundColor Gray
}

if (-not $EnableSandbox -and -not $RunTest) {
    Write-Host @"
Setup Script Tester
==================

Usage:
  .\test-setup.ps1 -EnableSandbox    Enable Windows Sandbox feature (requires admin + restart)
  .\test-setup.ps1 -RunTest          Run setup.ps1 in a Windows Sandbox

Prerequisites:
  - Windows 10/11 Pro or Enterprise
  - Windows Sandbox feature enabled
  - Virtualization enabled in BIOS

The test will:
  1. Launch a clean Windows Sandbox
  2. Run your setup.ps1 script
  3. Verify all packages installed correctly
  4. Log results to desktop

All changes are automatically discarded when the sandbox closes.
"@ -ForegroundColor Cyan
}
