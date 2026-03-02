# Paper 09: YinYang Tutorial, Fun Pack Standard, OAuth3 Leave-App, Agent Notification API, MCP Server, YinYang Chat
**Date:** 2026-03-02 | **Auth:** 65537 | **Rung:** 641
**Status:** CANONICAL
**Applies to:** solace-browser
**Depends on:** Paper 04 (Yinyang Dual Rail), Paper 07 (Budget), Paper 08 (Delight Engine)
**Cross-ref:** solaceagi/papers/22+25 (Yinyang), solace-cli/papers/04 (Triple-Twin)

---

## 1. Executive Summary

This paper defines six interlocking systems that complete the Yinyang user-facing layer:

1. **YinYang Tutorial Popup** — 5-step guided tour for first-time users, 13 locales, Anti-Clippy compliant
2. **Fun Pack Standard** — downloadable personality content packs (jokes, facts, seasonal) with JSON format spec and store integration
3. **OAuth3 Leave-App Confirmation** — fail-closed consent gate triggered when the browser is about to navigate to any OAuth3 authorization redirect
4. **Agent Notification API** — push-based SSE channel for agent-to-Yinyang notifications with typed priority queue
5. **MCP Server Standard** — stdio JSON-RPC 2.0 transport exposing 7 browser tools to Claude and any MCP-capable agent
6. **YinYang Chat** — OpenRouter-powered conversational layer with browser state context, powering the settings page "Ask YinYang" section

**Core Insight:** These six systems share one architecture invariant — they all flow through Yinyang. The tutorial teaches, Fun Packs warm, OAuth3 confirmation protects, notifications inform, MCP connects, Chat answers. Yinyang is the single point of presence.

---

## 2. YinYang Tutorial Popup

### 2.1 Purpose and Trigger

First-time users land on a capable browser with 18 apps, OAuth3, and a dual-rail interface they have never seen. Without guided onboarding, the blank state is intimidating. The tutorial is a 5-step modal that runs exactly once, teaches the essential concepts, and ends with delight.

**Trigger conditions (both must be true):**
- URL matches `home.html` or `start.html`
- `localStorage.getItem('sb_tutorial_v1')` is `null` or missing

