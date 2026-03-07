param(
    [Parameter(Mandatory = $true)]
    [string]$InputMsi,
    [switch]$RequireSigning
)

$ErrorActionPreference = "Stop"

$runningOnWindows = $false
if (Get-Variable -Name IsWindows -ErrorAction SilentlyContinue) {
    $runningOnWindows = [bool]$IsWindows
}
elseif ($env:OS -eq "Windows_NT") {
    $runningOnWindows = $true
}

if (-not $runningOnWindows) {
    throw "scripts/sign-windows-msi.ps1 must run on Windows."
}

$msiPath = [System.IO.Path]::GetFullPath($InputMsi)
if (-not (Test-Path -LiteralPath $msiPath)) {
    throw "MSI not found: $msiPath"
}

function Resolve-SignToolPath {
    $cmd = Get-Command "signtool.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $sdkRoots = @(
        "${env:ProgramFiles(x86)}\Windows Kits\10\bin",
        "${env:ProgramFiles}\Windows Kits\10\bin"
    )
    foreach ($root in $sdkRoots) {
        if (-not (Test-Path -LiteralPath $root)) {
            continue
        }
        $matches = Get-ChildItem -Path $root -Recurse -Filter "signtool.exe" -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending
        if ($matches -and $matches.Count -gt 0) {
            return $matches[0].FullName
        }
    }

    return $null
}

function Get-IsTruthy([string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) {
        return $false
    }
    $normalized = $value.Trim().ToLowerInvariant()
    return $normalized -in @("1", "true", "yes", "on")
}

$required = $RequireSigning.IsPresent -or (Get-IsTruthy $env:WINDOWS_SIGNING_REQUIRED)
$existingSig = Get-AuthenticodeSignature -FilePath $msiPath

if ($existingSig.Status -eq "Valid") {
    Write-Host "MSI already signed and valid: $msiPath"
    exit 0
}

$pfxB64 = $env:WINDOWS_CODESIGN_PFX_BASE64
$pfxPassword = $env:WINDOWS_CODESIGN_PFX_PASSWORD
$thumbprint = $env:WINDOWS_CODESIGN_CERT_THUMBPRINT
$timestampUrl = $env:WINDOWS_CODESIGN_TIMESTAMP_URL
if ([string]::IsNullOrWhiteSpace($timestampUrl)) {
    $timestampUrl = "http://timestamp.digicert.com"
}

$hasPfx = -not [string]::IsNullOrWhiteSpace($pfxB64)
$hasThumbprint = -not [string]::IsNullOrWhiteSpace($thumbprint)

if (-not $hasPfx -and -not $hasThumbprint) {
    if ($required) {
        throw "Windows signing required but no signing material provided. Set WINDOWS_CODESIGN_PFX_BASE64 (+ password) or WINDOWS_CODESIGN_CERT_THUMBPRINT."
    }
    Write-Host "No signing material configured; skipping MSI signing (WINDOWS_SIGNING_REQUIRED=0)."
    exit 0
}

$signTool = Resolve-SignToolPath
if (-not $signTool) {
    if ($required) {
        throw "Windows signing required but signtool.exe was not found."
    }
    Write-Host "signtool.exe not found; skipping MSI signing (WINDOWS_SIGNING_REQUIRED=0)."
    exit 0
}

$tmpPfx = $null
try {
    $signArgs = @(
        "sign",
        "/fd", "SHA256",
        "/td", "SHA256",
        "/tr", $timestampUrl
    )

    if ($hasPfx) {
        if ([string]::IsNullOrWhiteSpace($pfxPassword)) {
            throw "WINDOWS_CODESIGN_PFX_PASSWORD is required when using WINDOWS_CODESIGN_PFX_BASE64."
        }
        $tmpPfx = Join-Path $env:TEMP ("solace-codesign-" + [guid]::NewGuid().ToString("N") + ".pfx")
        [System.IO.File]::WriteAllBytes($tmpPfx, [System.Convert]::FromBase64String($pfxB64))
        $signArgs += @("/f", $tmpPfx, "/p", $pfxPassword)
    }
    elseif ($hasThumbprint) {
        $cleanThumbprint = $thumbprint.Replace(" ", "")
        $signArgs += @("/sha1", $cleanThumbprint)
    }

    $signArgs += @($msiPath)
    & $signTool @signArgs
    if ($LASTEXITCODE -ne 0) {
        throw "signtool sign failed with exit code $LASTEXITCODE"
    }
}
finally {
    if ($tmpPfx -and (Test-Path -LiteralPath $tmpPfx)) {
        Remove-Item -LiteralPath $tmpPfx -Force -ErrorAction SilentlyContinue
    }
}

$finalSig = Get-AuthenticodeSignature -FilePath $msiPath
if ($finalSig.Status -ne "Valid") {
    throw "MSI signature verification failed after signing. Status: $($finalSig.Status) ($($finalSig.StatusMessage))"
}

Write-Host "MSI signed successfully."
Write-Host "Signer: $($finalSig.SignerCertificate.Subject)"
