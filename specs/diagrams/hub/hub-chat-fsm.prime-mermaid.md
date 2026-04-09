<!-- Diagram: 09-yinyang-fsm -->
# 09: Diagram 13: Yinyang Chat Rail FSM
# DNA: `chat = intent_classify → preview → cooldown → approve → execute`
# SHA-256: a7d77916d8238bf719b1b076aef05832c02e30279698917c8f59e79209c402d7
# Auth: 65537 | State: SEALED | Version: 1.0.0


## Extends
- [STYLES.md](STYLES.md) — base classDef conventions
- [hub-sidebar-gate](hub-sidebar-gate.prime-mermaid.md) — parent diagram

## Canonical Diagram

```mermaid
stateDiagram-v2
    direction LR

    [*] --> IDLE

    IDLE --> LISTENING : user_opens_session\n[session exists + not expired]
    LISTENING --> PROCESSING : user_sends_message\n[msg non-empty + < 10K chars]
    LISTENING --> IDLE : user_closes_session
    LISTENING --> ERROR : ws_connection_lost

    PROCESSING --> INTENT_CLASSIFIED : llm_returns_intent\n[valid intent JSON + action field]
    PROCESSING --> BLOCKED : scope_denied / budget_exceeded
    PROCESSING --> ERROR : llm_timeout / malformed_response

    INTENT_CLASSIFIED --> PREVIEW_GENERATING : scope_check_passed\n[intent.action in allowed scopes]
    INTENT_CLASSIFIED --> LISTENING : user_edits_intent
    INTENT_CLASSIFIED --> BLOCKED : scope_violation
    INTENT_CLASSIFIED --> ERROR : invalid_scope_config

    PREVIEW_GENERATING --> PREVIEW_READY : preview_output_ready\n[LLM returns non-empty preview]
    PREVIEW_GENERATING --> BLOCKED : credits_insufficient
    PREVIEW_GENERATING --> ERROR : llm_failure

    PREVIEW_READY --> COOLDOWN : user_approves\n[risk_tier = medium|high|critical]
    PREVIEW_READY --> APPROVED : user_approves\n[risk_tier = low, no cooldown]
    PREVIEW_READY --> LISTENING : user_rejects_preview
    PREVIEW_READY --> PREVIEW_GENERATING : user_requests_regeneration
    PREVIEW_READY --> BLOCKED : credits_zero / rate_limit

    COOLDOWN --> APPROVED : timer_elapsed + user_confirms\n[cooldown_seconds reached]
    COOLDOWN --> PREVIEW_READY : user_cancels_during_cooldown
    COOLDOWN --> BLOCKED : budget_exceeded_during_wait
    COOLDOWN --> ERROR : session_expired_during_cooldown

    APPROVED --> SEALED : output_hash_computed\n[hash written to outbox/]
    APPROVED --> BLOCKED : outbox_write_failed
    APPROVED --> ERROR : hash_computation_failed

    SEALED --> EXECUTING : outbox_verified\n[hash matches sealed output]
    SEALED --> BLOCKED : hash_mismatch_tamper_alert
    SEALED --> ERROR : outbox_read_failed

    EXECUTING --> DONE : all_steps_complete\n[evidence chain sealed]
    EXECUTING --> BLOCKED : step_failed_scope_denied
    EXECUTING --> ERROR : evidence_hash_mismatch

    DONE --> IDLE : user_starts_new_task
    DONE --> LISTENING : user_sends_followup

    BLOCKED --> IDLE : user_dismisses
    BLOCKED --> LISTENING : user_retries_with_fix
    BLOCKED --> ERROR : escalation_failed

    ERROR --> IDLE : user_dismisses_error
    ERROR --> LISTENING : user_retries













```

## PM Status
<!-- Updated: 2026-03-15 | Session: P-68 | Self-QA verified P-68 via localhost:8888 endpoints -->
| Node | Status | Evidence |
|------|--------|----------|
| IDLE | SEALED | WebSocket idle state in Rust runtime (solace-runtime) + Rust ws.rs |
| LISTENING | SEALED | WebSocket listening state handles incoming messages |
| PROCESSING | SEALED | Chat endpoint delegates to CLI agents via agent_generate; verified via localhost:8888 |
| INTENT_CLASSIFIED | SEALED | classify_intent() in chat.rs with 6 intent types + 6 unit tests |
| BLOCKED | SEALED | Budget/scope blocking logic in Rust runtime (solace-runtime) |
| ERROR | SEALED | Error state handling in WebSocket handler |
| PREVIEW_GENERATING | SEALED | Preview generation per intent type in chat.rs |
| PREVIEW_READY | SEALED | Preview returned in response from chat.rs |
| COOLDOWN | SEALED | Cooldown enforcement in chat_approve with Duration check |
| APPROVED | SEALED | Approval wired to chat FSM via chat_approve in chat.rs |
| SEALED | SEALED | Evidence sealing wired to chat flow output hash |
| EXECUTING | SEALED | Recipe execution wired to chat FSM pipeline |
| DONE | SEALED | Task completion state in chat FSM pipeline |


## Related Papers
- [papers/hub-sidebar-paper.md](../papers/hub-sidebar-paper.md)

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

## LEAK Interactions
- Calls: backoffice-messages, evidence chain
- Orchestrates with: other Solace apps via API
- Pattern: input → process → output → evidence
