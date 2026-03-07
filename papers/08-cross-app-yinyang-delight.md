# Paper 08: Cross-App Orchestration + Yinyang Universal Interface + Delight Engine
# DNA: `apps compose via outbox→inbox; yinyang = single UI; delight = warm_token → effect`
**Date:** 2026-03-01 | **Auth:** 65537 | **Rung:** 641
**Status:** CANONICAL
**Depends on:** Paper 02 (Inbox/Outbox), Paper 04 (Yinyang), Paper 07 (Budget)

---

## 1. Executive Summary

This paper defines three interlocking systems:

1. **Cross-App Orchestration** — apps discover, compose, and delegate to partner apps through inbox/outbox, with full Part 11 evidence across multi-app workflows
2. **Yinyang Universal Interface** — Yinyang is the ONLY user interface for everything: task execution, customer support, app requests, alerts, and casual conversation
3. **Delight Engine** — JavaScript plugin system for celebrations, humor, seasonal effects, and emotional warmth, triggered by warm tokens from the Triple-Twin smalltalk phase

**Core Insight:** Users never leave Yinyang. Yinyang handles it or escalates it. The escalation itself is invisible — user talks to Yinyang, Yinyang talks to solaceagi.com support API.

---

## 2. Cross-App Architecture

### 2.1 Partner App Discovery

Every app declares which other apps it can compose with:

```yaml
# ~/.solace/apps/gmail-inbox-triage/manifest.yaml
partners:
  produces_for:
    - google-drive-saver      # "Save attachment to Drive"
    - slack-triage             # "Notify team in Slack"
    - calendar-brief           # "Schedule follow-up"
  consumes_from:
    - morning-brief            # "Include email summary"
    - linkedin-outreach        # "Draft reply from LinkedIn lead"
  discovers:
    - category: communications # can find any comms app
    - tag: email               # can find any email-related app
```

### 2.2 Cross-App Message Protocol

Apps communicate ONLY through outbox → inbox file drops. Never direct function calls.

```
APP A (gmail-inbox-triage)
  outbox/suggestions/notify-slack.json
    → { "target_app": "slack-triage",
        "action": "send_message",
        "channel": "#inbox-alerts",
        "content": "3 urgent emails need attention",
        "evidence_ref": "run_abc123" }

ORCHESTRATOR picks up outbox file
  → validates target_app is in partners.produces_for
  → validates budget (cross-app budget gate B6)
  → drops into target app inbox

APP B (slack-triage)
  inbox/requests/from-gmail-inbox-triage-run_abc123.json
    → reads request, executes, writes evidence back
```

### 2.3 Orchestrator Apps

Coordination-only apps that work exclusively through inbox/outbox:

```yaml
# morning-brief (orchestrator app)
type: orchestrator
orchestrates:
  - gmail-inbox-triage    # "What's in my email?"
  - calendar-brief        # "What's on my calendar?"
  - github-issue-triage   # "What needs review?"
  - slack-triage          # "Any urgent Slack?"

workflow:
  1. Trigger all 4 apps in parallel (budget-gated)
  2. Collect outbox results from each
  3. LLM ONCE: synthesize into single morning brief
  4. Write to outbox/reports/morning-brief-{date}.md
  5. Surface in Yinyang bottom rail
```

### 2.4 Required App Directory Structure

Every app MUST have this structure (enforced by `manifest validate`):

```
~/.solace/apps/{app-id}/
  manifest.yaml              # metadata + partners + scopes
  recipe.json                # execution steps
  budget.json                # per-action limits
  diagrams/                  # REQUIRED: Mermaid FSM diagrams
    workflow.md              # app workflow (AI reads this)
    data-flow.md             # what data goes where
    partner-contracts.md     # cross-app interfaces
  inbox/
    prompts/                 # custom instructions
    templates/               # reusable templates
    assets/                  # files for AI
    policies/                # hard rules
    datasets/                # reference data
    requests/                # incoming cross-app requests
    conventions/             # app-specific config
      config.yaml            # app settings
      defaults.yaml          # default values
      examples/              # example files
  outbox/
    previews/                # pending approval
    drafts/                  # work products
    reports/                 # analyses
    suggestions/             # cross-app suggestions
    runs/{run-id}/           # evidence bundles
```

### 2.5 Diagram-First App Development

AI discovers what to do by reading diagrams:

```
1. AI reads diagrams/workflow.md → understands app FSM
2. AI reads diagrams/data-flow.md → understands I/O
3. AI reads diagrams/partner-contracts.md → knows who to call
4. AI reads inbox/conventions/config.yaml → gets user prefs
5. AI reads inbox/conventions/defaults.yaml → gets fallbacks
6. AI executes recipe.json with budget.json gates
```

