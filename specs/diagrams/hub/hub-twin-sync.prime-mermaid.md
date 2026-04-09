<!-- Diagram: 21-twin-sync-flow -->
# 21: Diagram: Twin Sync Flow
# DNA: `sync = connect → encrypt(AES-256-GCM) → push/pull → merge(local_wins)`
# SHA-256: de2b0b716ce6a6429cc90bc228392cf5b1df2b823247e92aa073a2c8bbd30448
# Auth: 65537 | State: SEALED | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-runtime](hub-runtime.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
sequenceDiagram
    participant User
    participant Local as Local Browser<br>(localhost:8888)
    participant Vault as Local Key Vault<br>(~/.solace/vault/)
    participant Tunnel as wss:// Tunnel<br>(cert-pinned)
    participant Cloud as Cloud Twin<br>(solaceagi.com)

    Note over User,Cloud: UPWARD SYNC (local  to  cloud)

    User->>Local: Request sync / delegate task
    Local->>Vault: Fetch sync OAuth3 token
    Vault-->>Local: token (sync.upload scope)
    Local->>Local: G1+G2+G3+G4 gate check
    Local->>Local: Capture state bundle<br>(cookies hash, fingerprint hash,<br>recipe manifest, evidence chain tip)
    Local->>Vault: Fetch user encryption key
    Vault-->>Local: key (never leaves local)
    Local->>Local: AES-256-GCM encrypt(state, key, nonce)
    Local->>Tunnel: Open wss:// with cert pinning
    Tunnel-->>Local: Certificate verified ✓
    Local->>Cloud: POST ciphertext + nonce + auth_tag
    Cloud-->>Local: sha256(ciphertext) receipt
    Local->>Local: Verify sha256 matches sent payload
    Local->>Local: Store sync_receipt.json

    Note over User,Cloud: CLOUD EXECUTION (while user sleeps)

    Cloud->>Cloud: Decrypt with user key<br>(key provided in encrypted sync payload)
    Cloud->>Cloud: Restore session (cookies, fingerprint)
    Cloud->>Cloud: Execute recipe task
    Cloud->>Cloud: Bundle evidence (ALCOA+)
    Cloud->>Cloud: Encrypt result for user

    Note over User,Cloud: DOWNWARD SYNC (cloud  to  local)

    User->>Local: Request result / check status
    Local->>Tunnel: Fetch encrypted result
    Tunnel-->>Local: Encrypted result payload
    Local->>Vault: Fetch user decryption key
    Local->>Local: Decrypt result
    Local->>Local: Check LOCAL_WINS version
    alt No conflict
        Local->>Local: Store result + evidence bundle
    else Conflict detected
        Local->>Local: LOCAL_WINS  to  apply local to cloud
        Local->>User: Notify: conflict resolved (local state kept)
    end
    Local-->>User: Task result + evidence
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-68 final sweep -->
No flowchart nodes — sequence diagram covers twin sync flow.
| Node | Status | Evidence |
|------|--------|----------|
| Local (localhost:8888) | SEALED | Solace Runtime running on :8888 |
| Vault (local key vault) | SEALED | AES-256-GCM vault in vault.py + crypto.rs |
| Tunnel | SEALED | Custom reverse tunnel architecture defined (NO Cloudflare). 878-line Python impl. Rust port = Phase 2. |
| Cloud | SEALED | solaceagi.com has twin/sync, twin/pull, heartbeat, devices endpoints (Firebase auth). Phase 2: cloud-side recipe execution. |
| Upward sync | SEALED | P-68 final sweep: sync_up (POST /api/v1/cloud/sync/up) fully implemented with AES-256-GCM encryption + SyncReceipt verification. |
| Cloud_execution | SEALED | Architecture defined: decrypt → restore session → execute recipe → bundle evidence → encrypt result. Phase 2 deployment. |
| Downward sync | SEALED | sync_down in cloud.rs fully implemented with AES-256-GCM decryption + merge_cloud_state() |
| LOCAL_WINS conflict | SEALED | merge_cloud_state() implements local-wins conflict resolution policy |



## Related Papers
- [papers/hub-three-realms-paper.md](../papers/hub-three-realms-paper.md)

## Forbidden States
```
PORT_9222 -> KILL
EXTENSION_API -> KILL
EVIDENCE_BEFORE_SEAL -> BLOCKED
```

## Verification
```
ASSERT: Diagram matches implementation
ASSERT: All nodes have defined status
ASSERT: Evidence hash recorded for changes
```
