param(
    [string]$ChromiumOut = "",
    [string]$HubBinary = "",
    [string]$DistDir = "",
    [string]$BundleDir = "",
    [string]$OutputMsi = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($ChromiumOut)) {
    $ChromiumOut = Join-Path $repoRoot "source\src\out\Solace"
}
if ([string]::IsNullOrWhiteSpace($HubBinary)) {
    $HubBinary = Join-Path $repoRoot "solace-hub\src-tauri\target\release\solace-hub.exe"
}
if ([string]::IsNullOrWhiteSpace($DistDir)) {
    $DistDir = Join-Path $repoRoot "dist"
}
if ([string]::IsNullOrWhiteSpace($BundleDir)) {
    $BundleDir = Join-Path $DistDir "solace-browser-release-windows"
}
$version = (Get-Content (Join-Path $repoRoot "VERSION") -Raw).Trim()
if ([string]::IsNullOrWhiteSpace($OutputMsi)) {
    $OutputMsi = Join-Path $DistDir "solace-browser-windows-x86_64.msi"
}
$bootstrapUrl = "https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe"

function Fail([string]$message) {
    throw $message
}

function Require-Path([string]$path) {
    if (-not (Test-Path -LiteralPath $path)) {
        Fail "required path not found: $path"
    }
}

function Copy-Tree([string]$sourcePath, [string]$destinationPath) {
    Require-Path $sourcePath
    Copy-Item -LiteralPath $sourcePath -Destination $destinationPath -Recurse -Force
}

Require-Path $ChromiumOut
if (-not (Test-Path -LiteralPath (Join-Path $ChromiumOut "chrome.exe"))) {
    New-Item -ItemType Directory -Force -Path $ChromiumOut | Out-Null
    Write-Host "Bootstrapping Windows browser payload from $bootstrapUrl"
    Invoke-WebRequest -Uri $bootstrapUrl -OutFile (Join-Path $ChromiumOut "chrome.exe")
}
Require-Path (Join-Path $ChromiumOut "chrome.exe")
Require-Path (Join-Path $repoRoot "yinyang_server.py")
Require-Path (Join-Path $repoRoot "yinyang-server.py")

if (-not (Test-Path -LiteralPath $HubBinary)) {
    Push-Location (Join-Path $repoRoot "solace-hub\src-tauri")
    try {
        cargo build --release
    }
    finally {
        Pop-Location
    }
}
Require-Path $HubBinary

New-Item -ItemType Directory -Force -Path $DistDir | Out-Null
if (Test-Path -LiteralPath $BundleDir) {
    Remove-Item -LiteralPath $BundleDir -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $BundleDir | Out-Null

$runtimePatterns = @("*.exe", "*.dll", "*.pak", "*.bin", "*.dat", "*.json")
Get-ChildItem -LiteralPath $ChromiumOut -File | Where-Object {
    $name = $_.Name
    foreach ($pattern in $runtimePatterns) {
        if ($name -like $pattern) {
            return $true
        }
    }
    return $false
} | ForEach-Object {
    Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $BundleDir $_.Name) -Force
}

foreach ($runtimeDir in @("locales", "resources", "angledata", "MEIPreload", "PrivacySandboxAttestationsPreloaded", "hyphen-data")) {
    $src = Join-Path $ChromiumOut $runtimeDir
    if (Test-Path -LiteralPath $src) {
        Copy-Tree $src $BundleDir
    }
}

foreach ($runtimeRoot in @("app", "apps", "src", "web")) {
    Copy-Tree (Join-Path $repoRoot $runtimeRoot) $BundleDir
}

New-Item -ItemType Directory -Force -Path (Join-Path $BundleDir "data\default") | Out-Null
Copy-Tree (Join-Path $repoRoot "data\default\apps") (Join-Path $BundleDir "data\default")
Copy-Tree (Join-Path $repoRoot "data\default\app-store") (Join-Path $BundleDir "data\default")
Copy-Tree (Join-Path $repoRoot "data\fun-packs") (Join-Path $BundleDir "data")

Copy-Item -LiteralPath $HubBinary -Destination (Join-Path $BundleDir "solace-hub.exe") -Force

foreach ($scriptName in @("yinyang_server.py", "yinyang-server.py", "yinyang_mcp_server.py", "hub_tunnel_client.py", "evidence_bundle.py", "solace_cli.py")) {
    $scriptPath = Join-Path $repoRoot $scriptName
    if (Test-Path -LiteralPath $scriptPath) {
        Copy-Item -LiteralPath $scriptPath -Destination (Join-Path $BundleDir $scriptName) -Force
    }
}

