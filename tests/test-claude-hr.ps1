# Minimal Windows Sandbox test for the claude-hr / Headroom proxy installation.
#
# Unlike test-setup.ps1 (which runs the FULL environment bootstrap and takes
# ~10 min), this test installs only bun and then runs the real setupHeadroom()
# from scripts/setup.ts in isolation. It verifies the deployed Headroom
# artifacts (proxy scripts, claude-hr shim, mise tasks) without scoop/mise/claude
# or starting the proxy container. Target wall-clock: ~2-3 min.
#
# Requires the Windows Sandbox feature (Containers-DisposableClientVM).

param(
    [switch]$EnableSandbox,
    [switch]$RunTest
)

$scriptRoot = $PSScriptRoot
$repoRoot = Split-Path $scriptRoot -Parent
$sandboxConfig = Join-Path $scriptRoot "test-claude-hr.wsb"
# Writable folder mapped into the sandbox so the in-sandbox run can report its
# result (pass/fail + transcript) back to the host. The sandbox VM is discarded
# on close, so its desktop transcript is otherwise unreachable.
$resultsDir = Join-Path $scriptRoot "test-claude-hr-results"

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
# Minimal test wrapper: install bun, run real setupHeadroom(), verify artifacts.
`$ErrorActionPreference = 'Continue'
`$transcriptFile = "C:\Users\WDAGUtilityAccount\Desktop\claude-hr-transcript.txt"
# Writable folder mapped from the host (tests\test-claude-hr-results) so results
# survive the sandbox being discarded on close.
`$resultsDir = "C:\TestResults"
`$failures = New-Object System.Collections.Generic.List[string]
function Assert-True(`$cond, `$pass, `$fail) {
    if (`$cond) { Write-Host "  `$pass" -ForegroundColor Green }
    else { Write-Host "  `$fail" -ForegroundColor Red; `$failures.Add(`$fail) }
}

# Start transcript to capture ALL output
Start-Transcript -Path `$transcriptFile -Force

Write-Host "Starting claude-hr / Headroom proxy test..."
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

# Seed the Trusted Root certificate store. A fresh Windows Sandbox image ships with
# a stale/empty root store, so .NET cannot validate GitHub's TLS certificate and
# downloads (the bun installer) fail with "Could not establish trust relationship
# for the SSL/TLS secure channel". This is a Sandbox-image limitation, not a setup
# issue; real machines already have populated root stores. The host exports its own
# root store to tests\sandbox-roots.sst (mapped read-only into the sandbox) and we
# import it here.
Write-Host "`nSeeding Trusted Root certificates from host (Sandbox workaround)..." -ForegroundColor Yellow
try {
    `$sstPath = "C:\TestFiles\tests\sandbox-roots.sst"
    if (Test-Path `$sstPath) {
        `$before = (Get-ChildItem Cert:\LocalMachine\Root -ErrorAction SilentlyContinue).Count
        certutil -addstore -f Root `$sstPath 2>&1 | Out-Null
        `$after = (Get-ChildItem Cert:\LocalMachine\Root -ErrorAction SilentlyContinue).Count
        Write-Host "  Root store: `$before -> `$after certs (imported from host .sst)" -ForegroundColor Green
    } else {
        Write-Host "  sandbox-roots.sst not found at `$sstPath; continuing anyway" -ForegroundColor Gray
    }
} catch {
    Write-Host "  Cert seed failed: `$(`$_.Exception.Message)" -ForegroundColor Red
}

# Install bun (the only dependency setupHeadroom needs on PATH). Use the official
# bun installer rather than scoop/mise so the test stays fast.
Write-Host "`nInstalling bun..." -ForegroundColor Yellow
try {
    Invoke-RestMethod https://bun.sh/install.ps1 | Invoke-Expression
} catch {
    Write-Host "  bun install failed: `$(`$_.Exception.Message)" -ForegroundColor Red
}
# bun installs to ~\.bun\bin; add it to PATH for this session.
`$bunBin = Join-Path `$env:USERPROFILE ".bun\bin"
if (Test-Path `$bunBin) {
    `$env:PATH = "`$bunBin;" + `$env:PATH
}
if (Get-Command bun -ErrorAction SilentlyContinue) {
    Write-Host "  bun: INSTALLED (`$(bun --version))" -ForegroundColor Green
} else {
    Write-Host "  bun: NOT FOUND (setupHeadroom shim smoke-test will be skipped)" -ForegroundColor Red
}

