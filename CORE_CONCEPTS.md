# Solace Browser Core Concepts

**Understand how Solace Browser works.** The fundamental ideas behind the system.

---

## 1. Persistent Browser Server (20x Speed)

### The Problem

Traditional browser automation:
- Start Chrome (2s)
- Navigate to page (1s)
- Interact (0.5s)
- Close Chrome (1s)
- **Per task: 4.5 seconds**

### The Solution

Keep a browser running continuously. Clients connect, use it, disconnect. The browser stays open.

```
Traditional:  Start → Navigate → Act → Close (4.5s each action)
Solace:       Connect → Act → Disconnect (0.1s each action)
                          ↓
                  Browser stays running
```

### How It Works

```bash
# 1. Start server (once, stays running)
python persistent_browser_server.py

# 2. Clients send HTTP requests
curl -X POST http://localhost:9222/navigate -d '{"url": "..."}'
curl -X POST http://localhost:9222/click -d '{"selector": "..."}'
curl http://localhost:9222/html-clean

# 3. Server executes in the persistent browser
# 4. Client receives result immediately

# Browser never closes (unless you stop the server)
```

### Speed Gains

| Operation | Traditional | Solace | Improvement |
|-----------|-------------|--------|-------------|
| Navigate | 3.0s | 0.1s | 30x faster |
| Click | 1.0s | 0.05s | 20x faster |
| Fill form | 2.0s | 0.1s | 20x faster |
| Per page | 30-60s | 2-3s | **20x faster** |

---

## 2. Page Snapshots (Multi-Channel Understanding)

### What Claude Needs

Claude can't see websites the same way humans do. So Solace provides **five complementary views** of each page:

1. **Raw HTML**: Exact page markup
2. **Cleaned HTML**: Simplified structure (human-readable)
3. **ARIA Tree**: Accessibility tree (semantic structure)
4. **Screenshot**: Visual representation
5. **Console Logs**: JavaScript errors and warnings

### Example: LinkedIn Login Page

```
Raw HTML (too verbose):
<div class="auth-form__form-container" role="form" ...>
  <div class="text-input-wrapper">
    <input id="username" ... />
  </div>
  ...
</div>

Cleaned HTML (readable):
<form>
  <input id="username" placeholder="Email or phone" />
  <input id="password" type="password" placeholder="Password" />
  <button aria-label="Sign in">Sign in</button>
</form>

ARIA Tree (semantic):
form
├─ input#username [required]
├─ input#password [required]
└─ button "Sign in"
```

### Why Multiple Views?

- **Raw HTML**: Precise selectors, debug actual structure
- **Cleaned HTML**: LLM understanding, logical organization
- **ARIA Tree**: Accessible names, semantic meaning
- **Screenshot**: Visual confirmation, see what humans see
- **Console**: Errors that blocked progress

### Using Snapshots in Your Code

```bash
# Get cleaned HTML (best for Claude)
curl http://localhost:9222/html-clean | jq -r '.html'

# Get ARIA tree (for semantic understanding)
curl http://localhost:9222/aria | jq '.tree'

# Get full snapshot (all views + metadata)
curl http://localhost:9222/snapshot | jq '.'
```

---

## 3. Selector Resolution (Finding Elements)

### CSS Selectors

Selectors are how you tell the browser "click this button" or "fill that input".

#### Basic Patterns

```css
/* By ID */
#username

/* By attribute */
input[type="email"]
button[aria-label="Save"]

/* By tag + class */
button.primary
form.login

/* Combined */
div.form input[type="password"]

/* Text matching */
button:has-text("Save")
a:contains("Learn More")
```

#### Finding Good Selectors

```bash
# 1. Get HTML
curl http://localhost:9222/html-clean | jq -r '.html'

# 2. Look for distinguishing features
# Examples:
# - id="email" → #email
# - type="submit" → button[type="submit"]
# - aria-label="Next" → button[aria-label="Next"]
# - class="primary" → .primary

# 3. Test selector in browser
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button:has-text(\"Next\")", "dryrun": true}'
# Returns: element found (or not found)
```

### Selector Strength

Some selectors are more reliable than others:

| Selector | Strength | Why |
|----------|----------|-----|
| `#email` | 0.99 | ID is unique |
| `button[aria-label="Save"]` | 0.95 | Accessibility labels rarely change |
| `.primary.large` | 0.80 | Multiple classes can be fragile |
| `div:nth-child(3) button` | 0.50 | Position is very fragile |
| `button:has-text("Save")` | 0.85 | Text can change |

**Rule**: Prefer IDs, then data attributes, then ARIA labels, last resort: text content.

---

## 4. Knowledge Capture (Recipes & PrimeWiki)

### Why Knowledge Capture?

After learning how to log in to LinkedIn, why repeat that learning next time?