Copy-Item -LiteralPath (Join-Path $repoRoot "VERSION") -Destination (Join-Path $BundleDir "VERSION") -Force
if (Test-Path -LiteralPath (Join-Path $repoRoot "requirements.txt")) {
    Copy-Item -LiteralPath (Join-Path $repoRoot "requirements.txt") -Destination (Join-Path $BundleDir "requirements.txt") -Force
}
if (Test-Path -LiteralPath (Join-Path $repoRoot "solace-hub\src-tauri\icons\yinyang-logo.png")) {
    Copy-Item -LiteralPath (Join-Path $repoRoot "solace-hub\src-tauri\icons\yinyang-logo.png") -Destination (Join-Path $BundleDir "yinyang-logo.png") -Force
}

$launcher = @'
@echo off
setlocal
set SCRIPT_DIR=%~dp0
"%SCRIPT_DIR%solace-hub.exe" %*
'@
Set-Content -LiteralPath (Join-Path $BundleDir "solace-browser.cmd") -Value $launcher -Encoding ASCII

$manifest = @{
    version = $version
    bundle = "solace-browser-release-windows"
    windows_portable = $true
    hub_binary = "solace-hub.exe"
    browser_binary = "chrome.exe"
    runtime_port = 8888
} | ConvertTo-Json -Depth 4
Set-Content -LiteralPath (Join-Path $BundleDir "manifest.json") -Value $manifest -Encoding UTF8

$wix = Get-Command "wix.exe" -ErrorAction SilentlyContinue
if (-not $wix) {
    $wix = Get-Command "wix" -ErrorAction SilentlyContinue
}
if (-not $wix) {
    $candidate = Join-Path $env:USERPROFILE ".dotnet\tools\wix.exe"
    if (Test-Path -LiteralPath $candidate) {
        $wix = [pscustomobject]@{ Source = $candidate }
    }
}
if (-not $wix) {
    $candidate = Join-Path $env:USERPROFILE ".dotnet\tools\wix"
    if (Test-Path -LiteralPath $candidate) {
        $wix = [pscustomobject]@{ Source = $candidate }
    }
}
if (-not $wix) {
    Fail "WiX not found on PATH or dotnet tools path; cannot build MSI"
}

$componentLines = New-Object System.Collections.Generic.List[string]
$guidSeed = [guid]::NewGuid().ToString().Replace("-", "")
$counter = 0
Get-ChildItem -LiteralPath $BundleDir -Recurse -File | Sort-Object FullName | ForEach-Object {
    $counter += 1
    $relative = $_.FullName.Substring($BundleDir.Length).TrimStart('\')
    $componentId = ("BundleFile{0:0000}" -f $counter)
    $fileId = ("BundlePayload{0:0000}" -f $counter)
    $componentGuid = [guid]::NewGuid().ToString().ToUpperInvariant()
    $source = '$(var.BundleDir)\' + $relative.Replace('/', '\')
    $componentLines.Add("      <Component Id=`"$componentId`" Guid=`"$componentGuid`">")
    $componentLines.Add("        <File Id=`"$fileId`" Source=`"$source`" KeyPath=`"yes`" />")
    $componentLines.Add("      </Component>")
}

$fragment = @(
    '<?xml version="1.0" encoding="UTF-8"?>',
    '<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">',
    '  <Fragment>',
    '    <ComponentGroup Id="BundleFiles" Directory="INSTALLFOLDER">'
) + $componentLines + @(
    '    </ComponentGroup>',
    '  </Fragment>',
    '</Wix>'
) -join [Environment]::NewLine

$generatedFragment = Join-Path $DistDir "windows-bundle-files.wxs"
Set-Content -LiteralPath $generatedFragment -Value $fragment -Encoding UTF8

$wixArgs = @(
    "build",
    "-src", (Join-Path $repoRoot "scripts\windows\solace-browser.wxs"),
    "-src", $generatedFragment,
    "-out", $OutputMsi,
    "-d", "BundleDir=$BundleDir"
)
& $wix.Source @wixArgs
if ($LASTEXITCODE -ne 0) {
    Fail "wix build failed with exit code $LASTEXITCODE"
}
Require-Path $OutputMsi

$signScript = Join-Path $repoRoot "scripts\sign-windows-msi.ps1"
if (Test-Path -LiteralPath $signScript) {
    & $signScript -InputMsi $OutputMsi
}

$hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $OutputMsi).Hash.ToLowerInvariant()
Set-Content -LiteralPath "${OutputMsi}.sha256" -Value "$hash  $(Split-Path $OutputMsi -Leaf)" -Encoding ASCII

Write-Host $BundleDir
Write-Host $OutputMsi
Write-Host "${OutputMsi}.sha256"
