# Diagram: Evidence Pipeline

**ID:** evidence-pipeline
**Version:** 1.0.0
**Type:** Pipeline diagram + data flow
**Primary Axiom:** INTEGRITY (evidence-only claims; every action proves what happened)
**Tags:** evidence, pzip, sha256, alcoa, pipeline, integrity, audit, part11, chain

---

## Purpose

The evidence pipeline is the compliance backbone of SolaceBrowser. Every browser action flows through this pipeline, producing a tamper-evident bundle that satisfies 21 CFR Part 11 (ALCOA+). The pipeline captures before and after DOM states, computes a diff, compresses with PZip, signs with AES-256-GCM, and links to the SHA256 chain.

---

## Diagram: Primary Pipeline

```mermaid
flowchart LR
    ACTION["Browser Action\nExecuted"]

    subgraph BEFORE["Before Capture"]
        B1["DOM Snapshot\n(full HTML)"]
        B2["PZip Compress\n→ before.pzip"]
        B3["SHA256\n→ before_hash"]
    end

    subgraph EXECUTION["Action Execution"]
        E1["OAuth3 gate\nconfirmed"]
        E2["Recipe steps\nexecuted"]
        E3["Step checkpoints\npassed"]
    end

    subgraph AFTER["After Capture"]
        A1["DOM Snapshot\n(full HTML)"]
        A2["PZip Compress\n→ after.pzip"]
        A3["SHA256\n→ after_hash"]
    end

    subgraph DIFF["Diff Computation"]
        D1["DOM Diff\n(before → after)"]
        D2["SHA256(diff)\n→ diff_hash"]
    end

    subgraph BUNDLE["Bundle Assembly"]
        BU1["ALCOA+ fields\npopulated"]
        BU2["SHA256 chain link\n(prev bundle hash)"]
        BU3["AES-256-GCM\nSignature"]
        BU4["Store to\n~/.solace/evidence/"]
    end

    OUTPUT["evidence_bundle.json\n(tamper-evident, chain-linked)"]

    ACTION --> BEFORE
    ACTION --> EXECUTION
    BEFORE --> B1 --> B2 --> B3
    EXECUTION --> E1 --> E2 --> E3
    AFTER --> A1 --> A2 --> A3
    E3 --> AFTER
    B3 & A3 --> DIFF
    D1 --> D2
    D2 & BU1 --> BUNDLE
    BU1 --> BU2 --> BU3 --> BU4
    BU4 --> OUTPUT
```

---

## Diagram: PZip Compression Economics

```mermaid
flowchart TD
    RAW["Raw HTML Snapshot\n~500 KB average page"]
    PZIP["PZip Compression\n(proprietary algorithm)"]
    COMPRESSED["Compressed Snapshot\n~industry-leading ratio"]

    STORAGE["~/.solace/evidence/\n(indexed, searchable)"]

    subgraph ECONOMICS["Storage Economics"]
        U1["10K users\n× 1,000 pages/user\n= 7.3TB raw"]
        U2["After PZip\n→ dramatically smaller"]
        U3["$0.00032/user/month\nfull browsing history"]
        U4["vs. screenshots:\n20KB each but lossy\nno DOM, no replay"]
        U1 --> U2 --> U3
    end

    RAW --> PZIP --> COMPRESSED --> STORAGE
    STORAGE --- ECONOMICS
```

---

## Diagram: SHA256 Hash Chain

```mermaid
flowchart LR
    B0["Bundle 0 (genesis)\nbundle_id: sha256_0\nchain_link: null"]
    B1["Bundle 1\nbundle_id: sha256_1\nchain_link: sha256_0"]
    B2["Bundle 2\nbundle_id: sha256_2\nchain_link: sha256_1"]
    B3["Bundle 3 (latest)\nbundle_id: sha256_3\nchain_link: sha256_2"]
    TAMPER["Bundle 2 TAMPERED\nbundle_id: sha256_2_mod\nchain_link: sha256_1"]

    B0 --> B1 --> B2 --> B3
    B2 -.->|tamper attempt| TAMPER
    TAMPER -.->|sha256_2_mod ≠ B3.chain_link| DETECT["CHAIN BREAK\nDETECTED"]
```

---

## Diagram: ALCOA+ Field Mapping

