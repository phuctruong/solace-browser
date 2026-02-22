# Diagram: Browser Action Lifecycle

**ID:** browser-action-lifecycle
**Version:** 1.0.0
**Type:** Lifecycle diagram + state machine
**Primary Axiom:** All 5 Axioms (one lifecycle touches all)
**Tags:** lifecycle, intent, oauth3, action, evidence, replay, determinism, closure, integrity, hierarchy, northstar

---

## Purpose

The browser action lifecycle traces a single browser action from user intent through to a replayable evidence artifact. It is the complete, end-to-end view of what happens when SolaceBrowser executes a task. Every major subsystem is represented: intent classification (recipe engine), authorization (OAuth3 gate), execution (browser-snapshot + recipe replay), and evidence (browser-evidence + chain).

---

## Diagram: Complete Lifecycle (All Phases)

```mermaid
stateDiagram-v2
    direction TB
    [*] --> INTENT : User states task in natural language

    state "Phase 1: INTENT CLASSIFICATION" as P1 {
        INTENT --> NORMALIZE : extract platform + action_type
        NORMALIZE --> CACHE_KEY : SHA256(normalized intent + platform)
    }

    state "Phase 2: OAUTH3 AUTHORIZATION" as P2 {
        CACHE_KEY --> G1 : token lookup
        G1 --> G2 : token exists
        G2 --> G3 : token not expired
        G3 --> G4 : scope present
        G4 --> AUTHORIZED : G4 pass or N/A
        G1 --> BLOCKED_AUTH
        G2 --> BLOCKED_AUTH
        G3 --> BLOCKED_AUTH
        G4 --> BLOCKED_AUTH
    }

    state "Phase 3: RECIPE MATCH" as P3 {
        AUTHORIZED --> CACHE_HIT : recipe found
        AUTHORIZED --> CACHE_MISS : no recipe
    }

    state "Phase 4: EXECUTION" as P4 {
        CACHE_HIT --> BEFORE_SNAPSHOT : load recipe.json
        CACHE_MISS --> BUILD_RECIPE : dispatch recipe-builder
        BUILD_RECIPE --> BEFORE_SNAPSHOT : new recipe ready
        BEFORE_SNAPSHOT --> STEP_EXECUTE : DOM snapshot captured
        STEP_EXECUTE --> CHECKPOINT : step completed
        CHECKPOINT --> STEP_EXECUTE : checkpoint pass → continue
        CHECKPOINT --> ROLLBACK : checkpoint fail → undo
        ROLLBACK --> BLOCKED_EXEC
        STEP_EXECUTE --> AFTER_SNAPSHOT : all steps complete
    }

    state "Phase 5: EVIDENCE" as P5 {
        AFTER_SNAPSHOT --> DIFF : compute DOM diff
        DIFF --> PZIP : compress snapshots
        PZIP --> CHAIN : link to previous bundle
        CHAIN --> SIGN : AES-256-GCM sign
        SIGN --> STORE : store in ~/.solace/evidence/
    }

    state "Phase 6: REPLAY (future)" as P6 {
        STORE --> REPLAY_CAPABLE : bundle is replay-ready
    }

    STORE --> DONE
    REPLAY_CAPABLE --> DONE
    DONE --> [*]
    BLOCKED_AUTH --> [*]
    BLOCKED_EXEC --> [*]

    note right of P2
        HIERARCHY axiom:
        G1 → G2 → G3 → G4 strict order
        Any failure → BLOCKED (fail-closed)
    end note

    note right of P4
        CLOSURE axiom:
        max_steps + timeout_ms enforced
        Checkpoint at every destructive step
    end note

    note right of P5
        INTEGRITY axiom:
        PZip + SHA256 + AES-256-GCM
        ALCOA+ fields required
    end note
```

---

## Diagram: Axiom Coverage Per Phase

```mermaid
flowchart LR
    subgraph AX["5 Axioms"]
        INT["INTEGRITY\nEvidence-only claims"]
        HIE["HIERARCHY\nGates are law"]
        DET["DETERMINISM\nSame input → same output"]
        CLO["CLOSURE\nFinite halting criterion"]
        NST["NORTHSTAR\nUniversal Portal"]
    end

    subgraph PH["6 Lifecycle Phases"]
        P1["Phase 1\nIntent"]
        P2["Phase 2\nOAuth3"]
        P3["Phase 3\nRecipe"]
        P4["Phase 4\nExecute"]
        P5["Phase 5\nEvidence"]
        P6["Phase 6\nReplay"]
    end

    DET --> P1
    HIE --> P2
    DET --> P3
    CLO --> P3
    DET --> P4
    CLO --> P4
    INT --> P4
    INT --> P5
    INT --> P6
    NST --> P1
    NST --> P6
```

