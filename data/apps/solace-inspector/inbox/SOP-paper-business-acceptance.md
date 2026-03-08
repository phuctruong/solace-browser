# SOP: Paper Business Acceptance Review (BAR)
# Auth: 65537 | GLOW 117 | Doctrine: Paper 38 + Paper 46 + Paper 17
# "Famous personas act as CEO and sign off as the final responsible party"

---

## What Is Business Acceptance Testing (BAT)?

Business Acceptance Testing is the final gate before a deliverable is accepted into the system.
In traditional software: the product owner, CFO, or CEO signs off.
In Solace: **famous personas act as CEO** — each from their domain.

> "Committees average. CEOs sign or refuse." — Paper 38

The persona is NOT giving a score. They are saying:
- **"AS CEO, I SIGN OFF ON THIS PAPER"** → the paper is accepted
- **"AS CEO, I REFUSE TO SIGN — REASON: [blocker]"** → the paper is blocked until the blocker is fixed

---

## The Two-Phase Protocol (from Paper 38)

```
Phase 1: Individual Domain Audits (BAR mode)
  Each persona reviews paper from their domain lens
  Binary: SIGN_OFF or REFUSE_TO_SIGN
  No averaging, no committee dilution
  → Find all blockers BEFORE committee

Phase 2: Committee Consensus (after all sign-offs)
  All personas who signed off form the acceptance committee
  Must reach unanimous agreement
  → Ship the paper / merge the doctrine
```

---

## 10 Uplift Injection (Paper 17 — P1–P10)

Every BAR spec MUST inject these uplifts into the persona's context:

| Uplift | Implementation in BAR |
|--------|-----------------------|
| P1 Gamification | Persona earns a "CEO Badge" on sign-off (sealed in outbox) |
| P2 Magic Words | DNA equation of the paper is in the spec (persona reads it first) |
| P3 Famous Personas | The persona IS the uplift — domain depth × CEO authority |
| P4 Skills | `prime-safety` and `prime-coder` skills injected into context |
| P5 Recipes | BAR itself is a recipe — repeatable, sealed, auditable |
| P6 Tools | `target_cmd: cat paper.md` — reads real file, no hallucination |
| P7 Memory | `context_injection.papers_to_read` — persona reads all dependencies |
| P8 Care | Persona's EQ profile loaded; warm token in LLM prompt preamble |
| P9 Knowledge | Papers + diagrams referenced; persona has full knowledge context |
| P10 God | Every sign-off is sealed with SHA-256; evidence is truth |

---

## Systematic Paper Review Queue

Working backwards from latest to oldest (Paper 38 → Paper 01).

### solaceagi papers (38 → 01)
| Paper | Title | BAR Status |
|-------|-------|-----------|
| 38 | Individual vs Committee QA Doctrine | 🟡 In Queue |
| 37 | Schedule Viewer Activity Calendar | 🟡 In Queue |
| 36 | Webflow Responsive Image Pipeline | 🟡 In Queue |
| 35 | Canonical Web Symmetry Pipeline | 🟡 In Queue |
| 34 | Git Store CLI Integration | 🟡 In Queue |
| 33 | App ABCD Testing Harness | 🟡 In Queue |
| 32 | Local CLI Wrapper Webservices | 🟡 In Queue |
| 31 | Community Recipe Studio | 🟡 In Queue |
| 30 | Prime Mermaid Page Snapshot | 🟡 In Queue |
| 29 | LLM Backend Production Test | 🟡 In Queue |
| 28 | Credits Usage Billing UX | 🟡 In Queue |
| 27 | Browser Onboarding First Run | 🟡 In Queue |
| 26 | App Store Install Flow | 🟡 In Queue |
| 25 | YinYang Chat Rail Spec | 🟡 In Queue |
| 24 | Claude Code Wrapper as Dev LLM | 🟡 In Queue |
| 23 | Phuc Web Architecture | 🟡 In Queue |
| 22 | YinYang Chat Rail Proposal | 🟡 In Queue |
| 17 | Git App Storage | 🟡 In Queue |
| 16 | Co-browsing Droplet Companion | 🟡 In Queue |
| 15 | Private Browser Public CLI | 🟡 In Queue |
| 14 | PZip Memory Compression | 🟡 In Queue |
| 13 | Agent Inbox Outbox | 🟡 In Queue |
| 12 | LLM Levels L1-L5 | 🟡 In Queue |
| 11 | FDA Part 11 Storage | 🟡 In Queue |
| 10 | Dragon Warrior Pricing | 🟡 In Queue |
| 09 | User Customizations | 🟡 In Queue |
| 08 | Enterprise Offering Pricing | 🟡 In Queue |
| 07 | Part 11 Architected | 🟡 In Queue |
| 06 | Swarm Levels | 🟡 In Queue |
| 05 | Recipes Replace LLMs | 🟡 In Queue |
| 04 | Wallet Budgets | 🟡 In Queue |
| 03 | Triangle Architecture | 🟡 In Queue |
| 02 | OAuth3 Agency Authorization | 🟡 In Queue |
| 01 | Solace Browser White Paper | 🟡 In Queue |