**Answer**: Save the knowledge.

### Recipes (Execution Instructions)

A recipe captures **how to do something** in a reproducible way:

```json
{
  "recipe_id": "linkedin-login",
  "reasoning": {
    "research": "LinkedIn requires email or phone + password",
    "strategy": "Fill email field, then password, then click login",
    "llm_learnings": "LinkedIn has rate limiting - adds 3s delay after failed attempt"
  },
  "portals": {
    "login_page": {
      "email_field": {
        "selector": "#username",
        "type": "fill",
        "strength": 0.99
      },
      "password_field": {
        "selector": "#password",
        "type": "fill",
        "strength": 0.99
      },
      "sign_in_button": {
        "selector": "button:has-text('Sign in')",
        "type": "click",
        "strength": 0.95
      }
    }
  },
  "execution_trace": [
    {"action": "navigate", "url": "https://linkedin.com/login"},
    {"action": "fill", "selector": "#username", "text": "user@example.com"},
    {"action": "fill", "selector": "#password", "text": "password"},
    {"action": "click", "selector": "button:has-text('Sign in')"}
  ],
  "next_ai_instructions": "If sign-in fails, wait 3s and retry (LinkedIn rate limits)"
}
```

Save to: `recipes/linkedin-login.recipe.json`

### PrimeWiki (Knowledge Nodes)

A PrimeWiki node captures **what you learned** with evidence:

```markdown
# PrimeWiki Node: LinkedIn Login Selectors

**Tier**: 47/127 (well-established pattern)
**Verified**: 2026-02-15 (fresh data)
**Success Rate**: 98% (across 47 logins)

## Claim Graph (Why This Works)

LinkedIn login uses standard accessibility selectors:
- Email/phone input: id="username" (unique ID)
- Password input: type="password" (semantic type)
- Sign-in button: aria-label="Sign in" (accessibility label)

These rarely change because they're part of accessibility standards.

## Portals (Where to Navigate)

From: LinkedIn login page
- If login succeeds → You see your feed
- If login fails → You see error message + retry option

## Evidence

- Evidence 1: Tested 47 times in last 30 days (success: 46, failure: 1)
- Evidence 2: LinkedIn accessibility audit (verified selectors in their own code)
- Evidence 3: LLM confidence: 0.98 (high confidence pattern)

## Execution Code

```python
async def login_linkedin(email, password):
    await browser.navigate("https://linkedin.com/login")
    await browser.fill("#username", email)
    await browser.fill("#password", password)
    await browser.click("button[aria-label='Sign in']")
    await browser.wait_for("xpath=//a[contains(., 'My Network')]")
    return True
```
```

Save to: `primewiki/linkedin_login.primewiki.md`

### Relationship

- **Recipe**: "How do I execute this?" (procedural)
- **PrimeWiki**: "Why does this work?" (evidence-based)
- **Together**: Execute with confidence + understand edge cases

---

## 5. Browser State & Verification

### State Types

The browser maintains three types of state:

1. **URL State**: Where are you? (current page)
2. **DOM State**: What's on the page? (HTML structure)
3. **Session State**: Who are you? (cookies, auth tokens)

### Verifying State

**Never assume an action worked. Always verify.**

```bash
# 1. Click a button
curl -X POST http://localhost:9222/click \
  -d '{"selector": "button:has-text(\"Next\")"}'

# 2. Get new state
curl http://localhost:9222/html-clean | jq -r '.url'
# Returns: "https://example.com/step-2"

# 3. Check for expected element
curl http://localhost:9222/html-clean | jq -r '.html' | grep -i "step 2"

# Success! URL changed AND expected content visible.
```

### Evidence Collection Pattern

**LOOK-FIRST → ACT → VERIFY-RESULT**

```bash
# LOOK: Get current state
BEFORE=$(curl http://localhost:9222/html-clean | jq -r '.html')
URL_BEFORE=$(curl http://localhost:9222/html-clean | jq -r '.url')

# ACT: Do something
curl -X POST http://localhost:9222/fill \
  -d '{"selector": "#email", "text": "user@example.com"}'

# VERIFY: Check result
AFTER=$(curl http://localhost:9222/html-clean | jq -r '.html')
echo "Email field filled: $AFTER" | grep "user@example.com"
# Should contain: "user@example.com"
```

---

## 6. Speed Optimization Details

### What Makes Solace Fast?

1. **Persistent Browser**: No startup overhead (20x)
2. **Smart Waiting**: Wait for specific elements, not arbitrary time (10x)
3. **Parallel Snapshots**: Get HTML + ARIA + screenshot simultaneously (2x)
4. **Cached Parsing**: HTML parsing cached when possible (1.5x)

Combined: **30-50x faster** per action, **20x faster** end-to-end.

