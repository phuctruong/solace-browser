# /load-browser-skills - Methodology Browser Skills Loader

Load the full browser methodology bundle from `canon/skills/methodology` into active context.

## Usage

```bash
/load-browser-skills
/load-browser-skills --verify
/load-browser-skills --quiet
```

## Skill Bundle (Combined)

Load these files in dependency-safe order:

1. `canon/skills/methodology/web-automation-expert.skill.md`
2. `canon/skills/methodology/live-llm-browser-discovery.skill.md`
3. `canon/skills/methodology/human-like-automation.skill.md`
4. `canon/skills/methodology/prime-mermaid-screenshot-layer.skill.md`
5. `canon/skills/methodology/silicon-valley-discovery-navigator.skill.md`

## Instructions for Claude

When user runs `/load-browser-skills [options]`:

1. Read all five files above.
2. Extract and confirm per skill:
   - `skill_id`
   - `version`
   - `status`
   - `depends_on`
   - core capabilities
3. Activate combined operating loop:
   - PERCEIVE: live browser state + snapshots
   - DECIDE: select action using portal/selector confidence
   - ACT: execute via browser API with human-like behavior
   - VERIFY: confirm page-state transition and evidence
   - LEARN: store PrimeWiki/PrimeMermaid/recipe updates
4. Return a load summary with loaded skills and readiness status.

## Standard Output

```text
✅ BROWSER METHODOLOGY SKILLS LOADED

Loaded: 5/5
- web-automation-expert v2.0.0
- live-llm-browser-discovery v1.0.0
- human-like-automation v1.0.0
- prime-mermaid-screenshot-layer v1.0.0
- silicon-valley-discovery-navigator v1.0.0

Mode: Live LLM Discovery + PrimeWiki/PrimeMermaid + Recipe Replay
Status: Ready
```

## Verify Mode (`--verify`)

Run quick checks and report pass/fail:

1. `canon/skills/methodology/*` paths exist and are readable.
2. Browser endpoint health check (`/api/status`) responds.
3. Snapshot flow available (`/api/snapshot`).
4. Prime artifact folders available for session output:
   - `marketing/sites/<site>/primewiki/`
   - `marketing/sites/<site>/primemermaid/`
   - `marketing/sites/<site>/screenshots/`
   - `marketing/sites/<site>/proof/`

## Quiet Mode (`--quiet`)

Return only:

```text
✅ 5 browser methodology skills loaded
```
