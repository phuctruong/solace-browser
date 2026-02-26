# Diagram: Twin Sync Flow

**ID:** twin-sync-flow
**Version:** 1.0.0
**Type:** Flow diagram + sequence diagram
**Primary Axiom:** NORTHSTAR (twin sync is the bridge to the Universal Portal)
**Tags:** twin, sync, local, cloud, aes-256-gcm, zero-knowledge, local-wins, conflict, delegation

---

## Purpose

The twin sync flow shows how the user's local browser state is synchronized to the cloud twin in a zero-knowledge manner — the cloud never sees plaintext, the user's key never leaves their machine, and local state always wins conflicts.

This diagram covers both upward sync (local → cloud) and downward sync (cloud → local) to give a complete picture of the twin architecture.

---

## Diagram: Full Sync Sequence

```mermaid
sequenceDiagram
    participant User
    participant Local as Local Browser<br/>(localhost:9222)
    participant Vault as Local Key Vault<br/>(~/.solace/vault/)
    participant Tunnel as wss:// Tunnel<br/>(cert-pinned)
    participant Cloud as Cloud Twin<br/>(solaceagi.com)

    Note over User,Cloud: UPWARD SYNC (local → cloud)

    User->>Local: Request sync / delegate task
    Local->>Vault: Fetch sync OAuth3 token
    Vault-->>Local: token (sync.upload scope)
    Local->>Local: G1+G2+G3+G4 gate check
    Local->>Local: Capture state bundle<br/>(cookies hash, fingerprint hash,<br/>recipe manifest, evidence chain tip)
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

    Cloud->>Cloud: Decrypt with user key<br/>(key provided in encrypted sync payload)
    Cloud->>Cloud: Restore session (cookies, fingerprint)
    Cloud->>Cloud: Execute recipe task
    Cloud->>Cloud: Bundle evidence (ALCOA+)
    Cloud->>Cloud: Encrypt result for user

    Note over User,Cloud: DOWNWARD SYNC (cloud → local)

    User->>Local: Request result / check status
    Local->>Tunnel: Fetch encrypted result
    Tunnel-->>Local: Encrypted result payload
    Local->>Vault: Fetch user decryption key
    Local->>Local: Decrypt result
    Local->>Local: Check LOCAL_WINS version
    alt No conflict
        Local->>Local: Store result + evidence bundle
    else Conflict detected
        Local->>Local: LOCAL_WINS → apply local to cloud
        Local->>User: Notify: conflict resolved (local state kept)
    end
    Local-->>User: Task result + evidence
```

---

## Diagram: Zero-Knowledge Guarantee

```mermaid
flowchart LR
    subgraph LOCAL["LOCAL (user controls)"]
        KEY["User Master Key\n(never transmitted)"]
        PLAINTEXT["Plaintext State\n(cookies, sessions, tokens)"]
        ENCRYPT["AES-256-GCM\nEncrypt"]
    end

    subgraph WIRE["WIRE (wss://, cert-pinned)"]
        CIPHERTEXT["Ciphertext\n+ nonce\n+ auth_tag"]
    end

    subgraph CLOUD["CLOUD (solaceagi.com)"]
        CLOUD_RECEIVES["Cloud receives:\nciphertext only"]
        CLOUD_DECRYPTS["Cloud decrypts:\n(using key from\nencrypted sync payload)"]
        CLOUD_TASK["Execute task\nwith user's session"]
    end

    KEY --> ENCRYPT
    PLAINTEXT --> ENCRYPT
    ENCRYPT --> CIPHERTEXT
    CIPHERTEXT --> CLOUD_RECEIVES
    CLOUD_RECEIVES --> CLOUD_DECRYPTS
    CLOUD_DECRYPTS --> CLOUD_TASK

    ZK_NOTE["Zero-knowledge proof:\nCloud confirms sha256(ciphertext)\nCloud cannot reconstruct key\nfrom ciphertext alone"]
    CLOUD_RECEIVES --- ZK_NOTE
```

---

## Diagram: LOCAL_WINS Conflict Resolution

