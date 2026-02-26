# Diagram: OAuth3 Enforcement Flow

**ID:** oauth3-enforcement-flow
**Version:** 1.0.0
**Type:** Flow diagram + state machine
**Primary Axiom:** HIERARCHY (gates are a strict precedence chain)
**Tags:** oauth3, scope, consent, step-up, enforcement, hierarchy, audit

---

## Purpose

The OAuth3 enforcement flow defines the exact sequence of checks that every browser action must pass before execution. It is a 4-gate cascade with strict precedence: later gates are only reached if earlier gates pass. Any gate failure produces a BLOCKED state and an audit record. There is no fail-open path.

---

## Diagram: 4-Gate Cascade (Primary)

```mermaid
flowchart TD
    ACTION_REQUEST["Browser Action Request\nplatform + action_type + token_ref"]

    G1{"G1: Token exists?\ntoken_id in vault"}
    G2{"G2: Not expired?\nexpires_at > now()"}
    G3{"G3: Scope present?\nrequired_scope in token.scopes"}
    G4{"G4: Step-up needed?\ndestructive action?"}

    STEP_UP["Request Step-Up\nUser confirms destructive action"]
    EXECUTE["Execute Action\nWith OAuth3 authorization"]
    EVIDENCE["Bundle Evidence\nALCOA+ + gate_audit.json"]

    BLOCKED_1["BLOCKED\nNo token — re-consent required"]
    BLOCKED_2["BLOCKED\nExpired — refresh or re-consent"]
    BLOCKED_3["BLOCKED\nScope missing — add scope to token"]
    BLOCKED_4["BLOCKED\nStep-up denied by user"]

    ACTION_REQUEST --> G1
    G1 -->|PASS| G2
    G1 -->|FAIL| BLOCKED_1
    G2 -->|PASS| G3
    G2 -->|FAIL| BLOCKED_2
    G3 -->|PASS| G4
    G3 -->|FAIL| BLOCKED_3
    G4 -->|"not destructive\n(PASS / N/A)"| EXECUTE
    G4 -->|"destructive\n(step-up required)"| STEP_UP
    STEP_UP -->|confirmed| EXECUTE
    STEP_UP -->|denied| BLOCKED_4
    EXECUTE --> EVIDENCE
```

---

## Diagram: Gate State Machine

```mermaid
stateDiagram-v2
    direction TB
    [*] --> INTAKE : action_request received
    INTAKE --> G1_CHECK : token_ref extracted from request
    G1_CHECK --> G2_CHECK : G1 PASS (token found in vault)
    G1_CHECK --> BLOCKED : G1 FAIL → audit record → EXIT
    G2_CHECK --> G3_CHECK : G2 PASS (token not expired)
    G2_CHECK --> REFRESH_OR_RECONSENT : G2 FAIL (expired)
    REFRESH_OR_RECONSENT --> G1_CHECK : token refreshed → retry gates
    REFRESH_OR_RECONSENT --> BLOCKED : user declines refresh → EXIT
    G3_CHECK --> G4_CHECK : G3 PASS (required scope present)
    G3_CHECK --> SCOPE_REQUEST : G3 FAIL (scope missing)
    SCOPE_REQUEST --> BLOCKED : user declines additional scope → EXIT
    SCOPE_REQUEST --> G1_CHECK : scope added → retry gates
    G4_CHECK --> EXECUTE : G4 N/A (non-destructive action)
    G4_CHECK --> STEP_UP : G4 required (destructive action)
    STEP_UP --> EXECUTE : step-up confirmed
    STEP_UP --> BLOCKED : step-up denied → EXIT
    EXECUTE --> EVIDENCE : action executed
    EVIDENCE --> [*] : evidence_bundle.json stored, gate_audit.json stored

    note right of G1_CHECK
        Failure: no token for platform
        Recovery: trigger consent flow
        Audit: gate_fail_record.json
    end note

    note right of G3_CHECK
        Scope format: platform.action
        linkedin.create_post
        gmail.compose.send
        Wildcard linkedin.* → BLOCKED
    end note

    note right of STEP_UP
        Required for: delete, execute, kill,
        payment, file write outside allowed_roots
        NOT required for: read, navigate, search
    end note
```

