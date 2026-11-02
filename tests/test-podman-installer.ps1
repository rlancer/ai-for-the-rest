# Tests the installer functions without downloading or installing software.
$ErrorActionPreference = "Stop"
$setupPath = Join-Path (Split-Path $PSScriptRoot -Parent) "scripts\setup.ps1"
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile($setupPath, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$installer = $ast.Find({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq "Install-OfficialPodman" }, $true)
if (-not $installer) { throw "Installer function missing" }
Invoke-Expression $installer.Extent.Text

$testRoot = Join-Path ([IO.Path]::GetTempPath()) ("aftr-podman-test-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$fakePodman = Join-Path $testRoot "podman.ps1"
Set-Content -LiteralPath $fakePodman -Value 'Write-Output "podman version test"; $global:LASTEXITCODE = 0'
$originalTemp = $env:TEMP
$originalPath = $env:PATH
$originalArch = $env:PROCESSOR_ARCHITECTURE
$originalArchW6432 = $env:PROCESSOR_ARCHITEW6432
$env:TEMP = $testRoot
$env:PROCESSOR_ARCHITECTURE = "AMD64"
$env:PROCESSOR_ARCHITEW6432 = ""

function Assert-True($Condition, $Message) {
    if (-not $Condition) { throw $Message }
}
function Assert-Throws([scriptblock]$Action, [string]$Pattern) {
    try { & $Action } catch {
        if ($_.Exception.Message -like $Pattern) { return }
        throw
    }
    throw "Expected failure matching: $Pattern"
}
function Reset-Mocks {
    $script:Installed = $false
    $script:Requests = 0
    $script:Installs = 0
    $script:ExitCode = 0
    $script:Hash = 'a' * 64
    $script:Digest = 'sha256:' + ('a' * 64)
    $script:SignatureStatus = "Valid"
    $script:MissingAfterInstall = $false
    $script:AssetName = "podman-installer-windows-amd64.msi"
}
function Get-PodmanExecutable {
    if ($script:Installed -and -not $script:MissingAfterInstall) { return $fakePodman }
}
function Invoke-RestMethod {
    [CmdletBinding()] param($Uri)
    $script:Requests++
    return [pscustomobject]@{ tag_name = 'v-test'; assets = @([pscustomobject]@{
        name = $script:AssetName; digest = $script:Digest
        browser_download_url = "https://github.com/podman-container-tools/podman/releases/download/v-test/$script:AssetName"
    }) }
}
function Invoke-WebRequest {
    [CmdletBinding()] param($Uri, $OutFile, [switch]$UseBasicParsing)
    [IO.File]::WriteAllText($OutFile, 'mock MSI')
}
function Get-FileHash {
    [CmdletBinding()] param($LiteralPath, $Algorithm)
    return [pscustomobject]@{ Hash = $script:Hash }
}
function Get-AuthenticodeSignature {
    [CmdletBinding()] param($LiteralPath)
    return [pscustomobject]@{ Status = $script:SignatureStatus }
}
function Start-Process {
    [CmdletBinding()] param($FilePath, $ArgumentList, $WindowStyle, [switch]$Wait, [switch]$PassThru)
    Assert-True ($FilePath -eq 'msiexec.exe') 'Must use the MSI installer'
    Assert-True ($ArgumentList -contains '/norestart') 'Must not restart Windows'
    Assert-True ($ArgumentList[1] -match '^".*\.msi"$') 'MSI path must be quoted'
    Assert-True ($Wait -and $PassThru) 'Must wait for the installer and inspect its exit code'
    $script:Installs++
    $script:Installed = $true
    return [pscustomobject]@{ ExitCode = $script:ExitCode }
}
try {
    Reset-Mocks
    Assert-Throws { Install-OfficialPodman -InstalledScoopApps @('podman') } '*installed through Scoop*'
    Assert-True ($script:Requests -eq 0 -and $script:Installs -eq 0) 'Scoop migration must not change the machine'

    Reset-Mocks
    $script:Installed = $true
    Install-OfficialPodman
    Assert-True ($script:Requests -eq 0 -and $script:Installs -eq 0) 'Existing installations must be kept'

    Reset-Mocks
    $script:Hash = 'b' * 64
    Assert-Throws { Install-OfficialPodman } '*SHA256 mismatch*'
    Assert-True ($script:Installs -eq 0) 'Checksum mismatch must prevent installation'

    Reset-Mocks
    $script:Digest = ''
    Assert-Throws { Install-OfficialPodman } '*SHA256 digest*'
    Assert-True ($script:Installs -eq 0) 'Missing digest must prevent installation'

    Reset-Mocks
    $script:SignatureStatus = 'NotSigned'
    Assert-Throws { Install-OfficialPodman } '*signature is not valid*'
    Assert-True ($script:Installs -eq 0) 'Invalid signature must prevent installation'

    Reset-Mocks
    Install-OfficialPodman
    Assert-True ($script:Installs -eq 1) 'x64 installation must succeed'

    Reset-Mocks
    $env:PROCESSOR_ARCHITEW6432 = 'ARM64'
    $script:AssetName = 'podman-installer-windows-arm64.msi'
    $script:ExitCode = 3010
    Install-OfficialPodman
    Assert-True ($script:Installs -eq 1) 'ARM64 and reboot-required exit code must be supported'
    $env:PROCESSOR_ARCHITEW6432 = ''

    Reset-Mocks
    $script:ExitCode = 1603
    Assert-Throws { Install-OfficialPodman } '*MSI failed with exit code 1603*'

    Reset-Mocks
    $script:MissingAfterInstall = $true
    Assert-Throws { Install-OfficialPodman } '*podman.exe was not found*'

    $config = Get-Content (Join-Path (Split-Path $PSScriptRoot -Parent) 'config\config.json') -Raw | ConvertFrom-Json
    Assert-True ($config.packages.windows.scoop -notcontains 'podman') 'Scoop must not install Podman'
    Write-Host 'Passed all 10 Podman installer checks.' -ForegroundColor Green
} finally {
    $env:TEMP = $originalTemp
    $env:PATH = $originalPath
    $env:PROCESSOR_ARCHITECTURE = $originalArch
    $env:PROCESSOR_ARCHITEW6432 = $originalArchW6432
    $resolvedTestRoot = [IO.Path]::GetFullPath($testRoot)
    $tempPrefix = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\aftr-podman-test-'
    if ($resolvedTestRoot.StartsWith($tempPrefix, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $resolvedTestRoot -Recurse -Force
    }
}
