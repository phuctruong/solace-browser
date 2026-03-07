# Deployment Notebook Report

Date: 2026-03-07
Project: solace-browser

## What was updated
1. Windows deployment flow is standardized on MSI (`solace-browser-windows-x86_64.msi`), not legacy `.exe`.
2. Notebook deployment checks now validate MSI format via OLE2 header bytes and `.msi` checksum naming.
3. `src/scripts/release_browser_cycle.sh` now runs MSI code-signing and supports fail-closed signing gate (`WINDOWS_SIGNING_REQUIRED=1`).
4. New script `scripts/sign-windows-msi.ps1` signs MSI with Authenticode + timestamp and verifies signature status.
5. MSI authoring now launches app automatically after successful interactive install (`UILevel >= 5`) with `--head`, never in silent installs.
6. Windows shortcuts (Start Menu + Desktop) are authored with `--head` to enforce headed default.
6. Windows icon pipeline now uses a canonical multi-size YinYang icon (16/32/48/64/128/256) for shortcuts and ARP icon.
7. Windows CI build now regenerates `resources/windows/solace-browser.ico` from YinYang assets before packaging.
8. Windows PyInstaller build runs with `--clean` in release cycle to prevent stale icon resources.
7. GitHub workflows now pass signing secrets and enforce signing on tag releases.

## Signing gate behavior
- Local/manual builds: signing is optional by default.
- Tag releases: signing is required (fail-closed).
- Supported signing inputs:
  - `WINDOWS_CODESIGN_PFX_BASE64` + `WINDOWS_CODESIGN_PFX_PASSWORD`, or
  - `WINDOWS_CODESIGN_CERT_THUMBPRINT`

## Why this fixes SmartScreen pain
- Unsigned MSI surfaces as `Unknown publisher` and triggers high-friction SmartScreen warnings.
- Signed + timestamped MSI provides trusted publisher identity and builds SmartScreen reputation over time.

## Remaining external requirement
1. Provide a valid code-signing certificate in CI secrets (OV/EV recommended; EV best for fastest SmartScreen trust).

## Internet references used (best practices)
1. Microsoft: `ProgramFiles64Folder` (64-bit install location guidance): https://learn.microsoft.com/en-us/windows/win32/msi/programfiles64folder
2. Microsoft: `UILevel` property (interactive vs silent installer UI behavior): https://learn.microsoft.com/en-us/windows/win32/msi/uilevel
3. Microsoft: `ARPPRODUCTICON` property (Add/Remove Programs icon): https://learn.microsoft.com/en-us/windows/win32/msi/arpproducticon
4. Microsoft: `signtool` options for modern digest + RFC3161 timestamp (`/fd`, `/td`, `/tr`): https://learn.microsoft.com/en-us/dotnet/framework/tools/signtool-exe
5. FireGiant/WiX: ARP and installer metadata best-practice surface: https://docs.firegiant.com/wix3/howtos/ui_and_localization/configure_arp_appearance/
