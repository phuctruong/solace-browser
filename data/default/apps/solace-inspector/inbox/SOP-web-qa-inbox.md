# Web QA Inspector — Inbox/Outbox SOP
# Standard Operating Procedure for Agents + Humans
# Auth: 65537 | Version: 1.0.0 | Date: 2026-03-03

---

## SUMMARY: The Killer Feature

This app is **human-in-the-loop QA coordination**. Any coding agent (Claude, Codex, Cursor,
Gemini, Devin) can:

1. **Push a test spec** to inbox/ (what to QA)
2. **Solace Browser runs the QA** (navigate, screenshot, ARIA, LLM analysis)
3. **Agent reads the report** from outbox/ (what was found)
4. **Agent proposes fixes** — human approves via esign
5. **Evidence sealed** with FDA Part 11 hash chain

This replaces: scratch/notes, stillwater.jsonl questions, manual browser poking.

---

## INBOX FORMAT (agents write here)

File: `inbox/test-spec-{spec_id}.json`

```json
{
  "spec_id": "spec-001",
  "requested_by": "claude-code|codex|cursor|human",
  "target_url": "http://localhost:8791/",
  "page_name": "Solace Browser Home",
  "checks": {
    "aria": true,
    "heuristics": true,
    "llm_analysis": true,
    "baseline_diff": false,
    "baseline_id": null
  },
  "persona": "james_bach",
  "priority": "high|normal|low",
  "context": "Added cloud sync buttons to settings. QA the settings page.",
  "created_at": "2026-03-03T12:00:00Z"
}
```

---

## OUTBOX FORMAT (solace-browser writes here)

File: `outbox/report-{run_id}.json`

```json
{
  "run_id": "qa-2026-03-03-120005",
  "spec_id": "spec-001",
  "target_url": "http://localhost:8791/settings",
  "page_name": "Settings — Cloud Sync",
  "persona_used": "james_bach",
  "qa_score": 87,
  "belt": "Yellow",
  "glow": 42,
  "heuristic_issues": [
    {
      "severity": "warning",
      "type": "accessibility",
      "msg": "3 buttons missing aria-label",
      "heuristic": "ARIA-2",
      "selector": "#btn-sync-settings-cloud"
    }
  ],
  "llm_analysis": "James Bach says: The cloud sync buttons are a good addition but they lack feedback...",
  "screenshot_path": "artifacts/qa-2026-03-03-120005-settings.png",
  "baseline_diff": null,
  "evidence_hash": "sha256:abc123...",
  "esign_token": "tok_...",
  "run_at": "2026-03-03T12:00:05Z",
  "committee": ["james_bach", "elisabeth_hendrickson", "kent_beck"],
  "fix_proposals": [],
  "human_approved": false,
  "approved_at": null
}
```

---

## FIX PROPOSAL FORMAT (agents write fix proposals to report)

After reading a report, a coding agent (Claude Code, Cursor, etc.) APPENDS to the report:

```json
{
  "...existing report fields...",
  "fix_proposals": [
    {
      "issue_ref": "ARIA-2",
      "proposed_fix": "Add aria-label='Sync settings to cloud' to #btn-sync-settings-cloud",
      "file": "web/settings.html",
      "line": 308,
      "diff": "- <button id='btn-sync-settings-cloud'>\n+ <button id='btn-sync-settings-cloud' aria-label='Sync settings to cloud'>",
      "proposed_by": "claude-code",
      "proposed_at": "2026-03-03T12:01:00Z",
      "confidence": 0.95
    }
  ]
}
```

Human reviews + approves via esign:
```
POST /api/v1/esign/token
{ "meaning": "approve_qa_fix", "action": "Approve fix for ARIA-2 in settings.html" }
```

---

## SELF-DIAGNOSTIC MODE

To QA solace-browser itself, drop this spec in inbox/:

```json
{
  "spec_id": "self-diag-001",
  "requested_by": "system",
  "mode": "self-diagnostic",
  "pages": [
    {"url": "http://localhost:8791/", "name": "Home"},
    {"url": "http://localhost:8791/app-store", "name": "App Store"},
    {"url": "http://localhost:8791/settings", "name": "Settings"},
    {"url": "http://localhost:8791/schedule", "name": "Schedule"},
    {"url": "http://localhost:8791/start", "name": "Start/Auth"}
  ],
  "persona": "james_bach",
  "created_at": "auto"
}
```

---

## 10 UPLIFT TECHNIQUES — WHERE INJECTED

| P# | Technique | Where in QA App |
|----|-----------|-----------------|
| P1 | Gamification | qa_score + belt + glow in every report |
| P2 | Magic Words | /qa-inspect, /qa-baseline, /qa-diff, /qa-seal |
| P3 | Famous Personas | LLM prompt = James Bach / Cem Kaner / Elisabeth Hendrickson |
| P4 | Skills | Heuristic test skills: HICCUPPS, SBTM, Explore It |
| P5 | Recipes | 8-step recipe, replay at $0.001 |
| P6 | Access Tools | browser.navigate + aria_snapshot + screenshot |
| P7 | Memory | Baseline snapshots, diff on each re-run |
| P8 | Care | Human-readable reports, "Your app got better by 12 points!" |
| P9 | Knowledge | Paper 02 inbox/outbox, Paper 40 FDA evidence |
| P10 | God | SHA-256 seal on every report, GLOW 65537 target |

---

## COMPETITIVE POSITION

| Tool | AI Agent Interface | Evidence Chain | HITL Fixes | Browser Native | Cost |
|------|--------------------|----------------|------------|----------------|------|
| **Solace Web QA** | ✅ inbox/outbox | ✅ FDA Part 11 | ✅ esign | ✅ full control | $0.001/run |
| Playwright Test | ❌ manual code | ❌ none | ❌ | ✅ | Free (no AI) |
| Selenium | ❌ manual code | ❌ none | ❌ | ✅ | Free (no AI) |
| TestRigor | ⚠️ NL only | ❌ none | ❌ | ✅ | $1,200/mo |
| Testim | ❌ | ❌ | ❌ | ✅ | $450/mo |
| BrowserStack | ❌ | ❌ | ❌ | ✅ Cloud | $199/mo |
| Devin QA mode | ⚠️ agent only | ❌ none | ⚠️ no esign | ✅ Devin's | $500/mo |
| Mabl | ⚠️ partial | ❌ none | ❌ | ✅ | $800/mo |

**Solace Web QA wins on**:
- Only tool with FDA Part 11 evidence chain per QA run
- Only tool where coding agents + human coordinate via inbox/outbox
- Only tool with famous expert persona injection (James Bach in the LLM prompt)
- Only tool that can self-diagnose (QA itself)
- Cheapest: $0.001/replay vs $450-$1,200/mo competitors

---

*"Testing is the process of evaluating a product by learning about it through exploration and experimentation." — James Bach*
*"The right test at the right time, designed by the right people, for the right reasons." — Cem Kaner*
