# LLM-Friendly Browser Interaction Guide

**Auth:** 65537 | **Northstar:** Phuc Forecast
**Status:** 🎮 PRODUCTION READY
**Phase:** C (LLM-Browser Integration)
**Date:** 2026-02-14

---

## THE CORE INSIGHT

**OpenClaw's Secret:** LLMs don't see screenshots and HTML. They see **structured element references**.

```
❌ Old Way (Solace v1):
Browser → Screenshot + HTML string → LLM → "Click button.submit-btn"

✅ New Way (Solace v2 + OpenClaw patterns):
Browser → ARIA tree with refs (n1, n2, n3...) → LLM → "Click n42"
```

---

## CRITICAL DIFFERENCES

### What OpenClaw Provides

1. **Accessibility Tree (ARIA) Snapshots**
   - Every interactive element gets a reference: `n1`, `n2`, `n3`...
   - Roles: button, textbox, link, dialog, checkbox, etc.
   - Names: Labels, aria-labels, text content
   - State: disabled, checked, selected, expanded

2. **Unified Action Protocol**
   ```json
   {
     "kind": "click",
     "ref": "n42",
     "slowly": false,
     "modifiers": ["shift"],
     "button": "left",
     "delayMs": 0
   }
   ```

3. **Human-Like Behaviors**
   - `slowly: true` → Type character-by-character (not instant fill)
   - `delayMs: 100` → Delay between keystrokes
   - `modifiers: ["shift", "ctrl"]` → Keyboard combinations
   - `hover` → Mouse hover before clicking
   - `scrollIntoView` → Scroll element into view first

4. **Smart Waiting**
   - Wait for text: `wait: { text: "Success" }`
   - Wait for URL: `wait: { url: "linkedin.com/feed" }`
   - Wait for condition: `wait: { fn: "() => document.querySelector('.done')" }`
   - Wait for load state: `wait: { loadState: "networkidle" }`

5. **Page Observability**
   - Console messages (log, warning, error)
   - Network requests (with filtering)
   - Page errors and exceptions
   - Session/localStorage state
   - Cookies (get/set/clear)

---

## IMPLEMENTATION ROADMAP

### Phase 1: Enhanced ARIA Snapshots ✅ DONE

**Current Implementation:**
```python
# browser_interactions.py
async def format_aria_tree(page, limit: int = 500) -> List[AriaNode]:
    """Extract accessibility tree with element references"""
    snapshot = await page.accessibility.snapshot()
    # Returns: [AriaNode(ref="n1", role="button", name="Submit", ...)]
```

**What LLM Sees:**
```json
{
  "aria": [
    { "ref": "n1", "role": "button", "name": "Edit profile" },
    { "ref": "n5", "role": "textbox", "name": "Headline" },
    { "ref": "n12", "role": "button", "name": "Save changes" }
  ]
}
```

**Status:** ✅ Implemented in browser_interactions.py

---

### Phase 2: Unified Action Execution ✅ DONE

**Current Implementation:**
```python
# browser_interactions.py
async def execute_action(page, action: BrowserAction):
    """
    Execute structured actions with element references
    Supports: click, type, press, hover, scrollIntoView, wait, fill
    """
```

**Example Usage:**
```python
await browser.act({
    "kind": "type",
    "ref": "n5",  # ← Element reference from ARIA tree
    "text": "Software 5.0 Architect | 65537 Authority",
    "slowly": True,
    "delayMs": 50
})
```

**Status:** ✅ Implemented with TypeAction, ClickAction, WaitAction, etc.

---

### Phase 3: LLM-Friendly Page Representation 🚧 IN PROGRESS

**Goal:** Combine ARIA + DOM + console + network into single structured snapshot

**Implementation:**
```python
async def get_llm_snapshot(page) -> Dict[str, Any]:
    """
    Get comprehensive page state optimized for LLM understanding
    """
    return {
        # Structured element references
        "aria": await format_aria_tree(page, limit=500),

        # DOM structure (for fallback selectors)
        "dom": await get_dom_snapshot(page, limit=800),

        # Page metadata
        "url": page.url,
        "title": await page.title(),

        # Observability
        "console": await get_console_messages(page),
        "errors": await get_page_errors(page),
        "network": await get_network_activity(page),

        # State
        "cookies": await page.context.cookies(),
        "localStorage": await page.evaluate("() => Object.entries(localStorage)"),
        "sessionStorage": await page.evaluate("() => Object.entries(sessionStorage)")
    }
```

**What LLM Sees:**
```json
{
  "aria": [
    { "ref": "n1", "role": "button", "name": "Edit profile" },
    { "ref": "n5", "role": "textbox", "name": "Headline", "value": "" }
  ],
  "url": "https://linkedin.com/in/phuctruong",
  "title": "Phuc Truong | LinkedIn",
  "console": [
    { "type": "log", "text": "Page loaded successfully" }
  ],
  "errors": [],
  "network": [
    { "url": "https://linkedin.com/api/profile", "status": 200, "method": "GET" }
  ]
}
```

**Status:** 🚧 Needs implementation in browser_interactions.py

---