### 2.6 Cross-App Evidence (Part 11)

Multi-app workflows produce a single evidence chain:

```
workflow_evidence_chain.jsonl:
  { run_id: "wf_123", step: 1, app: "gmail-inbox-triage", action: "scan", ... }
  { run_id: "wf_123", step: 2, app: "gmail-inbox-triage", action: "classify", ... }
  { run_id: "wf_123", step: 3, app: "slack-triage", action: "send_message", ... }
  { run_id: "wf_123", step: 4, app: "google-drive-saver", action: "upload", ... }
  { run_id: "wf_123", step: 5, app: "morning-brief", action: "synthesize", ... }
```

Each entry references `prev_hash` from the previous step, creating an unbroken chain across apps.

### 2.7 Budget Gate B6: Cross-App Delegation

New budget gate for cross-app calls:
- B6: Target app installed AND in partners list AND target budget > 0
- Cross-app calls inherit MIN(source_budget, target_budget) — MIN-cap principle
- Orchestrator apps have their own budget separate from child app budgets

---

## 3. Yinyang Universal Interface

### 3.1 Yinyang Is the Only Interface

Users NEVER need to leave Yinyang for anything:

| User Need | Yinyang Handles |
|-----------|----------------|
| Run an app | "Triage my Gmail" → triggers execution |
| Check status | "What's running?" → shows active runs |
| Approve/reject | Preview in bottom rail with buttons |
| Customer support | "I want a LinkedIn app" → creates support ticket |
| Request new app | "Can you build X?" → evaluates, fixes or escalates |
| Report bug | "Gmail triage missed my VIP emails" → bug ticket |
| Customize app | "Change Gmail to only scan last 2 hours" → edits config |
| Settings | "Turn on screenshots" → updates settings.json |
| Alerts | Solaceagi pushes alerts → Yinyang surfaces them |
| Small talk | "How's it going?" → warm, witty response |
| Billing | "What's my usage?" → shows cost summary |

### 3.2 Yinyang Fix vs Escalate Rules

```
CAN FIX (Yinyang handles directly):
  - Edit inbox/conventions/config.yaml (user prefs)
  - Edit inbox/prompts/ files (custom instructions)
  - Toggle settings in ~/.solace/settings.json
  - Explain what an app does (read diagrams/)
  - Show run history and evidence
  - Re-run a failed task
  - Answer questions about the platform
  - Small talk and emotional support

MUST ESCALATE (sends to solaceagi.com support API):
  - New app requests ("build me a TikTok app")
  - Recipe changes ("make Gmail triage faster")
  - Bug reports with evidence attached
  - Security concerns
  - Billing disputes
  - Feature requests
  - Anything requiring code changes

ESCALATION FLOW:
  User → Yinyang → POST /api/v1/support/ticket
    → { type: "app_request|bug|feature|billing",
        context: { current_page, session_transcript, evidence_refs },
        priority: "low|medium|high" }
  Yinyang confirms: "I've sent this to the team. Ticket #1234."

  solaceagi.com can push updates back:
  GET /api/v1/support/tickets/{id}/status → Yinyang shows update
```

### 3.3 Yinyang Customization

Users customize Yinyang through inbox:

```
~/.solace/yinyang/
  personality.yaml           # tone, humor level, formality
  greetings.json            # custom greetings (override defaults)
  favorites.json            # user's preferred jokes/facts
  blocked_topics.json       # topics to avoid
  custom_commands.json      # user-defined shortcuts
```

Example personality.yaml:
```yaml
tone: warm_friendly          # warm_friendly | professional | casual | minimal
humor_level: high            # off | low | medium | high
formality: casual            # formal | casual | technical
name: "Yin"                  # custom name (default: Yinyang)
pronouns: "they/them"        # customizable
idle_behavior: facts         # jokes | facts | tips | silent
greeting_style: playful      # playful | professional | minimal
```

### 3.4 Alert Queue (solaceagi → Yinyang)

solaceagi.com can push alerts to users:

```
GET /api/v1/alerts/pending → returns queued alerts
POST /api/v1/alerts/{id}/dismiss → mark as read

Alert types:
  - app_update: "Gmail Inbox Triage v1.2 available"
  - support_reply: "Your ticket #1234 has been resolved"
  - usage_warning: "You've used 80% of your monthly budget"
  - new_app: "New app available: YouTube Script Writer"
  - system: "Scheduled maintenance tonight at 2am"
  - celebration: "You've completed 100 runs! 🎉"
```