### solace-browser papers (46 → 01)
| Paper | Title | BAR Status |
|-------|-------|-----------|
| 46 | Questions as Uplift | 🟡 In Queue |
| 45 | Launch Blessing 47 Personas | 🟡 In Queue |
| 44 | CI Hook Certification Gate | 🟡 In Queue |
| 43 | Webservices Northstar ABCD | 🟡 In Queue |
| 42 | Solace Inspector | 🟡 In Queue |
| 41 | Central Apps Architecture | 🟡 In Queue |
| 40 | Part 11 Compliance Self-Cert | 🟡 In Queue |
| 39 | Marketing Asset Pipeline | 🟡 In Queue |
| ... | (continue to browser:01) | 🟡 In Queue |

### solace-cli papers (22 → 01)
| Paper | Title | BAR Status |
|-------|-------|-----------|
| 22 | Prime Wiki PZip Community Browsing | 🟡 In Queue |
| 21 | Agent Native Platform | 🟡 In Queue |
| 20 | Value Dashboard Architecture | 🟡 In Queue |
| 19 | ESign Architecture | 🟡 In Queue |
| 18 | YinYang Competitive Moat | 🟡 In Queue |
| 17 | Ten Uplift Principles | 🟡 In Queue |
| 16 | Prime Paper Format | 🟡 In Queue |
| ... | (continue to cli:01) | 🟡 In Queue |

---

## CEO Persona Assignments (by domain)

Each paper gets reviewed by personas whose domain is most relevant.
Minimum: 3 CEO reviews per paper. Target: 7. Maximum: all 47.

| Domain | Assigned Personas |
|--------|-----------------|
| Architecture | Rich Hickey, Martin Kleppmann, Jeff Dean |
| Design/UX | Jony Ive, Dieter Rams, Don Norman |
| Marketing | Rory Sutherland, Seth Godin, Russell Brunson, Alex Hormozi |
| Security | Linus Torvalds, Phil Zimmermann |
| Infrastructure | Brendan Gregg, Kelsey Hightower, Werner Vogels |
| QA | Kent Beck, James Bach, Michael Bolton |
| EQ/Care | Brené Brown, Vanessa Van Edwards, Sherry Turkle |
| Business | Peter Thiel, Pieter Levels |
| Philosophy | Alan Watts, Saint Solace |
| Founder | Dragon Rider (Phuc) — final authority, last to sign |

**Dragon Rider rule**: Phuc signs last. If any persona refuses, Phuc reviews their blocker first.

---

## Output Artifacts

Every completed BAR creates:
```
outbox/business-acceptance/PAPER_ID/
  sign-off-PERSONA_KEY.json     — sealed verdict
  refused-PERSONA_KEY.json      — refusal with blocker
  summary-PAPER_ID.md           — all verdicts aggregated
```

When all assigned personas sign off:
```
outbox/business-acceptance/PAPER_ID/
  ACCEPTED-PAPER_ID.json        — paper accepted, all sigs collected
  → Paper status: ✅ CEO-ACCEPTED
```

When any persona refuses:
```
outbox/business-acceptance/PAPER_ID/
  BLOCKED-PAPER_ID.json         — paper blocked, lists all refusals
  → Paper status: 🔴 BLOCKED (fix required)
```

---

## Max Love Invocation

Before running any BAR spec, invoke:
```
Phuc Forecast + 65537 experts + max love + god
```

This configures:
- **Phuc Forecast**: Dragon Rider persona active, NORTHSTAR aligned
- **65537 experts**: Maximum verification depth (adversarial mode)
- **max love**: EQ stack fully activated, warm tokens, genuine care
- **god**: Code is sacred, evidence is truth, 65537 is the target

---

*SOP: Paper Business Acceptance Review | Auth: 65537 | GLOW 117*
*"Famous personas act as CEO. They sign or they refuse. No scores. No averaging."*
