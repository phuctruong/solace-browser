# PrimeWiki: HackerNews Invariants

**Platform**: Hacker News (news.ycombinator.com)
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21

---

## Hard Invariants (MUST NEVER VIOLATE)

### I-1: No Flag Automation
```
INVARIANT: No recipe may click the "flag" link on any story or comment.
Automated flagging is a severe ToS violation and can result in IP ban.
VIOLATION: Any recipe with action=click targeting [href*='flag'].
```

### I-2: No Vote Manipulation
```
INVARIANT: No recipe may upvote content on behalf of multiple accounts
or execute batch upvotes on a single account at non-human speed.
VIOLATION: Looping upvote actions on multiple stories within < 60s.
```

### I-3: Session Required for Write Operations
```
INVARIANT: All recipes with oauth3_scopes containing "hackernews.write.*"
MUST load hackernews_working_session.json as step 1.
VIOLATION: Any write recipe that does not have load_session as step 1.
```

### I-4: No Credential Injection
```
INVARIANT: No recipe step may inject literal passwords into form fields.
VIOLATION: Any step with action=type targeting input[name='pw'] or input[type='password'].
```

### I-5: Story Title Compliance
```
INVARIANT: Titles submitted via hn-submit-story MUST NOT:
  - Contain ALL_CAPS words
  - Contain exclamation marks
  - Exceed 80 characters
VIOLATION: Submitting titles that violate HN title guidelines.
```

### I-6: No Duplicate Submission Bypass
```
INVARIANT: If HN detects a duplicate URL, the recipe MUST return DUPLICATE_URL
error and NOT attempt to resubmit with a modified URL to bypass the check.
VIOLATION: Any retry logic that changes URL parameters to bypass duplicate detection.
```

---

## Soft Invariants (SHOULD hold)

### S-1: Read-Only Recipes Need No Session
```
INVARIANT: Recipes with oauth3_scopes containing only "hackernews.read.*"
SHOULD NOT require a session — all HN reads are public.
Exception: Reading personalized content (upvote state) requires session.
```

### S-2: Human-Like Submission Timing
```
INVARIANT: hn-submit-story SHOULD NOT be executed more than twice per hour
on the same account.
```

### S-3: Screenshot Before Submit
```
INVARIANT: All write recipes SHOULD capture a screenshot before the submit
action as evidence of intent.
```

---

## Must-Hold Properties Per Recipe

| Recipe | Property | Test |
|--------|----------|------|
| read-frontpage | 25-30 stories extracted | stories.length >= 25 |
| read-frontpage | All stories have title | every story.title truthy |
| read-frontpage | All stories have story_id | every story.story_id truthy |
| read-frontpage | Story IDs are numeric strings | parseInt(story_id) > 0 |
| submit-story | Redirected to /item?id= after submit | story_url contains '/item?id=' |
| submit-story | No duplicate URL (checked before submit) | no DUPLICATE_URL in submission |
| read-comments | story_id in output | output.story_id == input.story_id |
| read-comments | All comments have text | every comment.text truthy |
| read-comments | Depth pixels are multiples of 40 | depth_pixels % 40 == 0 |
| search | query echoed in output | output.query == input.query |
| search | All results have title | every result.title truthy |

---

## Forbidden Patterns

```
FORBIDDEN: Clicking .flag link on any story or comment
FORBIDDEN: Automating votes on more than 10 stories per minute
FORBIDDEN: Creating HN accounts programmatically
FORBIDDEN: Submitting the same URL more than once (duplicate bypass)
FORBIDDEN: Mass-commenting across multiple threads in rapid succession
FORBIDDEN: Accessing /vote endpoint directly (must use UI click)
FORBIDDEN: Accessing private user data (other users' emails, private messages)
FORBIDDEN: Submitting clearly off-topic stories (spam, purely promotional)
```

---

## Invariant Verification Checklist

Before marking any HN recipe as rung 641:

- [ ] Read recipes do NOT require load_session as step 1 (public access)
- [ ] Write recipes have load_session as step 1
- [ ] No recipe targets [href*='flag'] or .flag selector
- [ ] All navigate targets use https://news.ycombinator.com/ or https://hn.algolia.com/
- [ ] oauth3_scopes declared match operation (read vs write)
- [ ] error_handling.session_expired defined (even for reads — graceful no-op)
- [ ] expected_evidence has screenshots=true and agency_token=true
- [ ] metadata.idempotent=true for all read operations
- [ ] metadata.idempotent=false for submit operations
- [ ] submit recipe checks for duplicate URL in error_handling
