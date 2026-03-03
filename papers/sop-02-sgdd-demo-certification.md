# SOP-02: Style Guide Driven Development + Static Demo Self-Certification
# Version: 1.0 | Effective: 2026-03-03 | Prepared by: Solace AGI
# Cross-ref: Paper 06 (Part 11), Paper 39 (Marketing Pipeline), Paper 40 (Self-Cert)
# Auth: 65537

---

## Purpose

Define the standard procedure for building features using the SGDD (Style Guide
Driven Development) methodology with Phuc's three innovations:
1. Static demo as FDA Part 11 self-certification evidence
2. Demo session as marketing asset pipeline input
3. 13-language-first constraint on all UI components

This SOP establishes that NO backend code is written before the static demo
receives committee sign-off (Anti-Clippy for engineering).

---

## Background: SGDD Industry Standard

Style Guide Driven Development (Bitovi, Pattern Lab, Storybook) creates UI components
in isolation in a living style guide, validates them interactively, and integrates
into the application only after stakeholder approval.

**What Phuc adds on top:**
- Demo screenshot IS the compliance record (FDA Part 11 ALCOA+)
- Demo session generates marketing GIFs (automated pipeline)
- Every text element must have `data-i18n` from the start
- Committee of 7 experts must approve before backend work begins

---

## Phase 1: DISCOVER

### 1.1 Load Context
```bash
/sb-boot <feature-goal>
```
Loads: 41+ prime skills, 5 browser methodology skills, all papers,
all styleguides, all diagrams. Committee activated.

### 1.2 4W+H Probe
Answer before proceeding:
- WHY: Which NORTHSTAR metric?
- WHAT: Exact deliverable, boundaries, non-goals?
- WHEN: Which phase? Dependencies?
- WHO: Committee sign-off required?
- HOW: New page? New component? Extend existing?

### 1.3 Component Inventory Check
```
Open: web/style-guide.html
Check: Does a similar component already exist?
  YES → Reuse + extend in place
  NO  → Create new section in style-guide.html
```

---

## Phase 2: STATIC DEMO (MANDATORY BEFORE BACKEND)

### 2.1 Build in style-guide.html
- Add new section with eyebrow + title + section-copy
- Use ONLY `--sb-*` CSS tokens (no hardcoded colors)
- All interactive states: empty, loading, data, error, success
- Full JS-powered interactivity (no backend calls)
- Add `data-i18n` attribute to EVERY text element

### 2.2 Mobile-First Checklist
- [ ] Renders correctly at 320px viewport
- [ ] Renders correctly at 768px viewport
- [ ] Renders correctly at 1024px viewport
- [ ] ARIA roles on all interactive elements
- [ ] Keyboard navigation works (Tab, Enter, Escape)
- [ ] `prefers-reduced-motion` respected

### 2.3 Committee Review
Open browser → navigate to `/style-guide`
Screenshot the new section:
```bash
curl -X POST http://localhost:9222/api/screenshot \
  -H 'Content-Type: application/json' \
  -d '{"path": "artifacts/sgdd-COMPONENT-YYYY-MM-DD.png"}'
```

Committee must verbally (or in session) approve each:
- [ ] Jon Ive: "Simplicity of purpose confirmed"
- [ ] Rory Sutherland: "Primary action clear and inevitable"
- [ ] Vanessa Van Edwards: "Warmth before transaction"
- [ ] Seth Godin: "Remarkable enough to share"
- [ ] Don Norman: "Error recovery path exists"

**STOP: Backend work is FORBIDDEN until this checklist is complete.**

---

## Phase 3: EVIDENCE CAPTURE (FDA Self-Cert)

### 3.1 Screenshot the Demo
Every static demo session creates ALCOA+ evidence:

| ALCOA+ | How |
|--------|-----|
| Attributable | Session user + timestamp in metadata |
| Legible | Playwright screenshot + Prime Mermaid snapshot |
| Contemporaneous | Auto-timestamped during capture |
| Original | First capture is THE record (immutable) |
| Accurate | SHA-256 hash verified |

```bash
# Store screenshot as self-cert evidence
cp artifacts/sgdd-COMPONENT-YYYY-MM-DD.png \
   marketing/screenshots/YYYY-MM-DD/sgdd-COMPONENT.png
sha256sum marketing/screenshots/YYYY-MM-DD/sgdd-COMPONENT.png >> \
   ~/.solace/audit/sgdd-cert-chain.jsonl
```

