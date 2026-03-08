# Solace Inspector — Master QA Board (Official)
# Replaces: Jira / Asana / Kanban + test cases + specs + open questions
# Authority: 65537 | Date: 2026-03-03 | Belt: Orange → Green

## What This Is

Every `.json` file in this directory = one Jira ticket + test case + spec + question.
Clearing inbox to 100/100 Green = completing the sprint.

## QA Best Practices Applied (From Industry Research, 2025)

### Heuristics Used (Solace Inspector Heuristic Set v2)
- **ARIA-1**: Every interactive element has an accessible name
- **ARIA-2**: Heading hierarchy is correct (H1 → H2 → H3, no skips)
- **SEO-1**: Every page has exactly one H1
- **SEO-2**: robots.txt + sitemap.xml reachable and valid
- **SEO-3**: Meta description present (< 160 chars)
- **BROKEN-1**: No broken images (skip hidden/lightbox placeholders)
- **BROKEN-2**: No 4xx/5xx on internal links
- **UX-1**: Primary CTAs visible above fold
- **UX-2**: Navigation links descriptive (not "Click Here")
- **UX-3**: Forms have labels on all inputs
- **SECURITY-1**: Protected endpoints return 401 without auth (fail-closed)
- **SECURITY-2**: No server version header leaking tech stack
- **SECURITY-3**: 404 returns 404 (not 500) for unknown routes
- **PERF-1**: Page renders in < 3 seconds (visual check via screenshot)
- **CONTENT-1**: No placeholder text ("Lorem ipsum", "TODO", "PLACEHOLDER")
- **CONTENT-2**: No mixed languages in same sentence
- **API-1**: JSON responses have correct Content-Type header
- **API-2**: Auth endpoints return 401 without token, not 403 or 200

### WCAG 2.2 AA Compliance (Active Standard 2025)
- Perceivable: alt text, captions, color contrast
- Operable: keyboard navigation, focus indicators
- Understandable: labels, error messages, consistent navigation
- Robust: valid HTML, ARIA roles, landmark regions

### Context-Driven Testing (James Bach / Michael Bolton, BBST)
- Session-Based Test Management: each spec = one chartered test session
- Every spec has a persona (BBST heuristic lens) and context (charter)
- Findings go in `analysis_response` field of sealed report
- Human approval gate before any fix is deployed

## Spec Categories

| Category | Count | Priority | Persona |
|----------|-------|----------|---------|
| solace-browser web pages | 9 | high | mixed |
| solaceagi web pages (existing) | 11 | high | cem_kaner |
| solaceagi web pages (new) | 10 | normal-critical | mixed |
| API endpoint tests (CLI/curl) | 10 | critical-high | kent_beck |
| Architecture verification (CLI) | 5 | high | mixed |
| Paper claim verification | 5 | high | mixed |
| **Total** | **50** | | |

## Gamification (GLOW Tracker)

Every spec that passes 100/100 Green = +1 GLOW.
Target: All 50 specs Green = GLOW 96–145 marathon.
Belt upgrade: 40 Green specs = Orange belt confirmed.
Dragon's Den unanimous 10/10 = Black belt candidate.

## Persona Committee

| Persona | Lens | When to Use |
|---------|------|-------------|
| James Bach (SBTM) | Rapid test coverage, charters | New feature pages |
| Cem Kaner (BBST) | Systematic heuristics, evidence | Compliance + security |
| Elisabeth Hendrickson | Charter-based exploration, delight | UX + onboarding |
| Kent Beck (TDD) | Minimal tests, test what you fear | API + CLI |
| Michael Bolton (RST) | Rapid Software Testing, oracle problem | Edge cases + content |

## Fix Protocol (HITL Loop)

1. Inspector seals report → `outbox/report-*.json`
2. Agent reads report → writes `agent_analysis_response`
3. Agent proposes fixes → `fix_proposals[]`
4. Human reviews → sets `human_approved: true`
5. Fix deployed → new run → should be Green