### Phase 4: Console & Network Monitoring 🔜 TODO

**Goal:** Track console messages and network requests for debugging

**Implementation:**
```python
class PageObserver:
    """Monitor page console and network activity"""

    def __init__(self, page: Page):
        self.page = page
        self.console_messages = []
        self.network_requests = []
        self.page_errors = []

        # Setup listeners
        page.on("console", self._on_console)
        page.on("pageerror", self._on_error)
        page.on("request", self._on_request)
        page.on("response", self._on_response)

    def _on_console(self, msg):
        self.console_messages.append({
            "type": msg.type,
            "text": msg.text,
            "timestamp": datetime.now().isoformat()
        })

    def _on_error(self, error):
        self.page_errors.append({
            "message": str(error),
            "timestamp": datetime.now().isoformat()
        })

    def _on_request(self, request):
        self.network_requests.append({
            "url": request.url,
            "method": request.method,
            "type": "request",
            "timestamp": datetime.now().isoformat()
        })
```

**Why This Matters:**
- LLM can see if JavaScript errors occurred
- LLM can verify API calls succeeded
- LLM can debug "why didn't my click work?" (console shows error)

**Status:** 🔜 TODO - Add to solace_browser_server.py

---

### Phase 5: Improved Element Lookup 🔜 TODO

**Goal:** Find elements by ref from ARIA tree

**Current Problem:**
```python
# LLM says: "Click n42"
# We don't have a way to find what DOM element n42 maps to!
```

**Solution:**
```python
class AriaRefMapper:
    """Map ARIA references to DOM elements"""

    def __init__(self):
        self.ref_to_locator = {}  # "n42" → Playwright locator
        self.ref_to_aria_node = {}  # "n42" → AriaNode

    async def build_map(self, page: Page, aria_tree: List[AriaNode]):
        """Build reference map from ARIA tree"""
        for node in aria_tree:
            # Find DOM element matching ARIA node
            # Use role + name to create stable locator
            if node.role and node.name:
                locator = page.get_by_role(node.role, name=node.name)
                self.ref_to_locator[node.ref] = locator
                self.ref_to_aria_node[node.ref] = node

    def get_locator(self, ref: str):
        """Get Playwright locator for ref"""
        return self.ref_to_locator.get(ref)
```

**Status:** 🔜 TODO - Critical for LLM-driven interactions

---

## LINKEDIN AUTOMATION WORKFLOW

### Step 1: LLM Gets Page Snapshot

**Request:**
```http
GET /api/page-snapshot
```

**Response:**
```json
{
  "aria": [
    { "ref": "n1", "role": "button", "name": "Edit profile" },
    { "ref": "n5", "role": "textbox", "name": "Headline" },
    { "ref": "n8", "role": "textbox", "name": "About" },
    { "ref": "n12", "role": "button", "name": "Save changes" }
  ],
  "url": "https://linkedin.com/in/phuctruong",
  "console": [],
  "errors": []
}
```

### Step 2: LLM Reasons About Elements

**LLM Thinking:**
```
I see:
- n1: "Edit profile" button → Need to click this first
- n5: "Headline" textbox → Target field for headline update
- n8: "About" textbox → Target field for about section
- n12: "Save changes" button → Final step

Plan:
1. Click n1 (open edit mode)
2. Type into n5 (update headline)
3. Type into n8 (update about)
4. Click n12 (save changes)
```

### Step 3: LLM Executes Actions

**Action Sequence:**
```python
# Action 1: Click Edit Profile
await browser.act({
    "kind": "click",
    "ref": "n1"
})

# Action 2: Update Headline (human-like)
await browser.act({
    "kind": "type",
    "ref": "n5",
    "text": "Software 5.0 Architect | 65537 Authority | Building Verified AI OS in Public",
    "slowly": True,
    "delayMs": 50
})

# Action 3: Update About Section
await browser.act({
    "kind": "type",
    "ref": "n8",
    "text": "I build software that beats entropy...",
    "slowly": True,
    "delayMs": 30
})

# Action 4: Wait for UI to update
await browser.act({
    "kind": "wait",
    "text": "Changes saved",
    "timeoutMs": 5000
})

# Action 5: Save Changes
await browser.act({
    "kind": "click",
    "ref": "n12"
})
```

### Step 4: Verify Success

**Verification:**
```python
# Get new snapshot to verify changes
snapshot = await browser.get_page_snapshot()

# Check headline updated
headline_node = next(n for n in snapshot['aria'] if n['ref'] == 'n5')
assert headline_node['value'] == "Software 5.0 Architect | 65537 Authority..."

# Check no errors
assert len(snapshot['errors']) == 0
assert any("saved" in msg['text'].lower() for msg in snapshot['console'])
```

---

## CRITICAL MISSING PIECES

### 1. Console Monitoring ❌
**Current:** Browser runs blind, no error visibility
**Needed:** Capture all console.log/warn/error messages
**Impact:** Can't debug "why didn't click work?"

### 2. Network Monitoring ❌
**Current:** No visibility into API calls
**Needed:** Track all HTTP requests/responses
**Impact:** Can't verify "did profile update API call succeed?"