**Skip conditions (any one prevents auto-trigger):**
- `localStorage.getItem('sb_tutorial_v1')` is `"done"` or `"skipped"`
- URL has query param `?tutorial=skip`
- Personality mode is `minimal` (respects Anti-Clippy law #4)

### 2.2 Storage Contract

```javascript
// Written on SKIP:
localStorage.setItem('sb_tutorial_v1', 'skipped');

// Written on COMPLETE (step 5 final button):
localStorage.setItem('sb_tutorial_v1', JSON.stringify({
  status: 'done',
  completed_at: new Date().toISOString(),
  locale: navigator.language,
  version: 1
}));

// Reset (for testing or user request via Yinyang):
localStorage.removeItem('sb_tutorial_v1');
// → triggers tutorial on next home.html load
```

Key `sb_tutorial_v1` is versioned. A future `sb_tutorial_v2` can re-trigger for new users without affecting users who completed v1.

### 2.3 Modal Architecture

```
┌────────────────────────────────────────────────────────────┐
│  [Skip tutorial]                              Step 1 of 5  │
│                                                            │
│            ┌──────────────────────────┐                   │
│            │   [YinYang rotating GIF] │                   │
│            │      ☯ (animated)        │                   │
│            └──────────────────────────┘                   │
│                                                            │
│         Welcome to Solace Browser                          │
│         Your AI-powered browser that works for you.        │
│                                                            │
│  ●●○○○                              [Next →]              │
└────────────────────────────────────────────────────────────┘
```

- Modal width: 480px (centered, semi-transparent backdrop)
- Progress dots: filled circle = visited, empty circle = upcoming
- [Skip tutorial] link: top-right, always visible — never hidden
- [Next] / [Back] / [Get started!] navigation buttons
- Keyboard: `→` or `Enter` = Next, `←` = Back, `Escape` = Skip

### 2.4 Five Steps (Content Specification)

#### Step 1: Welcome

```
Title:    "Welcome to Solace Browser"
Visual:   yinyang-spin.gif (128×128px, looping, 12fps)
Body:     "I'm YinYang — your AI browser companion.
          I help you automate repetitive tasks, protect your
          privacy, and stay in control of every action I take.
          Let me show you the essentials."
Buttons:  [Next →]
```

#### Step 2: Browser Control

```
Title:    "I can navigate, click, and read the web"
Visual:   Animated demo panel (320×180px) showing:
          - Browser navigating to gmail.com
          - Click highlight animation on inbox
          - Screenshot thumbnail captured
Body:     "Using real browser automation, I can triage your
          inbox, fill forms, check prices, and take
          screenshots — all on your local machine.
          Nothing leaves your computer without your approval."
Demo:     Live preview (optional): navigate localhost:9222
          to a safe demo page and take a screenshot
Buttons:  [← Back]  [Next →]
```

#### Step 3: OAuth3 Safety

```
Title:    "I never act without your approval"
Visual:   Approval dialog mockup (static PNG):
          ┌──────────────────────────────────┐
          │ ☯ Preview: Triage Gmail Inbox    │
          │                                  │
          │ Steps: Scan → Classify → Archive │
          │ Cost: ~$0.003 | Time: ~12s       │
          │                                  │
          │  [✓ Approve]    [✗ Cancel]       │
          └──────────────────────────────────┘
Body:     "Before I touch anything, I show you exactly what
          I'm about to do, how much it costs, and how long
          it takes. You click Approve. Then I act.
          I will never silently execute anything."
Buttons:  [← Back]  [Next →]
```

#### Step 4: App Store

```
Title:    "18 apps, one click to automate"
Visual:   App store grid thumbnail (320×180px):
          3×3 grid showing app icons:
          Gmail | Calendar | GitHub
          Slack | LinkedIn | Drive
          YouTube | Twitter | Morning Brief
Body:     "Open the App Store to browse 18 pre-built
          automations across email, social, productivity,
          and engineering. Install in one click.
          No API keys required for most apps."
Buttons:  [← Back]  [Next →]
```

#### Step 5: Fun Mode

```
Title:    "One more thing..."
Visual:   Confetti burst animation (canvas-confetti, 1.5s)
          + emoji rain: 🎉 ☯ 🚀 ⭐ 💡
Body:     [Joke drawn from default Fun Pack — see Section 3]
          Example: "Why do programmers prefer dark mode?
                   Because light attracts bugs. 🐛"
          ──
          "You're ready. Let's get started."
Buttons:  [← Back]  [🚀 Let's get started!]
```

On clicking `[🚀 Let's get started!]`:
1. Write `sb_tutorial_v1 = done` to localStorage
2. Fire `YinyangDelight.on('tutorial_complete')` → confetti burst
3. Dismiss modal
4. Focus bottom rail chat input
5. Pre-fill chat: `"What can you help me with today?"`

### 2.5 Internationalization (13 Locales)

All 5 step strings are stored in the i18n pipeline. Locale key prefix: `tutorial.*`.

```json
// web/i18n/en.json (excerpt)
{
  "tutorial.step1.title": "Welcome to Solace Browser",
  "tutorial.step1.body": "I'm YinYang — your AI browser companion...",
  "tutorial.step2.title": "I can navigate, click, and read the web",
  "tutorial.step2.body": "Using real browser automation...",
  "tutorial.step3.title": "I never act without your approval",
  "tutorial.step3.body": "Before I touch anything...",
  "tutorial.step4.title": "18 apps, one click to automate",
  "tutorial.step4.body": "Open the App Store to browse 18 pre-built...",
  "tutorial.step5.title": "One more thing...",
  "tutorial.step5.cta": "🚀 Let's get started!",
  "tutorial.skip": "Skip tutorial"
}
```

Locale detection order:
1. `?lang=` URL param
2. `localStorage.getItem('sb_locale')`
3. `navigator.language` (strip region: `en-US` → `en`)
4. Fallback: `en`

Supported locales: `en, es, vi, zh, pt, fr, ja, de, ar, hi, ko, id, ru`

Step 5 joke is drawn from the locale-specific Fun Pack (`default-{locale}.json`). Falls back to `default-en.json` if locale pack not installed.

### 2.6 Anti-Clippy Compliance

| Anti-Clippy Law | Tutorial Implementation |
|----------------|------------------------|
| Summon don't ambush | Only triggers on home.html/start.html, never mid-session |
| Boundary moments | Fires at the single best moment: very first page load |
| Skip at any point | [Skip tutorial] always visible; Escape key works every step |
| Learn from rejections | `skipped` state stored; never re-shows without user request |
| Expertise detection | If personality mode = `minimal` → tutorial auto-skipped |
| Honest about what we are | Step 3 shows the real approval dialog, not a promise |

### 2.7 Re-trigger (User Request)

User can re-trigger at any time by asking Yinyang:
```
User: "Show me the tutorial again"
Yinyang: "Sure! I'll show it on next page load."
→ localStorage.removeItem('sb_tutorial_v1')
→ Yinyang: "Reload the page to start the tutorial."
```

### 2.8 Invariants

1. Tutorial fires AT MOST ONCE per browser install (localStorage persists)
2. Step 5 joke always comes from a Fun Pack (never hardcoded)
3. Skip is always accessible — never require completing all 5 steps
4. Confetti fires ONLY on Step 5 completion, never on skip
5. Tutorial state never syncs to cloud — purely local UX state
6. Locale auto-detected; never ask user to choose language before tutorial

---

## 3. Fun Pack Standard

### 3.1 Purpose

The Delight Engine (Paper 08) established jokes and facts as core delight content. Fun Packs formalize the downloadable format, locale support, community contribution, and App Store integration. A Fun Pack is a versioned JSON bundle containing jokes, facts, seasonal greetings, and emoji configurations — portable, reviewable, and community-authored.

### 3.2 JSON Format Specification

```json
{
  "_meta": {
    "id": "default-en",
    "name": "Default English Pack",
    "version": "1.0.0",
    "locale": "en",
    "author": "solace-browser",
    "license": "CC-BY-4.0",
    "created_at": "2026-03-01",
    "updated_at": "2026-03-01",
    "description": "100 jokes + 100 facts for the default English experience",
    "tags": ["default", "family-friendly", "tech"],
    "content_rating": "G",
    "sha256": "sha256:COMPUTED_AT_BUILD"
  },
  "jokes": [
    {
      "id": "j001",
      "text": "Why do programmers prefer dark mode? Because light attracts bugs.",
      "tags": ["tech", "coding"],
      "emoji": "🐛",
      "warmth": "medium"
    },
    {
      "id": "j002",
      "text": "A SQL query walks into a bar, walks up to two tables and asks: 'Can I join you?'",
      "tags": ["tech", "database"],
      "emoji": "🗄️",
      "warmth": "medium"
    }
  ],
  "facts": [
    {
      "id": "f001",
      "text": "Honey never spoils. Archaeologists have found 3,000-year-old honey in Egyptian tombs that was still edible.",
      "tags": ["nature", "food"],
      "emoji": "🍯",
      "source": "Smithsonian Magazine"
    },
    {
      "id": "f002",
      "text": "There are more possible chess games than atoms in the observable universe.",
      "tags": ["math", "games"],
      "emoji": "♟️",
      "source": "Shannon's Chess Theorem"
    }
  ],
  "greetings": [
    {
      "id": "g001",
      "time_of_day": "morning",
      "text": "Good morning! Ready to tackle the day?",
      "emoji": "☀️"
    },
    {
      "id": "g002",
      "time_of_day": "evening",
      "text": "Wrapping up for the day? I hope it went well.",
      "emoji": "🌙"
    }
  ],
  "seasonal": [
    {
      "id": "s001",
      "holiday": "new_year",
      "date_range": ["Jan-01", "Jan-07"],
      "greeting": "Happy New Year! Wishing you an amazing year ahead.",
      "emojis": ["🎆", "🥂", "✨", "🎉"],
      "color": "#ffd700"
    }
  ]
}
```

**Field rules:**

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `_meta.id` | string | yes | `{name}-{locale}` slug, URL-safe |
| `_meta.version` | semver | yes | Bump minor for content additions |
| `_meta.locale` | BCP-47 | yes | `en`, `zh`, `ar`, etc. |
| `_meta.content_rating` | G/PG/PG-13 | yes | Default pack must be G |
| `_meta.sha256` | string | yes | Computed at pack build; verified on install |
| `jokes[].warmth` | low/medium/high | yes | Maps to delight engine warm_token |
| `jokes[].tags` | string[] | yes | Used for blocked_topics.json filtering |
| `facts[].source` | string | no | Encouraged for credibility |

### 3.3 Default Packs

**Default pack per locale (100 jokes + 100 facts + 20 greetings + 12 seasonal):**

```
data/fun-packs/
  default-en.json     ← English (required, ships with browser)
  default-es.json     ← Spanish
  default-vi.json     ← Vietnamese
  default-zh.json     ← Chinese (Simplified)
  default-pt.json     ← Portuguese
  default-fr.json     ← French
  default-ja.json     ← Japanese
  default-de.json     ← German
  default-ar.json     ← Arabic
  default-hi.json     ← Hindi
  default-ko.json     ← Korean
  default-id.json     ← Indonesian
  default-ru.json     ← Russian
```

`default-en.json` is bundled with the browser installation. All other locale packs are downloaded on first locale detection or user request. Size target: < 50KB per pack (uncompressed).

### 3.4 Pack Loading Logic

```javascript
// FunPackManager.js

class FunPackManager {
  constructor(locale = 'en') {
    this.locale = locale;
    this.loadedPacks = [];
    this.seen = new Set();  // tracks seen joke/fact IDs this session
  }

  async load() {
    // 1. Load locale pack if available, else fall back to en
    const localePack = await this.loadPack(`default-${this.locale}`);
    if (!localePack && this.locale !== 'en') {
      await this.loadPack('default-en');
    }
    // 2. Load any community packs user has installed
    const installed = JSON.parse(localStorage.getItem('sb_fun_packs') || '[]');
    for (const packId of installed) {
      await this.loadPack(packId);
    }
  }

  async loadPack(packId) {
    // Check local cache first (IndexedDB)
    let pack = await db.funPacks.get(packId);
    if (!pack) {
      // Download from server
      const res = await fetch(`/api/fun-packs/${packId}`);
      if (!res.ok) return null;
      pack = await res.json();
      // Verify sha256 before storing
      const verified = await verifySha256(pack);
      if (!verified) throw new Error(`Fun pack ${packId} failed integrity check`);
      await db.funPacks.put(pack, packId);
    }
    this.loadedPacks.push(pack);
    return pack;
  }

  getJoke(filter = {}) {
    // Merge all loaded packs' jokes
    const allJokes = this.loadedPacks.flatMap(p => p.jokes);
    // Filter by blocked topics (from ~/.solace/yinyang/blocked_topics.json)
    const blocked = this.getBlockedTopics();
    const eligible = allJokes.filter(j =>
      !this.seen.has(j.id) &&
      !j.tags.some(t => blocked.includes(t))
    );
    if (eligible.length === 0) {
      this.seen.clear();  // reset seen set — all jokes exhausted
      return this.getJoke(filter);
    }
    const joke = eligible[Math.floor(Math.random() * eligible.length)];
    this.seen.add(joke.id);
    return joke;
  }

  getFact(filter = {}) {
    const allFacts = this.loadedPacks.flatMap(p => p.facts);
    const blocked = this.getBlockedTopics();
    const eligible = allFacts.filter(f =>
      !this.seen.has(f.id) &&
      !f.tags.some(t => blocked.includes(t))
    );
    if (eligible.length === 0) {
      this.seen.clear();
      return this.getFact(filter);
    }
    const fact = eligible[Math.floor(Math.random() * eligible.length)];
    this.seen.add(fact.id);
    return fact;
  }

  getGreeting(timeOfDay) {
    const allGreetings = this.loadedPacks.flatMap(p => p.greetings || []);
    const matching = allGreetings.filter(g => g.time_of_day === timeOfDay);
    if (matching.length === 0) return null;
    return matching[Math.floor(Math.random() * matching.length)];
  }

  getSeasonalContent() {
    const today = new Date();
    const allSeasonal = this.loadedPacks.flatMap(p => p.seasonal || []);
    return allSeasonal.find(s => isInDateRange(today, s.date_range)) || null;
  }
}
```

### 3.5 Server Endpoints

**GET /api/fun-packs**
Returns the catalog of available packs.

```json
// Response
{
  "packs": [
    {
      "id": "default-en",
      "name": "Default English Pack",
      "version": "1.0.0",
      "locale": "en",
      "size_bytes": 42000,
      "content_rating": "G",
      "tags": ["default", "family-friendly", "tech"],
      "download_url": "/api/fun-packs/default-en",
      "sha256": "sha256:abc..."
    },
    {
      "id": "star-wars-en",
      "name": "Star Wars Fan Pack",
      "version": "1.2.0",
      "locale": "en",
      "size_bytes": 18000,
      "content_rating": "G",
      "tags": ["star-wars", "sci-fi", "movies"],
      "download_url": "/api/fun-packs/star-wars-en",
      "sha256": "sha256:def..."
    }
  ],
  "total": 47
}
```

**GET /api/fun-packs/{pack_id}**
Downloads the full pack JSON. Served with `Cache-Control: max-age=86400`.

```bash
curl /api/fun-packs/default-en
# Returns: full pack JSON (see Section 3.2 schema)
```

**POST /api/fun-packs/download**
Installs a community pack by URL. Validates sha256 before storing.

```json
// Request
{
  "url": "https://community.solaceagi.com/packs/star-wars-en-v1.2.0.json",
  "expected_sha256": "sha256:def..."
}

// Response (success)
{
  "status": "installed",
  "pack_id": "star-wars-en",
  "version": "1.2.0",
  "joke_count": 80,
  "fact_count": 40
}

// Response (sha256 mismatch)
{
  "status": "error",
  "code": "SHA256_MISMATCH",
  "message": "Pack integrity check failed. Download aborted."
}
```

### 3.6 App Store Integration

Fun Packs appear in the App Store under a dedicated category:

```
App Store → Fun & Personality
  ├── Default English Pack (installed)
  ├── Default Spanish Pack
  ├── Default Vietnamese Pack
  │   ...
  ├── Star Wars Fan Pack (community)
  ├── Cat Facts Pack (community)
  ├── Science Nerds Pack (community)
  └── [Browse community packs →]
```

Each pack card shows: name, locale, content rating, joke count, fact count, install status, sha256 badge.

Community packs are submitted via pull request to `github.com/solaceagi/fun-packs`. Review criteria:
- Content rating G (default store) or PG (adult store, opt-in)
- No marketing content, no product placement
- No topics on blocked list (political, religious controversy, explicit)
- sha256 computed and verified

### 3.7 User Favorites + Blocked Topics

```javascript
// ~/.solace/yinyang/favorites.json
{
  "liked_jokes": ["j001", "j047", "j088"],
  "liked_facts": ["f023", "f061"],
  "disliked_jokes": ["j055"],    // never show again
  "disliked_facts": []
}

// ~/.solace/yinyang/blocked_topics.json
{
  "blocked_tags": ["politics", "religion", "explicit"]
}
```

Selection priority: user favorites > recency filter > random from eligible pool.

### 3.8 Invariants

1. `default-en.json` ships with every browser installation — never requires network on first run
2. Every pack install verifies sha256 before writing to IndexedDB
3. No joke or fact repeats within a session (seen Set cleared only on exhaustion)
4. `blocked_topics.json` filters apply across ALL loaded packs
5. Community packs are reviewed before store listing (no auto-publish)
6. Pack schema version is in `_meta.version`; breaking schema changes increment major version

---

## 4. OAuth3 Leave-App Confirmation Standard

### 4.1 Purpose

When the user (or an agent acting on their behalf) is about to navigate away from the current app to an OAuth3 authorization endpoint, the browser must pause and show a confirmation gate. This protects against:
- Confused deputy attacks (a recipe silently delegating more scope than the user intended)
- Accidental over-authorization (user clicks a link without realizing it grants access)
- Budget surprises (user doesn't know what the token will cost)

This gate is a hard boundary. It is not a soft warning.

### 4.2 Trigger Detection

```javascript
// OAuth3LeaveAppGuard.js

const OAUTH3_URL_PATTERNS = [
  /solaceagi\.com\/auth\//,
  /\/oauth3\/authorize/,
  /\/oauth\/authorize/,
  /[?&]response_type=code/,
  /[?&]client_id=sw_/,         // Stillwater OAuth3 client
  /[?&]scope=[^&]*oauth3/i
];

function isOAuth3Redirect(url) {
  return OAUTH3_URL_PATTERNS.some(pattern => pattern.test(url));
}

// Hook into Playwright navigation events
page.on('framenavigated', async (frame) => {
  if (frame !== page.mainFrame()) return;
  const url = frame.url();
  if (isOAuth3Redirect(url)) {
    await page.goBack();                      // immediately navigate back
    await showOAuth3ConfirmationGate(url);    // then show gate
  }
});
```

Navigation is reversed FIRST before showing the gate. The gate is not a modal on top of the OAuth3 page — the user never sees the OAuth3 page until they confirm.

### 4.3 Confirmation Gate UI

```
┌─────────────────────────────────────────────────────────────┐
│  ☯ OAuth3 Authorization Request                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  The app wants to connect to:                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 🔒 solaceagi.com/auth/authorize                      │   │
│  │ Client: Gmail Inbox Triage (v1.2.0)                  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Permissions requested:                                     │
│    ✉️  gmail.read.inbox        — Read your inbox            │
│    📁  gmail.archive           — Archive emails             │
│    ⭐  gmail.labels.write      — Apply labels               │
│                                                             │
│  What this DOES:   Lets Yinyang read and organize email     │
│  What this CANNOT: Send email, delete email, access Drive   │
│                                                             │
│  Your benefits:                                             │
│    ✓ Automated inbox triage (save 45 min/week)             │
│    ✓ Revoke access any time in Settings → Tokens           │
│    ✓ Audit log of every action (Part 11 evidence)          │
│                                                             │
│  Current budget: $4.32 remaining this month                 │
│  Estimated token cost: $0.003 per triage run               │
│  [Adjust budget ▼]                                          │
│                                                             │
│  Auto-cancels in: 15s ████████████████░░░░░░ [cancel now]  │
│                                                             │
│  [✗ Cancel]          [⚙️ Adjust Budget]   [✓ Proceed]       │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Scope Display Rules

Each scope line shows:
- Icon (emoji derived from scope category)
- Scope string (`gmail.read.inbox`)
- Human-readable description (one line, no jargon)

Scope categories and icons:

| Scope prefix | Icon | Category |
|-------------|------|----------|
| `gmail.*` | ✉️ | Email |
| `calendar.*` | 📅 | Calendar |
| `github.*` | 🐙 | Code |
| `drive.*` | 📁 | Storage |
| `slack.*` | 💬 | Messaging |
| `linkedin.*` | 💼 | Professional |
| `payment.*` | 💳 | Financial |
| `oauth3.*` | 🔑 | Authorization |
| `stillwater.*` | ☯ | Platform |

Human-readable descriptions are stored in `data/scope-descriptions/{locale}.json`:

```json
{
  "gmail.read.inbox": "Read your inbox",
  "gmail.archive": "Archive emails",
  "gmail.labels.write": "Apply labels",
  "gmail.send.email": "Send email on your behalf",
  "calendar.read": "Read your calendar",
  "calendar.write": "Create and modify events"
}
```

### 4.5 Budget Inline Adjustment

When user clicks `[Adjust Budget]`, the gate expands inline (no navigation):

```
▼ Adjust Budget

Current LLM budget per day:   [  $0.50  ] ← editable input
Max runs per day:              [  10     ] ← editable input

[Cancel adjustment]  [Save and proceed]
```

On `[Save and proceed]`:
1. Write new budget to `~/.solace/apps/{app-id}/budget.json`
2. Log budget change to evidence chain
3. Continue with OAuth3 authorization

On `[Cancel adjustment]`: collapse adjustment panel, return to gate.

### 4.6 Fail-Closed Countdown

**15-second countdown with auto-cancel** (fail-closed):

```javascript
// OAuth3 gate countdown
let countdown = 15;
const timer = setInterval(() => {
  countdown--;
  updateCountdownUI(countdown);
  if (countdown <= 0) {
    clearInterval(timer);
    cancelOAuth3Authorization();    // auto-cancel, log to evidence
    showToast('Authorization cancelled (timeout). No action was taken.');
  }
}, 1000);

// Cancel timer on any user interaction:
//   [Proceed] → proceed
//   [Cancel] → cancel
//   [Adjust Budget] → pause countdown (reset to 30s on open)
document.querySelector('[data-oauth3-gate]').addEventListener('click', () => {
  clearInterval(timer);
});
```

Countdown pauses when [Adjust Budget] panel is open. Resets to 30s when panel closes.

Auto-cancel is NOT silent. It writes to evidence:
```json
{
  "event": "oauth3_gate_auto_cancelled",
  "reason": "countdown_expired",
  "url": "https://solaceagi.com/auth/authorize?...",
  "scopes_requested": ["gmail.read.inbox"],
  "timeout_seconds": 15
}
```

### 4.7 Outcomes and Evidence

Every gate event (proceed, cancel, timeout) is written to the evidence chain:

```json
// Proceed
{
  "event": "oauth3_gate_approved",
  "url": "https://solaceagi.com/auth/authorize",
  "client_id": "gmail-inbox-triage",
  "scopes_approved": ["gmail.read.inbox", "gmail.archive", "gmail.labels.write"],
  "budget_at_approval": { "llm_day_cents": 50 },
  "ts": "2026-03-02T10:00:00Z",
  "user_action": "explicit_click"
}

// Cancel
{
  "event": "oauth3_gate_cancelled",
  "reason": "user_clicked_cancel",
  "ts": "2026-03-02T10:00:08Z"
}
```

### 4.8 Settings Override

Users can configure gate behavior in `~/.solace/settings.json`:

```json
{
  "oauth3_gate": {
    "enabled": true,            // false = disable gate (not recommended)
    "countdown_seconds": 15,    // 5-60 range
    "trusted_clients": [        // skip gate for these client_ids
      "gmail-inbox-triage"
    ],
    "always_show_budget": true
  }
}
```

`trusted_clients` still shows the gate for untrusted clients. It skips the gate ONLY for clients explicitly listed. Trusted status is earned per client — not a global bypass.

### 4.9 Invariants

1. Navigation is reversed BEFORE the gate is shown — user never sees the OAuth3 page first
2. Countdown is always shown — no silent indefinite wait
3. Countdown expires = auto-cancel (fail-closed)
4. Every gate outcome (proceed, cancel, timeout) written to evidence chain
5. Budget inline edit writes to budget.json immediately — not deferred
6. No scope can be hidden — all requested scopes shown, no collapsing
7. `trusted_clients` requires explicit opt-in per client, never a global bypass

---

## 5. Agent Notification API Standard

### 5.1 Purpose

Agents running in the background (recipe execution, cross-app orchestration, cloud tasks) need to surface status, alerts, and results to the user through Yinyang. The Agent Notification API is the single channel for this. Agents push; Yinyang pulls via SSE. The user sees notifications in the bottom rail without opening any other UI.

### 5.2 Endpoints

**POST /api/yinyang/notify**

Agent pushes a notification into the queue.

```json
// Request
{
  "type": "task_complete",
  "message": "Gmail Inbox Triage finished. 42 emails processed, 5 starred, 28 archived.",
  "priority": "normal",
  "agent_id": "gmail-inbox-triage",
  "run_id": "run_abc123",
  "actions": [
    { "label": "View Report", "url": "/apps/gmail-inbox-triage/runs/run_abc123" },
    { "label": "Undo", "action": "undo_run", "run_id": "run_abc123" }
  ],
  "metadata": {
    "emails_processed": 42,
    "cost_cents": 3,
    "duration_ms": 11420
  }
}

// Response
{
  "status": "queued",
  "notification_id": "notif_xyz456",
  "queued_at": "2026-03-02T10:00:11Z"
}
```

**GET /api/yinyang/events**

Server-Sent Events stream. Yinyang connects once; notifications arrive in real time.

```
// SSE stream format
Content-Type: text/event-stream
Cache-Control: no-cache

data: {"id":"notif_xyz456","type":"task_complete","message":"...","priority":"normal","ts":"2026-03-02T10:00:11Z"}

data: {"id":"notif_abc789","type":"budget_warning","message":"You've used 80% of today's LLM budget.","priority":"high","ts":"2026-03-02T10:01:00Z"}
```

**GET /api/yinyang/status**

Returns queue state (used by Yinyang to show badge count in bottom rail).

```json
{
  "queue_depth": 3,
  "unread_count": 2,
  "notifications": [
    {
      "id": "notif_xyz456",
      "type": "task_complete",
      "message": "Gmail Inbox Triage finished...",
      "priority": "normal",
      "read": false,
      "ts": "2026-03-02T10:00:11Z"
    }
  ],
  "last_checked": "2026-03-02T09:59:00Z"
}
```

**POST /api/yinyang/notifications/{id}/read**

Mark a notification as read. No body required.

```json
// Response
{ "status": "marked_read", "id": "notif_xyz456" }
```

### 5.3 Notification Type Taxonomy

| type | Priority default | Bottom rail behavior | Delight effect |
|------|-----------------|---------------------|----------------|
| `task_complete` | normal | Show summary + action buttons | warm_friendly glow |
| `task_failed` | high | Auto-expand rail, show error | none |
| `task_blocked` | high | Auto-expand rail, show block reason | none |
| `budget_warning` | high | Show badge + amber top rail | none |
| `budget_exhausted` | critical | Auto-expand, block further runs | none |
| `app_update` | low | Badge only, no auto-expand | none |
| `support_reply` | normal | Show reply, link to ticket | warm_friendly glow |
| `milestone` | normal | Expand + confetti | celebrate confetti |
| `system` | low | Badge only | none |
| `celebration` | normal | Auto-expand + confetti | celebrate confetti |

Priority levels: `critical > high > normal > low`

### 5.4 Bottom Rail Display

Yinyang renders notifications at the top of the expanded bottom rail:

```
┌────────────────────────────────────────────────────────────┐
│ ☯ Yinyang | $3.44 | Yellow Belt | [●2]              [▼]   │
│────────────────────────────────────────────────────────────│
│ [task_complete] Gmail Inbox Triage — done              ✓   │
│   42 emails processed · $0.03 · 11.4s                     │
│   [View Report]  [Undo]                                    │
│                                                            │
│ [budget_warning] You've used 80% of today's LLM budget.   │
│   $0.40 of $0.50 used today.  [Adjust budget]       [✗]  │
│                                                            │
│────────────────────────────────────────────────────────────│
│ User: What just happened?                                  │
│ Yinyang: Your Gmail triage completed...                    │
│ [Type a message...                                ] [Send] │
└────────────────────────────────────────────────────────────┘
```

Notification badge `[●2]` shows unread count in collapsed rail. Clicking expands rail.

`critical` notifications auto-expand the bottom rail regardless of user preference. All others respect the collapsed/expanded preference.

### 5.5 Agent Push Authentication

Agents must include a `sw_sk_` token in the Authorization header:

```bash
curl -X POST http://localhost:9222/api/yinyang/notify \
  -H "Authorization: Bearer sw_sk_browser_xyz789" \
  -H "Content-Type: application/json" \
  -d '{ "type": "task_complete", "message": "...", "priority": "normal", "agent_id": "gmail-inbox-triage" }'
```

The browser validates that `agent_id` matches an installed app in `~/.solace/apps/`. Unknown agent IDs are rejected:

```json
{
  "status": "error",
  "code": "UNKNOWN_AGENT",
  "message": "Agent 'unknown-app' is not installed. Notification rejected."
}
```

### 5.6 SSE Connection Management

```javascript
// YinyangNotificationClient.js

class YinyangNotificationClient {
  connect() {
    this.source = new EventSource('/api/yinyang/events', {
      withCredentials: true
    });

    this.source.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      this.handleNotification(notification);
    };

    this.source.onerror = () => {
      // Reconnect with exponential backoff: 1s, 2s, 4s, 8s, max 30s
      this.reconnectDelay = Math.min((this.reconnectDelay || 1000) * 2, 30000);
      setTimeout(() => this.connect(), this.reconnectDelay);
    };

    this.source.onopen = () => {
      this.reconnectDelay = 1000;  // reset on successful connect
    };
  }

  handleNotification(notification) {
    // 1. Add to queue
    this.queue.push(notification);
    // 2. Update badge count
    updateBadgeCount(this.queue.filter(n => !n.read).length);
    // 3. Auto-expand if critical
    if (notification.priority === 'critical') expandBottomRail();
    // 4. Fire delight effect if applicable
    const delightType = NOTIFICATION_DELIGHT_MAP[notification.type];
    if (delightType) YinyangDelight.fire(delightType);
  }
}
```

### 5.7 Invariants

1. SSE is the ONLY channel for agent-to-Yinyang communication — no polling, no WebSocket
2. Unknown `agent_id` values are rejected — no anonymous notifications
3. `critical` priority always auto-expands bottom rail (overrides user preference)
4. Notifications queue persists across page reloads (IndexedDB backed)
5. Notification count shown in badge; Yinyang never interrupts user mid-chat to deliver normal/low priority
6. Mark-as-read requires explicit user interaction — never auto-cleared

---

## 6. MCP Server Standard

### 6.1 Purpose

Model Context Protocol (MCP) is the emerging standard for connecting AI agents to external tools via a stdio JSON-RPC 2.0 transport. The Solace Browser MCP server exposes 7 browser tools to any MCP-capable agent (Claude Desktop, Claude Code, custom agents). This makes the solace-browser a first-class MCP tool provider.

### 6.2 Transport

- **Protocol:** stdio JSON-RPC 2.0
- **Transport:** stdin/stdout (spawned subprocess)
- **Routes to:** `localhost:9222` (Playwright headless browser server)
- **Process:** `solace-mcp-server` binary (Node.js wrapper)

### 6.3 Server Manifest

```json
{
  "name": "solace-browser",
  "version": "1.0.0",
  "description": "Solace Browser — AI-controlled browser with OAuth3, budget gates, and Part 11 evidence",
  "protocol": "mcp",
  "transport": "stdio",
  "tools": [
    "navigate", "click", "fill", "screenshot",
    "snapshot", "evaluate", "aria_snapshot"
  ]
}
```

### 6.4 The 7 Tools

**Tool 1: navigate**

Navigate the browser to a URL.

```json
{
  "name": "navigate",
  "description": "Navigate the browser to a URL. Returns page title and final URL after redirect.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "url": {
        "type": "string",
        "description": "Full URL to navigate to (must include https://)"
      },
      "wait_until": {
        "type": "string",
        "enum": ["load", "domcontentloaded", "networkidle"],
        "default": "load",
        "description": "When to consider navigation complete"
      }
    },
    "required": ["url"]
  }
}