### Wait Strategies

```javascript
// ❌ Slow: Arbitrary sleep
await page.goto(url, { waitUntil: 'networkidle' });
await sleep(1000);  // Wait 1 second for good measure
// This waits unnecessarily if page loads in 100ms

// ✅ Fast: Wait for element
await page.goto(url, { waitUntil: 'domcontentloaded' });
await page.waitForSelector('button[aria-label="Save"]');
// Returns immediately when element appears
```

---

## 7. Multi-Channel Encoding

### Visual Pattern Recognition

Elements can be encoded by **visual attributes** that humans instantly recognize:

- **Shape**: Button = rectangle, Link = underline, Form = box
- **Color**: Blue = navigate, Green = confirm, Red = warning, Gray = disabled
- **Hierarchy**: Large text = title, Small text = label, Outline = important
- **Texture**: Solid = actionable, Transparent = disabled, Dotted = temporary

### Why This Matters

Humans look at a page and instantly see: "There's a red button that says 'Cancel'". But Claude reads HTML and needs to infer meaning.

By capturing **visual encoding** in the ARIA tree and cleaned HTML, Claude gets the same semantic understanding humans do.

```
Visual: Red rectangle button with white text "Cancel"
         ↓
ARIA: button[aria-label="Cancel" role="button" aria-disabled="false"]
       style="background: #ff4444; color: white; padding: 10px 20px;"
         ↓
Claude understands: "This is a critical action button that cancels the current operation"
```

---

## 8. Session Persistence

### Why Save Sessions?

Logging in takes 20-30 seconds. If you re-login every time, 30 tasks = 10 minutes of login time.

**Solution**: Save authentication cookies once, reuse them.

### How It Works

```bash
# 1. Login and save cookies
curl -X POST http://localhost:9222/save-session
# Saves to: artifacts/session.json

# 2. Next time, load cookies before visiting
curl -X POST http://localhost:9222/load-session \
  -d '{"session_file": "artifacts/session.json"}'

# 3. Navigate to protected page (already logged in!)
curl -X POST http://localhost:9222/navigate \
  -d '{"url": "https://linkedin.com/in/me/"}'

# 4. Confirmation
curl http://localhost:9222/html-clean | jq -r '.html' | grep "Edit profile"
# Success! You're logged in without re-entering password.
```

### When Sessions Expire

Some websites expire sessions after 7 days. Plan accordingly:

```bash
# Check session age
ls -l artifacts/session.json

# If older than 7 days, re-login and save new session
# Most websites: keep for 30 days
# High-security sites (banking): keep for 1 day
```

---

## 9. Error Handling & Recovery

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| "Selector not found" | Element doesn't exist or selector is wrong | Get fresh HTML, verify selector exists |
| "Timeout waiting for element" | Element takes too long to appear | Increase wait timeout in config |
| "Session expired" | Cookies too old or revoked | Re-login and save new session |
| "Bot detected" | Website blocked automated traffic | Add delays, rotate user agents, use proxies |

### Recovery Pattern

```python
def try_action_with_recovery(action, max_retries=3):
    for attempt in range(max_retries):
        try:
            result = action()
            return result
        except SelectorNotFound:
            # Get fresh HTML, find new selector
            html = get_html()
            # Analyze and adjust selector
            action.update_selector(find_correct_selector(html))
        except SessionExpired:
            # Re-login
            login()
            # Retry
    raise FinalFailure("Action failed after 3 retries")
```

---

## 10. Architecture Diagram

```
Client (You)
    ↓
    ├─ curl requests (HTTP)
    ↓
Persistent Browser Server
    ├─ HTTP Handler (receives requests)
    ├─ Playwright Browser (maintains state)
    ├─ Page (current page in focus)
    ├─ ARIA Tree Extractor
    ├─ HTML Cleaner
    └─ Screenshot Capturer
    ↓
    ├─ Returns: JSON response
    │   ├─ html (cleaned)
    │   ├─ aria (tree structure)
    │   ├─ screenshot (PNG)
    │   ├─ url (current page)
    │   └─ metadata
    ↓
Client processes response
```

---

## Next Steps

- **Ready to try it?** → Go to [QUICK_START.md](./QUICK_START.md)
- **Want to debug?** → Go to [DEVELOPER_DEBUGGING.md](./DEVELOPER_DEBUGGING.md)
- **Ready for advanced?** → Go to [ADVANCED_TECHNIQUES.md](./ADVANCED_TECHNIQUES.md)
- **Need full API?** → Go to [API_REFERENCE.md](./API_REFERENCE.md)

---

**Key Takeaway**: Solace Browser = Persistent browser (20x faster) + Multi-channel snapshots (Claude understands) + Knowledge capture (no rediscovery waste)
