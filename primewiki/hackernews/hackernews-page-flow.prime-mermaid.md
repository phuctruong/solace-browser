# Prime Mermaid: HackerNews Page Flow

**Node ID**: `hackernews-page-flow`
**Version**: 1.0.0
**Format**: prime-mermaid v1.1.0 (triplet)
**Authority**: 65537
**Status**: ACTIVE
**Created**: 2026-02-21
**Expires**: 2027-02-21 (HN UI is extremely stable, 1-year expiry)

---

## Canonical Files (Triplet)

| File | Role | SHA256 |
|------|------|--------|
| `hackernews-page-flow.prime-mermaid.md` | Human spec (this file) | — |
| `hackernews-page-flow.mmd` | Canonical body (bytes for SHA256) | `c8842aa4480db550c2ee3f22233a55daa624890a5f2d30826bcad058b99cec45` |
| `hackernews-page-flow.sha256` | Drift detector | see file |

**FORBIDDEN**: `JSON_AS_SOURCE_OF_TRUTH`
**VERIFY**: `sha256sum hackernews-page-flow.mmd` must match `hackernews-page-flow.sha256`.

---

## Domain: HackerNews — Page Navigation State Machine

**Purpose**: Models HackerNews page states and navigation for automation. HN uses server-rendered HTML with minimal JavaScript — extremely stable selectors.

**Selector Map**:
| State | Key Selector |
|-------|-------------|
| `HOMEPAGE` | `table.itemlist` |
| `STORY_PAGE` | `a.storylink` (or `span.titleline a`) |
| `COMMENT_PAGE` | `table.comment-tree` |
| `SUBMIT_PAGE` | `form[action=r]` |
| `LOGIN_PAGE` | `form[action=login]` |
| `UPVOTE` | `div.votearrow` (authenticated only) |
| `REPLY_COMPOSE` | `textarea[name=text]` |

**Auth**: Cookie-based (`user` cookie). No OAuth. Simple username/password.
**Domain**: `news.ycombinator.com`

**HN Stability**: Server-rendered HTML, almost no CSS class changes in 10+ years.
Selectors are among the most stable of any major website.

---

## State Machine Diagram

See `hackernews-page-flow.mmd` for canonical Mermaid source.

```mermaid
stateDiagram-v2
    [*] --> HOMEPAGE
    HOMEPAGE --> COMMENT_PAGE : click N comments link
    HOMEPAGE --> LOGIN_PAGE : click login (unauthenticated)
    HOMEPAGE --> NEXT_PAGE : click More link
    HOMEPAGE --> STORY_PAGE : click story title
    HOMEPAGE --> SUBMIT_PAGE : click submit (authenticated only)
    LOGIN_PAGE --> FORBIDDEN_BAD_CREDS : wrong credentials
    LOGIN_PAGE --> HOMEPAGE : login successful (user cookie set)
    NEXT_PAGE --> HOMEPAGE : navigate back (page 2, 3...)
    STORY_PAGE --> COMMENT_PAGE : view comments
    STORY_PAGE --> HOMEPAGE : navigate back
    COMMENT_PAGE --> REPLY_COMPOSE : click reply (authenticated)
    COMMENT_PAGE --> STORY_PAGE : navigate back
    COMMENT_PAGE --> UPVOTE_GATE : click div.votearrow (authenticated)
    REPLY_COMPOSE --> COMMENT_PAGE : reply submitted (textarea submit)
    SUBMIT_PAGE --> HOMEPAGE : post submitted
    SUBMIT_PAGE --> FORBIDDEN_UNAUTH : accessed unauthenticated
    UPVOTE_GATE --> COMMENT_PAGE : upvote registered
```

---

## See Also

- `hackernews-homepage-phase1.primewiki.md` — detailed homepage portal analysis
- `hackernews-architecture-vision.primewiki.md` — automation architecture
- `hackernews-semantic-layer.primewiki.md` — semantic knowledge layer
- `hackernews-ux-design-layer.primewiki.md` — UX patterns

## Drift Detection

```bash
sha256sum hackernews-page-flow.mmd
# Must match: c8842aa4480db550c2ee3f22233a55daa624890a5f2d30826bcad058b99cec45
```