### 3.2 Update Paper 40 Self-Cert Record
Add entry to `papers/40-part11-compliance-selfcert.md`:
```markdown
| YYYY-MM-DD | COMPONENT_NAME | Tested in SGDD demo | PASS |
```

---

## Phase 4: MARKETING PIPELINE

### 4.1 Capture Animated GIF
```bash
# Capture frames during demo session
# (Playwright captures each interaction step as PNG)
# Then:
./marketing/scripts/make-gif.sh \
  marketing/frames/COMPONENT-YYYY-MM-DD/ \
  COMPONENT-walkthrough 80
```

### 4.2 Update Gallery
```
Copy GIF → web/images/gallery/ in solaceagi project
Update GALLERY_ITEMS in site_content.py
Commit → Cloud Build → solaceagi.com/gallery auto-updates
```

### 4.3 Draft Social Post
```
YinYang drafts: POST /api/yinyang/chat
  Prompt: "Write a Twitter post for this COMPONENT feature demo"
  Output → marketing/social/drafts/YYYY-MM-DD/COMPONENT.md
```

---

## Phase 5: TRANSLATE (13 Languages)

### 5.1 Add Keys to en.json
For every new `data-i18n` key in the static demo:
```json
"component_key": "English value"
```

### 5.2 Translate with Swarm Agents
```
Agent 1 (parallel): es, vi, zh, pt, fr, ja
Agent 2 (parallel): de, ar, hi, ko, id, ru
```

### 5.3 Verify
```bash
grep -l "component_key" app/locales/yinyang/*.json | wc -l
# Expected: 13 (all 13 locales)
python3 -c "import json; [json.load(open(f)) for f in \$(ls app/locales/yinyang/*.json)]"
# Expected: no errors
```

---

## Phase 6: BUILD (SGDD Plug & Play)

Only after Phases 1-5 are complete:

### 6.1 Backend Implementation
- Add server endpoint in `web/server.py`
- Wire frontend to real data
- Remove fake/placeholder data from style-guide demo

### 6.2 Integration
- Copy component HTML to actual page
- Connect to real API endpoint
- Verify in browser against static demo baseline

### 6.3 Commit
```bash
git add .
git commit -m "feat: COMPONENT_NAME — SGDD phase complete
  - Static demo approved by committee (YYYY-MM-DD)
  - FDA self-cert: marketing/screenshots/YYYY-MM-DD/sgdd-COMPONENT.png
  - Marketing GIF: marketing/gifs/COMPONENT-walkthrough.gif
  - 22 i18n keys × 13 locales translated
  Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Quality Gates (Fail-Closed)

| Gate | Requirement | Failure Action |
|------|-------------|---------------|
| G1 | Static demo complete and working | Stop. Complete demo first. |
| G2 | Committee sign-off received | Stop. Get approval. |
| G3 | FDA screenshot captured + SHA-256 | Stop. Capture evidence. |
| G4 | All text has data-i18n attr | Stop. Add missing attrs. |
| G5 | All 13 locales translated | Stop. Run swarm agent. |
| G6 | No hardcoded colors in CSS | Stop. Replace with --sb-* tokens. |
| G7 | prefers-reduced-motion supported | Stop. Add media query. |

---

## Deviations

Deviations from this SOP require written justification and committee approval.
Emergency deviation: document in commit message with `[SOP-DEVIATION: reason]`.

---

## References

- SGDD Methodology: Bitovi (bitovi.com/blog/style-guide-driven-development)
- Atomic Design: Brad Frost (atomicdesign.bradfrost.com)
- Storybook.js (storybook.js.org) — component gallery paradigm
- FDA 21 CFR Part 11: Paper 06 + Paper 40
- Marketing Pipeline: Paper 39
- /sb-boot command: `.claude/commands/sb-boot.md`

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2026-03-03 | Initial SOP — SGDD + FDA cert + marketing pipeline |

---

**DNA:** `sgdd = styleguide × demo × committee × fda_cert × marketing × i18n_13`
**Gate:** No backend before committee approves static demo. Non-negotiable.
