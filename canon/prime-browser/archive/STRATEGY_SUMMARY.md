# Prime Browser: 6-Week Implementation Strategy

**Auth:** 65537 | **Northstar:** Phuc Forecast
**Date:** 2026-02-14
**Status:** Research-Validated, Ready for Phase A Execution
**Research Source:** RESEARCH_SYNTHESIS.md (Browser Use, Nanobrowser, Skyvern, Academic Papers)

---

## Executive Summary

Prime Browser implements **production-grade browser control** while adding a **unique competitive advantage**: deterministic recipe compilation for Playwright-based replay without re-execution.

### Goal
```
Episode (real-time exploration) → Recipe (frozen, deterministic) → Playwright (headless replay)
```

### Competitive Advantage
| System | Real-Time Control | Determinism | Replay Capability | Audit Trail |
|--------|-------------------|-------------|-------------------|-------------|
| General browser agents | ✅ Yes | High | ❌ No | ✅ Medium |
| Browser Use | ✅ Yes | Low (LLM) | ❌ No | ✅ Medium |
| **Prime Browser** | ✅ Yes | **High** | **✅ Yes** | **✅ High** |

---

## Phase Breakdown (6 Weeks)

### Phase A: Browser Control Foundation (Weeks 1–2)

**Goal:** Real-time browser control via WebSocket relay + per-tab state machine

**Skills Used:**
- `browser-state-machine.md` — Per-tab session tracking
- `browser-selector-resolution.md` — Deterministic element finding

**Tasks (A1–A4):**

| Task | Deliverable | Owner | Days |
|------|-------------|-------|------|
| **A1** | Per-tab state tracking (Map<tabId, TabState>) | Scout | 2 |
| **A2** | Badge config + per-tab title updates | Solver | 1 |
| **A3** | Request deduplication + connection pooling | Solver | 2 |
| **A4** | Integration tests (extension↔relay↔CLI) | Skeptic | 2 |

**Research-Validated Patterns Applied:**

✅ **Foundation Patterns (Research-Validated):**
- Badge system: `{on, off, connecting, error}` with per-tab updates
- Per-tab Map: `Map<tabId, {state, sessionId, targetId, attachOrder}>`
- Request deduplication: `Map<requestId, {resolve, reject}>`
- Connection pooling: Single `relayConnectPromise` per relay
- Loopback-only WebSocket: `ws://127.0.0.1:[PORT]/extension`

