# 19 — Browser Release Loop

```mermaid
flowchart TD
    START[Start release round] --> TARGET[Select TARGET_OS: linux/macos/windows]
    TARGET --> BUILD[Compile binary with PyInstaller]
    BUILD --> TYPE[Verify native binary format<br/>ELF or Mach-O or PE]
    TYPE --> HASH[Generate SHA-256]
    HASH --> CIART[Upload native artifact bundle to GitHub Actions]
    CIART --> PROMOTE[Promote artifact bundle to GCS]
    PROMOTE --> UP_V[Upload versioned artifact to GCS]
    UP_V --> UP_L[Upload latest artifact to GCS]
    UP_L --> LINK[Publish/verify solaceagi.com download links]
    LINK --> DL[Download from production URL]
    DL --> SMOKE[Run binary with --head]
    SMOKE --> STATUS{GET /api/status OK?}
    STATUS -->|No| FAIL[Fail release + keep previous latest]
    STATUS -->|Yes| MATRIX[Run production API matrix from openapi.json]
    MATRIX --> API_OK{Any 5xx or transport failures?}
    API_OK -->|Yes| FAIL
    API_OK -->|No| REPORT[Write metrics + report in scratch]
    REPORT --> DONE[Release round complete]
```

## Notes
- Platform object names:
  - Linux: `solace-browser-linux-x86_64`
  - macOS: `solace-browser-macos-universal`
  - Windows: `solace-browser-windows-x86_64.exe`
- Native host requirements:
  - Linux artifacts on Linux (`ubuntu-22.04` baseline in CI)
  - macOS artifacts on macOS (runner-native Mach-O)
  - Windows artifacts on Windows
- Binary-type gate is fail-closed:
  - reject upload if target artifact type does not match platform
- Versioned path is immutable (`v{VERSION}`), latest is mutable.
- Cache-control: `v{VERSION}` immutable caching; `latest` no-store.
- Website contract:
  - `www.solaceagi.com` must link to `https://storage.googleapis.com/solace-downloads/solace-browser/latest/<artifact>`
- Smoke runtime is head-on by default (`--head`), not headless.
- First run auto-installs missing Playwright Chromium into `~/.cache/ms-playwright`.
- Production API matrix validates routing, auth gates, and server stability.
- Every round writes evidence and timings to `scratch/release-cycle/<timestamp>/`.
