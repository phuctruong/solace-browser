# PrimeWiki: HackerNews Domain Knowledge

**Platform**: Hacker News (news.ycombinator.com)
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21

---

## HN Culture & Community Norms

### Post Types and Conventions
- **Standard story**: A link to external content with a descriptive title
- **Ask HN**: Starts with "Ask HN:" — question to the community. No URL, text required.
- **Show HN**: Starts with "Show HN:" — showcasing a project. Include what it does in title.
- **Tell HN**: Starts with "Tell HN:" — sharing news/info without seeking discussion
- **Job posting**: Posted directly by YC-affiliated companies from /jobs

### Title Rules (Strictly Enforced)
- Title should match the article's actual title (do not editorialize)
- No ALL CAPS words
- No exclamation marks (!)
- No misleading/clickbait framing
- No "(Important)", "(Must Read)" modifiers
- Maximum 80 characters
- Flagged by community for rule violations → mods remove

### Comment Culture
- High signal, low noise expectation
- Substantive comments preferred over "+1" or "This"
- Off-topic comments get flagged
- Political comments often get vouch-gated (collapsed by default)
- "dang" (Dan Gackle) is head mod — thoughtful, patient
- Heated arguments → "please don't do this" from dang

---

## Karma System

### Karma Thresholds (Approximate)
| Threshold | Unlocks |
|-----------|---------|
| 1 | Can submit stories and comment |
| 2 | Upvote button visible |
| 500 | Can see comment scores |
| 1000 | Can flag |
| 10000 | Vouch queue access |

### Karma Effects on Automation
- New accounts (karma = 0): Cannot submit — need to comment first
- Karma < 2: Upvote button not shown in DOM
- Karma >= 500: `.score` element visible on comments (otherwise hidden)
- Very high karma: Comments start at higher visibility level

---

## Story Lifecycle

```
SUBMITTED → PENDING (new story, not yet visible to all)
    ↓ upvotes accumulate + time
NEW (visible on /newest)
    ↓ enough velocity
FRONTPAGE (ranked by hot algorithm)
    ↓ more time / drop in velocity
SECOND_PAGE → THIRD_PAGE → ...
    ↓ very old or flagged
KILLED (still visible but no points shown, grayed out)
```

### Ranking Algorithm
HN uses a modified Wilson score with time decay:
```
score = (points - 1)^0.8 / (age_hours + 2)^1.8
```
Comments, flags, and mod intervention also affect ranking.

---

## Flagging System

- Users can flag stories they believe violate guidelines
- If enough flags: story moved off front page
- Heavily flagged stories: admin review
- "Hellbanned" accounts: Posts appear to them but invisible to others
- Stories can be "vouched" by trusted users to restore if wrongly flagged

**Automation Warning**: Flagging automation is a major ToS violation. Never implement flag automation.

---

## Ask HN / Show HN Specific Rules

### Ask HN
- Must be an honest question, not rhetorical
- Should not be answerable via a Google search
- Should be relevant to HN audience (tech, startup, science, ideas)
- Text field required (context for the question)

### Show HN
- Must be something you made yourself
- Should be genuinely interesting/useful to technical audience
- Should include what it is in the title ("Show HN: X is a Y that does Z")
- First comment by submitter should describe the project in detail

---

## Algolia HN Search

Official search endpoint: `https://hn.algolia.com`

API endpoint (no auth needed):
```
GET https://hn.algolia.com/api/v1/search
  ?query={q}
  &tags=story,ask_hn,show_hn   (or: comment,job)
  &dateRange=all,past24h,pastWeek,pastMonth,pastYear
  &page=0
  &hitsPerPage=20
```

Response: JSON with `hits` array, each hit has:
- `objectID`: story ID
- `title`: story title
- `url`: external URL
- `points`: score
- `author`: username
- `created_at`: ISO timestamp
- `num_comments`: comment count
- `story_text`: for Ask/Show HN with text

SolaceBrowser uses the browser-rendered version (hn.algolia.com/search) for screenshot evidence, but the API is available for bulk operations.

---

## Rate Limits and ToS

| Action | Limit |
|--------|-------|
| Page reads | None (crawler-friendly) |
| Submissions | ~1-2 per day (accounts with low karma more restricted) |
| Comments | No hard limit but flood detection exists |
| Votes | Normal browsing speed, no automated voting |
| API (Algolia) | 10,000 req/day per IP (unofficial limit) |

### Terms of Service Notes
- HN does not have a public ToS beyond "don't be a jerk"
- The community guidelines at /newsguidelines.html are the rules
- pg (Paul Graham) has commented that automated reads are fine
- Automated writes (mass submissions, vote manipulation) are not ok
- Creating multiple accounts is against the rules
