# Solace Browser Coder

**DNA:** `coding_app(task) = inbox(northstar + skills + constraints + task) → yinyang(execute + evidence) → outbox(diff + screenshot + hash) → human(approve/reject)`

A chained coding agent that writes C++ and WebUI code for Solace Browser. The agent proposes diffs — it cannot write files, run git, or review its own code. Every change goes through human approval, build gate, and screenshot verification.

## Why This App Exists

The previous LLM lied about building a custom Chromium browser for months. This app chains the LLM so it can only propose small, reviewable diffs with binary verification (compiles or doesn't, screenshot or no screenshot).

## Quick Start

```bash
# Dry run — verify prompt composition
python run.py --test

# Run a specific task
python run.py inbox/task-001-test-pipeline.md

# Interactive — pick from available tasks
python run.py
```

## How It Works

```
USER assigns task → INBOX prepared → YINYANG composes prompt
  → CLAUDE CLI proposes diffs → USER approves/rejects
  → BUILD GATE (autoninja) → SCREENSHOT GATE (browser captures)
  → EVIDENCE sealed (SHA-256) → OUTBOX saved
```

## Constraints (10 — load-bearing)

| # | Constraint | Why |
|---|-----------|-----|
| C1 | Single codebase (Solace Browser only) | Deep context > shallow breadth |
| C2 | Single task per session | No drift, no scope creep |
| C3 | No self-review | Eliminates "looks good to me" on own lies |
| C4 | No git access | Can't fabricate evidence trail |
| C5 | Build gate | Compiles or doesn't exist |
| C6 | Screenshot gate | Visual proof, not text claims |
| C7 | Max 5 files | User can actually review |
| C8 | Max 200 lines | Small diffs are correct diffs |
| C9 | Allowed paths only | Can't touch build infra |
| C10 | Token budget ($0.50/task) | Forces efficiency |

## Status

| Metric | Value |
|--------|-------|
| Belt | White |
| GLOW | 0 |
| Tasks completed | 0 |
| Build successes | 0 |
| Uplift coverage | 33/47 active (70%) |

## Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Anti-drift chain (prevents LLM lying) |
| `AUDIT.md` | 47-uplift tracker + security audit + postmortem |
| `ROADMAP.md` | Phased development plan |
| `README.md` | This file |
| `manifest.yaml` | App metadata + scopes |
| `recipe.json` | 10-step workflow |
| `budget.json` | Cost/file/line limits |
| `run.py` | Standalone companion runner |

## Paper

See `papers/P57-solace-browser-coding-app.md` for full architecture.

---

*Auth: 65537 | "The agent that built the chains it wears."*