Yinyang surfaces alerts in bottom rail on next interaction. Never interrupts. Never auto-expands for low-priority alerts.

---

## 4. Delight Engine

### 4.1 Architecture

```
yinyang-delight.js (core library, ~8KB gzipped)
  ├── confetti.js       → canvas-confetti (CDN, 4.2KB)
  ├── emoji.js          → js-confetti (CDN, 2.4KB)
  ├── toast.js          → notyf (CDN, 3KB)
  ├── typing.js         → typed.js (CDN, 4KB)
  ├── sounds.js         → Web Audio API (0KB, native)
  ├── seasonal.js       → holiday detection + themed effects
  ├── easter-eggs.js    → Konami code + hidden triggers
  └── plugins/          → user-downloadable extensions
```

### 4.2 Warm Token → Delight Trigger

The Triple-Twin Phase 1 warm_token drives delight effects:

```javascript
// warm_token from CPU/LLM smalltalk twin
const warmToken = { mode: "celebrate", trigger: "user_achieved_milestone" };

// Delight engine responds to warm_token
YinyangDelight.respond(warmToken);
// → fires confetti + success toast + celebration sound
```

Warm token → effect mapping:

| warm_token.mode | Visual Effect | Sound | Toast |
|-----------------|--------------|-------|-------|
| celebrate | confetti burst | fanfare chime | "Achievement unlocked!" |
| encourage | sparkles | gentle ding | "Keep going, you've got this." |
| birthday | emoji rain (🎂🎁🎈) | birthday tune | "Happy birthday!" |
| holiday | seasonal theme | themed sound | holiday greeting |
| warm_friendly | subtle glow | none | warm greeting |
| neutral_professional | none | none | none |
| suppress_humor | none | none | none |

### 4.3 Key Moment Triggers

```javascript
YinyangDelight.on('first_run_complete', () => {
  confetti({ particleCount: 100, spread: 70 });
  toast.success("Your first run is complete!");
});

YinyangDelight.on('milestone_100_runs', () => {
  jsConfetti.addConfetti({ emojis: ['🏆', '💯', '⭐', '🚀'] });
  toast.success("100 runs! You're a power user.");
});

YinyangDelight.on('holiday_detected', (holiday) => {
  jsConfetti.addConfetti({ emojis: holiday.emojis });
  toast.open({ message: holiday.greeting, background: holiday.color });
});
```

Built-in moments:
- first_run_complete
- first_app_installed
- milestone_10_runs, milestone_100_runs, milestone_1000_runs
- streak_7_days, streak_30_days
- birthday (from user profile)
- holiday_detected (auto-detect from date)
- support_ticket_resolved
- new_app_available
- budget_saved (showed user cost savings)

### 4.4 Jokes & Facts Database

```
data/default/yinyang/
  jokes.json             # 50+ curated tech jokes
  facts.json             # 50+ fun facts
  smalltalk.json         # warm greetings + conversation starters
  holidays.json          # holiday dates + themed content
  celebrations.json      # achievement messages + effects
```

Yinyang draws from these during idle moments, warm_token=warm_friendly, or when user asks "tell me a joke."

Selection algorithm:
1. Check user's `favorites.json` — prefer liked content
2. Check `blocked_topics.json` — skip avoided topics
3. Check time-of-day — morning greetings vs evening wind-down
4. Check day-of-week — Friday energy vs Monday encouragement
5. Never repeat within same session
6. Track which jokes/facts user has seen (learned_smalltalk.jsonl)

### 4.5 Plugin System

Users can install delight plugins:

```yaml
# ~/.solace/yinyang/plugins/star-wars-mode.yaml
name: Star Wars Mode
type: delight_plugin
triggers:
  celebrate: { effect: "lightsaber_ignite", sound: "imperial_march" }
  encourage: { message: "Do or do not. There is no try." }
  greeting: { pool: ["May the Force be with you.", "I have a good feeling about this."] }
```

Plugin registry at solaceagi.com/store/plugins. Community-contributed. Reviewed before publishing.

### 4.6 Seasonal Themes

Auto-detected from system date:

| Date Range | Theme | Emojis | Color |
|-----------|-------|--------|-------|
| Dec 20-Jan 2 | Winter Holidays | ❄️🎄⭐🎅 | #c41e3a |
| Jan 25-Feb 2 | Lunar New Year | 🧧🐉🎆🏮 | #ff0000 |
| Feb 14 | Valentine's Day | ❤️💕💖💗 | #ff69b4 |
| Mar 17 | St. Patrick's Day | ☘️🍀🌈💚 | #008000 |
| Oct 25-Nov 1 | Halloween | 🎃👻🦇🕸️ | #ff6600 |
| Nov (4th Thu US) | Thanksgiving | 🦃🍂🌽🥧 | #8B4513 |
| User birthday | Birthday | 🎂🎁🎈🥳 | #ff69b4 |

