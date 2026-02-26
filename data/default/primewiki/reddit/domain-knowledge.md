# PrimeWiki: Reddit Domain Knowledge

**Platform**: Reddit
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21

---

## Subreddit Culture & Norms

### Post Format Rules
- **Title quality**: Most subreddits ban clickbait — titles must describe content accurately
- **Self-promotion limits**: Rule of 9:1 (9 community contributions per 1 self-promotion post)
- **Link domain ban**: Popular subreddits often ban rehosting sites (i.imgur.com alternative: i.redd.it)
- **Flair requirements**: Many subreddits require post flair — check subreddit rules before submitting
- **Text vs link**: Some subreddits allow only self-posts; others only link posts

### Karma System
- **Link karma**: Earned from post upvotes (approximate; not exact due to vote fuzzing)
- **Comment karma**: Earned from comment upvotes
- **Minimum karma thresholds**: Some subreddits require 50-1000 karma to post
- **Account age requirements**: Common: 7 days, 30 days, 90 days for posting rights
- **Vote fuzzing**: Reddit deliberately fuzzes vote counts ±5-15% to prevent bot manipulation

### AutoModerator Triggers
Common AutoModerator removal triggers that automation must avoid:
- Account age < 30 days
- Account karma < 50
- Post contains URLs to banned domains
- Post title matches forbidden regex patterns
- Username pattern (bot-like names get extra scrutiny)
- Posting in short time intervals (burst posting)
- Copy-pasted identical posts across subreddits

### Post States
| State | Visual Indicator | Meaning |
|-------|-----------------|---------|
| Active | Normal post | Visible and accepting votes/comments |
| Removed by mod | `[removed]` title | AutoModerator or mod removed — still visible to poster briefly |
| Deleted by user | `[deleted]` title | User deleted post — content gone |
| Locked | 🔒 icon | Comments disabled by moderator |
| Pinned/Stickied | Green outline | Mod-pinned, shows at top |
| NSFW | `nsfw` tag | Age-gate for NSFW communities |
| Spoiler | `spoiler` tag | Blurred content |
| OC | `oc` tag | Original content |

---

## Subreddit Types & Access Levels

| Type | Access | Bot Behavior |
|------|--------|-------------|
| Public | Open read + post | Normal automation |
| Restricted | Open read, approved-user post | Cannot post without approval |
| Private | Approved members only | Cannot read without invitation |
| Quarantined | Requires opt-in | opt-in confirmation required first |
| Banned | Not accessible | Returns 403 or redirect |
| NSFW | Requires 18+ confirmation | Session must have NSFW enabled |

### Detecting Access Level
```
old.reddit.com/r/{subreddit}/about.json → {"data": {"subreddit_type": "public"}}
Restricted: shows "you must be approved" on submit form
Private: no content visible, "This community is private"
Quarantined: "Are you sure?" interstitial before loading
```

---

## Reddit Voting System

### Vote Score Calculation
- **Score** = upvotes - downvotes (fuzzy ±10%)
- **Upvote ratio** = upvotes / (upvotes + downvotes)
- **Hot ranking** uses: log(score) + (age in hours / 12.5) formula
- Scores shown are approximate — actual counts are hidden

### Voting Constraints
- Cannot vote on own posts/comments
- Cannot re-vote (clicking again removes vote)
- Votes within 5 minutes of session start may be delayed
- Account karma < 10: votes may be hidden/not counted
- IP-based rate limiting applies to rapid voting

---

## Reddit URL Patterns

| Resource | URL Pattern |
|----------|------------|
| Homepage | `reddit.com/` |
| Subreddit | `reddit.com/r/{sub}/` |
| Subreddit (sorted) | `reddit.com/r/{sub}/{sort}/` |
| Post | `reddit.com/r/{sub}/comments/{id}/{slug}/` |
| User profile | `reddit.com/u/{username}/` |
| Search | `reddit.com/search?q={query}` |
| Subreddit search | `reddit.com/r/{sub}/search?q={query}&restrict_sr=on` |
| Submit | `reddit.com/r/{sub}/submit` |
| Old Reddit equivalent | Replace `reddit.com` with `old.reddit.com` |

### Post ID Format
- **Full name**: `t3_{base36_id}` (e.g., `t3_abc123`)
- **Short ID**: just `{base36_id}` in URLs
- **Comment full name**: `t1_{base36_id}`
- **User full name**: `t2_{base36_id}`

---

## Anti-Bot Context for Reddit

### What Reddit Monitors
1. User-Agent string — use real browser UA, not scraper UA
2. Session cookie age — fresh sessions are suspicious
3. Action velocity — more than 30 actions/minute triggers holds
4. IP reputation — residential IPs trusted more than datacenter
5. Timing patterns — perfectly timed clicks = bot indicator
6. Account history — accounts with sudden activity spikes get scrutinized

### Safe Automation Patterns
- Use a real browser session (puppeteer with real Chrome binary)
- Load cookies from a real login session (30+ day old account)
- Add 1-3 second random delays between actions
- Scroll page before clicking (humans scroll first)
- Mix in read actions between write actions
- Do not automate more than 20 posts per day
- Never post identical content across subreddits within 1 hour

---

## API vs Browser Scraping

Reddit has two tiers:
1. **Official API** (api.reddit.com) — Rate limited to 100 req/min with OAuth, requires app registration
2. **Browser scraping** (old.reddit.com) — Same rate limits as human browsing, no API key needed

SolaceBrowser uses browser scraping for:
- No API key required
- Same data as users see
- Works for content behind login walls
- Bypasses some API endpoint rate limits

Use Official API when:
- Need bulk data (1000+ items)
- Need structured JSON without HTML parsing
- Need real-time streaming data
