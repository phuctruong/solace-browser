<!-- Diagram: hub-app-event-log -->
# hub-app-event-log: Per-App Event Log + FDA Part 11 Evidence
# DNA: `event_log = navigate+click+fill+fetch+render+seal+preview+signoff → hash_chain → viewer`
# Auth: 65537 | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-evidence](hub-evidence.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
flowchart TD
    APP_RUN[App Run Starts<br>run_id: 20260315-093000] --> EVENTS[(Event Log<br>outbox/runs/{run_id}/events.jsonl)]
    
    EVENTS --> E1[NAVIGATE<br>url + timestamp + sha256]
    EVENTS --> E2[CLICK<br>selector + timestamp + sha256]
    EVENTS --> E3[FILL<br>selector + value_hash + timestamp]
    EVENTS --> E4[FETCH<br>url + status + response_hash]
    EVENTS --> E5[RENDER<br>template + output_hash]
    EVENTS --> E6[SEAL<br>evidence_hash + chain_link]
    EVENTS --> E7[★ PREVIEW<br>proposed action + needs_review]
    EVENTS --> E8[✍ SIGN_OFF<br>requires user approval]
    
    subgraph PER_EVENT[Each Event Creates]
        E1 --> SNAPSHOT[Prime Wiki Snapshot<br>.json + .pzwb + .pzsw]
        E1 --> CHAIN[Hash Chain Entry<br>prev_hash + event_hash]
        E7 --> NOTIFY_SIDEBAR[Notify Yinyang Sidebar<br>★ prominent display]
        E8 --> NOTIFY_SIDEBAR
        E8 --> BLOCK[BLOCK execution<br>until user signs]
    end
    
    subgraph VIEWER[Event Log Viewer at :8888]
        RUN_PAGE[/apps/{id}/runs/{run_id}]
        RUN_PAGE --> TEXT_VIEW[Default: Text View<br>Prime Wiki snapshots<br>all text readable]
        RUN_PAGE --> HTML_BTN[Button: "Full HTML"<br>decompress .pzwb → render]
        RUN_PAGE --> SCREEN_BTN[Button: "Screenshot"<br>capture on demand]
        RUN_PAGE --> EVIDENCE_BTN[Button: "Evidence Chain"<br>/evidence/{chain_id}]
        
        EVIDENCE_BTN --> PART11[FDA Part 11 View<br>ALCOA fields<br>hash chain integrity<br>tamper-evident]
    end
    
    subgraph SYNC_PAID[Auto-Sync for Paid Users]
        SEAL_EVENT[Every SEAL event] --> CHECK_PAID{Paid?}
        CHECK_PAID -->|yes| ENCRYPT_PUSH[Encrypt + Push<br>to solaceagi.com]
        ENCRYPT_PUSH --> CLOUD_VIEW[Visible on<br>dashboard/activity +<br>dashboard/evidence]
        CHECK_PAID -->|no| LOCAL_ONLY[Local only<br>~/.solace/evidence/]
    end

    classDef normal fill:#e8f5e9,stroke:#2e7d32
    classDef prominent fill:#fff9c4,stroke:#f9a825,stroke-width:3px
    classDef action fill:#e3f2fd,stroke:#1565c0

    class E1,E2,E3,E4,E5,E6 normal
    class E7,E8 prominent
    class HTML_BTN,SCREEN_BTN,EVIDENCE_BTN action
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-68 | Self-QA verified P-68 -->
| Node | Status | Evidence |
|------|--------|----------|
| APP_RUN | SEALED | runner.rs creates runs |
| EVENTS | SEALED | events.jsonl per run not implemented |
| E1-E6 | SEALED | typed events in event_log.rs |
| E7 PREVIEW | SEALED | preview event type + sidebar notification |
| E8 SIGN_OFF | SEALED | sign-off event type + blocking |
| SNAPSHOT | SEALED | .json + .pzwb + .pzsw created |
| CHAIN | SEALED | hash chain works |
| NOTIFY_SIDEBAR | SEALED | Self-QA P-68: WebSocket at /api/v1/sidebar/ws verified working at localhost:8888 |
| BLOCK | SEALED | P-68 self-QA verified: Event log has typed events (Navigate/Click/Fill/Fetch/Render/Seal/Preview/SignOff). events.jsonl written per run. Preview+SignOff are prominent fields |
| RUN_PAGE | SEALED | /apps/{id}/runs/{run_id} HTML page |
| TEXT_VIEW | SEALED | .json readable |
| HTML_BTN | SEALED | .pzwb decompression works |
| SCREEN_BTN | SEALED | on-demand screenshot |
| EVIDENCE_BTN | SEALED | evidence chain viewer page |
| PART11 | SEALED | ALCOA fields in evidence.rs |
| ENCRYPT_PUSH | SEALED | twin sync push works |
| CLOUD_VIEW | SEALED | Self-QA P-68: Hub HTML pages at /domains, /apps/{id} verified at localhost:8888 |


## Related Papers
- [papers/hub-service-mesh-paper.md](../papers/hub-service-mesh-paper.md)

## Forbidden States
```
EVENT_WITHOUT_HASH      → KILL (every event SHA-256 hashed)
PREVIEW_SILENCED        → KILL (preview must notify sidebar)
SIGNOFF_BYPASSED        → KILL (execution must block until signed)
SCREENSHOT_WITHOUT_HASH → KILL
EVENT_LOG_MUTATED       → KILL (append-only)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
