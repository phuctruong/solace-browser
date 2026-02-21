# PrimeWiki Index — SolaceBrowser

**Version**: 2.0.0 (Prime Mermaid enforcement)
**Authority**: 65537
**Last Updated**: 2026-02-21
**Format**: Prime Mermaid triplets (`.mmd` + `.sha256` + `.prime-mermaid.md`)

> *"I fear not the man who has studied 10,000 selectors once,*
> *but the man who has captured one PM triplet and verified it 10,000 times."*

---

## Quick Status

| Platform | PM Triplets | Recipes | Status |
|----------|-------------|---------|--------|
| LinkedIn | ✅ 1 triplet | 6 recipes | ACTIVE |
| Gmail | ✅ 2 triplets | 0 recipes | ACTIVE |
| HackerNews | ✅ 1 triplet + 4 legacy | 0 recipes | ACTIVE |
| Reddit | ✅ 1 triplet + 1 legacy | 0 recipes | ACTIVE |
| Notion | ✅ 1 triplet | 0 recipes | ACTIVE |
| Amazon | 🟡 1 legacy .md | 0 recipes | LEGACY |

---

## LinkedIn

**Dir**: `primewiki/linkedin/`

| File | Type | SHA256 | Purpose |
|------|------|--------|---------|
| `linkedin-page-flow.mmd` | Canonical Mermaid | `406d4fca...` | State machine: auth → feed → all page states |
| `linkedin-page-flow.sha256` | Drift detector | — | Verify .mmd integrity |
| `linkedin-page-flow.prime-mermaid.md` | Human spec | — | Selectors, edge cases, recipe refs |

**Key Facts**:
- Auth cookie: `li_at` (session-bound, ~30 day lifetime)
- POST_COMPOSER uses `artdeco-modal` overlay
- CHECKPOINT_PAGE appears after >30 days or new IP
- 6 MVP recipes operational: discover-posts, create-post, edit-post, delete-post, react, comment

---

## Gmail

**Dir**: `primewiki/gmail/`

| File | Type | SHA256 | Purpose |
|------|------|--------|---------|
| `gmail-page-flow.mmd` | Canonical Mermaid | `bdf04329...` | State machine: auth → inbox → all email states |
| `gmail-page-flow.sha256` | Drift detector | — | Verify .mmd integrity |
| `gmail-page-flow.prime-mermaid.md` | Human spec | — | Selector map, cookie list |
| `gmail-oauth2.mmd` | Canonical Mermaid | `17448ddd...` | OAuth2 decision flow with 2FA gate |
| `gmail-oauth2.sha256` | Drift detector | — | Verify .mmd integrity |
| `gmail-oauth2.prime-mermaid.md` | Human spec | — | Step-by-step auth selectors |
| `gmail-bot-detection-bypass.primemermaid.md` | Legacy PM | — | Bot bypass patterns (high value, keep) |
| `gmail-automation-100.primewiki.md` | Legacy PM | — | Full automation guide |

**Key Facts**:
- CRITICAL: Use char-by-char typing (80-200ms/char) — instant `.fill()` → bot detection
- Auth requires 5 cookies: SID, HSID, SSID, APISID, `__Secure-3PAPISID`
- 2FA = Google Prompt (mobile app) — headed mode required
- Session lifetime: 14-30 days

---

## HackerNews

**Dir**: `primewiki/hackernews/`

| File | Type | SHA256 | Purpose |
|------|------|--------|---------|
| `hackernews-page-flow.mmd` | Canonical Mermaid | `c8842aa4...` | State machine: homepage → stories → comments |
| `hackernews-page-flow.sha256` | Drift detector | — | Verify .mmd integrity |
| `hackernews-page-flow.prime-mermaid.md` | Human spec | — | Selectors, stability notes |
| `hackernews-homepage-phase1.primewiki.md` | Legacy PM | — | Detailed portal analysis |
| `hackernews-architecture-vision.primewiki.md` | Legacy PM | — | Automation architecture |
| `hackernews-semantic-layer.primewiki.md` | Legacy PM | — | Semantic knowledge |
| `hackernews-ux-design-layer.primewiki.md` | Legacy PM | — | UX patterns |