// Example response
{
  "url": "https://mail.google.com/mail/u/0/#inbox",
  "title": "Inbox - Gmail",
  "status": 200,
  "elapsed_ms": 1240
}
```

**Tool 2: click**

Click a DOM element by CSS selector or ARIA role.

```json
{
  "name": "click",
  "description": "Click a DOM element. Supports CSS selectors and ARIA role+name targeting.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "selector": {
        "type": "string",
        "description": "CSS selector (e.g., 'button.compose') or ARIA label (e.g., 'role=button[name=Compose]')"
      },
      "timeout_ms": {
        "type": "integer",
        "default": 5000,
        "description": "Max wait for element to appear (ms)"
      }
    },
    "required": ["selector"]
  }
}

// Example response
{
  "clicked": true,
  "selector": "button[aria-label='Compose']",
  "element_text": "Compose",
  "elapsed_ms": 340
}
```

**Tool 3: fill**

Fill a form input field.

```json
{
  "name": "fill",
  "description": "Fill an input, textarea, or contenteditable element with text.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "selector": {
        "type": "string",
        "description": "CSS selector or ARIA label targeting the input field"
      },
      "value": {
        "type": "string",
        "description": "Text to type into the field (replaces existing content)"
      },
      "clear_first": {
        "type": "boolean",
        "default": true,
        "description": "Clear existing content before filling"
      }
    },
    "required": ["selector", "value"]
  }
}

