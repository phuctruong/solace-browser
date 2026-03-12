# GitHub Issue Triage — NORTHSTAR
# DNA: `triage(github) = scan(issues+PRs) × classify(severity+blocker+type) × action → zero_stale`
# Auth: 65537 | v1.0.0

## NORTHSTAR MISSION

**No stale issues. No missed PR reviews. Developer flow state protected.**

GitHub notifications are signal — but they're also noise. The triage's job:
separate the signal (blocked PR, security bug, critical user-facing issue)
from the noise (auto-assigned bots, low-priority feature requests, CI flakes).

## COMPETITIVE EDGE VS LINEAR / JIRA AI / GITHUB COPILOT

| Competitor | Gap |
|-----------|-----|
| Linear | Great UX but requires migrating from GitHub. $8/mo. Separate tool. |
| Jira AI | Enterprise only. Expensive. Not GitHub-native. |
| GitHub Copilot Chat | Answers code questions but no triage automation. |
| Release Radar | Newsletter, not actionable triage. |

**Our moat:**
1. No GitHub API tokens — uses your existing browser session
2. Cross-repo awareness: PR in repo-A blocked by issue in repo-B = linked CRITICAL
3. Evidence chain: every review/close action is tamper-evident
4. Developer context: knows your codebase patterns (your yinyang server = port 8888, never 9222)

## SUCCESS METRICS

- **Stale issues >2 weeks**: 0 (triage flags, suggests close or delegate)
- **PR review turnaround**: ≤24 hours for CRITICAL, ≤72h for HIGH
- **CI flake classification**: ≥80% of CI flakes auto-classified LOW (not CRITICAL)
- **Security issue SLA**: 100% of security labels → CRITICAL within 1 hour

## NORTHSTAR QUESTION

> "Does every developer know what to work on next, and is nothing blocking them?"

YES = success. Unclear priorities + stale PRs = triage is failing.
