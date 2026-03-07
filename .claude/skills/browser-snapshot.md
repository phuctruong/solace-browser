# DNA: `snapshot(capture, parse, build_refs, validate, emit) = deterministic DOM truth`

# SKILL: browser-snapshot v1.0 (auto-load)
# Auth: 65537 | Axiom: DETERMINISM

## Purpose
AI-native DOM snapshot with numeric ref-based element targeting. Deterministic capture via
Playwright _snapshotForAI, bidirectional RoleRefMap, staleness detection on DOM mutation,
and four-strategy selector healing chain (CSS, ARIA, XPath, visual).

## When This Skill Activates
- Before any browser action: a fresh snapshot is required
- DOM mutation detected: refs must be invalidated and recaptured
- Recipe replay needs portal resolution against current DOM
- Selector healing triggered when primary selector fails to locate element

## Forbidden States
- **STALE_REF_USED** -- action attempted using ref whose snapshot_version is outdated
- **SCREENSHOT_ONLY** -- action planned using only screenshot without DOM snapshot
- **SELECTOR_DRIFT_UNDETECTED** -- selector matched wrong element due to DOM change without re-snapshot
- **REF_COLLISION** -- two DOM elements assigned the same ref_id within a snapshot
- **IMPLICIT_SELECTOR** -- selector used that was not derived from current RoleRefMap

## Interaction Effects

| Combined With | Multiplicative Effect |
|--------------|----------------------|
| browser-recipe-engine | RoleRefMap refs power recipe portal resolution; healing chain recovers from DOM drift |
| browser-evidence | Before/after snapshots feed evidence diff computation |
| browser-anti-detect | Snapshot refs inform humanized click targeting with jitter offsets |
| browser-oauth3-gate | Snapshot must be fresh before any authorized action executes |

## Cross-References
- Skill: `data/default/skills/browser-snapshot.md` (full specification with FSM, RoleRefMap schema, healing chain)
- Skill: `data/default/skills/browser-recipe-engine.md` (recipe portals consume snapshot refs)
- Skill: `data/default/skills/browser-evidence.md` (evidence uses before/after snapshots for diff)
- Paper: `solace-cli/papers/04-triple-twin-orchestration.md` (CPU+LLM snapshot decision)
- Paper: `solace-cli/papers/09-software5-triangle.md` (Browser vertex architecture)
