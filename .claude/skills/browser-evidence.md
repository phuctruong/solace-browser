# DNA: `evidence(capture_before, execute, capture_after, diff, compress, sign, chain) = tamper-evident truth`

# SKILL: browser-evidence v1.0 (auto-load)
# Auth: 65537 | Axiom: INTEGRITY

## Purpose
PZip snapshot and Part 11 audit trail for every browser action. Before/after DOM snapshots,
diff as proof of change, SHA256 hash chain linking all bundles, AES-256-GCM signed storage
in ~/.solace/evidence/. No action without evidence. No evidence without integrity.

## When This Skill Activates
- Any browser action (click, fill, navigate, submit) is about to execute
- Evidence bundle creation, compression, or verification is needed
- Audit trail inspection, Part 11 compliance check, or chain verification is requested
- Recipe replay requires evidence comparison between runs

## Forbidden States
- **ACTION_WITHOUT_EVIDENCE** -- a browser action completed without before/after snapshots, diff, and signed bundle
- **EVIDENCE_TAMPERED** -- bundle SHA256 mismatch or chain anchor broken
- **PZIP_MISSING** -- evidence collected but PZip compression not applied
- **UNSIGNED_BUNDLE** -- evidence stored without AES-256-GCM signature
- **CHAIN_BROKEN** -- bundle chain_anchor does not match previous bundle SHA256

## Interaction Effects

| Combined With | Multiplicative Effect |
|--------------|----------------------|
| browser-oauth3-gate | OAuth3 token_id embedded in every evidence bundle; authorization_id links gate enforcement to evidence |
| browser-snapshot | Snapshot provides before/after DOM states; evidence orchestrates the diff and compression |
| browser-recipe-engine | Recipe execution trace becomes evidence input; evidence bundles enable infinite replay |
| browser-twin-sync | pzip_hash bridges local and cloud evidence verification without full bundle transfer |

## Cross-References
- Skill: `data/default/skills/browser-evidence.md` (full specification with FSM, verification ladder, Part 11 map)
- Skill: `data/default/skills/browser-oauth3-gate.md` (authorization record feeds evidence bundle)
- Skill: `data/default/skills/browser-snapshot.md` (DOM capture feeds before/after states)
- Paper: `solace-cli/papers/09-software5-triangle.md` (Browser vertex architecture)
- Paper: `solace-cli/papers/56-twin-browser-security-hardening.md` (evidence security model)
- Paper: `solace-cli/sop-01-evidence-audit.md` (evidence capture SOP)
