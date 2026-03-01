# Diagram 10: Capture Pipeline — page.on('load') to 100% RTC
**Date:** 2026-03-01 | **Auth:** 65537
**Cross-ref:** Paper 05 (PZip Stillwater), Paper 06 (Evidence)

---

## Full Capture Pipeline

```mermaid
flowchart TD
    LOAD["page.on('load')"] --> CHECK{"First time\nseeing domain?"}

    CHECK -->|Yes| INIT["Create ~/.solace/stillwater/{domain}/\nCreate ~/.solace/history/{domain}/\nCapture ALL site assets"]
    CHECK -->|No| DOM

    INIT --> DOM["DOM Snapshot\n(dom_snapshot.py)\nDOMRefs + form_state + dom_hash"]

    DOM --> WIKI["Prime Wiki Entry\nAdd to {domain}/sitemap.jsonl\nLinks + headings + forms"]
    DOM --> MERMAID["Prime Mermaid Snapshot\nDOM structure + form values\nMermaid stateDiagram-v2\n(THIS IS THE RIPPLE)"]

    MERMAID --> RTC{"PZip 100% RTC\nsha256(reconstructed)\n== sha256(original)?"}

    RTC -->|"YES ✓"| STORE["Store Locally\n{ts}.ripple.mmd\nsitemap.jsonl"]
    RTC -->|"NO ✗"| FIX["Capture Missing Assets\nSave to Stillwater\nRetry RTC"]
    FIX --> RTC

    style LOAD fill:#2d7a2d,color:#fff
    style DOM fill:#2d7a2d,color:#fff
    style WIKI fill:#7a5a00,color:#fff
    style MERMAID fill:#7a5a00,color:#fff
    style RTC fill:#222,color:#fff
    style STORE fill:#2d7a2d,color:#fff
    style FIX fill:#1a5cb5,color:#fff
    style INIT fill:#2d7a2d,color:#fff
```

## Data Flow

```mermaid
graph TB
    subgraph "Browser (ALL computation here)"
        PL["page.on('load')"]
        DS["dom_snapshot.py\nDOMRef capture"]
        PM["Prime Mermaid\nsnapshot → stateDiagram"]
        PW["Prime Wiki\nsitemap entry"]
        PZ["PZip\nverify 100% RTC"]
        SW["Stillwater\nsite + public assets"]
        RP["Ripple Store\n~/.solace/history/"]
    end

    subgraph "solaceagi.com (receive only)"
        CDN["CDN: Stillwater bundles"]
        INBOX["Append-only inbox"]
    end

    PL --> DS --> PM --> PZ
    DS --> PW
    PZ --> SW
    PZ -->|verified| RP
    SW -.->|"periodic sync"| INBOX
    CDN -.->|"pull on startup"| SW

    style PL fill:#2d7a2d,color:#fff
    style DS fill:#2d7a2d,color:#fff
    style PM fill:#7a5a00,color:#fff
    style PW fill:#7a5a00,color:#fff
    style PZ fill:#222,color:#fff
    style SW fill:#2d7a2d,color:#fff
    style RP fill:#2d7a2d,color:#fff
    style CDN fill:#7a2d7a,color:#fff
    style INBOX fill:#7a2d7a,color:#fff
```

## Storage Layout

```
~/.solace/
  history/{domain}/{ts}.ripple.mmd     ← Prime Mermaid snapshot (2-5 KB)
  history/{domain}/sitemap.jsonl        ← Prime Wiki entries
  stillwater/{domain}/v{N}/             ← site-specific assets (versioned)
  stillwater/public/v{N}/               ← shared libraries
```

## Invariants

1. ALL computation is client-side (zero cloud compute)
2. 100% RTC must pass before ripple is stored
3. Missing assets trigger Stillwater capture + retry (never store invalid ripple)
4. Stillwater versions are never deleted (Part 11 compliance)
5. DOM snapshot uses existing dom_snapshot.py (675 lines, DOMRef system)
6. Prime Mermaid snapshot IS the ripple (not a separate artifact)
