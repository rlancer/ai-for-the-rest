# Test script for setup.ps1 using Windows Sandbox
# Requires Windows Sandbox feature to be enabled
# Enable via: Enable-WindowsOptionalFeature -FeatureName "Containers-DisposableClientVM" -All -Online

param(
    [switch]$EnableSandbox,
    [switch]$RunTest
)

$scriptRoot = $PSScriptRoot
$setupScript = Join-Path $scriptRoot "setup.ps1"
$sandboxConfig = Join-Path $scriptRoot "test-sandbox.wsb"

if ($EnableSandbox) {
    Write-Host "Enabling Windows Sandbox feature..." -ForegroundColor Cyan
    Enable-WindowsOptionalFeature -FeatureName "Containers-DisposableClientVM" -All -Online
    Write-Host "Please restart your computer to complete the installation." -ForegroundColor Yellow
    exit
}

if ($RunTest) {
    # Create a test wrapper script that runs in the sandbox
    $testWrapper = @"
# Test wrapper for setup.ps1
`$ErrorActionPreference = 'Continue'
`$transcriptFile = "C:\Users\WDAGUtilityAccount\Desktop\setup-transcript.txt"

# Start transcript to capture ALL output
Start-Transcript -Path `$transcriptFile -Force

Write-Host "Starting setup.ps1 test..."
Write-Host "PowerShell Version: `$(`$PSVersionTable.PSVersion)"

try {
    # Dot-source the setup script so it runs in this session
    . "C:\TestFiles\setup.ps1"
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
            <HostFolder>$scriptRoot</HostFolder>
            <SandboxFolder>C:\TestFiles</SandboxFolder>
            <ReadOnly>true</ReadOnly>
        </MappedFolder>
    </MappedFolders>
    <LogonCommand>
        <Command>cmd /c start powershell -ExecutionPolicy Bypass -NoExit -File C:\TestFiles\test-wrapper.ps1</Command>
    </LogonCommand>
    <MemoryInMB>4096</MemoryInMB>
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