# Run the REAL setupHeadroom() from scripts/setup.ts in isolation. setup.ts only
# runs main() when executed directly (import.meta.main), so importing it just
# loads the module; we then call the exported setupHeadroom(). This keeps the test
# honest: if setupHeadroom's deploy/shim/mise logic changes, this exercises it.
#
# Bun cannot import .ts files directly from the read-only Sandbox mount (it fails
# with "EPERM reading ..."), so stage a WRITABLE copy of scripts/ + config/ first,
# preserving the layout setup.ts expects (it resolves headroom/ via import.meta.dir
# and config/config.json via ../config).
Write-Host "`nStaging repo (scripts/ + config/) to a writable location..." -ForegroundColor Yellow
`$stageDir = "C:\Users\WDAGUtilityAccount\Desktop\aftr-stage"
if (Test-Path `$stageDir) { Remove-Item `$stageDir -Recurse -Force }
New-Item -ItemType Directory -Path `$stageDir -Force | Out-Null
Copy-Item "C:\TestFiles\scripts" (Join-Path `$stageDir "scripts") -Recurse -Force
Copy-Item "C:\TestFiles\config"  (Join-Path `$stageDir "config")  -Recurse -Force

Write-Host "Running real setupHeadroom() from staged scripts/setup.ts..." -ForegroundColor Yellow
`$harness = Join-Path `$stageDir "run-setup-headroom.ts"
`$setupUrl = "file:///" + ((Join-Path `$stageDir "scripts\setup.ts") -replace '\\','/')
@"
// Import the real setupHeadroom from the staged repo and run it in isolation.
import { setupHeadroom } from "`$setupUrl";
await setupHeadroom();
"@ | Out-File -FilePath `$harness -Encoding UTF8

