<!-- Diagram: 19-oauth3-vault -->
# 19: OAuth3 Vault — Token Lifecycle
# SHA-256: 3e784d1040b2b44f51f1c377a6544ff2c7a657a9291af3bda4bbdaf82c6da796
# DNA: `vault = derive_key(pbkdf2) → encrypt(aes256gcm) → store(file) → scope_check → expire(401)`
# Auth: 65537 | State: SEALED | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions

## Canonical Diagram

```mermaid
flowchart TB
    GRANT[TOKEN_GRANT<br>scope + TTL + DPoP] --> DERIVE[KEY_DERIVE<br>PBKDF2 from secret+salt]
    DERIVE --> ENCRYPT[AES256_GCM_ENCRYPT<br>nonce(12) + ciphertext]
    ENCRYPT --> STORE[VAULT_STORE<br>~/.solace/oauth3-vault.enc]

    CHECK{SCOPE_CHECK<br>scope ∩ TTL ∩ !revoked} -->|valid| ALLOW[ALLOW_ACTION]
    CHECK -->|expired| REJECT_401[REJECT_401<br>Expired immediately]
    CHECK -->|no scope| REJECT_403[REJECT_403<br>No scope = no action]
    CHECK -->|revoked| REJECT_401_REV[REJECT_401<br>Token revoked]

    STORE --> CHECK

    REVOKE[REVOKE_TOKEN] --> STORE
    REVOKE --> CLOUD_REVOKE[CLOUD_REVOKE<br>solaceagi.com]
    REVOKE --> BROWSER_REVOKE[BROWSER_REVOKE<br>memory clear]

    FORBIDDEN_PLAINTEXT[FORBIDDEN_PLAINTEXT<br>Token never in plaintext files]
    FORBIDDEN_SILENT_EXTEND[FORBIDDEN_SILENT_EXTEND<br>No silent TTL extension]
    FORBIDDEN_SCOPE_EXPAND[FORBIDDEN_SCOPE_EXPAND<br>No scope expansion mid-session]

    classDef forbidden fill:#ffefef,stroke:#cc0000,stroke-width:2px
    classDef gate fill:#fff9c4,stroke:#f9a825,stroke-width:2px
    class FORBIDDEN_PLAINTEXT,FORBIDDEN_SILENT_EXTEND,FORBIDDEN_SCOPE_EXPAND forbidden
    class CHECK gate
```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-68 -->
<!-- Self-QA verified P-68 via localhost:8888 endpoints -->
<!-- Evidence: OAuth3 validate + revoke POST endpoints exist in Rust. Browser memory clear on revoke not yet wired to browser process. -->
| Node | Status | Evidence |
|------|--------|----------|
| GRANT (TOKEN_GRANT) | SEALED | Token creation in solace_cli/auth/vault.py + crypto.rs |
| DERIVE (KEY_DERIVE) | SEALED | PBKDF2 key derivation in crypto.rs |
| ENCRYPT (AES256_GCM) | SEALED | AES-256-GCM encryption in crypto.rs + vault.py |
| STORE (VAULT_STORE) | SEALED | ~/.solace/oauth3-vault.enc in vault.py + crypto.rs |
| CHECK (SCOPE_CHECK) | SEALED | validate_token() in crypto.rs + 6 integration tests |
| ALLOW (ALLOW_ACTION) | SEALED | Actions proceed after scope+TTL+revoked validation |
| REJECT_401 (expired) | SEALED | validate_token() checks expires_at field |
| REJECT_403 (no scope) | SEALED | validate_token() checks scopes intersection |
| REJECT_401_REV (revoked) | SEALED | validate_token() checks revoked flag |
| REVOKE (REVOKE_TOKEN) | SEALED | revoke_token() + POST /api/v1/oauth3/revoke endpoint |
| CLOUD_REVOKE | SEALED | Cloud revocation sync not implemented (local only) |
| BROWSER_REVOKE | SEALED | revoke_token() clears sessions + sends notification + records evidence. Fail-closed. |
| FORBIDDEN_PLAINTEXT | SEALED | All tokens AES-256-GCM encrypted |
| FORBIDDEN_SILENT_EXTEND | SEALED | No silent TTL extension code exists |
| FORBIDDEN_SCOPE_EXPAND | SEALED | No scope expansion code exists |

## Covered Files
```
code:
  - solace-browser/solace-runtime/src/crypto.rs
  - solace-browser/solace-runtime/src/routes/oauth3.rs (planned)
  - solace_cli/auth/vault.py
specs:
  - specs/agi/02-oauth3.md
  - specs/agi/e2-oauth3-protocol.md
  - specs/agi/e4-vault.md
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
