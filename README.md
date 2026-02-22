# Solace Browser — The Twin Browser Dojo

> "Be water, my friend. Flow through walls. Work while you sleep." — Bruce Lee (adapted)

[![Status](https://img.shields.io/badge/Phase-1%20MVP%20Build-blue)](specs/BUILD-SPEC.md)
[![Rung](https://img.shields.io/badge/Rung%20Target-641-green)](specs/QA-CHECKLIST.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Stillwater](https://img.shields.io/badge/Stillwater-v1.5.0-purple)](https://github.com/phuctruong/stillwater)

---

## The Twin

You browse. Your twin works.

```
LOCAL  → You: normal browser, logged in, living your life
CLOUD  → Twin: headless clone, identical fingerprint, running tasks 24/7

One click to sync. AES-256-GCM zero-knowledge encryption.
Your sessions stay yours. The cloud can't read them. Only your twin can use them.
```

This is not an extension. This is not a chatbot sidebar.

This is a **second you** — an AI rider on your digital shadow — delegating work
while you sleep, armed with recipes that execute 70x faster than pure LLM reasoning.

---

## The Five Moats

| Moat | What it means |
|------|---------------|
| **Anti-Detection** | Canvas/WebGL/JA3/Bezier mouse/inertia scroll — your twin IS you to every bot detector |
| **Recipe System** | Externalized reasoning → 70% cache hit → $0.01/task vs $0.20 competitors |
| **Twin Architecture** | Local browsing + cloud AGI delegation — work while you sleep |
| **Fingerprint Sync** | Cloud browser has your exact fingerprint, timezone, plugins, fonts |
| **Stillwater Verification** | Evidence bundles, not just screenshots — you can audit every action |

---

## The Dojo Belt System

You don't install Solace Browser. You **earn** it, layer by layer.

| Belt | Rung | What You Can Do |
|------|------|-----------------|
| 🤍 White | Setup | Run the browser server, navigate, take screenshots |
| 🟡 Yellow | 641 | Execute basic recipes (discover, post, comment) |
| 🟠 Orange | 641+ | Session sync across machines, headless execution |
| 🟢 Green | 274177 | Cloud delegation, recipe hit rate > 50% |
| 🔵 Blue | 274177+ | PrimeWiki maps, PrimeMermaid page geometry |
| 🟤 Brown | 65537 | Anti-detection passing BotD/CreepJS, fingerprint sync |
| ⚫ Black | 65537 | Twin architecture, cloud farm, zero-knowledge vault |

---

## The Scrolls (Skills)

Skills are loaded into sub-agents. Read the full scroll before production work.

| Scroll | What it teaches |
|--------|----------------|
| [`skills/prime-safety.md`](skills/prime-safety.md) | Fail-closed safety layer — always loaded first |
| [`skills/prime-wishes.md`](skills/prime-wishes.md) | Wish contract system — seal before you execute |
| [`skills/phuc-swarms.md`](skills/phuc-swarms.md) | Multi-agent orchestration — Scout→Forecast→Solve→Verify |
| [`skills/phuc-cleanup.md`](skills/phuc-cleanup.md) | Repo janitor — keep the dojo clean |

---

## The Spellbook (Recipes)

Recipes are externalized reasoning. Cast once, replay instantly.

```bash
# See all recipes
ls recipes/*.recipe.json

# The LinkedIn Dojo (6 spells):
recipes/linkedin-discover-posts.recipe.json   # scan the feed for worthy posts
recipes/linkedin-create-post.recipe.json      # conjure a post into existence
recipes/linkedin-edit-post.recipe.json        # revise what you've written
recipes/linkedin-delete-post.recipe.json      # banish a post (irreversible)
recipes/linkedin-react-post.recipe.json       # mark a post with your presence
recipes/linkedin-comment-post.recipe.json     # leave your words on another's post
```

**Why recipes beat pure LLM every time:**
- Cold LLM reasoning: 30–60s per task
- Cached recipe replay: 3–5s per task
- Recipe caching dramatically reduces per-task cost compared to cold LLM calls.

---

## The Arena (Supported Sites)

| Site | Status | Recipes |
|------|--------|---------|
| 🔵 LinkedIn | ✅ Active | 6 (discover, post, edit, delete, react, comment) |
| 📧 Gmail | ✅ Active | 2 (oauth-login, send-email) |
| 🔴 Reddit | ✅ Active | 5 (login, navigate, upvote, comment, create-post) |
| 🟠 Hacker News | ✅ Active | 4 (navigate, upvote, comment, hide) |
| ⚫ GitHub | ✅ Active | 1 (create-issue) |
| 🔵 Google | ✅ Active | 1 (search) |

---

## The Kata (Quick Start)

```bash
# 1. Start the browser server (port 9222)
python persistent_browser_server.py

# 2. Start the UI (port 9223)
python ui_server.py

# 3. Open http://localhost:9223 — your dojo dashboard

# 4. Navigate in a headed session first (to capture your session)
# 5. Click "Sync Session" on the site card
# 6. Run a recipe from the Kanban board
```

**API Endpoints (40+ available at port 9222):**

```bash
POST /navigate          # go to URL
POST /click             # click element by selector
POST /fill              # type text into field
GET  /snapshot          # ARIA tree of current page
GET  /html-clean        # cleaned HTML for LLM consumption
GET  /screenshot        # PNG screenshot
POST /save-session      # export session state
POST /fingerprint-check # verify anti-detection status
POST /scroll-human      # human-like scroll
```

---

## The Map (PrimeWiki)

PrimeWiki is the living knowledge graph of each site. Built from real sessions.
Stored in `primewiki/`. Submitted to the Stillwater Store for community benefit.

```json
{
  "site": "linkedin.com",
  "pages": {
    "feed": {
      "post_card": { "selector": "role=article", "strength": 0.95 },
      "like_button": { "selector": ".reactions-react-button", "strength": 0.90 }
    }
  }
}
```

---

## The Blueprint (PrimeMermaid)

PrimeMermaid is page geometry: what interactive elements exist, where they are,
what state machines govern them. Cast once, navigate forever.

```
stateDiagram-v2
  [*] --> Feed
  Feed --> PostModal : click Start a post
  PostModal --> Posted : click Post button
  Posted --> [*]
```

Stored in `primewiki/` as `.mmd` files. Rendered live in the Activity View.

---

## The Mission

This is the first open-source AI twin browser built on verifiable evidence,
not vibes. Every action is logged. Every task has an artifact. Every recipe
has a reasoning block you can audit.

The Bitwarden model: open-source the client. Keep the cloud paid.
- **Free**: self-host, run your own twin, use community recipes
- **Paid** ([solaceagi.com](https://www.solaceagi.com)): managed cloud, 70% recipe cache, fingerprint sync

---

## The Code of the Dojo

Built with Stillwater OS. Governed by the verification ladder.

| Principle | Application |
|-----------|-------------|
| No claim without evidence | Every recipe has a `reasoning` block |
| Fail-closed | Sessions fail safe; never destructive without sealed wish |
| Externalized reasoning | LLM thinking → recipes → instant replay |
| Open core, paid cloud | Client = MIT. Recipe library + farm = solaceagi.com |

---

## See Also

- [`NORTHSTAR.md`](NORTHSTAR.md) — mission, metrics, model strategy
- [`IDEAS.md`](IDEAS.md) — 65537-expert analysis of the opportunity
- [`specs/BUILD-SPEC.md`](specs/BUILD-SPEC.md) — MVP build spec (Phase 1)
- [`specs/QA-CHECKLIST.md`](specs/QA-CHECKLIST.md) — verification checklist
- [`primewiki/`](primewiki/) — site knowledge graphs
- [`recipes/`](recipes/) — automation recipe library
- [Stillwater OS](https://github.com/phuctruong/stillwater) — the AI verification framework powering this

---

> Born from a boat. Forged at Harvard. Battle-tested in startups.
> Now open-sourced for the world.
>
> Absorb what is useful. Discard what is useless. Add what is essentially your own. — Bruce Lee
