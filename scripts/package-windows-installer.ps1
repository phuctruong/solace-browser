param(
    [Parameter(Mandatory = $true)]
    [string]$InputBinary,
    [Parameter(Mandatory = $true)]
    [string]$OutputInstaller,
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
    throw "scripts/package-windows-installer.ps1 must run on Windows."
}

$inputPath = [System.IO.Path]::GetFullPath($InputBinary)
if (-not (Test-Path -LiteralPath $inputPath)) {
    throw "Input binary not found: $inputPath"
}

$outputInstallerPath = [System.IO.Path]::GetFullPath($OutputInstaller)
$outputDir = Split-Path -Parent $outputInstallerPath
$outputBaseName = [System.IO.Path]::GetFileNameWithoutExtension($outputInstallerPath)
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$repoRoot = [System.IO.Path]::GetFullPath((Join-Path $PSScriptRoot ".."))
$licensePath = Join-Path $repoRoot "LICENSE"

function Resolve-IsccPath {
    $cmd = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $default = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    if (Test-Path -LiteralPath $default) {
        return $default
    }

    Write-Host "Inno Setup not found. Installing via Chocolatey..."
    choco install innosetup --yes --no-progress | Out-Host

    $cmd = Get-Command "iscc.exe" -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }
    if (Test-Path -LiteralPath $default) {
        return $default
    }
    throw "Unable to locate ISCC.exe after installing Inno Setup."
}

$isccPath = Resolve-IsccPath

$tempDir = Join-Path $env:TEMP ("solace-installer-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
$issPath = Join-Path $tempDir "solace-browser-installer.iss"

$icoPath = Join-Path $repoRoot "resources\windows\solace-browser.ico"

$issContent = @'
#define AppName "Solace Browser"
#define AppPublisher "Solace AGI"
#define AppExeName "solace-browser.exe"

[Setup]
AppId={{5EA84A4E-95FA-452D-B6A0-39250E8CB5A9}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\Solace Browser
DefaultGroupName=Solace Browser
OutputDir={#OutputDir}
OutputBaseFilename={#OutputBaseFilename}
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64
WizardStyle=modern
PrivilegesRequired=admin
SetupIconFile={#SetupIcon}
UninstallDisplayIcon={app}\{#AppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "{#InputBinary}"; DestDir: "{app}"; DestName: "{#AppExeName}"; Flags: ignoreversion
Source: "{#SetupIcon}"; DestDir: "{app}"; DestName: "solace-browser.ico"; Flags: ignoreversion
Source: "{#LicenseFile}"; DestDir: "{app}"; DestName: "LICENSE"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\Solace Browser"; Filename: "{app}\{#AppExeName}"; Parameters: "--head"
Name: "{group}\Uninstall Solace Browser"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Solace Browser"; Filename: "{app}\{#AppExeName}"; Parameters: "--head"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Parameters: "--head"; Description: "Launch Solace Browser"; Flags: nowait postinstall skipifsilent
'@

Set-Content -Path $issPath -Value $issContent -Encoding UTF8

$compileArgs = @(
    "/Qp",
    "/DAppVersion=$AppVersion",
    "/DOutputDir=$outputDir",
    "/DOutputBaseFilename=$outputBaseName",
    "/DInputBinary=$inputPath",
    "/DLicenseFile=$licensePath",
    "/DSetupIcon=$icoPath",
    $issPath
)

Write-Host "Compiling Windows installer with Inno Setup..."
& $isccPath @compileArgs | Out-Host

$producedInstaller = Join-Path $outputDir ($outputBaseName + ".exe")
if (-not (Test-Path -LiteralPath $producedInstaller)) {
    throw "Installer output not found: $producedInstaller"
}

if ($producedInstaller -ne $outputInstallerPath) {
    Move-Item -LiteralPath $producedInstaller -Destination $outputInstallerPath -Force
}

Write-Host "Installer created: $outputInstallerPath"