try {
    & bun `$harness
    Write-Host "setupHeadroom() completed." -ForegroundColor Green
} catch {
    Write-Host "ERROR running setupHeadroom: `$_" -ForegroundColor Red
    Write-Host `$_.ScriptStackTrace
}

# Verify deployed artifacts
Write-Host "`n=== Verification ==="
Write-Host "Checking Headroom proxy launcher (claude-hr)..."
# setupHeadroom deploys scripts to ~/.config/headroom, writes a claude-hr shim to
# ~/.local/bin, and registers mise tasks. The proxy container is NOT started (no
# podman VM in the sandbox), so we only verify the deployed artifacts.
`$hrDir = Join-Path `$env:USERPROFILE ".config\headroom"
`$hrProxy = Join-Path `$hrDir "headroom-proxy.ts"
`$hrLauncher = Join-Path `$hrDir "claude-via-proxy.ts"
`$hrShim = Join-Path `$env:USERPROFILE ".local\bin\claude-hr.cmd"
`$miseCfg = Join-Path `$env:USERPROFILE ".config\mise\config.toml"
# The shim path is written by Node's homedir(), which may use the 8.3 short name
# (e.g. RLANCE~1) while `$env:USERPROFILE expands to the long name. Match on the
# stable path tail rather than the full home-prefixed absolute path.
`$expectedShimTail = ".config\headroom\claude-via-proxy.ts"

Assert-True (Test-Path `$hrProxy) "headroom-proxy.ts: DEPLOYED" "headroom-proxy.ts: MISSING"
Assert-True (Test-Path `$hrLauncher) "claude-via-proxy.ts: DEPLOYED" "claude-via-proxy.ts: MISSING"
if (Test-Path `$hrShim) {
    Write-Host "  claude-hr.cmd shim: INSTALLED" -ForegroundColor Green
    `$shimContent = (Get-Content `$hrShim) -join ' / '
    Write-Host "    content: `$shimContent"
    # The shim must invoke bun against the deployed claude-via-proxy.ts.
    `$shimOk = `$shimContent.Contains(`$expectedShimTail) -and `$shimContent.Contains("bun ")
    Assert-True `$shimOk "shim target: CORRECT (bun -> claude-via-proxy.ts)" "shim target: WRONG (expected ...`$expectedShimTail)"
} else {
    Write-Host "  claude-hr.cmd shim: MISSING" -ForegroundColor Red
    `$failures.Add("claude-hr.cmd shim: MISSING")
}
if (Test-Path `$miseCfg) {
    `$miseContent = Get-Content `$miseCfg -Raw
    `$claudeTasks = ([regex]::Matches(`$miseContent, '\[tasks\."claude"\]')).Count
    Assert-True (`$miseContent -match '# >>> aftr headroom tasks >>>') "mise tasks sentinel: PRESENT" "mise tasks sentinel: MISSING"
    Assert-True (`$claudeTasks -eq 1) "mise [tasks.\"claude\"] count: `$claudeTasks (expected 1)" "mise [tasks.\"claude\"] count: `$claudeTasks (expected 1)"
} else {
    Write-Host "  mise config.toml: MISSING" -ForegroundColor Red
    `$failures.Add("mise config.toml: MISSING")
}

# Smoke-test the shim forwards to the launcher. Without podman the proxy 'ensure'
# step is expected to fail with a 'no container engine' style error (NOT a
# 'command not found'), which proves the shim resolved and ran the launcher.
if ((Test-Path `$hrShim) -and (Get-Command bun -ErrorAction SilentlyContinue)) {
    Write-Host "  Running 'claude-hr --version' (proxy start expected to fail without podman):"
    `$hrOut = & `$hrShim --version 2>&1 | Out-String
    Write-Host (`$hrOut.Trim() -split "`n" | ForEach-Object { "    `$_" }) -Separator "`n"
    if (`$hrOut -match 'container engine|podman|docker') {
        Write-Host "  shim forwarded to launcher: CONFIRMED (failed at container-engine check, as expected)" -ForegroundColor Green
    } else {
        Write-Host "  shim forwarded to launcher: UNCONFIRMED (unexpected output above)" -ForegroundColor Yellow
    }
}

# Summarize and report the result back to the host via the mapped results folder.
`$passed = (`$failures.Count -eq 0)
Write-Host "`n=== Test Complete ==="
if (`$passed) {
    Write-Host "RESULT: PASS (all Headroom artifacts verified)" -ForegroundColor Green
} else {
    Write-Host "RESULT: FAIL (`$(`$failures.Count) check(s) failed):" -ForegroundColor Red
    `$failures | ForEach-Object { Write-Host "  - `$_" -ForegroundColor Red }
}

Stop-Transcript
Write-Host "Transcript saved to: `$transcriptFile"

# Copy result + transcript to the host-mapped writable folder (survives sandbox close).
try {
    if (-not (Test-Path `$resultsDir)) { New-Item -ItemType Directory -Path `$resultsDir -Force | Out-Null }
    `$resultLine = if (`$passed) { "PASS" } else { "FAIL: " + (`$failures -join '; ') }
    `$resultLine | Out-File -FilePath (Join-Path `$resultsDir "result.txt") -Encoding UTF8 -Force
    Copy-Item `$transcriptFile (Join-Path `$resultsDir "claude-hr-transcript.txt") -Force -ErrorAction SilentlyContinue
    Write-Host "Result written to host: `$resultsDir\result.txt" -ForegroundColor Cyan
} catch {
    Write-Host "Could not write result to host folder: `$(`$_.Exception.Message)" -ForegroundColor Yellow
}

# Keep window open
Read-Host "`nPress Enter to close"
"@

    $wrapperPath = Join-Path $scriptRoot "test-claude-hr-wrapper.ps1"
    $testWrapper | Out-File -FilePath $wrapperPath -Encoding UTF8

    # Export the host's Trusted Root store so the sandbox can validate GitHub TLS
    # (needed for the bun installer download). The fresh Sandbox image has a stale
    # root store and certutil -syncWithWU is unreliable inside it; this serialized
    # store is mapped in read-only and imported by the wrapper before bun installs.
    # Generated artifact (gitignored). Serialize via .NET (Export-Certificate -Type
    # SST rejects the full store with 0x80092005 on duplicate cert properties).
    # Dedupe by thumbprint first.
    $sstPath = Join-Path $scriptRoot "sandbox-roots.sst"
    Write-Host "Exporting host root certificates to $sstPath..." -ForegroundColor Cyan
    $rootColl = New-Object System.Security.Cryptography.X509Certificates.X509Certificate2Collection
    foreach ($c in (Get-ChildItem Cert:\LocalMachine\Root | Sort-Object Thumbprint -Unique)) {
        $null = $rootColl.Add($c)
    }
    $sstBytes = $rootColl.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::SerializedStore)
    [System.IO.File]::WriteAllBytes($sstPath, $sstBytes)
    Write-Host "  Exported $($rootColl.Count) root certs ($([math]::Round($sstBytes.Length/1KB)) KB)" -ForegroundColor Green

    # Prepare a clean writable results folder mapped into the sandbox so the
    # in-sandbox test can report its pass/fail result back to the host.
    if (Test-Path $resultsDir) { Remove-Item $resultsDir -Recurse -Force }
    New-Item -ItemType Directory -Path $resultsDir -Force | Out-Null

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
        <MappedFolder>
            <HostFolder>$resultsDir</HostFolder>
            <SandboxFolder>C:\TestResults</SandboxFolder>
            <ReadOnly>false</ReadOnly>
        </MappedFolder>
    </MappedFolders>
    <LogonCommand>
        <Command>powershell -ExecutionPolicy Bypass -Command "Set-MpPreference -DisableRealtimeMonitoring `$true; Start-Process powershell -ArgumentList '-ExecutionPolicy Bypass -NoExit -File C:\TestFiles\tests\test-claude-hr-wrapper.ps1'"</Command>
    </LogonCommand>
    <MemoryInMB>8192</MemoryInMB>
</Configuration>
"@

    $sandboxXml | Out-File -FilePath $sandboxConfig -Encoding UTF8

    Write-Host "Starting Windows Sandbox with claude-hr test configuration..." -ForegroundColor Cyan
    Write-Host "The sandbox will:" -ForegroundColor Yellow
    Write-Host "  1. Mount this folder as C:\TestFiles (read-only)" -ForegroundColor Gray
    Write-Host "  2. Install bun, then run the real setupHeadroom()" -ForegroundColor Gray
    Write-Host "  3. Verify the deployed claude-hr / Headroom artifacts" -ForegroundColor Gray
    Write-Host "  4. Save transcript to sandbox desktop (claude-hr-transcript.txt)" -ForegroundColor Gray
    Write-Host ""

    # Launch the sandbox
    Start-Process $sandboxConfig

    Write-Host "Sandbox launched! Watch the sandbox window for progress." -ForegroundColor Green
    Write-Host "When done, simply close the sandbox - all changes are discarded." -ForegroundColor Gray
}

if (-not $EnableSandbox -and -not $RunTest) {
    Write-Host @"
claude-hr / Headroom Proxy Tester
=================================

Minimal Windows Sandbox test that validates ONLY the claude-hr / Headroom proxy
installation (no full environment setup). Target: ~2-3 min vs ~10 min for
test-setup.ps1.

Prerequisites:
  - Windows 10/11 Pro or Enterprise
  - Windows Sandbox feature enabled
  - Virtualization enabled in BIOS

Usage:
  .\test-claude-hr.ps1 -EnableSandbox   # one-time: enable the Sandbox feature
  .\test-claude-hr.ps1 -RunTest         # export host certs + launch the sandbox test
"@ -ForegroundColor Cyan
}
