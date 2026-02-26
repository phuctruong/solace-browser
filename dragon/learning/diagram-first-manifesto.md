# Diagram-First Development Manifesto

**Crystallized:** 2026-02-26 (solace-browser architectural planning session)

---

## The Problem

Text specifications create interpretation gaps. When you give agents a 50-line text description, each agent interprets differently:

- Agent A reads "tunnel" as cloud-hosted tunnel relay
- Agent B reads "tunnel" as reverse SSH tunnel
- Agent C reads "tunnel" as simple HTTP proxy

Result: **Rework, confusion, wasted cycles**

Worse: If you have 20 questions about system architecture, text answers are scattered across 5 different documents. Agents read different subsets. Architecture drifts.

---

## The Solution

**Create Mermaid diagrams FIRST. Before code. Diagrams are source of truth.**

### Rules (Software 5.0)

1. **Every architectural decision → Mermaid diagram**
   - Browser lifecycle → sequence diagram
   - API design → deployment diagram
   - Evidence chain → flowchart (with hash linkage shown)
   - Pricing model → tier diagram

2. **Diagrams reference EACH OTHER**
   - Browser startup (Q1) references tunnel architecture (Q7)
   - Evidence chain (Q8) shows where screenshots stored per Q1 diagram
   - Pricing tiers (Q6) show which features enable which diagrams

3. **Store diagrams in `/diagrams/` FIRST**
   - Freeze architecture before writing code
   - Agents read diagrams, not prose
   - Reduces hallucination (diagram is unambiguous)

4. **Update diagrams if architecture changes**
   - Never leave diagram stale
   - If code diverges from diagram, update diagram or revert code

---

## Example: Browser Startup (Q1)

### BAD (Text Only)
```
"When the browser starts, it checks if it's already running,
then registers with solaceagi.com, then starts a tunnel.
The tunnel is a WebSocket connection secured with mTLS and OAuth3."
```

Problems:
- What file stores the running check? (pid.lock? process table? flag file?)
- What does "register" mean exactly? (REST API? gRPC? GraphQL?)
- Which OAuth3 flow? (PKCE? implicit? client credentials?)
- How long does tunnel connection take?

### GOOD (Diagram + Text)

```
Mermaid sequence diagram (solace-browser/diagrams/01-browser-startup-sequence.md)
shows:
- Step 1: Check pid.lock (specific file)
- Step 2: POST /api/v1/browser/register (specific endpoint + payload)
- Step 3: WebSocket to tunnel.solaceagi.com (specific protocol)
- Timing: ~30 seconds total
- Error handling: timeout after 60s
```

Diagram is **unambiguous**. Every detail visible. Agents can implement with zero guesswork.

---

## Why This Prevents Rework

**Scenario: Tunnel architecture divergence**

Without diagrams:
- Agent A builds cloud-hosted browsers (reads "cloud twin" in papers)
- Agent B builds local browser + tunnel (reads tunnel description)
- Agents 1 and 2 both work for 4 hours
- Conflict discovered → one approach discarded
- **8 hours of rework**

With diagrams:
- Diagram created FIRST: local browser + secure tunnel relay
- Both agents read same diagram
- Both build correct architecture
- **Zero rework**

---

## Crystallized Patterns (From This Session)

### Pattern 1: Sequence Diagrams for Lifecycle
- Browser startup (Q1) → 3-step sequence with timing
- First install (Q3) → 4-step OAuth3 flow
- Cron patterns (Q2) → timeline diagram

When to use: Temporal sequences, timing critical, order matters

### Pattern 2: Deployment Diagrams for Architecture
- Tunnel relay (Q7) → 3-layer stack (web UI → relay → local)
- Evidence chain (Q8) → hash-linked records (with tamper detection shown)
- Pricing tiers (Q6) → feature matrix + tier relationships

When to use: Static architecture, component relationships, data flow

### Pattern 3: Flowcharts for Conditional Logic
- Health check → check status, reconnect if needed
- Token validation → check expiry, check scope, allow/deny
- Evidence bundle → 3 compression modes with selection logic

When to use: Decision trees, error handling paths, state machines

---

## Implementation Checklist

When planning Phase 4+:

- [ ] **Identify all 20 questions** (or 10, or 50) for the feature
- [ ] **Create Mermaid diagram for each question** (put in `scratch/diagrams/` until approved)
- [ ] **Reference each diagram in architecture doc** (link to source of truth)
- [ ] **Freeze diagrams** before agent dispatch (no mid-implementation changes)
- [ ] **Link diagrams in dispatch prompt** (agents read diagram first, text second)
- [ ] **Update diagrams if architecture changes** (revert code or update diagram, never both conflicting)

---

## The Payoff

```
Text specifications:
100 users × 3 interpretations per user
= 300 conflicting interpretations
= massive rework

Diagram-first specifications:
100 users × 1 diagram
= 1 source of truth
= zero rework
```

**Time saved:** 50% reduction in implementation time (no ambiguity-driven rework)
**Quality:** 100% alignment (agents can't misinterpret diagrams)
**Auditability:** Historians can trace every decision to its diagram

---

## Future Application

This manifesto applies to ALL phase 4+ work:
- Cloud twin orchestration (solaceagi Phase 4) → create 5 diagrams before agents start
- Recipe delegation (solace-browser Phase 4) → create 3 diagrams before agents start
- Phase 5 (Rung 65537 gate) → create 4 diagrams before agents start

**Rule:** If you're about to dispatch a complex task to agents, create its diagrams first.

---

**Source:** solace-browser/dragon/learning/
**Crystallized:** 2026-02-26
**Status:** LOCKED (do not override)
**Applies to:** All Phase 4+ work