```mermaid
stateDiagram-v2
    direction LR
    [*] --> SYNC_CHECK : cloud reports state version
    SYNC_CHECK --> NO_CONFLICT : cloud_version == local_version
    SYNC_CHECK --> CONFLICT_DETECTED : cloud_version != local_version
    NO_CONFLICT --> MERGE_CLOUD : accept cloud results (task output)
    CONFLICT_DETECTED --> COMPARE_VERSIONS : compare local_wins_version (monotonic counter)
    COMPARE_VERSIONS --> LOCAL_WINS_APPLY : local_wins_version >= cloud_wins_version
    COMPARE_VERSIONS --> MANUAL_MERGE_REQUIRED : cloud_wins_version > local_wins_version
    LOCAL_WINS_APPLY --> APPLY_LOCAL_TO_CLOUD : push local state to cloud
    APPLY_LOCAL_TO_CLOUD --> MERGE_CLOUD : cloud updated, no data lost
    MANUAL_MERGE_REQUIRED --> USER_PROMPT : prompt user to review and confirm merge
    USER_PROMPT --> MERGE_CLOUD : user confirms merge
    USER_PROMPT --> KEEP_LOCAL : user rejects cloud state
    MERGE_CLOUD --> [*] : sync complete
    KEEP_LOCAL --> [*] : local preserved, cloud rolled back

    note right of LOCAL_WINS_APPLY
        LOCAL_WINS is absolute for automatic resolution.
        Cloud never overwrites local silently.
    end note
```

---

## Diagram: Sync State Bundle Contents

```mermaid
classDiagram
    class StateBundleLocal {
        +String state_id
        +String capture_timestamp
        +Int local_wins_version
        +Array platforms
        +String fingerprint_hash
        +String recipes_version
        +String evidence_chain_tip
    }

    class PlatformSession {
        +String platform
        +Boolean session_active
        +String storage_state_hash
        +Int cookies_count
        +Int session_age_days
    }

    class EncryptedPayload {
        +Bytes ciphertext
        +Bytes nonce_96bit
        +Bytes auth_tag
        +String sha256_of_ciphertext
    }

    class SyncReceipt {
        +String sync_id
        +String sync_timestamp
        +String state_id
        +String cloud_payload_hash_confirmed
        +Boolean conflict_detected
        +Boolean local_wins_applied
        +Boolean tunnel_cert_pinned
        +Int rung_achieved
    }

    StateBundleLocal "1" --> "*" PlatformSession : contains
    StateBundleLocal --> EncryptedPayload : encrypted to
    EncryptedPayload --> SyncReceipt : produces
```

---

## Notes

### Why Zero-Knowledge?

The twin architecture requires the cloud to execute tasks using the user's authenticated sessions. This means the user's cookies and session tokens must be available on the cloud. The challenge: the cloud is a third-party service — the user cannot fully trust it.

Zero-knowledge sync solves this: the user's key is used to encrypt the state before transmission. The cloud decrypts using a session key that was transmitted in the encrypted payload (envelope encryption). If the cloud is compromised, the attacker gets ciphertext but not the user's master key.

This is the architecture of zero-knowledge services like 1Password and Bitwarden. SolaceBrowser applies the same model to browser session delegation.

### Why LOCAL_WINS?

The user's local machine is the source of truth for their digital identity. The cloud twin is a delegate — it executes on the user's behalf, but it does not own the user's identity. If there is ever a conflict between what the user's local machine has and what the cloud has, the local machine wins.

This prevents a class of attacks where a compromised cloud could plant modified state onto the user's local machine.

### Certificate Pinning

The wss:// tunnel uses certificate pinning to the solaceagi.com leaf certificate. This prevents MITM attacks on the sync channel. If the certificate does not match the pinned value, the tunnel is rejected and BLOCKED. This is TUNNEL_DOWNGRADE → BLOCKED in the forbidden states.

---

## Related Artifacts

- `data/default/skills/browser-twin-sync.md` — full twin sync skill
- `data/default/recipes/recipe.twin-sync.md` — full sync lifecycle recipe
- `combos/twin-delegation.md` — delegation combo using twin sync
- `data/default/diagrams/browser-multi-layer-architecture.md` — sync lives between Layer 4 (cloud execution) and Layer 5 (evidence)