// Example response
{
  "filled": true,
  "selector": "div[aria-label='To']",
  "value": "john@example.com",
  "elapsed_ms": 210
}
```

**Tool 4: screenshot**

Take a screenshot of the current page or a specific element.

```json
{
  "name": "screenshot",
  "description": "Capture a screenshot. Returns base64-encoded PNG.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "selector": {
        "type": "string",
        "description": "Optional CSS selector — clips screenshot to element bounds"
      },
      "full_page": {
        "type": "boolean",
        "default": false,
        "description": "Capture full scrollable page height"
      },
      "format": {
        "type": "string",
        "enum": ["png", "jpeg"],
        "default": "png"
      }
    }
  }
}

// Example response
{
  "format": "png",
  "width": 1280,
  "height": 800,
  "data": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "elapsed_ms": 890
}
```

**Tool 5: snapshot**

Capture a Prime Mermaid DOM snapshot for evidence and analysis.

```json
{
  "name": "snapshot",
  "description": "Capture a Prime Mermaid DOM snapshot (structured page data for analysis and evidence).",
  "inputSchema": {
    "type": "object",
    "properties": {
      "include_forms": {
        "type": "boolean",
        "default": true,
        "description": "Include form field states"
      },
      "include_links": {
        "type": "boolean",
        "default": true,
        "description": "Include all links on the page"
      },
      "max_depth": {
        "type": "integer",
        "default": 5,
        "description": "Maximum DOM tree depth to capture"
      }
    }
  }
}

