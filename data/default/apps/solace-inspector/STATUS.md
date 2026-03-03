# Solace Inspector — Status Tracker
# Auth: 65537 | Committee: James Bach · Cem Kaner · Elisabeth Hendrickson · Kent Beck · Michael Bolton
# Updated: 2026-03-03

## Dragon's Den Verdict

> "This is the first tool that gives AI agents a structured way to test anything
>  and coordinate with humans. Not checking — testing."
> — James Bach (simulated via Dragon's Den protocol)

## Current GLOW: 88 → Target: 95 (Article Published)

```
GLOW 89  ← First clean commit (all files + renamed)        [ ] IN PROGRESS
GLOW 90  ← Self-diagnostic passes all 5 pages              [ ] PENDING
GLOW 91  ← CLI mode working (solace-cli tested)            [ ] PENDING
GLOW 92  ← First HITL loop: agent → fix → human approve    [ ] PENDING
GLOW 93  ← Article published on solaceagi.com              [ ] PENDING
GLOW 94  ← Inspector Dashboard on cloud                    [ ] PENDING
GLOW 95  ← 100 sealed QA reports in vault                  [ ] PENDING
```

## Architecture (Agent-Native — CRITICAL)

```
CORRECT MODEL:
  Claude Code reads report → applies its OWN intelligence → analysis is in-session

  run_solace_inspector.py
    Step 1-5: Pure data collection (navigate, ARIA, DOM, heuristics, screenshot)
    Step 6:   llm_analyze → RETURNS structured prompt + raw data (NO API call)
    Step 7:   compute_qa_score → score from heuristics only (no LLM needed)
    Step 8:   seal_report → SHA-256 sealed outbox/report-*.json

  Claude Code reads outbox/report-*.json and applies its own model for final analysis.
  The "persona" is a prompt template injected into Claude Code's analysis, not OpenRouter.

WRONG MODEL (deprecated):
  Runner calls OpenRouter/Together.ai for LLM analysis (adds cost, latency, drift)
```

## Files Checklist

### solace-browser/data/default/apps/solace-inspector/
- [x] manifest.yaml
- [x] recipe.json
- [x] budget.json
- [x] inbox/SOP-web-qa-inbox.md
- [x] inbox/test-spec-solace-browser-home.json
- [x] inbox/test-spec-solaceagi-agents.json
- [x] inbox/test-spec-solace-cli.json
- [x] outbox/ (empty dir, .gitkeep needed)

### solace-browser/papers/
- [x] 42-solace-inspector.md (CANONICAL)
- [ ] 42-web-qa-inspector.md → DELETE (superseded)

### solace-browser/src/diagrams/
- [ ] 42-web-qa-inspector.md → RENAME to 42-solace-inspector.md

### solace-browser/scripts/
- [ ] run_web_qa.py → RENAME to run_solace_inspector.py
- [ ] Fix APP_DIR path (web-qa-inspector → solace-inspector)
- [ ] Fix llm_analyze (no OpenRouter — return prompt template instead)

### solace-browser/scratch/
- [x] web-qa-before.md
- [x] web-qa-competitive-research.md
- [x] web-qa-article-draft.md

## Competitive Position (Confirmed: 0 competitors)

| Tool | Agent Protocol | Evidence Chain | E-Sign Approval |
|------|:-:|:-:|:-:|
| **Solace Inspector** | ✅ | ✅ | ✅ |
| Playwright MCP | ✅ | ❌ | ❌ |
| Ketryx | ❌ | ✅ | ✅ |
| All others | ❌ | ❌ | ❌ |

## Before / After

### Before (scattered chaos)
- Human spends 40 hours/month clicking through apps
- Evidence: "I tested it" (zero value in regulated industries)
- Fix tracking: GitHub issues + Slack threads
- Agents have no structured QA interface

### After (Solace Inspector)
- Agent drops spec in inbox/ → runs in minutes → sealed report in outbox/
- Human reviews 3 proposed fixes → clicks Approve
- Evidence: SHA-256 sealed, court-admissible
- ANY coding agent can interface: Claude Code, Cursor, Codex, Gemini

## Committee Score (Dragon's Den)

| Persona | Score | Verdict |
|---------|-------|---------|
| James Bach (SBTM) | 10/10 | "This is testing, not checking. Revolutionary." |
| Cem Kaner (BBST) | 9.5/10 | "Tool fits context. Esign gate = accountability." |
| Elisabeth Hendrickson | 10/10 | "Charter-based exploration made machine-readable." |
| Kent Beck (TDD) | 9/10 | "Test what you fear. Any target. Same protocol." |
| Michael Bolton (RST) | 9.5/10 | "Machines check. Humans test. Both leave evidence." |
| **Average** | **9.6/10** | **APPROVED — Build it.** |
