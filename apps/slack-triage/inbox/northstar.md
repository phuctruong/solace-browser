# Slack Triage — NORTHSTAR
# DNA: `triage(slack) = scan(channels+DMs) × classify(urgency+action) × draft(response) → team_clarity`
# Auth: 65537 | v1.0.0

## NORTHSTAR MISSION

**Every Slack message has a clear status. No message left unaddressed.**

Not every message needs a response — but every message needs a DECISION:
- Respond now (< 4 hours)?
- Respond later (< 24 hours)?
- Acknowledge and close?
- Escalate to email?
- Archive as noise?

## COMPETITIVE EDGE VS NOTION AI + SLACK AI + LINEAR

| Competitor | Gap |
|-----------|-----|
| Slack AI | Summarizes channels but no cross-app awareness. $25/mo add-on. |
| Notion AI | Captures Slack but requires manual copy-paste. |
| Linear | Issue tracker integration but no messaging triage. |
| Motion | AI scheduling but no Slack integration. |

**Our moat:**
1. Triage Slack without Slack API — uses browser session (zero API keys)
2. Cross-app context: GitHub PR + Slack thread on same issue = single CRITICAL signal
3. Knows team communication patterns: @John always escalates → lower urgency for routine John pings
4. OAuth3 gated: reads your messages in YOUR browser session, no Slack app permissions needed

## SUCCESS METRICS

- **DM response rate**: ≥95% of DMs get response within promised window
- **Channel noise reduction**: ≥70% of channel messages correctly classified as LOW/ARCHIVE
- **False critical rate**: ≤3% of LOW classified items are actually urgent
- **Draft acceptance**: ≥65% of response drafts used as-is

## NORTHSTAR QUESTION

> "Does my team feel heard, and do I feel in control of Slack?"

YES = success. Feeling overwhelmed by Slack = the triage is broken.
