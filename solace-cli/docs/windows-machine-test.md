# Solace Browser Windows Machine Test Guide

Date: 2026-03-03
Scope: Validate real Windows download + install + runtime using production binaries and `https://www.solaceagi.com/agents`.

## 1. Prerequisites
- Windows 10/11 x64
- PowerShell 5.1+ (PowerShell 7 recommended)
- Internet access to:
  - `https://www.solaceagi.com/browser`
  - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/`

## 2. Download From Production
Open PowerShell and run:

```powershell
$ErrorActionPreference = 'Stop'
$OutDir = "$env:USERPROFILE\\Downloads\\solace-browser-test"
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$BinUrl = 'https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe'
$ShaUrl = 'https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe.sha256'
$BinPath = Join-Path $OutDir 'solace-browser-windows-x86_64.exe'
$ShaPath = Join-Path $OutDir 'solace-browser-windows-x86_64.exe.sha256'

Invoke-WebRequest -Uri $BinUrl -OutFile $BinPath
Invoke-WebRequest -Uri $ShaUrl -OutFile $ShaPath
```

## 3. Verify SHA-256 (Required)
```powershell
$Expected = (Get-Content $ShaPath).Split(' ')[0].Trim()
$Actual = (Get-FileHash -Algorithm SHA256 $BinPath).Hash.ToLower()
"Expected: $Expected"
"Actual:   $Actual"
if ($Expected -ne $Actual) { throw 'Checksum mismatch. Stop here.' }
```

## 4. Start Solace Browser
```powershell
$Port = 9222
$Proc = Start-Process -FilePath $BinPath -ArgumentList "--head --port $Port" -PassThru
"Started PID: $($Proc.Id)"
```

Notes:
- First run may take longer while Playwright Chromium is provisioned.
- Cache path used by runtime: `C:\Users\\<you>\\.cache\\ms-playwright`.

## 5. Runtime Health Checks
```powershell
$Base = 'http://127.0.0.1:9222'

# Wait up to 5 minutes for first-run startup
$Ready = $false
for ($i = 0; $i -lt 300; $i++) {
  try {
    $Status = Invoke-RestMethod -Uri "$Base/api/status" -Method Get
    $Ready = $true
    break
  } catch {
    Start-Sleep -Seconds 1
  }
}
if (-not $Ready) { throw 'Runtime did not become ready in time.' }

$Health = Invoke-RestMethod -Uri "$Base/api/health" -Method Get
$Status = Invoke-RestMethod -Uri "$Base/api/status" -Method Get
$Health | ConvertTo-Json -Depth 6
$Status | ConvertTo-Json -Depth 6
```

Expected:
- `/api/health` returns `ok: true`
- `/api/status` returns `running: true`

## 6. Validate /agents Instruction Flow
Navigate runtime to production instructions page:

```powershell
$NavBody = @{ url = 'https://www.solaceagi.com/agents' } | ConvertTo-Json
$Nav = Invoke-RestMethod -Uri "$Base/api/navigate" -Method Post -ContentType 'application/json' -Body $NavBody
$StatusAfter = Invoke-RestMethod -Uri "$Base/api/status" -Method Get
$Nav | ConvertTo-Json -Depth 6
$StatusAfter | ConvertTo-Json -Depth 6
```

Expected:
- Navigate call returns `success: true`
- Status `current_url` includes `https://www.solaceagi.com/agents`

## 7. Optional Snapshot Checks
```powershell
Invoke-RestMethod -Uri "$Base/api/aria-snapshot" -Method Get | Out-File (Join-Path $OutDir 'aria-snapshot.json')
Invoke-RestMethod -Uri "$Base/api/page-snapshot" -Method Get | Out-File (Join-Path $OutDir 'page-snapshot.json')
Invoke-RestMethod -Uri "$Base/api/snapshot" -Method Post -ContentType 'application/json' -Body '{}' | Out-File (Join-Path $OutDir 'snapshot.json')
```

## 8. Stop Runtime
```powershell
Stop-Process -Id $Proc.Id -Force
```

## 9. Pass/Fail Gate
Pass only if all are true:
1. Download succeeds from production URL.
2. SHA-256 matches published `.sha256`.
3. `/api/health` => `ok: true`.
4. `/api/status` => `running: true`.
5. Navigate to `https://www.solaceagi.com/agents` succeeds.

Fail-closed rule:
- Any mismatch/error blocks sign-off.
