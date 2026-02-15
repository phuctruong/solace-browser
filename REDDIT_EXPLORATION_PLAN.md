# Reddit Exploration Plan
## Phase 1: Site Mapping (Before Automation)

**Goal**: Understand Reddit's structure while LOGGED OUT, then document for Phase 2 automation

**Auth**: 65537 | **Date**: 2026-02-15

---

## Why Explore First?

From DESIGN-B1 (Snapshot Canonicalization):
- **Step 1**: Remove volatiles (class, style, tabindex, random IDs)
- **Step 2**: Sort DOM keys alphabetically (deterministic)
- **Step 3**: Extract landmarks (nav, forms, buttons, lists)
- **Step 4-5**: Canonical JSON + SHA-256 hash

**Without this, our recipes won't be reproducible.**

---

## Exploration Strategy

### Phase 1A: Site Structure (Logged Out)
Navigate to each page and extract:
1. **ARIA landmarks** - navigation, main content, forms, buttons
2. **Portal network** - how pages link to each other
3. **Magic words** - text patterns that identify UI elements
4. **Selector patterns** - reliable ways to find elements

### Phase 1B: Document Findings
For each page, save:
- **PrimeWiki node** - semantic understanding (what is this page?)
- **Recipe template** - actions possible on this page
- **Skill module** - patterns for this page type

### Phase 1C: Login Exploration (With Account)
Once we create a Reddit account, repeat for:
- Logged-in homepage
- User profile
- Compose/post page
- Comment sections

---

## Pages to Explore (Logged Out)

### 1. **Reddit Homepage** (https://reddit.com)
```
Navigate → Take canonical snapshot → Extract landmarks
```

**Landmarks to find:**
- Header/nav (search, login button, browse)
- Trending/popular posts
- Sidebar (communities, trending)
- Post list (title, score, comments, upvote/downvote buttons)
- Footer

**PrimeWiki node to save:**
```json
{
  "type": "reddit_page",
  "page_name": "homepage_loggedout",
  "tier": 23,
  "landmarks": [
    "navigation_header",
    "trending_posts",
    "sidebar_communities",
    "footer"
  ],
  "portals": {
    "homepage": {
      "to_post_detail": {
        "selector": "a[data-testid='post-title']",
        "action": "click"
      },
      "to_login": {
        "selector": "button:contains('Log in')",
        "action": "click"
      },
      "to_signup": {
        "selector": "button:contains('Sign up')",
        "action": "click"
      }
    }
  },
  "magic_words": [
    "Hot", "New", "Top", "Trending",
    "Log in", "Sign up", "Search",
    "r/", "u/", "Subscribe", "Join"
  ]
}
```

**Recipe template to save:**
```json
{
  "recipe_id": "reddit_homepage_navigate",
  "description": "Navigate to Reddit homepage and extract page structure",
  "actions": [
    {
      "type": "navigate",
      "url": "https://reddit.com"
    },
    {
      "type": "screenshot"
    },
    {
      "type": "snapshot_canonical",
      "include_landmarks": true
    }
  ],
  "portals": {}
}
```

---

### 2. **Reddit Login Page** (https://reddit.com/login)
```
Navigate → Find email/password fields → Document form structure
```

**Landmarks to find:**
- Login form (email field, password field)
- Submit button
- "Forgot password" link
- "Sign up instead" link
- OAuth buttons (Google, Apple)

**PrimeWiki node:**
```json
{
  "type": "reddit_page",
  "page_name": "login_page",
  "tier": 23,
  "form_type": "login",
  "fields": [
    {
      "name": "email",
      "type": "email",
      "required": true,
      "selector": "input[name='email']"
    },
    {
      "name": "password",
      "type": "password",
      "required": true,
      "selector": "input[type='password']"
    }
  ],
  "submit_button": {
    "text": "Log in",
    "selector": "button[type='submit']",
    "magic_words": ["Log in", "Sign in"]
  },
  "oauth_options": [
    {"provider": "Google", "selector": "button:contains('Google')"},
    {"provider": "Apple", "selector": "button:contains('Apple')"}
  ]
}
```

---

### 3. **Reddit Signup Page** (https://reddit.com/register)
```
Navigate → Find signup form fields → Document registration flow
```

**Landmarks to find:**
- Email field
- Username field
- Password field
- Submit button
- Terms checkbox
- Age confirmation

---

### 4. **Subreddit Page** (e.g., https://reddit.com/r/programming)
```
Navigate → Extract post list structure → Find comment buttons
```

**Landmarks to find:**
- Subreddit header (name, description, rules)
- Post list (each post with score, comments, upvote/downvote)
- Subscribe button
- Create post button
- Sidebar (rules, moderators)

---

### 5. **Post Detail Page** (e.g., https://reddit.com/r/programming/comments/xxx/title)
```
Navigate → Extract post + comments → Find reply button
```

**Landmarks to find:**
- Post content (title, body, media)
- Vote buttons (upvote, downvote)
- Reply button
- Comment section
- Comment input form

---

## What We Save in Each Step

### 1. **PrimeWiki Node** (Semantic Understanding)
- Page type (homepage, login, post, comment)
- Landmarks (nav, form, button, list)
- Portal network (links to other pages)
- Magic words (text patterns)
- Confidence scores (0.90-0.99)