---

## Diagram: Replay Capability

```mermaid
flowchart TD
    BUNDLE["evidence_bundle.json\n(stored in ~/.solace/evidence/)"]

    REPLAY_OPTIONS["Replay Options"]

    UI["Kanban UI\n(browse history by session)"]
    CARD["Page Card\n(click any page in session)"]
    RENDER["Full HTML render\n(iframe, exactly what agent saw)"]
    FORM_FILLS["Form fills visible\n(before/after per field)"]
    REPLAY_EXEC["Recipe replay execution\n(re-execute recipe exactly)"]

    BUNDLE --> REPLAY_OPTIONS
    REPLAY_OPTIONS --> UI
    UI --> CARD
    CARD --> RENDER
    RENDER --> FORM_FILLS
    REPLAY_OPTIONS --> REPLAY_EXEC

    ECONOMICS["PZip makes this affordable:\n$0.00032/user/month\nfor full HTML history\n(not screenshots)"]
    BUNDLE --- ECONOMICS
```

---

## Lifecycle Timing Summary

| Phase | Mechanism | Latency | Cost |
|-------|---------|---------|------|
| 1: Intent | haiku LLM | < 500ms | ~$0.0001 |
| 2: OAuth3 | haiku + vault | < 300ms | ~$0.0001 |
| 3: Recipe Match (hit) | hash lookup | < 100ms | $0.000 |
| 3: Recipe Match (miss) | sonnet LLM | 30-120s | ~$0.03 |
| 4: Execute (hit) | haiku + playwright | 1-5s | ~$0.0005 |
| 4: Execute (miss) | sonnet + playwright | 30-120s | ~$0.05 |
| 5: Evidence | CPU + PZip + haiku | < 500ms | ~$0.0001 |
| 6: Replay capability | CPU | 0ms (pre-built) | $0.000 |
| **Total (cache hit)** | — | **< 7s** | **~$0.001** |
| **Total (cache miss)** | — | **< 3 min** | **~$0.05** |

---

## Lifecycle Artifact Manifest

Every lifecycle execution MUST produce the following artifacts:

```
Artifacts per lifecycle run:
  classified_intent.json    — Phase 1 output
  gate_audit.json           — Phase 2 output (all 4 gates)
  recipe.json               — Phase 3 output (served or built)
  execution_trace.json      — Phase 4 output (step-by-step)
  before_snapshot.pzip      — Phase 4/5 boundary
  after_snapshot.pzip       — Phase 4/5 boundary
  evidence_bundle.json      — Phase 5 output (ALCOA+ signed)

Optional artifacts (cold-miss path):
  pm_triplet.json           — Phase 3 (new recipe built)
  test_result.json          — Phase 3 validation
```

Missing any required artifact = incomplete lifecycle = rung target NOT achieved.

---

## Notes

### Why 6 Phases?

Each phase has a distinct responsibility and a distinct failure mode:
1. **Intent** can fail if the input is ambiguous
2. **OAuth3** can fail if consent is not established
3. **Recipe** can fail on cache miss (triggers cold-miss path)
4. **Execute** can fail if DOM changed or max_steps exceeded
5. **Evidence** can fail if PZip or chain is unavailable
6. **Replay** is not a failure mode — it is a future capability built from Phase 5 artifacts

Collapsing phases would mean one failure mode could silently mask another.

### The Replay Loop (Why It Matters)

Phase 6 (Replay) closes the loop: every action executed is automatically replayable. This is the + Enduring and + Available ALCOA+ principles in action. More practically, it is what allows the Kanban history UI to exist: every page the agent visited, every form fill it made, every action it took — all replayable and inspectable by the user.

No other browser automation tool stores full HTML replay history at this cost or with this completeness.

---

## Related Artifacts

- `diagrams/browser-multi-layer-architecture.md` — 5-layer view of same pipeline
- `diagrams/oauth3-enforcement-flow.md` — Phase 2 detail
- `diagrams/recipe-engine-fsm.md` — Phase 3 FSM detail
- `diagrams/evidence-pipeline.md` — Phase 5 pipeline detail
- `diagrams/part11-alcoa-mapping.md` — Phase 5 compliance mapping