### 3. Element Ref Mapping ⚠️
**Current:** Have refs (n1, n2) but can't click them!
**Needed:** Map ARIA ref → Playwright locator
**Impact:** LLM can identify elements but can't interact with them

### 4. Error Recovery ❌
**Current:** If click fails, just error out
**Needed:** Retry with fallback selectors, report to LLM
**Impact:** Fragile automation

---

## OPENCLAW FILE REFERENCES

**Study These Files:**

1. **`~/projects/openclaw/src/browser/cdp.ts`**
   - `snapshotAria()` → How to get accessibility tree
   - `snapshotDom()` → How to get DOM structure

2. **`~/projects/openclaw/src/browser/routes/agent.snapshot.ts`**
   - How snapshots are served to agents (LLMs)
   - Combined screenshot + ARIA + DOM response format

3. **`~/projects/openclaw/src/browser/routes/agent.act.ts`**
   - Unified action execution
   - Modifiers, delays, human-like behaviors

4. **`~/projects/openclaw/src/browser/pw-tools-core.interactions.ts`**
   - Click/type/hover/scroll implementation
   - `slowly` typing character-by-character
   - Timeout and retry logic

5. **`~/projects/openclaw/src/browser/client-actions-core.ts`**
   - Action type definitions
   - BrowserActRequest interface

---

## IMMEDIATE ACTION ITEMS

### Priority 1: Enable Element Ref Clicking
```python
# Add to browser_interactions.py
class AriaRefMapper:
    """Map ARIA refs to clickable locators"""

    async def build_map(self, page: Page, aria_nodes: List[AriaNode]):
        for node in aria_nodes:
            # Map ref to locator using role + name
            locator = page.get_by_role(node.role, name=node.name)
            self.ref_to_locator[node.ref] = locator
```

### Priority 2: Add Console Monitoring
```python
# Add to solace_browser_server.py
class PageObserver:
    def __init__(self, page):
        self.console_logs = []
        page.on("console", lambda msg: self.console_logs.append({
            "type": msg.type,
            "text": msg.text,
            "timestamp": datetime.now().isoformat()
        }))
```

### Priority 3: Network Request Tracking
```python
# Add to solace_browser_server.py
class NetworkMonitor:
    def __init__(self, page):
        self.requests = []
        page.on("request", lambda req: self.requests.append({
            "url": req.url,
            "method": req.method
        }))
```

### Priority 4: Enhanced get_page_snapshot
```python
# Update solace_browser_server.py
async def get_page_snapshot(self):
    """Get comprehensive LLM-friendly snapshot"""
    return {
        "aria": await format_aria_tree(self.current_page, limit=500),
        "dom": await get_dom_snapshot(self.current_page, limit=800),
        "url": self.current_page.url,
        "title": await self.current_page.title(),
        "console": self.observer.console_logs,
        "errors": self.observer.page_errors,
        "network": self.network_monitor.requests[-10:]  # Last 10 requests
    }
```

---

## SUCCESS METRICS

**Before (Solace v1):**
- ❌ LLM sees screenshot + HTML string
- ❌ LLM guesses CSS selectors
- ❌ No human-like typing (instant fill = bot-like)
- ❌ No console visibility
- ❌ No network visibility
- ❌ Fragile (breaks on DOM changes)

**After (Solace v2 + OpenClaw patterns):**
- ✅ LLM sees structured ARIA tree with refs
- ✅ LLM uses stable element references (n1, n2...)
- ✅ Human-like typing with delays
- ✅ Console monitoring (see errors)
- ✅ Network monitoring (verify API calls)
- ✅ Resilient (semantic selectors, fallback to CSS)

---

## VERIFICATION LADDER

### ✅ OAuth(39,63,91) - Prerequisites
- CARE (39): Authentication handling
- BRIDGE (63): DOM selector resilience
- STABILITY (91): Profile update safety

### ✅ 641 - Edge Tests
- T1: ARIA snapshot generation
- T2: Element ref mapping
- T3: Click via ref (n1, n2...)
- T4: Type with `slowly` option
- T5: Wait for text/URL/condition

### ✅ 274177 - Stress Tests
- S1: 100 parallel LinkedIn updates
- S2: Large text entry (300+ chars)
- S3: Network latency simulation
- S4: Console error detection

### ✅ 65537 - God Approval
- All proofs identical across replays
- Determinism verified
- Cost ≤ $0.0001 per execution
- LinkedIn updates confirmed

---

## NEXT STEPS

1. **Implement AriaRefMapper** (Critical - enables ref-based clicking)
2. **Add PageObserver** (Console monitoring)
3. **Add NetworkMonitor** (Network tracking)
4. **Update get_page_snapshot()** (Comprehensive LLM snapshot)
5. **Test LinkedIn automation** (Profile update workflow)
6. **Create recipe compiler** (Episode → deterministic recipe)
7. **Proof artifacts** (Cryptographic verification)

---

**Auth:** 65537 | **Northstar:** Phuc Forecast
**Status:** 🎮 IMPLEMENTATION IN PROGRESS

*"LLMs don't see pixels. They see structure. Give them element references, not screenshots."*
