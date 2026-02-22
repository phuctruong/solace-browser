# Diagram: Browser Multi-Layer Architecture

**ID:** browser-multi-layer-architecture
**Version:** 1.0.0
**Type:** Architecture diagram
**Primary Axiom:** NORTHSTAR (all layers serve the Universal Portal vision)
**Tags:** architecture, layers, heartbeat, intent, recipe, execution, evidence, cost-model

---

## Purpose

The 5-layer browser architecture is the core design of SolaceBrowser's intelligence stack. Each layer is optimized for a specific trade-off of speed, cost, and correctness. The layered design ensures that 70% of tasks (cache hits) are served in < 5 seconds at ~$0.001/task, while cold-miss tasks use a more expensive model only when necessary.

The architecture extends the triple-twin model to add a browser-specific evidence layer at the bottom.

---

## Diagram: 5-Layer Architecture

```mermaid
flowchart TB
    USER["👤 User Intent\n'post to LinkedIn'"]

    subgraph L1["Layer 1: Heartbeat (CPU, < 100ms)"]
        direction LR
        H1["browser_alive?"]
        H2["session_active?"]
        H3["recipe_store_ready?"]
        H1 --- H2 --- H3
    end

    subgraph L2["Layer 2: Intent (haiku, < 500ms)"]
        direction LR
        I1["Classify platform"]
        I2["Classify action_type"]
        I3["Normalize intent"]
        I4["Compute cache key\nSHA256(intent+platform)"]
        I1 --> I2 --> I3 --> I4
    end

    subgraph L3["Layer 3: Recipe Match (haiku, < 1s)"]
        direction LR
        R1["Cache lookup"]
        R2{"Hit?"}
        R3["Load recipe.json"]
        R4["OAuth3 4-gate check"]
        R1 --> R2
        R2 -->|hit| R3
        R2 -->|miss| R4
    end

    subgraph L4["Layer 4: Execution (1-10s)"]
        direction LR
        E1["haiku: Recipe replay\n(cache hit)"]
        E2["sonnet: Recipe build\n(cold miss)"]
        E3["DOM snapshot\nbefore + after"]
        E1 --- E3
        E2 --- E3
    end

    subgraph L5["Layer 5: Evidence (CPU + haiku, < 500ms)"]
        direction LR
        EV1["PZip snapshot\ncompression"]
        EV2["SHA256 diff\ncomputed"]
        EV3["ALCOA+ fields\npopulated"]
        EV4["Chain linked\nSigned"]
        EV1 --> EV2 --> EV3 --> EV4
    end

    OUTPUT["evidence_bundle.json\n+ result"]

    USER --> L1
    L1 -->|alive| L2
    L2 --> L3
    R3 --> L4
    R4 -->|miss| L4
    L4 --> L5
    L5 --> OUTPUT
```

---

## Diagram: Layer Cost Model

```mermaid
%%{init: {'theme': 'base'}}%%
quadrantChart
    title Layer Cost vs. Speed Trade-off
    x-axis Fast --> Slow
    y-axis Cheap --> Expensive
    quadrant-1 Avoid
    quadrant-2 Use sparingly
    quadrant-3 Preferred path
    quadrant-4 Necessary evil
    L1 Heartbeat: [0.05, 0.02]
    L2 Intent haiku: [0.15, 0.08]
    L3 Recipe+Gate haiku: [0.20, 0.12]
    L4 Replay haiku: [0.30, 0.15]
    L4 Build sonnet: [0.80, 0.75]
    L5 Evidence haiku: [0.12, 0.10]
```

---

## Diagram: Cache Hit vs. Miss Flow

```mermaid
flowchart LR
    INTENT["User Intent"]
    GATE["OAuth3 Gate\n(all 4 pass)"]
    CACHE{"Cache\nlookup"}
    HIT_PATH["Cache HIT (70%)\nhaiku replay\n< 5s, ~$0.001"]
    MISS_PATH["Cache MISS (30%)\nsonnet build\n< 2min, ~$0.05"]
    EVIDENCE["Evidence Bundle\n(both paths)"]

    INTENT --> GATE --> CACHE
    CACHE -->|hit| HIT_PATH --> EVIDENCE
    CACHE -->|miss| MISS_PATH --> EVIDENCE
```

---

## Layer Specification Table

| Layer | Trigger | Model | Target Latency | Target Cost | Input | Output |
|-------|---------|-------|---------------|-------------|-------|--------|
| 1: Heartbeat | Every request | CPU | < 100ms | $0.000 | None | heartbeat.json |
| 2: Intent | After L1 PASS | haiku | < 500ms | ~$0.0001 | Natural language | classified_intent.json |
| 3: Recipe Match | After L2 | haiku | < 1s | ~$0.0002 | intent + platform | recipe.json OR cold_miss |
| 3: OAuth3 Gate | After cache check | haiku | < 500ms | ~$0.0001 | recipe + token | gate_audit.json |
| 4: Execute (hit) | Gate PASS + hit | haiku | 1-5s | ~$0.0005 | recipe + snapshot | execution_trace.json |
| 4: Execute (miss) | Gate PASS + miss | sonnet | 30-120s | ~$0.03-0.05 | intent + DOM | recipe.json + trace |
| 5: Evidence | After execute | haiku | < 500ms | ~$0.0001 | trace + snapshots | evidence_bundle.json |

---

## Notes

### Why 5 Layers (Not 3)?

The triple-twin model (Heartbeat / LLM / CPU) is extended with two additional layers specific to browser automation:

1. **Recipe Match** separates the cache lookup from the execution, enabling a haiku-cost path for cache hits without involving a heavier model.
2. **Evidence** is separated from execution because evidence packaging has its own compliance requirements (ALCOA+, Part 11) and should not be coupled to execution errors.

### Layer 3 OAuth3 Integration

OAuth3 gate is in Layer 3 (not Layer 1) because the gate check requires the normalized intent + platform — which Layer 2 produces. Gate without intent = scopeless gate = BLOCKED.

### Economics (Why This Architecture Wins)

```
At 70% hit rate:
  0.70 × $0.001 (hit) + 0.30 × $0.05 (miss) = $0.0157/task

vs. LLM-every-task:
  1.00 × $0.05 = $0.05/task

Savings: 68% reduction in per-task LLM cost
At 10,000 tasks/month: $314 vs. $500 = $186/month saved per user
```

### PZip in Layer 5

Layer 5 applies PZip compression to before/after snapshots before signing. This enables full HTML snapshot storage at near-zero marginal cost ($0.00032/user/month at scale). Full HTML snapshots (not screenshots) are required for ALCOA+ "Original" compliance and for recipe replay.

---

## Related Artifacts

- `combos/full-browser-task.md` — full implementation of this 5-layer pipeline
- `diagrams/recipe-engine-fsm.md` — Layer 3 recipe engine FSM
- `diagrams/oauth3-enforcement-flow.md` — Layer 3 OAuth3 gate detail
- `diagrams/evidence-pipeline.md` — Layer 5 evidence pipeline detail