// Example response
{
  "url": "https://mail.google.com/mail/u/0/#inbox",
  "snapshot_hash": "sha256:abc...",
  "mermaid": "stateDiagram-v2\n  [*] --> inbox\n  inbox --> email_list\n  ...",
  "elements_count": 342,
  "forms_count": 1,
  "links_count": 89,
  "elapsed_ms": 420
}
```

**Tool 6: evaluate**

Execute JavaScript in the page context and return the result.

```json
{
  "name": "evaluate",
  "description": "Execute JavaScript in the browser page context. Returns the expression result as JSON.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "expression": {
        "type": "string",
        "description": "JavaScript expression or function body to evaluate (must return JSON-serializable value)"
      },
      "timeout_ms": {
        "type": "integer",
        "default": 5000,
        "description": "Max execution time (ms)"
      }
    },
    "required": ["expression"]
  }
}

// Example request
{ "expression": "document.querySelectorAll('tr.zA').length" }

// Example response
{ "result": 42, "type": "number", "elapsed_ms": 120 }
```

**Tool 7: aria_snapshot**

Capture the ARIA accessibility tree for the current page.

```json
{
  "name": "aria_snapshot",
  "description": "Capture the ARIA accessibility tree. Best for understanding page structure without visual noise.",
  "inputSchema": {
    "type": "object",
    "properties": {
      "selector": {
        "type": "string",
        "description": "Optional root element selector (defaults to document body)"
      },
      "include_hidden": {
        "type": "boolean",
        "default": false,
        "description": "Include elements with aria-hidden=true"
      }
    }
  }
}