---

## 5. Core Apps (Day One)

### 5.1 Must-Ship Apps (10)

| App ID | Category | Type | Safety | Partners |
|--------|----------|------|--------|----------|
| gmail-inbox-triage | Communications | Standard | B | morning-brief, slack-triage, google-drive-saver |
| calendar-brief | Productivity | Standard | A | morning-brief, gmail-inbox-triage |
| focus-timer | Productivity | Standard | A | calendar-brief, morning-brief |
| github-issue-triage | Engineering | Standard | B | slack-triage, morning-brief |
| slack-triage | Communications | Standard | B | morning-brief, gmail-inbox-triage |
| linkedin-outreach | Sales | Standard | C | gmail-inbox-triage |
| google-drive-saver | Productivity | Standard | A | all (universal save target) |
| youtube-script-writer | Marketing | Standard | B | google-drive-saver |
| twitter-monitor | Marketing | Standard | A | slack-triage, morning-brief |
| reddit-scanner | Engineering | Standard | A | slack-triage, morning-brief |

### 5.2 No-API Exclusive Apps (5)

Web-native only — no vendor API keys needed:

| App ID | Platform | What It Does |
|--------|----------|-------------|
| whatsapp-responder | WhatsApp Web | Read/reply to messages |
| amazon-price-tracker | Amazon.com | Track prices, alert on drops |
| instagram-poster | Instagram.com | Schedule and post content |
| twitter-poster | Twitter/X.com | Compose and post tweets |
| linkedin-poster | LinkedIn.com | Create posts, engage |

### 5.3 Orchestrator Apps (3)

| App ID | Orchestrates | Output |
|--------|-------------|--------|
| morning-brief | gmail + calendar + github + slack | Daily summary report |
| weekly-digest | morning-brief × 5 + trends | Weekly summary with trends |
| lead-pipeline | linkedin-outreach + gmail + calendar | CRM-lite lead tracking |

### 5.4 Day-One App Matrix

```
Communications:    gmail-inbox-triage, slack-triage, whatsapp-responder
Productivity:      calendar-brief, focus-timer, google-drive-saver, morning-brief, weekly-digest
Sales & Marketing: linkedin-outreach, youtube-script-writer, lead-pipeline
Engineering:       github-issue-triage, reddit-scanner
Social Media:      twitter-monitor, twitter-poster, instagram-poster, linkedin-poster
Shopping:          amazon-price-tracker

Total: 18 apps (10 standard + 5 no-API exclusive + 3 orchestrators)
```

---

## 6. Invariants

1. Apps communicate ONLY through outbox → inbox file drops, never direct calls
2. Cross-app evidence chains are unbroken — every step references prev_hash
3. Orchestrator apps never have direct web access — they only read child outboxes
4. Yinyang is the ONLY user-facing interface for all platform interactions
5. Yinyang NEVER auto-approves anything (Anti-Clippy law)
6. Yinyang escalates what it cannot fix — never pretends to handle what it can't
7. Delight effects are warm_token-driven, never random or disruptive
8. Jokes/facts never repeat within a session
9. All plugins are reviewed before store publishing
10. Required diagrams/ dir in every app — AI reads diagrams to understand workflow

---

## Forbidden Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Apps calling each other via direct function invocation | Breaks the outbox→inbox file-drop protocol and makes workflows unauditable |
| Yinyang auto-approving actions without user click | Violates Anti-Clippy law and removes the consent gate from the execution chain |
| Delight effects firing randomly without a warm_token trigger | Creates noise that trains users to ignore celebrations, defeating the purpose |

## 7. Cross-References

| Section | solaceagi Papers | solace-cli Papers |
|---------|-----------------|-------------------|
| Cross-App | papers/13-agent-inbox-outbox | Paper 04 (Triple-Twin) |
| Yinyang UI | papers/22+25 (Yinyang) | Diagram 13 (Yinyang FSM) |
| Delight | — (new) | Paper 04 (warm tokens) |
| Evidence | papers/07+11 (Part 11) | Diagram 03 (Evidence) |
| Budget B6 | papers/04+19 (Wallet) | Paper 14 (Dispatch) |
| EQ System | — | Personas: eq/* (VVE, Brown, Ekman) |