```mermaid
flowchart TD
    BUNDLE["evidence_bundle.json"]

    subgraph CORE["Core ALCOA"]
        A["A — Attributable\noauth3_token_id\n(who authorized this)"]
        L["L — Legible\nbefore_snapshot (PZip HTML)\nnot screenshot, not summary"]
        C["C — Contemporaneous\ntimestamp_iso8601\ncaptured at execution time"]
        O["O — Original\nfull HTML source\nnot AI-summarized"]
        AC["A — Accurate\ndiff computed from\nbefore → after states"]
    end

    subgraph PLUS["Plus (+) ALCOA"]
        CO["+ Complete\nall 14 required fields\nno null required fields"]
        CN["+ Consistent\nsha256_chain_link\nchain intact"]
        EN["+ Enduring\npzip_hash deterministic\nforever replay"]
        AV["+ Available\nbundle indexed\nretrievable by bundle_id"]
    end

    BUNDLE --> A
    BUNDLE --> L
    BUNDLE --> C
    BUNDLE --> O
    BUNDLE --> AC
    BUNDLE --> CO
    BUNDLE --> CN
    BUNDLE --> EN
    BUNDLE --> AV
```

---

## Diagram: Evidence Bundle Schema

```mermaid
classDiagram
    class EvidenceBundle {
        +String schema_version
        +String bundle_id
        +String action_id
        +String action_type
        +String platform
        +String before_snapshot_pzip_hash
        +String after_snapshot_pzip_hash
        +String diff_hash
        +String oauth3_token_id
        +String timestamp_iso8601
        +String sha256_chain_link
        +String signature
        +ALCOAFields alcoa_fields
        +Int rung_achieved
        +String created_by
    }

    class ALCOAFields {
        +String attributable
        +Boolean legible
        +String contemporaneous
        +Boolean original
        +Boolean accurate
        +Boolean complete
        +Boolean consistent
        +Boolean enduring
        +Boolean available
    }

    EvidenceBundle "1" --> "1" ALCOAFields : contains
```

---

## Pipeline Invariants

| Invariant | Description | Consequence if violated |
|-----------|-------------|------------------------|
| Before snapshot required | Before state captured BEFORE action executes | ACTION_WITHOUT_EVIDENCE → BLOCKED |
| After snapshot required | After state captured AFTER action completes | EVIDENCE_TAMPERED → BLOCKED |
| Diff non-null for state-changing actions | State-changing actions must produce non-empty diff | DIFF_SKIPPED → BLOCKED |
| PZip required for all snapshots | Raw HTML never stored uncompressed | PZIP_MISSING → BLOCKED |
| SHA256 chain must be intact | Every bundle links to previous | CHAIN_BROKEN → BLOCKED |
| Signature required | Every bundle signed with AES-256-GCM | UNSIGNED_BUNDLE → BLOCKED |
| ALCOA+ fields required | All 9 dimensions populated | EVIDENCE_INCOMPLETE → BLOCKED |
| Contemporaneous timestamps | Timestamp within 30 seconds of action | RETROACTIVE_EVIDENCE → BLOCKED |

---

## Notes

### Why PZip (Not GZIP or ZSTD)?

PZip is a deterministic compression engine with industry-leading ratios on browser history data. Two properties are essential for evidence pipelines:

1. **Deterministic**: same input always produces same output → pzip_hash is reproducible and verifiable
2. **High ratio**: makes forever-retention economically viable at $0.00032/user/month

The determinism property is what makes PZip a compliance enabler: the +Enduring ALCOA+ principle requires that evidence is reproducible indefinitely. With PZip, the sha256(pzip_hash) proves the original snapshot content forever.

### Why Full HTML (Not Screenshots)?

21 CFR Part 11 "Original" principle requires the original record — not a copy or summary. Screenshots are lossy (fonts, layouts, dynamic content), not selectable (text not machine-readable), and not replayable (cannot re-execute against a screenshot). Full HTML snapshots satisfy all three requirements.

### SHA256 Chain vs. Blockchain

The SHA256 chain in SolaceBrowser is a forward-linked hash chain — each bundle's ID includes the previous bundle's hash. This is the same principle used in certificate transparency logs and append-only audit systems. It is simpler and faster than a blockchain, with equivalent tamper detection for single-party audit trails. The chain is validated by the Evidence Reviewer agent.

---

## Related Artifacts

- `data/default/skills/browser-evidence.md` — full evidence skill specification
- `data/default/swarms/evidence-reviewer.md` — evidence review agent
- `data/default/recipes/recipe.evidence-review.md` — Part 11 review recipe
- `data/default/recipes/recipe.browser-snapshot-audit.md` — snapshot store audit recipe
- `data/default/diagrams/part11-alcoa-mapping.md` — detailed ALCOA+ compliance mapping