// Example response
{
  "tree": "- document\n  - banner\n    - link 'Google' (url: /)\n  - main\n    - heading 'Inbox' (level: 1)\n    - list\n      - listitem 'RE: Q1 Report, john@example.com'\n      ...",
  "node_count": 234,
  "elapsed_ms": 380
}
```

### 6.5 JSON-RPC 2.0 Protocol

All communication over stdio follows the JSON-RPC 2.0 spec:

```json
// Request (agent → MCP server, via stdin)
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/call",
  "params": {
    "name": "navigate",
    "arguments": {
      "url": "https://mail.google.com",
      "wait_until": "networkidle"
    }
  }
}

// Response (MCP server → agent, via stdout)
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"url\":\"https://mail.google.com/mail/u/0/#inbox\",\"title\":\"Inbox - Gmail\",\"status\":200,\"elapsed_ms\":1240}"
      }
    ]
  }
}

// Error response
{
  "jsonrpc": "2.0",
  "id": 2,
  "error": {
    "code": -32000,
    "message": "Navigation failed: net::ERR_NAME_NOT_RESOLVED",
    "data": { "url": "https://nonexistent.example.com" }
  }
}

// Tool list (agent discovery)
{
  "jsonrpc": "2.0",
  "id": 0,
  "method": "tools/list",
  "params": {}
}
```

### 6.6 Budget Gate Integration

Every MCP tool call that triggers a browser action passes through the budget gates (Paper 07 B1–B6) before execution:

```python
# mcp_server.py (budget gate middleware)

