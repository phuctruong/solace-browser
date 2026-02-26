# PrimeWiki: Reddit Process Model

**Platform**: Reddit (old.reddit.com)
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21
**C-Score**: 0.95 (Coherence — old.reddit selectors highly stable)
**G-Score**: 0.92 (Gravity — key landmarks verified)

---

## Architecture Decision: old.reddit.com vs new.reddit.com

SolaceBrowser recipes target **old.reddit.com** exclusively.

| Factor | old.reddit.com | new.reddit.com (SPA) |
|--------|---------------|----------------------|
| DOM complexity | Low (HTML tables) | High (React SPA, shadow DOM) |
| Selector stability | Very high (stable since 2012) | Low (changes with every deploy) |
| Page weight | ~200KB | ~2MB |
| Load time | 1-2s | 3-5s |
| Bot detection | Minimal | Moderate |
| Login required | Only for voting/posting | Only for voting/posting |

**Decision**: Always navigate to `old.reddit.com/{path}` in all Reddit recipes.

---

## Navigation State Machine

```
UNAUTHENTICATED
    ↓ navigate old.reddit.com
PUBLIC_FEED  (read-only, no login needed)
    ↓ load reddit_working_session.json
AUTHENTICATED
    ↓ navigate /r/{subreddit}
SUBREDDIT_LISTING
    ↓ navigate /r/{subreddit}/submit
SUBMIT_FORM
    ↓ fill + click button.save
POST_CREATED
    ↓ navigate post URL
THREAD_VIEW
    ↓ click .arrow.up
VOTE_REGISTERED
    ↓ navigate /search?q={query}
SEARCH_RESULTS
```

---

## Page Structures

### Subreddit Listing (`/r/{subreddit}`)

```html
<div class="content" role="main">
  <div id="siteTable">
    <div class="thing link" data-fullname="t3_abc123" data-type="link">
      <div class="midcol">
        <div class="arrow up"></div>           <!-- upvote button -->
        <div class="score unvoted" title="142">142</div>
        <div class="arrow down"></div>         <!-- downvote button -->
      </div>
      <div class="entry">
        <p class="title"><a class="title may-blank" href="...">Post Title</a></p>
        <p class="tagline">
          submitted by <a class="author">username</a>
          to <a class="subreddit" href="/r/programming">r/programming</a>
        </p>
        <ul class="flat-list">
          <li><a class="comments">234 comments</a></li>
        </ul>
      </div>
    </div>
  </div>
</div>
```

### Thread / Comment View (`/r/{sub}/comments/{id}/`)

```html
<div class="commentarea">
  <div class="nestedlisting">
    <div class="thing comment" data-fullname="t1_xyz789" data-depth="0">
      <div class="entry">
        <p class="tagline">
          <a class="author">commenter_name</a>
          <span class="score unvoted" title="87">87 points</span>
        </p>
        <div class="usertext-body">
          <div class="md"><p>Comment text here</p></div>
        </div>
        <div class="child">
          <!-- nested replies here -->
        </div>
      </div>
    </div>
  </div>
</div>
```

### Submit Form (`/r/{subreddit}/submit`)

```html
<form id="postsubmit">
  <input type="radio" id="kind-link" value="link" name="kind">
  <input type="radio" id="kind-self" value="self" name="kind">
  <input id="title" type="text" name="title" maxlength="300">
  <input id="url" type="text" name="url">      <!-- link post only -->
  <textarea id="text" name="text"></textarea>  <!-- self post only -->
  <button class="save" type="submit">submit</button>
</form>
```

### Search Results (`/search?q={query}`)

```html
<div class="search-result-listing">
  <div class="thing link" data-type="link" data-fullname="t3_abc123">
    <!-- same .thing structure as subreddit listing -->
    <p class="tagline">
      <a class="subreddit">r/programming</a>  <!-- shows subreddit attribution -->
    </p>
  </div>
</div>
```

---

## Key Selectors Table

| Element | Selector | Confidence |
|---------|----------|-----------|
| Main content | `.content[role='main']` | 0.98 |
| Post container | `.thing[data-type='link']` | 0.97 |
| Post title + URL | `a.title.may-blank` | 0.97 |
| Post author | `.thing .author` | 0.96 |
| Post score | `.thing .score.unvoted` | 0.95 |
| Post ID | `data-fullname` attribute | 0.99 |
| Upvote button | `.thing .arrow.up` | 0.97 |
| Upvote active | `.thing .arrow.up.upmod` | 0.97 |
| Comment count | `.thing a.comments` | 0.94 |
| Post flair | `.linkflairlabel` | 0.90 |
| Comment area | `.commentarea` | 0.98 |
| Nested listing | `.nestedlisting` | 0.97 |
| Comment body | `.comment .usertext-body .md` | 0.96 |
| Comment author | `.comment .author` | 0.97 |
| Comment score | `.comment .score.unvoted` | 0.94 |
| Comment depth | `data-depth` attribute | 0.99 |
| Submit form | `form#postsubmit` | 0.98 |
| Title input | `#title` | 0.99 |
| URL input | `#url` | 0.99 |
| Text area | `#text` | 0.99 |
| Submit button | `button.save` | 0.96 |
| Link radio | `input[value='link']` | 0.99 |
| Self radio | `input[value='self']` | 0.99 |
| Search input | `input[name='q']` | 0.99 |
| Search results | `.search-result-listing` | 0.95 |
| Stickied post | `.thing.stickied` | 0.97 |

---

## Auth State Detection

| Condition | Indicator | Action |
|-----------|-----------|--------|
| Authenticated | `.user a` with username in nav | Proceed |
| Not logged in | `.login-required` visible or no username | Load session or abort |
| Session expired | Redirected to `reddit.com/login` | Reload session cookies |
| 2FA prompted | `/challenge` URL pattern | BLOCKED — manual intervention |

---

## Rate Limits (from community knowledge)

| Action | Limit |
|--------|-------|
| Posts | 1 per 10 minutes (new accounts), 1 per 10 mins (established) |
| Comments | No hard limit, but 1/5s recommended |
| Votes | ~50/min before fuzzing starts |
| Searches | ~60/min |
| API (unofficial) | Same as browser |

---

## OAuth3 Scope Map

| Action | OAuth3 Scope | Risk |
|--------|-------------|------|
| Browse subreddit | `reddit.read.subreddit` | low |
| Read comments | `reddit.read.comments` | low |
| Search | `reddit.read.search` | low |
| Submit post | `reddit.write.submit` | medium |
| Vote | `reddit.write.vote` | medium |
| Comment | `reddit.write.comment` | medium |
| Delete post | `reddit.write.delete` | high |
