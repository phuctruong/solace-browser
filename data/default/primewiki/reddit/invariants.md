# PrimeWiki: Reddit Invariants

**Platform**: Reddit (old.reddit.com)
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21

These invariants MUST hold for all Reddit automation. Violation = recipe failure or account ban.

---

## Hard Invariants (MUST NEVER VIOLATE)

### I-1: Session Required for Write Operations
```
INVARIANT: Any recipe with oauth3_scopes containing "reddit.write.*"
MUST load a valid session as step 1.
VIOLATION: Unauthenticated write → 403 or login redirect → recipe failure.
```

### I-2: old.reddit.com Always
```
INVARIANT: All navigate targets MUST use old.reddit.com domain.
new.reddit.com SPA selectors are unstable and break without notice.
VIOLATION: Use of www.reddit.com or new.reddit.com URLs.
```

### I-3: No Credential Injection
```
INVARIANT: No recipe step may inject literal username/password strings.
All auth is via session cookie files (load_session action).
VIOLATION: Any step with action=type targeting login/password fields with literal values.
```

### I-4: Post Rate Limit Respect
```
INVARIANT: No recipe may submit more than 1 post per 10 minutes on the same account.
VIOLATION: Multiple reddit-create-post recipe executions within 600s on same session.
```

### I-5: No Self-Promotion Spam
```
INVARIANT: Content submitted via reddit-create-post must not be duplicate
of content submitted to another subreddit within the previous 3600s.
VIOLATION: Cross-posting identical URL/text to >1 subreddit within 1 hour.
```

### I-6: Vote Truthfulness
```
INVARIANT: Upvote actions may only be performed on content the user
genuinely finds valuable. Mass vote brigading is prohibited.
VIOLATION: Voting on content without reading it; coordinated voting on targeted posts.
```

---

## Soft Invariants (SHOULD hold; documented exceptions allowed)

### S-1: Subreddit Rules Compliance
```
INVARIANT: Before submitting to any subreddit, check /r/{sub}/about/rules
and verify the post content complies.
Exception: Known/verified subreddits with pre-checked rules (e.g., r/test for testing).
```

### S-2: Human-Like Timing
```
INVARIANT: All typing actions SHOULD use delay_ms >= 60.
All navigate-to-click sequences SHOULD have >= 1000ms wait.
Exception: Testing environments may use faster timing.
```

### S-3: Session Freshness
```
INVARIANT: Session cookie file should be <= 7 days old.
Reddit invalidates sessions after extended inactivity.
Exception: Accounts with "stay logged in" checked may persist longer.
```

### S-4: Screenshot Evidence
```
INVARIANT: Every recipe SHOULD capture at least 2 screenshots:
  1. Page state before the primary action
  2. Page state after the primary action (confirming result)
Exception: Pure read/extraction recipes may use 1 screenshot.
```

---

## Must-Hold Properties Per Recipe

| Recipe | Property | Test |
|--------|----------|------|
| browse-subreddit | Returns non-empty posts for active public sub | posts.length > 0 |
| browse-subreddit | All posts have title | every post.title truthy |
| browse-subreddit | No score injection | score is numeric string or 'hidden' |
| create-post | Redirected to /comments/ URL after submit | url matches /comments/ |
| create-post | Session cookie loaded before form | step 1 = load_session |
| create-post | Title length <= 300 chars | len(title) <= 300 |
| read-comments | Comment body non-empty for non-deleted | body.length > 0 or is_deleted |
| read-comments | Depth attribute is numeric | int(depth) >= 0 |
| upvote-post | .upmod class present after click | has_class .upmod |
| upvote-post | Score after >= score before (or equal due to fuzzing) | score_after >= score_before |
| search | All results have title and URL | every result.url truthy |
| search | URLs point to reddit.com | url contains 'reddit.com' |

---

## Forbidden Patterns

```
FORBIDDEN: Clicking the 'report' or 'flag' link on any post or comment via automation
FORBIDDEN: Automated commenting at rate > 5 comments/minute
FORBIDDEN: Vote manipulation (voting via multiple sessions on same post)
FORBIDDEN: Posting same URL to >3 subreddits per day
FORBIDDEN: Account farming (creating new accounts to boost scores)
FORBIDDEN: Bypassing subreddit restrictions via exploit URLs
FORBIDDEN: Storing passwords in recipe files
FORBIDDEN: Logging out the session during recipe execution
FORBIDDEN: Navigating to NSFW communities without explicit opt-in in session
```

---

## Invariant Verification Checklist

Before marking any Reddit recipe as rung 641:

- [ ] Session loaded as step 1
- [ ] All navigate targets use old.reddit.com
- [ ] No literal credentials in any step text field
- [ ] Write recipes have error_handling.rate_limited defined
- [ ] All selectors match those documented in process-model.md
- [ ] oauth3_scopes declared and match actual permissions needed
- [ ] expected_evidence has screenshots=true and agency_token=true
- [ ] metadata.idempotent=false for all write operations
- [ ] error_handling.session_expired defined in every recipe