async def execute_tool(name, arguments, agent_id):
    # Identify app scope from agent_id
    app = AppRegistry.get(agent_id)

    # Run through budget gates
    gate_result = BudgetGates.check(
        action=name,
        app=app,
        arguments=arguments
    )

    if not gate_result.allowed:
        return {
            "error": {
                "code": -32001,
                "message": f"Budget gate {gate_result.gate} blocked: {gate_result.reason}",
                "data": { "gate": gate_result.gate, "action": name }
            }
        }

    # Execute tool
    result = await browser.execute(name, arguments)

    # Record evidence
    await evidence_chain.append({
        "tool": name,
        "arguments": sanitize(arguments),  # redact secrets
        "agent_id": agent_id,
        "result_hash": sha256(result),
        "budget_gate": gate_result.gate,
        "ts": utcnow()
    })

    return result
```

### 6.7 CLAUDE.md Config Snippet

Copy this into any project's CLAUDE.md to enable Solace Browser MCP tools:

```markdown
## MCP Tool: Solace Browser

Browser automation is available via the Solace Browser MCP server.

Tools available: navigate, click, fill, screenshot, snapshot, evaluate, aria_snapshot

The browser server runs at localhost:9222. The MCP server is a stdio wrapper.

Start the browser server:
  python3 ~/projects/solace-browser/solace_browser_server.py --port 9222 --headless

MCP server config (add to claude_desktop_config.json):
  {
    "mcpServers": {
      "solace-browser": {
        "command": "node",
        "args": ["/home/phuc/projects/solace-browser/mcp/server.js"],
        "env": {
          "BROWSER_HOST": "localhost",
          "BROWSER_PORT": "9222"
        }
      }
    }
  }

Usage notes:
- navigate first, then use snapshot or aria_snapshot to understand page structure
- Use aria_snapshot for form discovery (more reliable than CSS selectors)
- screenshot returns base64 PNG for visual verification
- evaluate runs JS in page context (use for data extraction)
- All actions pass through budget gates — set app budget before automation
- Evidence is written to ~/.solace/audit/audit_chain.jsonl on every action
```

### 6.8 Invariants

1. Every MCP tool call passes through B1–B6 budget gates before execution
2. Every MCP tool call writes to the evidence chain (Part 11 compliant)
3. Tool arguments are sanitized before evidence logging (no secrets in audit log)
4. JSON-RPC 2.0 spec compliance required — no protocol extensions
5. MCP server runs as a subprocess of the calling agent — no daemon required
6. Browser server must be running at localhost:9222 before MCP server starts — fail fast if unavailable

---

## 7. YinYang Chat (OpenRouter-Powered)

### 7.1 Purpose

The bottom rail chat input (Paper 04) needs a backend. YinYang Chat is the API endpoint that powers conversational interaction. It uses OpenRouter to route to `meta-llama/llama-3.3-70b-instruct` with a system prompt that includes browser state context. This same endpoint powers the settings page "Ask YinYang" section.

### 7.2 Endpoint Specification

**POST /api/yinyang/chat**

```json
// Request
{
  "message": "Triage my Gmail inbox",
  "context": {
    "current_page": "home.html",
    "belt": "yellow",
    "installed_apps": ["gmail-inbox-triage", "calendar-brief", "morning-brief"],
    "active_run": null,
    "budget_remaining_cents": 432,
    "last_run": {
      "app": "gmail-inbox-triage",
      "completed_at": "2026-03-02T09:45:00Z",
      "summary": "42 emails processed"
    }
  },
  "history": [
    { "role": "user", "content": "What apps do I have installed?" },
    { "role": "assistant", "content": "You have 3 apps installed: Gmail Inbox Triage, Calendar Brief, and Morning Brief." }
  ],
  "session_id": "sess_abc123"
}

// Response
{
  "reply": "I'll start Gmail Inbox Triage for you. Before I begin, here's what I'll do:\n\n• Scan your last 50 emails\n• Classify by priority (VIP, newsletters, noise)\n• Archive newsletters and noise\n• Star messages from priority contacts\n\nEstimated cost: ~$0.003 | Time: ~12 seconds\n\nShall I proceed?",
  "intent": "run_app",
  "app_id": "gmail-inbox-triage",
  "requires_approval": true,
  "preview": {
    "steps": [
      "Scan last 50 emails",
      "Classify by priority",
      "Archive newsletters and noise",
      "Star messages from priority contacts"
    ],
    "estimated_cost_cents": 3,
    "estimated_duration_ms": 12000
  },
  "tokens_used": 847,
  "model": "meta-llama/llama-3.3-70b-instruct",
  "cost_cents": 1
}
```

### 7.3 System Prompt

```
You are YinYang, the AI companion for Solace Browser. You are warm, witty, and precise.

PERSONA:
- Warm and friendly, never robotic
- Concise (no padding, no filler phrases)
- Honest: say "I don't know" rather than guess
- Never self-aggrandizing ("As an AI language model...")
- Use dry humor when the context supports it

WHAT YOU CAN DO:
- Run installed apps (gmail-inbox-triage, calendar-brief, morning-brief)
- Explain what apps do (read their manifests and diagrams)
- Show run history and evidence
- Change settings (edit ~/.solace/settings.json via Yinyang write API)
- Change app config (edit inbox/conventions/config.yaml)
- Answer questions about the platform
- Tell jokes and share facts (draw from Fun Pack)
- Provide emotional support and encouragement

WHAT YOU CANNOT DO:
- Run apps without showing a preview first (Anti-Clippy law)
- Auto-approve any action (never use "I'll just go ahead and...")
- Build new apps or modify recipe.json (escalate to solaceagi.com)
- Access the internet directly (you use the browser for that)
- Remember anything between sessions (session memory only)

