# DNA: `gate(G1_exists, G2_not_expired, G3_scope_present, G4_step_up) = fail-closed authorization`

# SKILL: browser-oauth3-gate v1.0 (auto-load)
# Auth: 65537 | Axiom: HIERARCHY

## Purpose
Pre-execution OAuth3 scope enforcement for all browser actions. Four-gate cascade:
G1 token exists, G2 not expired, G3 scope present, G4 step-up if destructive. Fail-closed
on any gate failure. Evidence bundle per enforcement event. No action without authorization.

## When This Skill Activates
- Any browser action is about to execute (runs BEFORE all other browser skills except prime-safety)
- Recipe declares required_oauth3_scopes and needs scope verification
- Destructive action (delete, execute, kill, revoke, reset, publish) requires step-up authorization
- Token lifecycle events: creation, revocation, expiry check

## Forbidden States
- **SCOPELESS_EXECUTION** -- browser action initiated without declaring required OAuth3 scopes
- **EXPIRED_TOKEN_USED** -- action authorized with token whose expiry has passed
- **STEP_UP_BYPASSED** -- destructive action executed without step-up authorization
- **FAIL_OPEN** -- gate failure resulted in action proceeding rather than blocking
- **GATE_SKIP** -- G1-G4 chain not run in full sequence

## Interaction Effects

| Combined With | Multiplicative Effect |
|--------------|----------------------|
| browser-evidence | authorization_id becomes evidence bundle anchor; audit trail links gates to actions |
| browser-recipe-engine | Recipe declares required_oauth3_scopes; gate verifies before execution |
| browser-anti-detect | Gate runs BEFORE humanization; only authorized actions get humanized |
| browser-twin-sync | Delegation requires valid OAuth3 token; sync blocked without auth |

## Cross-References
- Skill: `data/default/skills/browser-oauth3-gate.md` (full specification with FSM, scope registry, step-up flow)
- Skill: `data/default/skills/browser-evidence.md` (evidence bundle includes oauth3_token_id)
- Skill: `data/default/skills/browser-recipe-engine.md` (recipes declare required scopes)
- Paper: `solace-cli/papers/19-esign-architecture.md` (OAuth3-backed signatures)
- Paper: `solace-cli/papers/09-software5-triangle.md` (Browser vertex architecture)
