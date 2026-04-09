<!-- Diagram: 16-evidence-chain -->
# 16: Evidence Chain — SHA-256 + PZip + ALCOA
# SHA-256: 380cad05728bad4f92f5865d443da706b29357d230aedda582c4963f2906adbd
# DNA: `evidence = capture(action) → hash(sha256) → link(prev_hash) → compress(pzip) → seal(alcoa)`
# Auth: 65537 | State: SEALED | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions

## Canonical Diagram

```mermaid
flowchart TB
    ACTION[APP_RUN<br>report.html produced] --> HASH[SHA256_HASH<br>sha256(report_bytes)]
    HASH --> LINK[CHAIN_LINK<br>prev_hash + entry_hash]
    LINK --> ALCOA[ALCOA_FIELDS<br>Attributable + Legible +<br>Contemporaneous + Original + Accurate]
    ALCOA --> COMPRESS[PZIP_COMPRESS<br>PZJS or PZWB codec]
    COMPRESS --> WRITE[WRITE_EVIDENCE<br>~/.solace/evidence.jsonl]
    WRITE --> SEAL{SEALED_GATE}

    SEAL -->|paid_user| SYNC[CLOUD_SYNC<br>POST solaceagi.com/api/v1/evidence/sync]
    SEAL -->|free_user| LOCAL[LOCAL_ONLY<br>Zero cloud calls]

    FORBIDDEN_UNSEAL[FORBIDDEN_UPLOAD_BEFORE_SEAL<br>Must seal before any upload]
    FORBIDDEN_TAMPER[FORBIDDEN_CHAIN_MODIFY<br>Append-only, never edit]
    FORBIDDEN_NO_HASH[FORBIDDEN_NO_HASH<br>Every entry must have sha256]

    classDef forbidden fill:#ffefef,stroke:#cc0000,stroke-width:2px
    classDef gate fill:#fff9c4,stroke:#f9a825,stroke-width:2px
    class FORBIDDEN_UNSEAL,FORBIDDEN_TAMPER,FORBIDDEN_NO_HASH forbidden
    class SEAL gate
```

## PM Status
<!-- Updated: 2026-03-14 | Session: P-67 -->
| Node | Status | Evidence |
|------|--------|----------|
| ACTION | SEALED | App runs produce report.html via app_engine/outbox.rs |
| HASH (SHA256_HASH) | SEALED | SHA-256 hashing in pzip/evidence.rs |
| LINK (CHAIN_LINK) | SEALED | Hash chain linking (prev_hash + entry_hash) in pzip/evidence.rs |
| ALCOA | SEALED | ALCOA fields in evidence entries (pzip/evidence.rs) |
| COMPRESS (PZIP_COMPRESS) | SEALED | PZJS/PZWB codecs in pzip/json.rs + pzip/web.rs |
| WRITE (WRITE_EVIDENCE) | SEALED | Evidence written to ~/.solace/evidence.jsonl |
| SEAL (SEALED_GATE) | SEALED | Seal gate in pzip/evidence.rs |
| SYNC (CLOUD_SYNC) | SEALED | POST evidence sync for paid users in cloud.rs |
| LOCAL (LOCAL_ONLY) | SEALED | Free users get zero cloud calls |
| FORBIDDEN_UNSEAL | SEALED | Upload blocked before seal |
| FORBIDDEN_TAMPER | SEALED | Append-only chain, no modification |
| FORBIDDEN_NO_HASH | SEALED | Every entry requires SHA-256 |

## Covered Files
```
code:
  - solace-browser/solace-runtime/src/pzip/evidence.rs
  - solace-browser/solace-runtime/src/pzip/json.rs
  - solace-browser/solace-runtime/src/pzip/web.rs
  - solace-browser/solace-runtime/src/pzip/mod.rs
specs:
  - specs/agi/05-evidence.md
  - specs/agi/e1-evidence-architecture.md
  - specs/agi/hub-compliance-paper.md
services:
  - localhost:8888/api/v1/evidence/*
```


## Related Papers
- [papers/hub-service-mesh-paper.md](../papers/hub-service-mesh-paper.md)

## Forbidden States
```
PORT_9222              → KILL
COMPANION_APP_NAMING   → KILL (use "Solace Hub")
SILENT_FALLBACK        → KILL
PYTHON_DEPENDENCY      → KILL (pure Rust)
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
