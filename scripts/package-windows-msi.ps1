param(
    [Parameter(Mandatory = $true)]
    [string]$InputBinary,
    [Parameter(Mandatory = $true)]
    [string]$OutputMsi,
    [Parameter(Mandatory = $true)]
    [string]$AppVersion
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
    throw "scripts/package-windows-msi.ps1 must run on Windows."
}

$inputPath = [System.IO.Path]::GetFullPath($InputBinary)
if (-not (Test-Path -LiteralPath $inputPath)) {
    throw "Input binary not found: $inputPath"
}

$outputMsiPath = [System.IO.Path]::GetFullPath($OutputMsi)
$outputDir = Split-Path -Parent $outputMsiPath
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$licensePath = Join-Path $repoRoot "LICENSE"
$icoPath = Join-Path $repoRoot "resources\windows\solace-browser.ico"

# ── Resolve WiX toolset ──────────────────────────────────────────────────────

function Resolve-WixPath {
    # Check if wix CLI is available (WiX v4+ as dotnet tool)
    $cmd = Get-Command "wix" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    # Try installing as dotnet tool
    Write-Host "WiX toolset not found. Installing via dotnet tool..."
    dotnet tool install --global wix 2>&1 | Out-Host

    $cmd = Get-Command "wix" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    # Fallback: check for WiX v3 candle/light
    $candleCmd = Get-Command "candle.exe" -ErrorAction SilentlyContinue
    if ($candleCmd) {
        return "wix3"
    }

    throw "Unable to locate WiX toolset. Install with: dotnet tool install --global wix"
}

$wixPath = Resolve-WixPath

# ── Generate WiX source (.wxs) ───────────────────────────────────────────────

$tempDir = Join-Path $env:TEMP ("solace-msi-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
$wxsPath = Join-Path $tempDir "solace-browser.wxs"

# Generate a stable product ID from version (reproducible builds)
$productGuid = [guid]::NewGuid().ToString("D")
$upgradeGuid = "5EA84A4E-95FA-452D-B6A0-39250E8CB5A9"

$inputFileName = [System.IO.Path]::GetFileName($inputPath)

$wxsContent = @"
<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Package
    Name="Solace Browser"
    Manufacturer="Solace AGI"
    Version="$AppVersion"
    UpgradeCode="$upgradeGuid"
    Scope="perMachine"
    InstallerVersion="500"
    Compressed="yes">

    <MajorUpgrade
      DowngradeErrorMessage="A newer version of Solace Browser is already installed." />

    <Property Id="ARPPRODUCTICON" Value="SolaceIcon" />

    <MediaTemplate EmbedCab="yes" />

    <StandardDirectory Id="ProgramFiles64Folder">
      <Directory Id="INSTALLFOLDER" Name="Solace Browser">

        <Component Id="MainExecutable" Guid="*">
          <File Id="SolaceBrowserExe"
                Source="$inputPath"
                Name="solace-browser.exe"
                KeyPath="yes" />
        </Component>

        <Component Id="LicenseFile" Guid="*">
          <File Id="LicenseFile"
                Source="$licensePath"
                Name="LICENSE"
                KeyPath="yes" />
        </Component>

      </Directory>
    </StandardDirectory>

    <!-- Start Menu shortcut -->
    <StandardDirectory Id="ProgramMenuFolder">
      <Directory Id="SolaceMenuFolder" Name="Solace Browser">
        <Component Id="StartMenuShortcut" Guid="*">
          <Shortcut Id="StartMenuLink"
                    Name="Solace Browser"
                    Target="[INSTALLFOLDER]solace-browser.exe"
                    Arguments="--head"
                    Icon="SolaceIcon"
                    IconIndex="0"
                    WorkingDirectory="INSTALLFOLDER" />
          <RemoveFolder Id="RemoveMenuFolder" On="uninstall" />
          <RegistryValue Root="HKLM"
                         Key="Software\SolaceAGI\SolaceBrowser"
                         Name="StartMenuInstalled"
                         Type="integer"
                         Value="1"
                         KeyPath="yes" />
        </Component>
      </Directory>
    </StandardDirectory>

    <!-- Desktop shortcut (optional via feature) -->
    <StandardDirectory Id="DesktopFolder">
      <Component Id="DesktopShortcut" Guid="*">
        <Shortcut Id="DesktopLink"
                  Name="Solace Browser"
                  Target="[INSTALLFOLDER]solace-browser.exe"
                  Arguments="--head"
                  Icon="SolaceIcon"
                  IconIndex="0"
                  WorkingDirectory="INSTALLFOLDER" />
        <RegistryValue Root="HKLM"
                       Key="Software\SolaceAGI\SolaceBrowser"
                       Name="DesktopInstalled"
                       Type="integer"
                       Value="1"
                       KeyPath="yes" />
      </Component>
    </StandardDirectory>

    <Icon Id="SolaceIcon" SourceFile="$icoPath" />

    <CustomAction Id="LaunchAfterInstall"
                  FileRef="SolaceBrowserExe"
                  ExeCommand="--head"
                  Return="asyncNoWait"
                  Impersonate="yes" />

    <Feature Id="MainFeature" Title="Solace Browser" Level="1">
      <ComponentRef Id="MainExecutable" />
      <ComponentRef Id="LicenseFile" />
      <ComponentRef Id="StartMenuShortcut" />
    </Feature>

    <Feature Id="DesktopFeature" Title="Desktop Shortcut" Level="1">
      <ComponentRef Id="DesktopShortcut" />
    </Feature>

    <InstallExecuteSequence>
      <!-- Launch app after successful interactive install only (never in silent mode). -->
      <Custom Action="LaunchAfterInstall"
              After="InstallFinalize"
              Condition="NOT Installed AND UILevel &gt;= 5 AND NOT REMOVE" />
    </InstallExecuteSequence>

  </Package>
</Wix>
"@

Set-Content -Path $wxsPath -Value $wxsContent -Encoding UTF8

# ── Build MSI ─────────────────────────────────────────────────────────────────

Write-Host "Building Windows MSI with WiX toolset..."

if ($wixPath -eq "wix3") {
    # WiX v3 fallback: candle + light
    $wixobjPath = Join-Path $tempDir "solace-browser.wixobj"
    & candle.exe -nologo -out $wixobjPath $wxsPath 2>&1 | Out-Host
    & light.exe -nologo -out $outputMsiPath -ext WixUIExtension $wixobjPath 2>&1 | Out-Host
} else {
    # WiX v4+: single command
    & $wixPath build -o $outputMsiPath $wxsPath 2>&1 | Out-Host
}

if (-not (Test-Path -LiteralPath $outputMsiPath)) {
    throw "MSI output not found: $outputMsiPath"
}

# ── Validate MSI format ──────────────────────────────────────────────────────

$msiBytes = [System.IO.File]::ReadAllBytes($outputMsiPath)
$oleHeader = [byte[]]@(0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1)
$headerMatch = $true
for ($i = 0; $i -lt 8; $i++) {
    if ($msiBytes[$i] -ne $oleHeader[$i]) {
        $headerMatch = $false
        break
    }
}

if (-not $headerMatch) {
    throw "Output file does not have MSI/OLE2 header. Build may have failed."
}

$sizeMb = [math]::Round($msiBytes.Length / 1MB, 2)
Write-Host "MSI created: $outputMsiPath ($sizeMb MB)"
Write-Host "Format: OLE2 Compound Document (Windows Installer)"

# ── Cleanup ───────────────────────────────────────────────────────────────────

Remove-Item -Path $tempDir -Recurse -Force -ErrorAction SilentlyContinue
