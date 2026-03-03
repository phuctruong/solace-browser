# Diagram 40 — FDA 21 CFR Part 11: Evidence Chain

**ID:** 40-part11-evidence-chain
**Version:** 1.0.0
**Type:** State diagram + compliance reference
**Primary Axiom:** INTEGRITY (evidence is immutable, chained, and sealed before the user has finished clicking)
**Tags:** part11, evidence, hash-chain, compliance, fda, seal, approval, audit, alcoa

---

## Purpose

Show the complete lifecycle of a Solace Browser agent action from user
intent to sealed, hash-chained, Part 11 compliant evidence. This diagram
is the canonical reference for auditors, enterprise buyers, and the
evidence-reviewer agent. It makes the compliance claim concrete: you can
trace every state transition to a specific file written to disk.

---

## Diagram 1: Evidence Chain State Machine (Primary)

```mermaid
stateDiagram-v2
    direction TB

    [*] --> TaskQueued : User selects recipe

    TaskQueued --> PreviewGenerated : LLM called once\n(read-only planning pass)

    PreviewGenerated --> AwaitingApproval : Preview rendered\nto user interface

    state AwaitingApproval {
        [*] --> WaitingForUser
        WaitingForUser --> UserApproves : Click APPROVE
        WaitingForUser --> UserRejects : Click REJECT
    }

    AwaitingApproval --> ApprovalRecorded : approval.json written\n(signer + timestamp + meaning)
    AwaitingApproval --> Discarded : run_id discarded\nno evidence created

    ApprovalRecorded --> Sealed : chmod 444 applied\nto approval.json\nBEFORE first action

    Sealed --> Executing : Recipe engine starts\nEvidence capture begins

    state Executing {
        [*] --> CaptureAction
        CaptureAction --> WriteActionEntry : seq + ts + who + what + why\n+ snapshot_hash + prev_hash
        WriteActionEntry --> CaptureAction : More actions
        WriteActionEntry --> [*] : All steps complete
    }

    Executing --> BundleComplete : actions.json finalized\nafter_snapshot written

    BundleComplete --> HashComputed : bundle.sha256 computed\nover all bundle files

    HashComputed --> BundleSealed : chmod 444 applied\nto all bundle files

    BundleSealed --> ChainAppended : chain entry written\nto audit_chain.jsonl\n(prev_hash linked)

    ChainAppended --> ChainVerified : Automatic chain walk\nverifies integrity

    ChainVerified --> Archived : PZip compression\n(66:1 average ratio)

    Archived --> Available : Indexed in evidence store\nSearchable + exportable

    Available --> [*]
    Discarded --> [*]

    note right of ApprovalRecorded
        §11.50 Electronic Signature
        §11.70 Signature Linking
        approval.json is immutable
        before execution starts
    end note

    note right of ChainAppended
        §11.10(e) Audit Trail
        §11.10(f) Sequence
        append-only jsonl
        tamper-evident
    end note

    note right of BundleSealed
        §11.10(c) Record Protection
        chmod 444 = no write
        for any process
    end note
```

---

## Diagram 2: Evidence Files Produced Per Run

