# 19 — Browser Release Loop

```mermaid
flowchart TD
    START[Start release round] --> BUILD[Compile binary with PyInstaller]
    BUILD --> HASH[Generate SHA-256]
    HASH --> UP_V[Upload versioned artifact to GCS]
    UP_V --> UP_L[Upload latest artifact to GCS]
    UP_L --> DL[Download from production URL]
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
- Versioned path is immutable (`v{VERSION}`), latest is mutable.
- Smoke runtime is head-on by default (`--head`), not headless.
- Production API matrix validates routing, auth gates, and server stability.
- Every round writes evidence and timings to `scratch/release-cycle/<timestamp>/`.
