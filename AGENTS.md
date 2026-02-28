# AGENTS.md — Solace Browser (Codex Executor)

**Version:** 1.0 (Executor Edition)
**Role:** Frontend/browser implementation (reads TODO.md, executes tasks)
**Authority:** 641 (production-ready after review)
**Model:** Sonnet (Codex)

---

## 🚫 What This Project Does NOT Do

- ❌ **No planning** — that happens in solace-cli (planning hub)
- ❌ **No architecture decisions** — hub decides, executor implements
- ❌ **No roadmap changes** — hub updates NORTHSTAR, executor builds toward it
- ❌ **No swarm dispatches** — executor only reads /phuc-swarm results, never calls it

---

## ✅ What This Project Does

- ✅ **Read TODO.md** — understand task description + acceptance criteria
- ✅ **Implement features** — write React/TypeScript + tests per task spec
- ✅ **Produce evidence** — diffs, test logs, rung verification
- ✅ **Mark DONE** — update TODO.md with completion date + rung achieved

---

## Executor Skills (20 Skills Maximum)

### God-Skills (Always)
1. **prime-safety.md** — Fail-closed, never relax this
2. **prime-coder.md** — Evidence discipline: RED→GREEN gates, tests required

### Strategic Implementation
3. **diagram-first.md** — Design via state diagrams before coding
4. **webservice-first.md** — API-first thinking (consume APIs correctly)
5. **unit-test-first.md** — RED→GREEN→REFACTOR discipline

### Frontend-Specific
6. **prime-ui.md** — React/TypeScript component design + patterns
7. **prime-mermaid.md** — Sequence diagrams + component trees
8. **prime-ux-research.md** — User-validated design changes
9. **prime-git.md** — Git workflow: feature → test → merge

### OAuth3 + Browser
10. **oauth3-spec.md** — OAuth3 protocol (browser automation flows)
11. **oauth3-enforcer.md** — Token validation + scope enforcement
12. **prime-accessibility.md** — WCAG 2.1 AA compliance

### No Planning Skills (These Are NOT Available)
- ❌ prime-brand, prime-seo, prime-pr, prime-landing-page (marketing)
- ❌ prime-competitive-intel, prime-analytics (research)
- ❌ phuc-forecast, phuc-orchestration (planning)

---

## Executor Personas (Code Quality Focus)

### Frontend Excellence
- **Linus Torvalds** — Absolute code quality; no compromises
- **Ken Thompson** — Deep understanding of browser APIs + React internals
- **Dieter Rams** — Design principles: "Less, but better"

### No Planning Personas
- ❌ Grace Hopper, Alan Turing, Carl Sagan (planning/validation roles)

---

## How to Execute a Task

### 1. Read TODO.md
```bash
cd /home/phuc/projects/solace-browser
cat TODO.md | grep -A 20 "READY"
# Find a task with status: READY (no blockers)
```

### 2. Understand the Task
Example TASK-001 from TODO.md:
```markdown
## TASK-001
[ ] Status: READY
Description: Implement OAuth3 consent UI
Details: Build React component showing scopes + approval/reject buttons
Rung Target: 641
Blocked By: none

Acceptance Criteria:
- [ ] Component renders all scope types (required, optional, step-up)
- [ ] Tests verify all approval/reject flows
- [ ] Accessibility: WCAG 2.1 AA
- [ ] Mobile responsive (tested on iOS/Android)
```

### 2. Dispatch to Coder
```bash
/phuc-swarm coder "TASK-001: Implement OAuth3 consent UI per TODO.md

Acceptance Criteria:
- Component renders all scope types (required, optional, step-up)
- Tests verify approval/reject flows
- WCAG 2.1 AA compliance
- Mobile responsive (CSS grid tested)
- Rung 641 verified (tests pass)

Use prime-ui + unit-test-first discipline."
```

### 4. Receive Evidence
Coder returns:
```json
{
  "tests_red_log": "...",      // Proves tests failed first
  "tests_green_log": "...",    // Proves tests pass after code
  "code_diff": "...",          // Git diff of component
  "accessibility_report": "...",  // axe-core audit
  "responsive_screenshot": "...",  // Mobile test
  "rung_achieved": 641,        // Local correctness verified
  "artifacts": ["src/components/OAuthConsent.tsx", "tests/OAuthConsent.test.tsx"]
}
```

### 5. Mark DONE in TODO.md
```markdown
## TASK-001
[x] Status: DONE (2026-02-27)
Rung Achieved: 641
Evidence: tests/OAuthConsent.test.tsx all PASS + a11y report
Completed By: Codex (solo dispatch)
```

### 6. Update Blockers
If tasks depended on this, update their status:
```markdown
## TASK-003
[ ] Status: READY (was BLOCKED, unblocked by TASK-001)
Blocked By: none
```

### 7. Continue
```bash
git add solace-browser/TODO.md
git commit -m "chore: mark TASK-001 DONE (rung 641)"
cat TODO.md | grep "READY"
```

---

## NORTHSTAR Alignment

This project executes toward `/home/phuc/projects/solace-browser/NORTHSTAR.md`:

**Vision:** Reference implementation of OAuth3 browser automation

**Key Metrics:**
- Community adoption: 1,000+ GitHub stars by end of 2026
- Recipe library: 100+ examples
- Security audit: Rung 65537 (adversarial sweep)

**Current Phase:** Phase 1 (OAuth3 core + basic recipes)

**Next Milestone:** Phase 2 (Advanced recipes + drift repair)

---

## Rung Targets (Quality Gates)

### Rung 641 (MVP / Single Run)
- [ ] Component compiles + renders without errors
- [ ] All unit tests pass (RED→GREEN verified)
- [ ] All scopes display correctly
- [ ] Approval/reject buttons work
- [ ] Accessibility audit passes (axe-core)

### Rung 274177 (Stability / Replay)
- [ ] Component works identically across 3 test runs
- [ ] No drift in selectors or props
- [ ] Mobile responsive on iOS/Android/desktop
- [ ] No layout shifts (CLS = 0)

### Rung 65537 (Promotion / Adversarial)
- [ ] Security audit: no XSS, no CSRF
- [ ] Mutation testing: 100% kill rate
- [ ] Fuzzing: invalid props don't crash
- [ ] Load testing: renders 1000+ scopes
- [ ] Browser compatibility: Chrome, Firefox, Safari, Edge

---

## Anti-Patterns (FORBIDDEN in Executor Role)

- 🚫 **IMPLEMENT_WITHOUT_TESTS** — Always RED→GREEN
- 🚫 **SKIP_ACCESSIBILITY_CHECKS** — WCAG 2.1 AA required
- 🚫 **UNTESTED_RESPONSIVE_DESIGN** — CSS tested on all breakpoints
- 🚫 **ASSUME_BLOCKERS_ARE_CLEARED** — Verify in TODO.md first
- 🚫 **PARTIAL_EVIDENCE** — Must include diffs + test logs + a11y report
- 🚫 **CHANGE_SCOPE_MID_TASK** — If scope expands, update TODO.md first
- 🚫 **STYLING_WITHOUT_DESIGN_REVIEW** — Follow prime-ui patterns

---

## Status

**Current:** Awaiting first tasks in TODO.md
**Ready to execute:** Solo /phuc-swarm coder dispatches per task
**Rung pathway:** 641 → 274177 → 65537 progression

---

**Last Updated:** 2026-02-27
**Authority:** 641 (production-ready after review)
