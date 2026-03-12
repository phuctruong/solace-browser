param(
    [string]$Bucket = "solace-downloads",
    [string]$Tag = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ([string]::IsNullOrWhiteSpace($Tag)) {
    $version = (Get-Content (Join-Path $repoRoot "VERSION") -Raw).Trim()
    $Tag = "v$version"
}

Push-Location $repoRoot
try {
    & (Join-Path $repoRoot "scripts\build-windows-release.ps1")
    python3 (Join-Path $repoRoot "scripts\promote_native_builds_to_gcs.py") `
        --tag $Tag `
        --artifacts-dir (Join-Path $repoRoot "dist") `
        --bucket $Bucket
}
finally {
    Pop-Location
}
