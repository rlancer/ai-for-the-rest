# Test wrapper for setup.ps1
$ErrorActionPreference = 'Continue'
$logFile = "C:\Users\WDAGUtilityAccount\Desktop\setup-log.txt"

function Log {
    param([string]$Message)
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$timestamp - $Message" | Tee-Object -FilePath $logFile -Append
}

Log "Starting setup.ps1 test..."
Log "PowerShell Version: $($PSVersionTable.PSVersion)"

try {
    # Run the setup script
    & "C:\TestFiles\setup.ps1" 2>&1 | ForEach-Object {
        Log $_
    }
    Log "Setup script completed successfully!"
} catch {
    Log "ERROR: $_"
}

# Verify installations
Log "
=== Verification ==="

Log "Checking scoop..."
if (Get-Command scoop -ErrorAction SilentlyContinue) {
    Log "  scoop: INSTALLED"
    Log "  Installed packages:"
    scoop list 2>&1 | ForEach-Object { Log "    $_" }
} else {
    Log "  scoop: NOT FOUND"
}

Log "
Checking mise..."
if (Get-Command mise -ErrorAction SilentlyContinue) {
    Log "  mise: INSTALLED"
    mise list 2>&1 | ForEach-Object { Log "    $_" }
} else {
    Log "  mise: NOT FOUND"
}

Log "
Checking bun..."
if (Get-Command bun -ErrorAction SilentlyContinue) {
    Log "  bun: INSTALLED ($(bun --version))"
} else {
    Log "  bun: NOT FOUND"
}

Log "
Checking claude..."
if (Get-Command claude -ErrorAction SilentlyContinue) {
    Log "  claude: INSTALLED"
} else {
    Log "  claude: NOT FOUND"
}

Log "
=== Test Complete ==="
Log "Log saved to: $logFile"

# Keep window open
Read-Host "
Press Enter to close"