```mermaid
flowchart TD
    subgraph RUN["run_id/ (e.g., gmail-inbox-triage-20260303-143019)"]
        direction TB

        M["manifest.json
        ──────────────────
        run_id, app_id, recipe_id
        recipe_hash, user_id, device_id
        oauth3_token_id
        started_at, completed_at
        action_count, budget_spent
        evidence_mode, status"]

        AP["approval.json
        ──────────────────
        signer.user_id
        signer.full_name
        signer.email
        approved_at (UTC)
        meaning
        method
        preview_hash
        steps_reviewed[]
        scopes_granted[]
        signature_hash
        ── sealed chmod 444 ──
        ── BEFORE execution ──"]

        AX["actions.json
        ──────────────────
        [{
          seq: 1,
          ts: ISO8601,
          who: user_id,
          action_type: navigate,
          url: ...,
          what: human description,
          why: recipe step ref,
          snapshot_hash: sha256,
          prev_hash: sha256
        }, ...]"]

        BS["before_snapshot.html
        ──────────────────
        Full page state
        before first action
        PZip compressed
        sha256 verified
        (the original record
         per §11.10(b))"]

        AS["after_snapshot.html
        ──────────────────
        Full page state
        after last action
        PZip compressed
        sha256 verified"]

        SS["screenshots/
        ──────────────────
        step-01.png
        step-02.png
        ...
        (visual aid only —
         NOT the primary record
         per ALCOA+ O principle)"]

        BH["bundle.sha256
        ──────────────────
        sha256  manifest.json
        sha256  actions.json
        sha256  approval.json
        sha256  before_snapshot.html
        sha256  after_snapshot.html
        sha256  screenshots/*.png
        ──────────────────
        BUNDLE: sha256 of all
        ── sealed chmod 444 ──"]
    end

    subgraph CHAIN["~/.solace/audit_chain.jsonl (append-only)"]
        CE["Chain Entry #{N}
        ──────────────────
        seq: N
        ts: ISO8601
        run_id: ...
        bundle_hash: sha256
        prev_hash: sha256 of entry N-1
        chain_hash: sha256(bundle+prev)"]
    end

    RUN --> CHAIN
    BH -->|"included in"| CE

    style AP fill:#1a3a2a,stroke:#00b4d8,color:#e0f7ff
    style BH fill:#1a1a3a,stroke:#00b4d8,color:#e0f7ff
    style CE fill:#2a1a1a,stroke:#ff6b6b,color:#fff0f0
```

---

## Diagram 3: 21 CFR Part 11 Section → Implementation

```mermaid
flowchart LR
    subgraph CFR["21 CFR Part 11 Requirements"]
        direction TB
        R_A["§11.10(a)\nSystem validation\naccuracy + reliability"]
        R_B["§11.10(b)\nAccurate copies\nof records"]
        R_C["§11.10(c)\nRecord protection\nthroughout retention"]
        R_D["§11.10(d)\nLimited access\nauthorized individuals"]
        R_E["§11.10(e)\nAudit trails\ndate/time + operator ID"]
        R_F["§11.10(f)\nSequence of events\nenforcement"]
        R_G["§11.10(g)\nAuthority checks\nright person, right action"]
        R_H["§11.10(h)\nDevice checks"]
        R_50["§11.50\nSignature manifestations\nname + date + meaning"]
        R_70["§11.70\nSignature linking\ncannot detach"]
    end

    subgraph IMPL["Solace Browser Implementation"]
        direction TB
        I_A["Recipe determinism\nCPU-replay identical output\nRung 641 test suite"]
        I_B["PZip lossless compression\nsha256(decompress) == original\nbefore_snapshot.html"]
        I_C["chmod 444 at seal\nAES-256-GCM vault\nSHA-256 chain tamper-detect"]
        I_D["OAuth3 sw_sk_ bearer\nper-app scope\nrevocable at any time"]
        I_E["audit_chain.jsonl\nappend-only\nwho + when + what + why + hash"]
        I_F["actions.json[].seq\nmonotonic integer\ngap detection on chain walk"]
        I_G["Approval gate (hard block)\nbudget gate (hard block)\nno execution without both"]
        I_H["device_id in OAuth3 token\nengine verifies device match\nrejects cross-device execution"]
        I_50["approval.json\nfull_name + timestamp + meaning\nmethod = explicit_button_click"]
        I_70["approval.json hash\ninside bundle.sha256\ninside chain entry\ncannot be detached"]
    end

    R_A --> I_A
    R_B --> I_B
    R_C --> I_C
    R_D --> I_D
    R_E --> I_E
    R_F --> I_F
    R_G --> I_G
    R_H --> I_H
    R_50 --> I_50
    R_70 --> I_70
```

---

## Diagram 4: Hash Chain Structure (Tamper Evidence)

