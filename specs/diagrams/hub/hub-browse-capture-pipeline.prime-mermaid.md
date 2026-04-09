<!-- Diagram: hub-browse-capture-pipeline -->
# hub-browse-capture-pipeline: Every Navigate → Auto-Detect HTML or API → Capture
# DNA: `navigate(url) → detect(html|json) → html→prime-wiki | json→apis → evidence(part11) + sync(paid)`
# Auth: 65537 | Version: 2.0.0
# THIS IS WHY EVERYTHING MUST BE A WEBSERVICE WITH MCP WRAPPER

## Core Insight
When a user navigates to ANY URL through Solace Browser, the Hub runtime:
1. Auto-detects if the response is HTML (visual page) or JSON (API endpoint)
2. HTML → extracts Stillwater/Ripple → stores in prime-wiki/ (what users SEE)
3. JSON → extracts schema/keys → stores in apis/ (what agents CALL)
4. Both → creates FDA Part 11 evidence entry (hash-chained)
5. Both → PZip compresses original for RTC reconstruction

Community browsing captures BOTH visual pages AND API contracts.
Same pipeline, auto-detect, different output destination.


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-evidence](hub-evidence.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TD
    NAV[User Navigates to URL<br>via browser or POST /api/navigate] --> FETCH[Fetch Response<br>from rendered DOM or HTTP]

    FETCH --> DETECT{Auto-Detect<br>Content-Type?}

    subgraph HTML_PATH[HTML → prime-wiki/ (visual)]
        DETECT -->|text/html| DOMAIN{Domain stillwater<br>exists?}
        DOMAIN -->|no| CREATE_SW[Create Domain Stillwater<br>nav + header + footer + CSS]
        DOMAIN -->|yes| LOAD_SW[Load Existing Stillwater]
        CREATE_SW --> SW_STORE[Store domain.stillwater.json]

        DETECT -->|text/html| EXTRACT_HTML[Extract Stillwater/Ripple<br>headings + sections + meta]
        EXTRACT_HTML --> SNAPSHOT_MD[.prime-snapshot.md<br>headings + sections + meta]
        EXTRACT_HTML --> WIKI_PZWB[prime-wiki/.pzwb<br>PZip original]
        EXTRACT_HTML --> 
    end

    subgraph API_PATH[JSON → apis/ (contract)]
        DETECT -->|application/json| EXTRACT_API[Extract API Schema<br>keys + types + values]
        EXTRACT_API --> API_SNAPSHOT[.prime-snapshot.md<br>API schema + keys]
        EXTRACT_API --> API_PZWB[apis/.pzwb<br>PZip original]
    end
    
    subgraph SCREENSHOT_OPT[Screenshot — Optional]
        FETCH --> SCREEN{Auto-screenshot<br>enabled in settings?}
        SCREEN -->|yes| CAPTURE[Capture screenshot<br>full page PNG]
        SCREEN -->|no| SKIP_SCREEN[Skip — text evidence only]
        CAPTURE --> SCREEN_HASH[SHA-256 hash screenshot]
    end
    
    subgraph EVIDENCE[FDA Part 11 Audit Trail — ALWAYS]
        JSON_OUT --> ENTRY[Create Evidence Entry]
        PZWB_OUT --> ENTRY
        SCREEN_HASH --> ENTRY
        SKIP_SCREEN --> ENTRY
        ENTRY --> CHAIN[Append to Hash Chain<br>prev_hash + entry_hash]
        CHAIN --> ALCOA[ALCOA Fields<br>Attributable: user_id<br>Legible: .json readable<br>Contemporaneous: timestamp<br>Original: .pzwb = exact<br>Accurate: SHA-256 verified]
        ALCOA --> SEAL[Seal Evidence<br>sha256(chain)]
    end
    
    subgraph SYNC[Auto-Sync — Paid Users Only]
        SEAL --> PAID{Paid user?<br>cloud_config.paid_user}
        PAID -->|yes| ENCRYPT[AES-256-GCM encrypt<br>evidence + snapshot]
        ENCRYPT --> PUSH[POST solaceagi.com<br>/api/v1/twin/sync]
        PUSH --> DASHBOARD[Visible on<br>solaceagi.com/dashboard/activity<br>+ /dashboard/evidence]
        PAID -->|no| LOCAL[Store locally only<br>~/.solace/wiki/ + ~/.solace/evidence/]
    end
    
    subgraph BUDGET_CHECK[Budget Gate — Before Navigate]
        NAV --> BUDGET{Budget exceeded?}
        BUDGET -->|blocked| REJECT[BLOCKED<br>daily/monthly limit hit]
        BUDGET -->|ok| FETCH
    end

    classDef always fill:#e8f5e9,stroke:#2e7d32
    classDef optional fill:#fff9c4,stroke:#f9a825
    classDef paid fill:#e3f2fd,stroke:#1565c0
    classDef gate fill:#ffefef,stroke:#cc0000

    class EXTRACT,JSON_OUT,PZWB_OUT,PZSW_OUT,ENTRY,CHAIN,ALCOA,SEAL always
    class CAPTURE,SCREEN optional
    class ENCRYPT,PUSH,DASHBOARD paid
    class BUDGET,REJECT gate
```

## What Gets Created Per Navigate
```
~/.solace/wiki/
├── domains/{domain}/
│   └── stillwater.json          ← shared structure for domain (created once)
├── ├── {sha256_hash}.pzwb           ← PZip compressed original HTML
└── 
~/.solace/evidence/
└── evidence.jsonl               ← append-only hash chain (every navigate = 1 entry)

~/.solace/screenshots/           ← optional
└── {timestamp}_{url_hash}.png   ← full page screenshot
```

## Why Webservice + MCP
Every step in this pipeline is an HTTP endpoint on :8888:
- POST /api/navigate → triggers the whole pipeline
- POST /api/v1/wiki/extract → creates decomposition
- POST /api/screenshot → captures screenshot
- POST /api/v1/evidence → creates audit entry
- POST /api/v1/cloud/sync/up → pushes to cloud

MCP tools wrap the same endpoints:
- tool: browser_navigate → same pipeline
- tool: browser_screenshot → same evidence
- tool: evidence_list → query the chain

An AI agent calling MCP tools gets the SAME evidence trail as a human browsing.
No difference. Every action is captured, hashed, and optionally synced.

## PM Status
<!-- Updated: 2026-03-15 | Session: P-68 | Self-QA verified P-68 -->
| Node | Status | Evidence |
|------|--------|----------|
| NAV | SEALED | POST /api/navigate exists in Rust runtime |
| FETCH | SEALED | runtime fetches pages |
| DOMAIN | SEALED | extract_page checks domains/{domain}/stillwater.prime-snapshot.md |
| CREATE_SW | SEALED | stillwater.prime-snapshot.md created on first visit (6 integration tests) |
| LOAD_SW | SEALED | subsequent visits skip creation (domain_stillwater_created=false) |
| SW_STORE | SEALED | ~/.solace/wiki/domains/{domain}/stillwater.prime-snapshot.md |
| EXTRACT | SEALED | POST /api/v1/wiki/extract works |
| JSON_OUT | SEALED | .json files created |
| PZWB_OUT | SEALED | .pzwb files created (RTC verified) |
| PZSW_OUT | SEALED | .pzsw files created |
| SCREEN | SEALED | Settings.auto_screenshot (default: false, serde default) |
| CAPTURE | SEALED | Self-QA P-68: POST /api/v1/wiki/extract creates .prime-snapshot.md + .pzwb (6 codecs, 145 snapshots) |
| SCREEN_HASH | SEALED | SHA-256 hash of screenshot in evidence record |
| ENTRY | SEALED | evidence entry creation works |
| CHAIN | SEALED | hash chain append works |
| ALCOA | SEALED | ALCOA fields in evidence.rs |
| SEAL | SEALED | seal_run works |
| PAID | SEALED | cloud_config.paid_user check |
| ENCRYPT | SEALED | AES-256-GCM encrypt |
| PUSH | SEALED | auto-sync trigger fires after extract for paid users |
| DASHBOARD | SEALED | Self-QA P-68: Hub pages /domains, /apps exist and render at localhost:8888 |
| LOCAL | SEALED | local storage works |
| BUDGET | SEALED | budget gate enforces limits |



## Related Papers
- [papers/hub-service-mesh-paper.md](../papers/hub-service-mesh-paper.md)
- [papers/hub-three-realms-paper.md](../papers/hub-three-realms-paper.md)

## Forbidden States
```
NAVIGATE_WITHOUT_EVIDENCE    → KILL (every navigate produces evidence)
SCREENSHOT_WITHOUT_HASH      → KILL (screenshots must be SHA-256 hashed)
SYNC_WITHOUT_ENCRYPT         → KILL (AES-256-GCM always)
EVIDENCE_AFTER_THE_FACT      → KILL (capture at time of navigate, not later)
MODIFY_EVIDENCE_CHAIN        → KILL (append-only, never mutate)
FREE_USER_CLOUD_SYNC         → BLOCKED (local only unless paid)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
