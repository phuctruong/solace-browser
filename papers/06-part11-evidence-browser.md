# Paper 06: Part 11 Evidence — Browser Implementation
# DNA: `evidence = snapshot + metadata + signature; hash_chain = tamper-evident ALCOA+`
**Date:** 2026-03-01 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser
**Cross-ref:** solaceagi/papers/07-part11-architected.md, 11-fda-part11-storage.md

---

## 1. What FDA Part 11 Requires (21 CFR Part 11)

Part 11 is about DATA integrity, not visual fidelity. ALCOA+ standard.

### What the FDA Wants
- **WHO** — unique verified identity (never shared accounts)
- **WHAT** — specific action on specific data
- **WHEN** — tamper-proof computer-generated timestamp
- **WHY** — reason for change
- **WHAT changed** — old value → new value
- **Tamper-evidence** — append-only, hash-chained

### What the FDA Does NOT Require
- Pixel-perfect screenshots
- Exact CSS reproduction
- Video recordings
- Full browser state

## 2. Prime Mermaid Snapshot IS the Evidence

A Prime Mermaid snapshot captures DATA (form fields, values, DOM structure). Combined with Stillwater for legible reconstruction. Slightly older Gmail CSS is fine — form data is what the FDA audits.

```
Part 11 record = Prime Mermaid snapshot + metadata + signature
  snapshot: DOM structure, form values, interactive elements
  metadata: who, when, what action, why, previous state
  signature: user_id + timestamp + meaning + SHA256 linkage
```

## 3. Evidence Chain

```
~/.solace/audit/
  audit_chain.jsonl          ← append-only hash chain
  evidence/
    {chain_hash}/
      snapshot.mermaid       ← Prime Mermaid page snapshot (THE record)
      metadata.json          ← who, what, when, why, action
      signature.json         ← user_id, timestamp, meaning, hash
      screenshot.png         ← optional visual aid (NOT the record)
```

### Chain Entry Format

```json
{
  "seq": 1042,
  "ts": "2026-03-01T14:30:22.000Z",
  "who": "user:phuc@solaceagi.com",
  "action": "form_submit",
  "url": "https://mail.google.com/mail/u/0/#inbox",
  "what": "Sent email to john@example.com",
  "why": "Recipe: gmail-inbox-triage step 3",
  "snapshot_hash": "sha256:abc...",
  "form_data": {"to": "john@example.com", "subject": "Re: Q1 Report"},
  "prev_hash": "sha256:xyz...",
  "chain_hash": "sha256:COMPUTED...",
  "signature": {"user_id": "usr_abc", "meaning": "approved_execution"}
}
```

## 4. Evidence Modes

| Mode | Captured | Size/Action | Use Case |
|------|----------|-------------|----------|
| `off` | Nothing | 0 | Privacy mode |
| `data` | Mermaid snapshot + metadata | ~2KB | FDA/GxP compliance |
| `visual` | Above + screenshot | ~500KB | Extra visual aid |

**`data` mode is sufficient for Part 11.** Screenshots are nice-to-have.

## 5. E-Signing (Logged-In Users)

```
E-SIGNATURE = user_id + timestamp + meaning + SHA256(record)

Meaning types:
  "reviewed"     — I saw this preview
  "approved"     — I approve this action
  "authored"     — I created this content
  "responsible"  — I take responsibility

Signature = SHA256(user_id + timestamp + meaning + record_hash)
Cannot be detached, copied, or transferred (Part 11 §11.70)
```

- Guest users: no e-signing, actions logged locally but unsigned
- Logged-in users: every approval is e-signed, Part 11 ready

## 6. Cloud Sync (Logged-In Only)

```
LOCAL → CLOUD (solaceagi.com)
  audit_chain.jsonl → Evidence Vault (encrypted at rest)
  Batch sync (periodic, setting-controlled)
  Cloud does ZERO processing — just stores
  Prime Mermaid snapshots sync (tiny ~2-5 KB each)
  NOT raw HTML/screenshots (too large)
```

## 7. ALCOA+ Mapping

| ALCOA+ | How We Comply |
|--------|--------------|
| Attributable | user_id + OAuth3 token on every entry |
| Legible | Prime Mermaid + Stillwater reconstruction |
| Contemporaneous | Computer-generated timestamp at event time |
| Original | First capture is the record (never replaced) |
| Accurate | SHA256 hash of captured data |
| Complete | Every action logged, no gaps in chain |
| Consistent | Hash chain links verify temporal order |
| Enduring | chmod 444 after seal, 90-day retention (Pro) |
| Available | Local always, cloud sync for backup |

## Forbidden Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Retroactively creating evidence after action execution | Violates ALCOA+ contemporaneous requirement and destroys audit integrity |
| Using screenshots as the primary Part 11 record | Screenshots are lossy visual aids; data-mode Mermaid snapshots are the legal record |
| Allowing writable sealed records (no chmod 444) | Permits tampering with evidence and fails immutability requirement |

## 8. Invariants

1. Evidence captured AT event time, never retroactively
2. Hash chain: entry_N.chain_hash = SHA256(prev_hash + action_hash)
3. Chain break = tamper alert (surfaced to user)
4. Sealed records are chmod 444 (immutable)
5. `data` mode sufficient for Part 11 (screenshots optional)
6. E-signing links signature to record (§11.70)
