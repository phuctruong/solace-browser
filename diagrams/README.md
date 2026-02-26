# Solace Browser Diagrams

Diagram-first architecture for solace-browser (Phase 4 + Phase 5)

## All Diagrams (6/6)

| # | Diagram | Questions | Rung |
|---|---------|-----------|------|
| **01** | [Browser Startup Sequence](01-browser-startup-sequence.md) | Q1: What happens when solace-browser first starts? | 641 |
| **02** | [Cron Scheduler Patterns](02-cron-scheduler-patterns.md) | Q2: How does cron fit in? | 641 |
| **03** | [First Install UX Flow](03-first-install-ux-flow.md) | Q3: First install experience? | 641 |
| **04** | [Tunnel Architecture](04-tunnel-architecture.md) | Q7: What does solaceagi.com offer? | 641 |
| **05** | [ALCOA+ Evidence Chain](05-alcoa-evidence-chain.md) | Q8: FDA Part 11: What's required? | 641 |
| **06** | [Dragon Warrior Pricing Tiers](06-dragon-warrior-pricing-tiers.md) | Q4-Q6: Pricing + paid tiers | 641 |

---

## How to Use These Diagrams

### For Codex Agents (Phase 4 Implementation)

1. **Start with these diagrams, not text specs**
   - Each diagram is source of truth
   - Never contradict a diagram with prose
   - If diagram and prose differ, update diagram or revert code

2. **Read diagrams in order:**
   - 01 (Browser startup) → foundation
   - 02 (Cron patterns) → builds on 01
   - 03 (First install) → builds on 01, 02
   - 04 (Tunnel architecture) → foundation for remote control
   - 05 (Evidence chain) → required for all operations
   - 06 (Pricing tiers) → determines feature availability

3. **Implement to diagram specs exactly**
   - 3-step startup sequence? Implement all 3 steps, in order
   - Hash chain with 6 fields? Implement all 6 fields
   - mTLS handshake? Don't simplify
   - OAuth3 validation? Don't skip

### For Auditors / Future Sessions

- Trace architectural decisions to their diagrams
- If architecture changes, update relevant diagram(s)
- If diagram is stale, replace (don't augment with notes)
- Prefer Mermaid over prose

---

## Questions These Diagrams Answer

**Q1:** What happens when solace-browser first starts?
→ Diagram 01 (3-step sequence diagram)

**Q2:** How does cron fit in?
→ Diagram 02 (3 patterns with timing)

**Q3:** First install experience?
→ Diagram 03 (4-step OAuth3 onboarding)

**Q4:** Is solace-browser private or OSS?
→ Diagram 06 shows feature tiers (private binary, free + paid tiers)

**Q5:** Can you use browser for free?
→ Diagram 06 (White Belt tier, $0, with constraints)

**Q6:** What's different in paid tier?
→ Diagram 06 (Yellow/Orange/Green/Black tiers, incremental features)

**Q7:** What does solaceagi.com offer?
→ Diagram 04 (Tunnel relay + web UI + OAuth3 validation)

**Q8:** FDA Part 11: What's required?
→ Diagram 05 (ALCOA+ evidence chain with hash linkage)

**Q9-Q12:** Apps ecosystem (answered in papers, not diagrams)

**Q13-Q20:** Documentation + team decisions (answered in dragon/)

---

## Technical Specifications

All diagrams include:
- **Mermaid code** (visually rendered)
- **Detailed text specs** (constraints, acceptance criteria)
- **Examples** (JSON, bash, pseudocode)
- **Constraints** (Software 5.0 rules)
- **Acceptance criteria** (testable)
- **Rung target** (641 for Phase 4)

---

## Constraints (Software 5.0)

- ✅ **Source of truth:** Diagrams are canonical, not comments
- ✅ **No silent failures:** Error cases shown explicitly
- ✅ **Determinism:** Same inputs → same behavior
- ✅ **Immutability:** Audit trails cannot be deleted
- ✅ **Token safety:** OAuth3 scopes enforced everywhere
- ✅ **Evidence first:** Every action produces artifacts

---

## Phase 4 Implementation Path

1. **Diagram 01 → Browser Startup**
   - Implement 3-step boot sequence
   - pid.lock file management
   - solaceagi.com registration
   - Tunnel connection

2. **Diagram 03 → First Install**
   - 4-step onboarding (install, init, login, test)
   - OAuth3 PKCE flow
   - Workspace initialization (~/.solace/)

3. **Diagram 02 → Cron Integration**
   - Auto-start/stop patterns
   - Scheduled recipe execution
   - Health checks + reconnection

4. **Diagram 04 → Tunnel Relay**
   - WebSocket connection + mTLS
   - Token validation per-message
   - Per-device isolation

5. **Diagram 05 → Evidence Chain**
   - Hash-linked audit logs
   - Tamper detection
   - 3 compression modes

6. **Diagram 06 → Tier Enforcement**
   - Free tier (White) constraints
   - Paid tier features unlocked by OAuth3 scope

---

## Maintenance

**When to update diagrams:**
- Architecture decision changes → update diagram FIRST
- Implementation diverges → either revert code or update diagram (not both)
- New question discovered → add new diagram
- Question superseded → mark old diagram as deprecated

**Never:**
- Leave diagram stale
- Contradict diagram with prose
- Add "notes" to diagram (replace it)

---

**Created:** 2026-02-26 (Architectural Planning Session)
**Status:** LOCKED (all 20 questions answered)
**Rung:** 641 (Phase 4 architecture fully specified)
**Next:** Phase 5 dispatch prompt (Rung 65537 gate)
