# DNA: `recipe(intent_classify, cache_lookup, verify_or_generate, execute, evidence, store) = bounded replay`

# SKILL: browser-recipe-engine v1.0 (auto-load)
# Auth: 65537 | Axiom: CLOSURE

## Purpose
Recipe matching, caching, and replay engine. SHA256-keyed cache (intent + platform + action_type),
versioned recipes with never-worse guarantee, step-by-step replay with checkpoint/rollback,
LLM cold-miss generation. 70% cache hit rate target for economic viability.

## When This Skill Activates
- User issues a task intent that needs browser automation (compose email, create post, etc.)
- Cache lookup needed for existing recipe match
- New recipe generation via LLM on cache miss
- Recipe version upgrade requires never-worse gate validation
- Checkpoint/rollback during recipe execution

## Forbidden States
- **UNVERIFIED_RECIPE_CACHED** -- recipe written to cache without passing validation (schema + test cases)
- **RECIPE_REGRESSION** -- new version produces worse results than the version it replaces
- **UNBOUNDED_EXECUTION** -- recipe execution without declared max_steps and timeout_seconds
- **SCOPELESS_RECIPE** -- recipe does not declare required OAuth3 scopes
- **CHECKPOINT_SKIP** -- destructive step executed without prior checkpoint

## Interaction Effects

| Combined With | Multiplicative Effect |
|--------------|----------------------|
| browser-snapshot | Recipe portals reference RoleRefMap refs; fresh snapshot required before replay |
| browser-oauth3-gate | Recipe declares required_oauth3_scopes; gate enforces before execution |
| browser-evidence | Execution trace becomes evidence input; evidence enables infinite replay at $0.001/task |
| browser-anti-detect | Humanized timing applied to recipe step execution; platform-specific patterns per recipe |

## Cross-References
- Skill: `data/default/skills/browser-recipe-engine.md` (full specification with FSM, cache key generation, never-worse gate)
- Skill: `data/default/skills/browser-snapshot.md` (RoleRefMap feeds recipe portal resolution)
- Skill: `data/default/skills/browser-oauth3-gate.md` (scope enforcement before recipe execution)
- Paper: `solace-cli/papers/04-triple-twin-orchestration.md` (CPU+LLM decision at preview)
- Paper: `solace-cli/papers/09-software5-triangle.md` (Browser vertex architecture)