---

## Diagram: Scope Hierarchy

```mermaid
flowchart TD
    DELEGATION["User Consent Grant\n'I allow SolaceAI to...'"]

    subgraph PLATFORM_SCOPE["Platform Scope (G3)"]
        PS1["linkedin.create_post"]
        PS2["linkedin.read_feed"]
        PS3["gmail.compose.send"]
        PS4["gmail.read_inbox"]
        PS5["twitter.create_tweet"]
    end

    subgraph STEP_UP_SCOPE["Step-Up Required (G4)"]
        SU1["linkedin.delete_post"]
        SU2["gmail.delete_message"]
        SU3["machine.write_file"]
        SU4["machine.execute_command"]
        SU5["twin.delegate"]
    end

    DELEGATION --> PLATFORM_SCOPE
    DELEGATION --> STEP_UP_SCOPE

    note1["No wildcards: linkedin.* → BLOCKED\nNo cross-platform: gmail.* in linkedin action → BLOCKED"]
    PLATFORM_SCOPE --- note1
```

---

## Diagram: Audit Record Schema

```mermaid
classDiagram
    class GateAuditRecord {
        +String audit_id
        +String action_id
        +String platform
        +String action_type
        +String token_id
        +Boolean g1_token_exists
        +Boolean g2_not_expired
        +Boolean g3_scope_present
        +Boolean g4_step_up_satisfied
        +String overall_result
        +String failure_gate
        +String failure_reason
        +String timestamp_iso8601
        +String sha256_chain_link
        +String signature
    }

    class ConsentRecord {
        +String consent_event_id
        +String token_id
        +Array scopes_granted
        +String granted_at
        +String expires_at
        +String revoked_at
        +Boolean revoked
        +String consent_ui_hash
    }

    GateAuditRecord --> ConsentRecord : references token_id
```

---

## Enforcement Rules Summary

| Rule | Description | Consequence |
|------|-------------|------------|
| Gate order | G1 → G2 → G3 → G4 strictly in order | Later gate cannot run before earlier gate |
| No gate skip | All 4 gates run every time | GATE_SKIP → BLOCKED |
| Fail closed | Any gate failure = BLOCKED | No fail-open path |
| Scope exact match | Scope must be exact: no wildcards, no pattern matching | Wildcard → G3 FAIL |
| Step-up for destructive | Delete, execute, payment, file write → G4 step-up | Step-up bypass → BLOCKED |
| Audit record | Every gate check (pass or fail) produces audit record | EVIDENCE_SKIP → BLOCKED |
| Revocation real-time | Token revocation propagates within 60 seconds | Revoked token → G1 FAIL |

---

## Notes

### Why 4 Gates (Not 1)?

A single "authorized?" check fails because authorization is multi-dimensional:
1. **Token existence** (G1) and **expiry** (G2) are temporal — they change independently of the action.
2. **Scope** (G3) is semantic — the same token may authorize some actions but not others.
3. **Step-up** (G4) is contextual — the same scope may require additional confirmation for destructive variants.

Combining them into one check would require a complex, fragile authorization function. The 4-gate cascade is simple, auditable, and each gate has a clear single responsibility.

### Why Fail Closed?

A fail-open gate means "when in doubt, allow." For AI browser delegation, fail-open is unacceptable: it means a user's accounts could be accessed, modified, or delegated without provable consent. The entire value proposition of SolaceBrowser is the consent guarantee. Fail-open destroys it.

### Scope Granularity

Scopes are formatted as `platform.action`:
- `linkedin.create_post` — NOT `linkedin.write`
- `gmail.compose.send` — NOT `gmail.*`

Granular scopes allow users to understand exactly what they are consenting to. "Allow SolaceAI to create posts on LinkedIn" is comprehensible. "Allow SolaceAI full LinkedIn access" is not.

---

## Related Artifacts

- `data/default/skills/browser-oauth3-gate.md` — full gate implementation spec
- `data/default/swarms/oauth3-auditor.md` — compliance auditor for gate results
- `data/default/recipes/recipe.oauth3-consent-flow.md` — full consent lifecycle
- `combos/oauth3-recipe-execute.md` — gate integrated into execution combo