BROWSER STATE (injected per request):
- Current page: {current_page}
- User belt: {belt}
- Installed apps: {installed_apps}
- Active run: {active_run}
- Budget remaining: {budget_remaining_cents} cents
- Last run: {last_run}

INTENT DETECTION:
When user asks to run an app, set intent="run_app" and app_id in your response.
When user asks to change settings, set intent="change_settings".
When user asks a question, set intent="answer".
When user needs escalation, set intent="escalate".

APPROVAL RULE (ABSOLUTE):
If your response involves an action (run_app, change_settings), ALWAYS set requires_approval=true
and include a preview. NEVER execute without a preview. NEVER.
```

### 7.4 OpenRouter Integration

```python
# app/services/yinyang_chat.py

import openai
from app.core.config import settings

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://solaceagi.com",
        "X-Title": "Solace Browser YinYang"
    }
)

async def chat(message: str, context: dict, history: list) -> dict:
    system_prompt = build_system_prompt(context)

    messages = [
        {"role": "system", "content": system_prompt},
        *history[-10:],   # last 10 turns only (context window management)
        {"role": "user", "content": message}
    ]

    response = client.chat.completions.create(
        model="meta-llama/llama-3.3-70b-instruct",
        messages=messages,
        max_tokens=512,
        temperature=0.7,
        response_format={"type": "json_object"}   # structured intent response
    )

    raw = response.choices[0].message.content
    result = parse_yinyang_response(raw)

    # Deduct cost from user's LLM budget
    tokens_used = response.usage.total_tokens
    cost_cents = compute_cost_cents(tokens_used, model="llama-3.3-70b")
    await budget_service.deduct(context['user_id'], cost_cents)

    return {
        "reply": result["reply"],
        "intent": result.get("intent", "answer"),
        "app_id": result.get("app_id"),
        "requires_approval": result.get("requires_approval", False),
        "preview": result.get("preview"),
        "tokens_used": tokens_used,
        "model": "meta-llama/llama-3.3-70b-instruct",
        "cost_cents": cost_cents
    }

def build_system_prompt(context: dict) -> str:
    return YINYANG_SYSTEM_PROMPT.format(
        current_page=context.get("current_page", "unknown"),
        belt=context.get("belt", "white"),
        installed_apps=", ".join(context.get("installed_apps", [])),
        active_run=context.get("active_run", "none"),
        budget_remaining_cents=context.get("budget_remaining_cents", 0),
        last_run=format_last_run(context.get("last_run"))
    )
```

### 7.5 Settings Page Integration ("Ask YinYang")

Each settings section has an `[Ask YinYang]` button that pre-fills the chat with context:

```javascript
// settings.js

const SECTION_PROMPTS = {
  'history':    'I want to change my history settings.',
  'budget':     'I want to adjust my LLM budget.',
  'apps':       'Tell me about my installed apps.',
  'privacy':    'What data does Solace Browser collect?',
  'fun-packs':  'How do I install a new Fun Pack?',
  'tokens':     'Show me my active OAuth3 tokens.',
  'evidence':   'How do I view my evidence history?'
};

document.querySelectorAll('[data-ask-yinyang]').forEach(btn => {
  btn.addEventListener('click', () => {
    const section = btn.dataset.askYinyang;
    const prompt = SECTION_PROMPTS[section] || 'Help me with this section.';
    expandBottomRail();
    fillChatInput(prompt);
    focusChatInput();
  });
});
```

### 7.6 Rate Limiting and Budget Protection

```python
# Per-user rate limits (fail-closed on violation)
RATE_LIMITS = {
    'requests_per_minute': 10,
    'requests_per_hour': 60,
    'max_tokens_per_request': 512,
    'max_history_turns': 10
}

# Budget gate check before every LLM call
async def chat_with_budget_check(user_id: str, *args, **kwargs):
    budget = await budget_service.get(user_id)

    if budget.llm_remaining_cents <= 0:
        raise BudgetExhaustedError(
            "LLM budget exhausted for today. "
            "Ask YinYang to adjust your budget or wait for reset."
        )

    if budget.llm_remaining_cents < MINIMUM_CHAT_CENTS:
        # warn but allow (minimum = 1 cent)
        await notify_low_budget(user_id, budget.llm_remaining_cents)

    return await chat(*args, **kwargs)
```

### 7.7 Fallback Models (OpenRouter)

If `meta-llama/llama-3.3-70b-instruct` is unavailable, OpenRouter automatically falls back through:

1. `meta-llama/llama-3.3-70b-instruct` (primary)
2. `mistralai/mistral-7b-instruct` (fallback — cheaper, lower quality)
3. `openai/gpt-4o-mini` (emergency fallback — user may be billed OpenAI rate)

Fallback model is logged in the response `model` field. Users can inspect which model served their request.

### 7.8 Invariants

1. Every chat call deducts from the user's LLM budget before returning a response
2. `requires_approval=true` ALWAYS accompanies any intent that involves an action
3. History is limited to last 10 turns — no unbounded context growth
4. System prompt injects live browser state on every request (never stale context)
5. Fallback model is logged in response — user always knows what served their request
6. Budget exhausted = 402 response with clear "Add credits" message, never silent failure

---

## 8. Cross-References

| Section | solaceagi Papers | solace-cli Papers/Diagrams |
|---------|-----------------|---------------------------|
| Tutorial | papers/22+25 (Yinyang FSM) | Diagram 13 (Yinyang FSM) |
| Fun Packs | papers/08 (Delight Engine) | Paper 04 (warm tokens) |
| OAuth3 Gate | papers/04+19 (Wallet+Preview) | Paper 14 (Phase 4 Dispatch) |
| Notify API | papers/22+25 (Alert Queue) | Diagram 10 (Core Flow) |
| MCP Server | papers/01 (Solace Browser) | Paper 07 (Three Realms) |
| YinYang Chat | papers/22+25 (Yinyang Chat) | Paper 04 (Triple-Twin) |

---

## 9. Invariants (All Sections)

1. Tutorial fires at most once — localStorage `sb_tutorial_v1` prevents re-trigger
2. Tutorial step 5 joke always drawn from Fun Pack — never hardcoded content
3. Fun Pack sha256 verified before install — no unsigned packs ever execute
4. OAuth3 gate reverses navigation before showing confirmation — user never lands on OAuth3 page unsafed
5. OAuth3 countdown expires = auto-cancel (fail-closed) — never silent indefinite wait
6. Agent notifications require valid `agent_id` matching an installed app — no anonymous push
7. MCP tool calls pass through B1–B6 budget gates — no unbudgeted browser actions
8. MCP tool call evidence logged to audit chain — every action traceable
9. YinYang Chat `requires_approval=true` on any action intent — Anti-Clippy law absolute
10. YinYang Chat budget checked before every LLM call — budget exhausted = hard stop