```mermaid
flowchart LR
    subgraph RUN1["Run #1041\ngmail-triage-20260303-143019"]
        B1["bundle.sha256\nf2ca1bb6c7..."]
    end

    subgraph ENTRY1["Chain Entry #1041"]
        E1["seq: 1041
        bundle_hash: f2ca1bb6...
        prev_hash: 9d8f3a21...
        chain_hash: SHA256(bundle+prev)
        = 7e4b9c2d..."]
    end

    subgraph RUN2["Run #1042\ngmail-triage-20260303-150511"]
        B2["bundle.sha256\na3d7f9c1..."]
    end

    subgraph ENTRY2["Chain Entry #1042"]
        E2["seq: 1042
        bundle_hash: a3d7f9c1...
        prev_hash: 7e4b9c2d... ← points to #1041
        chain_hash: SHA256(bundle+prev)
        = b8e1f4a9..."]
    end

    subgraph RUN3["Run #1043\ngmail-triage-20260303-153022"]
        B3["bundle.sha256\nc5a2e8d4..."]
    end

    subgraph ENTRY3["Chain Entry #1043"]
        E3["seq: 1043
        bundle_hash: c5a2e8d4...
        prev_hash: b8e1f4a9... ← points to #1042
        chain_hash: SHA256(bundle+prev)
        = d9f3b7c2..."]
    end

    RUN1 --> ENTRY1
    ENTRY1 -->|"chain_hash\nbecomes\nprev_hash"| ENTRY2
    RUN2 --> ENTRY2
    ENTRY2 -->|"chain_hash\nbecomes\nprev_hash"| ENTRY3
    RUN3 --> ENTRY3

    TAMPER["If any past entry is modified:\nchain_hash changes\nnext entry's prev_hash\ndoes not match\nTAMPER ALERT"]
    ENTRY2 -. "tamper here" .-> TAMPER
```

---

## Compliance Summary Table

| Requirement | File | Verification Command |
|-------------|------|---------------------|
| §11.10(a) validation | `test_suite/rung_641.py` | `pytest test_suite/ -k part11` |
| §11.10(b) accurate copies | `before_snapshot.html` (PZip) | `python3 -m solace_browser.audit --verify-pzip {run_id}` |
| §11.10(c) record protection | `chmod 444` on all files | `ls -la ~/.solace/evidence/{run_id}/` |
| §11.10(d) limited access | `approval.json.oauth3_token_id` | `python3 -m solace_browser.auth --check-token` |
| §11.10(e) audit trail | `audit_chain.jsonl` | `python3 -m solace_browser.audit --verify-chain` |
| §11.10(f) sequence | `actions.json[].seq` | `python3 -m solace_browser.audit --verify-sequence {run_id}` |
| §11.10(g) authority checks | `approval.json` + gate code | `python3 -m solace_browser.audit --verify-approval {run_id}` |
| §11.10(h) device checks | `approval.json.device_id` | `python3 -m solace_browser.audit --verify-device {run_id}` |
| §11.50 signature | `approval.json` | `python3 -m solace_browser.audit --show-signature {run_id}` |
| §11.70 signature linking | `bundle.sha256` | `python3 -m solace_browser.audit --verify-bundle {run_id}` |

---

## ALCOA+ Quick Reference

| ALCOA+ | Evidence File | Field |
|--------|--------------|-------|
| Attributable | `actions.json` | `.who` (user_id + device_id) |
| Legible | `before_snapshot.html` | Full HTML, machine-readable forever |
| Contemporaneous | `actions.json` | `.ts` (captured at execution) |
| Original | `before_snapshot.html` | Full HTML, not screenshot |
| Accurate | `actions.json` | `.snapshot_hash` (state at each step) |
| Complete | `manifest.json` | All 14 required fields present |
| Consistent | `audit_chain.jsonl` | `.chain_hash` chain walk |
| Enduring | `bundle.pzip` | Deterministic; `chmod 444` |
| Available | `~/.solace/evidence/` | Indexed; lookup < 5 seconds |

---

## Related Artifacts

- `papers/40-part11-compliance-selfcert.md` — Full compliance paper + self-cert template
- `papers/sop-01-evidence-audit.md` — Evidence capture and audit trail SOP
- `papers/06-part11-evidence-browser.md` — ALCOA+ detail (canonical)
- `data/default/diagrams/part11-alcoa-mapping.md` — ALCOA+ to component mapping
- `data/default/diagrams/evidence-pipeline.md` — Evidence pipeline components
- `data/default/skills/browser-evidence.md` — Evidence skill implementation
