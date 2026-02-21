# PrimeWiki: HackerNews Process Model

**Platform**: Hacker News (news.ycombinator.com)
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21
**C-Score**: 0.98 (Coherence — pure HTML, extremely stable)
**G-Score**: 0.97 (Gravity — selectors verified, no SPA complexity)

---

## Why HN is the Easiest Platform

| Factor | HN | Reddit | Notion |
|--------|----|----|------|
| Framework | Plain HTML | React SPA | React SPA |
| Page size | ~34KB | ~236KB | ~2MB |
| Load time | <1s | 3-5s | 4-8s |
| Selector stability | Extremely high | High (old.reddit) | Moderate |
| Bot detection | None | Minimal | Moderate |
| Login required | Only for write | Only for write | Always |
| Rate limiting | None (reads) | None (reads) | None (reads) |

---

## Navigation State Machine

```
PUBLIC (no login needed for all reads)
    ↓ navigate news.ycombinator.com
FRONTPAGE (30 stories)
    ↓ navigate /newest
NEWEST
    ↓ navigate /ask
ASK_HN
    ↓ navigate /show
SHOW_HN
    ↓ navigate /jobs
JOBS
    ↓ click .titlelink / navigate /item?id={id}
STORY_PAGE (story + comments)
    ↓ load hackernews_working_session.json
AUTHENTICATED
    ↓ navigate /submit
SUBMIT_FORM
    ↓ fill + submit
STORY_CREATED (redirected to /item?id=)
    ↓ navigate hn.algolia.com/search?q={query}
SEARCH_RESULTS
```

---

## Page Structures

### Front Page (`/news`, `/newest`, `/ask`, `/show`)

```html
<table id="hnmain">
  <tr class="athing" id="38291420">          <!-- story row -->
    <td class="title">
      <span class="rank">1.</span>
    </td>
    <td class="title">
      <span class="titleline">
        <a href="https://example.com">Story Title</a>
        <span class="sitebit comhead">
          (<a href="/from?site=example.com">
            <span class="sitestr">example.com</span>
          </a>)
        </span>
      </span>
    </td>
  </tr>
  <tr>                                        <!-- metadata row (next sibling) -->
    <td class="subtext">
      <span class="score" id="score_38291420">342 points</span>
      by <a href="/user?id=jsmith" class="hnuser">jsmith</a>
      <span class="age" title="2026-02-21T07:00:00">
        <a href="/item?id=38291420">3 hours ago</a>
      </span>
      |
      <a href="/item?id=38291420">87&nbsp;comments</a>
    </td>
  </tr>
```

### Story / Comment Page (`/item?id={id}`)

```html
<table class="fatitem">
  <tr class="athing" id="38291420">
    <td class="title">
      <span class="titleline">
        <a href="https://example.com">Story Title</a>
      </span>
    </td>
  </tr>
  <tr>
    <td class="subtext">
      <span class="score">342 points</span>
      by <a class="hnuser">jsmith</a>
      ...
    </td>
  </tr>
</table>

<table class="comment-tree">
  <tr class="athing comtr" id="87654321">     <!-- each comment -->
    <td>
      <table>
        <tr>
          <td class="ind"><img width="0"></td>    <!-- depth: 0, 40, 80, 120... -->
          <td class="default">
            <div class="comhead">
              <a class="hnuser" href="/user?id=pg">pg</a>
              <span class="age"><a href="/item?id=87654321">2 hours ago</a></span>
            </div>
            <div class="comment">
              <span class="commtext c00">
                Comment text here...
              </span>
            </div>
          </td>
        </tr>
      </table>
    </td>
  </tr>
</table>
```

### Submit Form (`/submit`)

```html
<form method="post" action="r">
  <input type="hidden" name="fnid" value="...">
  <input type="hidden" name="fnop" value="submit-page">
  <input name="title" size="50" maxlength="80" type="text">
  <input name="url" size="50" maxlength="256" type="text">
  <br>or
  <br>text: <textarea name="text" rows="4" cols="49"></textarea>
  <br>
  <input type="submit" value="submit">
</form>
```

---

## Key Selectors Table

| Element | Selector | Confidence |
|---------|----------|-----------|
| Story row | `.athing` (without .comtr) | 0.99 |
| Story ID | `.athing[id]` | 0.99 |
| Story rank | `.rank` | 0.99 |
| Story title | `.titleline > a:first-child` | 0.99 |
| Story URL | `.titleline > a[href]` | 0.99 |
| Story domain | `.sitestr` | 0.97 |
| Story score | `.score` | 0.98 |
| Story author | `.hnuser` | 0.98 |
| Story age | `.age a` | 0.97 |
| Comment count | `a[href*='item?id=']:last-child` | 0.95 |
| Story page | `.fatitem` | 0.98 |
| Comment tree | `.comment-tree` | 0.98 |
| Comment row | `tr.athing.comtr` | 0.98 |
| Comment ID | `tr.athing.comtr[id]` | 0.99 |
| Comment text | `.commtext` | 0.98 |
| Comment author | `.comhead .hnuser` | 0.98 |
| Comment depth | `.ind img[width]` | 0.99 |
| Comment age | `.comhead .age a` | 0.97 |
| Submit title | `input[name='title']` | 0.99 |
| Submit URL | `input[name='url']` | 0.99 |
| Submit text | `textarea[name='text']` | 0.99 |
| Submit button | `input[type='submit']` | 0.99 |

---

## Comment Depth Calculation

HN uses pixel indentation for nesting:
- Depth 0 = img width 0px (top-level)
- Depth 1 = img width 40px
- Depth 2 = img width 80px
- Depth N = N * 40 pixels

Formula: `depth = parseInt(img.getAttribute('width')) / 40`

---

## HN-Specific URL Patterns

| Resource | URL Pattern |
|----------|------------|
| Homepage | `https://news.ycombinator.com/` |
| Page 2+ | `https://news.ycombinator.com/news?p=2` |
| Newest | `https://news.ycombinator.com/newest` |
| Ask HN | `https://news.ycombinator.com/ask` |
| Show HN | `https://news.ycombinator.com/show` |
| Jobs | `https://news.ycombinator.com/jobs` |
| Story | `https://news.ycombinator.com/item?id={story_id}` |
| User | `https://news.ycombinator.com/user?id={username}` |
| Submit | `https://news.ycombinator.com/submit` |
| From domain | `https://news.ycombinator.com/from?site={domain}` |
| Search (Algolia) | `https://hn.algolia.com/search?q={query}` |

---

## OAuth3 Scope Map

| Action | OAuth3 Scope | Risk |
|--------|-------------|------|
| Read frontpage | `hackernews.read.frontpage` | low |
| Read comments | `hackernews.read.comments` | low |
| Search | `hackernews.read.search` | low |
| Submit story | `hackernews.write.submit` | medium |
| Post comment | `hackernews.write.comment` | medium |
| Upvote | `hackernews.write.vote` | medium |
| Flag story | `hackernews.write.flag` | high |