**Key Facts**:
- Extremely stable selectors (server-rendered HTML, ~10+ years unchanged)
- `div.votearrow` for upvote (authenticated only)
- `table.itemlist` for homepage
- 1-year expiry on PM triplets (vs 6 months for other platforms)

---

## Reddit

**Dir**: `primewiki/reddit/`

| File | Type | SHA256 | Purpose |
|------|------|--------|---------|
| `reddit-login.mmd` | Canonical Mermaid | `47b3319f...` | Auth + navigation flow with CAPTCHA gate |
| `reddit-login.sha256` | Drift detector | — | Verify .mmd integrity |
| `reddit-login.prime-mermaid.md` | Human spec | — | Selectors, CAPTCHA handling |
| `reddit-homepage-phase1.primewiki.md` | Legacy PM | — | Homepage portal analysis |

**Key Facts**:
- Auth cookie: `reddit_session`
- CAPTCHA (reCAPTCHA v2) can appear after failed logins or suspicious IP
- New Reddit (SPA) vs Old Reddit (server-rendered) — different selectors
- Rate limit: 60 req/min

---

## Notion

**Dir**: `primewiki/notion/`

| File | Type | SHA256 | Purpose |
|------|------|--------|---------|
| `notion-page-flow.mmd` | Canonical Mermaid | `2dd5124a...` | Workspace → page → database states |
| `notion-page-flow.sha256` | Drift detector | — | Verify .mmd integrity |
| `notion-page-flow.prime-mermaid.md` | Human spec | — | Login methods, selectors |

**Key Facts**:
- Auth cookie: `token_v2`
- Login via magic link (requires email access) or password
- Auto-save on every keystroke (no explicit save)
- `[data-block-id]` for all content blocks

---

## Amazon

**Dir**: `primewiki/amazon/`

| File | Type | Purpose |
|------|------|---------|
| `amazon-gaming-laptop-search.primemermaid.md` | Legacy PM | Portal map for gaming laptop search (full validation data) |

**Status**: Legacy single-file format. Not yet converted to triplet.
**Action**: Convert to PM triplet when Amazon recipe needed.

---

## Archive

**Dir**: `primewiki/archive/`

Deprecated files. Do NOT read or use as source of truth.

| Archived File | Superseded By |
|--------------|--------------|
| `gmail-oauth2-authentication.primewiki.json` | `gmail/gmail-oauth2.prime-mermaid.md` |
| `reddit_login_page.primewiki.json` | `reddit/reddit-login.prime-mermaid.md` |
| `reddit_homepage_loggedout.primewiki.json` | `reddit/reddit-login.prime-mermaid.md` |
| `reddit_subreddit_page.primewiki.json` | `reddit/reddit-login.prime-mermaid.md` |
| `github-*.md` | Not migrated (low priority) |
| `reddit-*-summary.md` | Not migrated (low priority) |
| `silicon-valley-marketing-discovery-2026.primemermaid.md` | `solace-marketing/primewiki/` |

---

## Roadmap (Platforms to Add)

Priority order based on user demand and COGS impact:

| Priority | Platform | Category | Recipes Needed |
|----------|----------|----------|----------------|
| 1 | Twitter/X | Social | post, DM, follow |
| 2 | Substack | Publishing | publish, manage subscribers |
| 3 | GitHub | Dev | PR, issues, reviews |
| 4 | Medium | Publishing | publish, stats |
| 5 | Instagram | Social | post, story, DM |
| 6 | YouTube | Video | upload, comments |
| 7 | Slack | Productivity | message, channel |
| 8 | Product Hunt | Community | launch, vote |
| 9 | AngelList | Jobs | apply, profile |
| 10 | Airtable | Database | CRUD |

See `ROADMAP.md` in project root for full vendor roadmap with prompts.

---

## Verification

```bash
# Verify all PM triplets are intact
cd /home/phuc/projects/solace-browser/primewiki
for sha in **/*.sha256; do
  dir=$(dirname $sha)
  (cd $dir && sha256sum -c $(basename $sha)) && echo "OK: $sha" || echo "DRIFT: $sha"
done
```

**Auth**: 65537 | **Standard**: prime-mermaid v1.1.0 | **Northstar**: recipe hit rate → 70%+