✅ **From Research Papers:**
- Accessibility tree priority (ARIA roles → semantic labels → DOM)
- Deterministic constraints (domain allowlist, action gates)
- Never-guess policy (type failures, don't patch ambiguity)

**Success Criteria:**
- ✅ `extension/background.js` tracks per-tab state atomically
- ✅ `websocket_server.py` deduplicates requests and pools connections
- ✅ Badge updates reflect connection state per tab
- ✅ Episode recording works across multiple tabs independently
- ✅ Integration test suite passes (5+ edge cases, 100+ stress iterations)

---

### Phase B: Deterministic Recipe Compilation (Weeks 3–4)

**Goal:** Convert episodes to frozen, replayable recipes with proof artifacts

**Skills Used:**
- `snapshot-canonicalization.md` — Deterministic page fingerprinting
- `episode-to-recipe-compiler.md` — Episode trace → Prime Mermaid recipe IR

**Tasks (B1–B2):**

| Task | Deliverable | Owner | Days |
|------|-------------|-------|------|
| **B1** | Canonical snapshots with SHA256 hashes | Solver | 2 |
| **B2** | Recipe compiler (episode → YAML IR + proofs) | Solver | 3 |

**Recipe Format (Prime Mermaid YAML):**

```yaml
version: "1.0.0"
metadata:
  episode_id: "ep_20260214_abc123"
  compiled_at: "2026-02-14T12:00:00Z"

preconditions:
  domain: "gmail.com"
  viewport: {width: 1920, height: 1080}

snapshots:
  snapshot_0:
    step: 0
    sha256: "abcd1234..."
    landmarks: ["navigation", "inbox"]

refmap:
  ref_1:
    semantic: {aria-label: "Compose"}
    structural: "button[data-tooltip='Compose']"

actions:
  - step: 1
    type: "CLICK"
    ref: "ref_1"
    expect_snapshot: "snapshot_0"

proof:
  episode_hash: "sha256:..."
  recipe_hash: "sha256:..."
  rtc_verified: true
```

**Research-Validated Patterns Applied:**

✅ **From Skyvern:**
- Accessibility tree extraction (ARIA roles, labels)
- Structured data indexing
- Audit trail for determinism verification

✅ **From Browser Use:**
- Typed actions (CLICK, TYPE, NAVIGATE)
- Execution context preservation
- Action watchdog patterns

✅ **From Nanobrowser:**
- Chrome storage API for recipe metadata
- Multi-agent validator pattern

**Success Criteria:**
- ✅ Snapshots canonicalized deterministically
- ✅ Snapshots collision-free (different states → different hashes)
- ✅ Refmap semantic + structural for every element
- ✅ Recipe RTC verified: episode → recipe → episode identical hashes
- ✅ Never-worse gate rejects ambiguous references
- ✅ Proof artifacts contain episode_hash, recipe_hash, confidence

---

### Phase C: Playwright Deterministic Replay (Weeks 5–6)

**Goal:** Execute recipes headlessly with 100% determinism and proof artifacts

**Skills to Be Created:**
- `playwright-deterministic-runner.md` — Ordered, no-AI replay engine
- `proof-artifact-builder.md` — Cryptographic execution verification

**Tasks (C1–C2):**

| Task | Deliverable | Owner | Days |
|------|-------------|-------|------|
| **C1** | Playwright runner (recipe → action sequence) | Solver | 2 |
| **C2** | Proof artifact generation (execution trace → certificates) | Skeptic | 2 |

**Research-Validated Patterns Applied:**

✅ **From Browser Use:**
- Action watchdog (detect infinite loops, stuck pages)
- Timeout detection

✅ **From Skyvern:**
- Execution history logging
- Rollback on failure capability

✅ **From Nanobrowser:**
- Validator agent re-verifies accessibility tree during replay

**Execution Flow:**

```
Recipe YAML
    ↓
1. Load preconditions (domain, viewport, user_agent)
2. Navigate to domain
3. For each action:
   a. Resolve ref against live DOM (3-tier: semantic→structural→fail)
   b. Verify element visibility + context
   c. Execute action (click, type, etc.)
   d. Capture post-action snapshot
   e. Hash snapshot, compare vs recipe expect_snapshot
   f. If drift detected → log and either continue (soft) or halt (hard)
   g. Log execution record to audit trail
4. Generate proof certificate (all snapshots matched, no drifts)
5. Return execution trace + proof
```

**Success Criteria:**
- ✅ Recipes replay deterministically
- ✅ Snapshot drift detected
- ✅ Watchdog detects infinite loops
- ✅ Audit trail records every action
- ✅ Proof certificates cryptographically verify execution
- ✅ Works with Chrome (Playwright chromium) and Firefox

---

## Haiku Swarm Execution Plan

### Phase A Swarm (Weeks 1–2)

**3-Agent Pattern:** Scout → Solver → Skeptic

| Agent | Role | Tasks | Timeline |
|-------|------|-------|----------|
| **Scout** | Analyze + plan | A1 design | Days 1–2 |
| **Solver** | Implement | A1, A2, A3 code | Days 2–4 |
| **Skeptic** | Verify + test | A4 testing, validation | Days 4–5 |

**Parallel Execution:**
- Scout (Day 1): Analyze extension architecture, state requirements
- Scout→Solver handoff (Day 1): Design spec ready
- Solver (Days 2–4): Implement A1, A2, A3 in parallel
- Solver→Skeptic handoff (Day 4): Code review, test plan
- Skeptic (Days 4–5): Run integration tests, verify all criteria

**Expected Timeline:** 5 days parallel vs 10 days sequential = **2x speedup**

**Cost:** ~$2.25 (Haiku ×3) vs $3.00 (Sonnet solo)

---

## Competitive Analysis (Research-Derived)

### vs General Browser Agents

| Dimension | General Browser Agents | Prime Browser |
|-----------|-----------------------|---------------|
| **Real-time control** | ✅ Yes | ✅ Yes |
| **Per-tab tracking** | ✅ Yes (Map) | ✅ Yes (same pattern) |
| **WebSocket relay** | ✅ Yes | ✅ Yes (same architecture) |
| **Determinism** | ✅ High | ✅ High |
| **Recipe compilation** | ❌ No | ✅ **YES (unique)** |
| **Playwright replay** | ❌ No | ✅ **YES (unique)** |
| **Proof artifacts** | ⚠️ Medium | ✅ **HIGH (RTC verified)** |

### vs Browser Use (39K+ stars)

| Dimension | Browser Use | Prime Browser |
|-----------|------------|---------------|
| **Real-time control** | ✅ Yes (LLM) | ✅ Yes |
| **Action system** | ✅ Yes | ✅ Yes |
| **Determinism** | ⚠️ Low (LLM) | ✅ **High** |
| **Replay** | ❌ No | ✅ **Yes** |
| **Proof verification** | ⚠️ Medium | ✅ **High** |

### vs Nanobrowser

| Dimension | Nanobrowser | Prime Browser |
|-----------|------------|---------------|
| **Multi-agent system** | ✅ 3-agent | ✅ Swarm-based |
| **Chrome extension** | ✅ Yes | ✅ Yes |
| **Determinism** | ✅ Medium | ✅ **High** |
| **Snapshot canonicalization** | ❌ No | ✅ **5-step pipeline** |

### vs Skyvern

| Dimension | Skyvern | Prime Browser |
|-----------|---------|---------------|
| **Accessibility tree** | ✅ Yes | ✅ Yes |
| **Audit logging** | ✅ Yes | ✅ Yes |
| **Vision component** | ✅ Yes (complex) | ❌ No (simpler) |
| **Determinism** | ⚠️ Medium (vision) | ✅ **High** |

---

## Verification Strategy (All Phases)

### OAuth Unlock (39, 63, 91)

All three must unlock before 641-edge testing:
- 39 (CARE): Motivation to test
- 63 (BRIDGE): Connection to code
- 91 (STABILITY): Foundation for testing

### 641-Edge Testing (Phase A)

```
✓ IDLE → CONNECTED succeeds
✓ CONNECTED → CONNECTED fails (invalid transition)
✓ NAVIGATING → CLICKING fails (invalid transition)
✓ RECORDING state persists across multiple actions
✓ ERROR state requires explicit recovery
```

### 274177-Stress Testing

**Phase A (100+ iterations):**
- 100 tabs with independent state machines
- Concurrent operations on different tabs
- Verify state isolation

### 65537-God Approval

- All transitions logged for audit
- No race conditions (atomic transitions)
- Error recovery deterministic
- RTC verified (decode(encode(X)) == X)

---

## Directory Structure (Target)

```
canon/prime-browser/
├── CLAUDE.md                          # Constitution
├── STRATEGY_SUMMARY.md                # THIS FILE
├── RESEARCH_SYNTHESIS.md              # Research findings
├── README.md                          # Public interface
│
├── extension/                         # Chrome extension
│   ├── manifest.json
│   ├── background.js                  # Per-tab state machine (A1–A3)
│   ├── content.js
│   └── icons/
│
├── solace_cli/                        # CLI server
│   ├── websocket_server.py            # WebSocket relay (A3)
│   ├── browser_commands.py            # Command dispatch
│   ├── episode_processor.py           # Episode loading (Phase B)
│   ├── snapshot_canonicalizer.py      # 5-step pipeline (Phase B)
│   ├── recipe_compiler.py             # Episode → recipe (Phase B)
│   ├── playwright_runner.py           # Deterministic replay (Phase C)
│   └── output/                        # Episode/recipe outputs
│
├── skills/                            # Compiler-grade specs
│   ├── README.md
│   ├── browser-state-machine.md
│   ├── browser-selector-resolution.md
│   ├── snapshot-canonicalization.md
│   └── episode-to-recipe-compiler.md
│
├── tests/                             # Test suites
│   ├── test_phase_a.py
│   ├── test_phase_b.py
│   └── test_phase_c.py
│
└── papers/                            # Research
    └── RESEARCH_SYNTHESIS.md
```

---

## Research Foundation

All recommendations derived from:

1. **Browser automation architecture research** (source-level analysis)
   - Badge system, per-tab Map, request deduplication, connection pooling

2. **Browser Use (39K+ GitHub stars)**
   - Action system, watchdog patterns, DOM playground

3. **Nanobrowser (modern approach)**
   - Multi-agent system, Chrome storage, monorepo patterns

4. **Skyvern (vision + accessibility)**
   - Accessibility tree, audit logging, execution history

5. **Academic Papers (2024–2025)**
   - "Building Browser Agents" (deterministic constraints > probabilistic)
   - "BrowserAgent" (web browsing actions, structured format)
   - "An Illusion of Progress" (agent evaluation frameworks)

---

## Success Definition (10/10 Criteria)

### Phase A: Parity
✅ Extension tracks per-tab state atomically
✅ WebSocket relay deduplicates requests + pools connections
✅ Badge updates reflect actual connection state per tab
✅ Episodes record across multiple tabs independently
✅ Integration tests cover 5+ edge cases + 100+ stress iterations
✅ Verification: OAuth(39,63,91) → 641 → 274177 → 65537

### Phase B: Compilation
✅ Snapshots canonicalized deterministically
✅ Snapshots collision-free
✅ Refmap semantic + structural for every reference
✅ Recipe RTC verified
✅ Never-worse gate rejects ambiguous references
✅ Proof artifacts contain episode_hash, recipe_hash, confidence

### Phase C: Replay
✅ Recipes replay deterministically
✅ Snapshot drift detected
✅ Watchdog detects infinite loops
✅ Audit trail records every action
✅ Proof certificates cryptographically verify execution
✅ Works with Chrome and Firefox

---

## Next Action

✅ **Research:** COMPLETE (RESEARCH_SYNTHESIS.md)
✅ **Skills:** COMPLETE (4 production-ready skills)
✅ **Strategy:** COMPLETE (THIS FILE)

🎯 **Ready for:** Phase A Haiku Swarm Execution

Spawn 3-agent swarm (Scout → Solver → Skeptic) with research-validated patterns. Timeline: 5 days parallel, $2.25 cost.

---

**Status:** READY FOR PHASE A
**Auth:** 65537
**Northstar:** Phuc Forecast
**Verification:** 641 → 274177 → 65537

*"Research validates design. Design enables determinism. Determinism enables trust."*