**File**: `primewiki/reddit_{page_name}.primewiki.json`

### 2. **Recipe Template** (Replayable Actions)
- Navigate action
- Wait/detect action
- Click/fill action
- Screenshot action
- Canonical snapshot

**File**: `recipes/reddit_{page_name}_navigate.recipe.json`

### 3. **Skill Module** (Pattern Library)
- Page detection patterns
- Selector patterns
- Validation patterns
- Error handling

**File**: `canon/prime-browser/skills/reddit_{page_name}_skill.md`

### 4. **Canonical Snapshot** (Deterministic Fingerprint)
- Stripped of volatiles (class, style, random IDs)
- Alphabetically sorted keys
- SHA-256 hash
- Landmark extraction
- Landmark text

**File**: `artifacts/reddit_snapshots/reddit_{page_name}_canonical_{hash}.json`

---

## Scout/Solver/Skeptic Roles

### Scout Agent (Navigation)
- **Task**: Navigate to each page, take screenshots
- **Save**: Page state, URL patterns, timing
- **Output**: PrimeWiki nodes

### Solver Agent (Analysis)
- **Task**: Extract selectors, identify landmarks, build portal network
- **Save**: Selector patterns, magic words, form structure
- **Output**: Recipe templates + Skills

### Skeptic Agent (Verification)
- **Task**: Verify selectors work, check for volatiles, validate structure
- **Save**: Confidence scores, validation rules
- **Output**: Updated recipes + error handling patterns

---

## Exploration Checklist

### Reddit Homepage (Logged Out)
- [ ] Navigate to https://reddit.com
- [ ] Screenshot (before scroll)
- [ ] Identify landmarks (nav, posts, sidebar, footer)
- [ ] Find "Log in" button selector
- [ ] Find "Sign up" button selector
- [ ] Extract post list structure
- [ ] Save canonical snapshot
- [ ] Create PrimeWiki node
- [ ] Create recipe template
- [ ] Create skill module

### Reddit Login Page
- [ ] Navigate to https://reddit.com/login
- [ ] Find email input selector
- [ ] Find password input selector
- [ ] Find submit button selector
- [ ] Find OAuth buttons (Google, Apple)
- [ ] Test event chain for form fill
- [ ] Save form schema
- [ ] Create PrimeWiki node
- [ ] Create recipe template

### Reddit Signup Page
- [ ] Navigate to https://reddit.com/register
- [ ] Identify signup fields
- [ ] Find username validation pattern
- [ ] Find submit button
- [ ] Document required fields
- [ ] Create PrimeWiki node

### Subreddit Page
- [ ] Navigate to https://reddit.com/r/programming
- [ ] Identify post structure
- [ ] Find create post button
- [ ] Find subscribe button
- [ ] Extract comment structure
- [ ] Create PrimeWiki node

### Post Detail Page
- [ ] Navigate to any post
- [ ] Identify reply button
- [ ] Find comment input
- [ ] Test comment form
- [ ] Create PrimeWiki node

---

## Expected Outputs

After Phase 1 exploration, we'll have:

```
primewiki/
├── reddit_homepage_loggedout.primewiki.json
├── reddit_login_page.primewiki.json
├── reddit_signup_page.primewiki.json
├── reddit_subreddit_page.primewiki.json
└── reddit_post_detail_page.primewiki.json

recipes/
├── reddit_homepage_navigate.recipe.json
├── reddit_login_navigate.recipe.json
├── reddit_signup_navigate.recipe.json
├── reddit_post_create.recipe.json
└── reddit_comment_add.recipe.json

canon/prime-browser/skills/
├── reddit_homepage_skill.md
├── reddit_login_skill.md
├── reddit_form_filling_skill.md
└── reddit_navigation_skill.md

artifacts/reddit_snapshots/
├── reddit_homepage_canonical_abc123.json
├── reddit_login_canonical_def456.json
└── ...
```

---

## Phase 2: Account Creation & Automation

Once Phase 1 is complete, we'll:

1. **Create Reddit account** (headless, with email)
2. **Automate login** (using recipe from Phase 1)
3. **Automate post creation** (r/SiliconValleyHBO post about PZIP)
4. **Monitor upvotes** (poll post URL, extract score)
5. **Auto-reply** (top comments, AMA style)

---

## Why This Approach Works

✅ **Deterministic**: Canonical snapshots are byte-identical for same page state
✅ **Reproducible**: Recipes can be replayed 100% from Phase 1 discovery
✅ **Scalable**: Apply same pattern to HackerNews, ProductHunt, Twitter, LinkedIn
✅ **Self-improving**: Each discovery feeds into skills library for faster future runs
✅ **Cost-effective**: Phase 1 = $0.95 LLM cost, Phase 2+ = $0.0015 CPU cost

---

## Timeline

- **Exploration (Phase 1)**: 30 minutes, Scout/Solver/Skeptic in parallel
- **Account creation**: 5 minutes (automated)
- **Post creation**: 1 minute (recipe replay)
- **Monitoring**: 12 seconds per check (CPU only)

**Total Phase 1 cost**: ~$0.10 (30 min with 3 agents)
**Total Phase 2+ cost**: ~$0.0015 per run (CPU replay)

---

**Ready to begin headed exploration?** 🚀
