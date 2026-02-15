# Solace Browser: OpenClaw-Style Features

## Overview

Solace Browser now includes OpenClaw-like features for **structured browser interaction** with **human-like behaviors**:

- ✅ **ARIA Snapshots** - Accessibility tree with element references
- ✅ **DOM Snapshots** - Complete DOM structure
- ✅ **Structured Actions** - Unified action model (click, type, wait, hover, etc.)
- ✅ **Human-Like Behaviors** - Slow typing, delays, modifiers, hovers
- ✅ **Smart Waiting** - Wait for text, URLs, load states, conditions

---

## Quick Start

### 1. Get ARIA Snapshot (Element References)

```python
import asyncio
from solace_browser_server import SolaceBrowser

async def main():
    browser = SolaceBrowser(headless=False)
    await browser.start()
    await browser.navigate("https://example.com")

    # Get accessibility tree with element references
    result = await browser.get_aria_snapshot(limit=500)

    print("ARIA Nodes:")
    for node in result['nodes']:
        print(f"  {node['ref']:5} | {node['role']:10} | {node['name']}")

    await browser.stop()

asyncio.run(main())
```

**Output:**
```
ARIA Nodes:
  n1    | link      | Skip to main content
  n2    | heading   | Example Domain
  n3    | paragraph | Example Domain. This domain is for...
  n4    | link      | More information...
```

### 2. Get DOM Snapshot (Structure)

```python
# Get complete DOM tree with references
result = await browser.get_dom_snapshot(limit=800)

print("DOM Nodes:")
for node in result['nodes'][:10]:
    print(f"{node['ref']:5} | {node['tag']:5} | {node.get('text', '')[:50]}")
```

### 3. Get Complete Page State

```python
# Get ARIA + DOM + page state all at once
result = await browser.get_page_snapshot()

print(f"URL: {result['url']}")
print(f"ARIA nodes: {len(result['aria'])}")
print(f"DOM nodes: {len(result['dom'])}")
```

### 4. Execute Structured Actions

```python
# Click action with modifiers
await browser.act({
    "kind": "click",
    "ref": "n42",  # Element reference from ARIA/DOM
    "modifiers": ["shift"],  # Shift+click
    "button": "left"
})

# Type action with slow typing (looks human!)
await browser.act({
    "kind": "type",
    "ref": "n17",
    "text": "user@example.com",
    "slowly": True,  # Type character by character
    "delayMs": 50    # 50ms between characters
})

# Smart wait for condition
await browser.act({
    "kind": "wait",
    "text": "Success!",  # Wait for text to appear
    "timeoutMs": 10000
})

# Hover before clicking (triggers tooltips)
await browser.act({
    "kind": "hover",
    "ref": "n42"
})

# Scroll element into view
await browser.act({
    "kind": "scrollIntoView",
    "ref": "n100"
})
```

---

## All Action Types

### Click Action
```python
{
    "kind": "click",
    "ref": "n42",                    # Element reference
    "button": "left",                # or "right", "middle"
    "modifiers": ["shift", "ctrl"],  # Keyboard modifiers
    "doubleClick": False,            # or True for double-click
    "delayMs": 100,                  # Delay before clicking
    "timeoutMs": 5000                # Wait timeout
}
```

### Type Action (with human-like slow typing!)
```python
{
    "kind": "type",
    "ref": "n17",
    "text": "Hello World",
    "slowly": True,      # Type character-by-character
    "delayMs": 50,       # Delay between characters (ms)
    "submit": False,     # Or True to press Enter after
    "timeoutMs": 5000
}
```

### Press Action
```python
{
    "kind": "press",
    "key": "Enter",      # or "Tab", "Escape", etc.
    "delayMs": 100,
    "timeoutMs": 5000
}
```

### Hover Action (triggers tooltips)
```python
{
    "kind": "hover",
    "ref": "n42",
    "timeoutMs": 5000
}
```

### Scroll Into View Action
```python
{
    "kind": "scrollIntoView",
    "ref": "n100",
    "timeoutMs": 5000
}
```

### Wait Action (smart waiting!)
```python
{
    "kind": "wait",
    "text": "Loading complete",      # Wait for text to appear
    "textGone": "Loading...",      # Or wait for text to disappear
    "url": "https://success.page", # Or wait for URL change
    "selector": "n42",             # Or wait for element to appear
    "loadState": "networkidle",    # Or "load", "domcontentloaded"
    "fn": "() => !!document.querySelector('.success')",  # Custom JS
    "timeoutMs": 30000
}
```

### Fill Action (fill multiple fields)
```python
{
    "kind": "fill",
    "fields": [
        {"ref": "n5", "text": "user@example.com"},
        {"ref": "n10", "text": "password123"}
    ],
    "timeoutMs": 5000
}
```

---

## HTTP API Endpoints

### Get ARIA Snapshot
```bash
curl http://localhost:9222/api/aria-snapshot?limit=500
```

Response:
```json
{
  "success": true,
  "nodes": [
    {
      "ref": "n1",
      "role": "button",
      "name": "Submit",
      "text": "Click to submit",
      "disabled": false
    }
  ],
  "count": 42,
  "url": "https://example.com",
  "timestamp": "2026-02-14T19:30:00.000000"
}
```

### Get DOM Snapshot
```bash
curl http://localhost:9222/api/dom-snapshot?limit=800
```

### Get Page Snapshot (combined)
```bash
curl http://localhost:9222/api/page-snapshot
```

### Execute Action
```bash
curl -X POST http://localhost:9222/api/act \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "click",
    "ref": "n42"
  }'
```

---

## Why This Matters

### Before (Traditional Approach)
```
Screenshot → AI guesses selector → click("button[aria-label='...']")
❌ AI has no structured reference
❌ Looks like bot (instant actions)
❌ Can't express hover, slow typing, modifiers
```

### After (OpenClaw-Style)
```
ARIA Snapshot → AI sees "n42 is a button" → act({kind: "click", ref: "n42"})
✅ AI has structured element references
✅ Looks human-like (slow typing, hovers)
✅ Rich interaction options (modifiers, delays, etc.)
✅ Smart waiting (text, URL, conditions)
```

---

## Example: LinkedIn Auto-Login

```python
async def login_with_new_features():
    browser = SolaceBrowser(headless=False)
    await browser.start()

    # Navigate to login
    await browser.navigate("https://www.linkedin.com/login")
    await asyncio.sleep(2)

    # Get page structure
    page = await browser.get_page_snapshot()

    # Find email field in ARIA tree
    email_field = next(n for n in page['aria'] if n['role'] == 'textbox' and 'email' in (n.get('name') or '').lower())

    # Type email slowly (looks human!)
    await browser.act({
        "kind": "type",
        "ref": email_field['ref'],
        "text": "user@example.com",
        "slowly": True,
        "delayMs": 75  # Human-like typing speed
    })

    # Find password field
    password_field = next(n for n in page['aria'] if n['role'] == 'textbox' and 'password' in (n.get('name') or '').lower())

    # Type password slowly
    await browser.act({
        "kind": "type",
        "ref": password_field['ref'],
        "text": "secure_password",
        "slowly": True,
        "delayMs": 80
    })

    # Find and click submit (with delay to look natural)
    submit_btn = next(n for n in page['aria'] if n['role'] == 'button' and 'sign in' in (n.get('name') or '').lower())

    await browser.act({
        "kind": "click",
        "ref": submit_btn['ref'],
        "delayMs": 500  # Pause before clicking
    })

    # Wait for success
    await browser.act({
        "kind": "wait",
        "url": "https://www.linkedin.com/feed",
        "timeoutMs": 30000
    })

    await browser.stop()
```

---

## Key Differences from Traditional Selectors

| Feature | Traditional | OpenClaw-Style |
|---------|------------|-----------------|
| Element reference | `button[aria-label='Submit']` | `n42` |
| Type command | `.fill()` (instant) | `act({kind: "type", slowly: true})` |
| Click modifiers | Not supported | `modifiers: ["shift", "ctrl"]` |
| Hover before click | Not built-in | `act({kind: "hover"})` |
| Waiting | `wait_for_selector()` | `act({kind: "wait", text: "Success"})` |
| Scrolling | Manual `scroll_to()` | `act({kind: "scrollIntoView"})` |
| AI visibility | Screenshot + HTML | ARIA tree + DOM + Screenshot |

---

## Testing

Run the interactive test:
```bash
python3 test_aria_interactions.py
```

This will:
1. Start browser
2. Get ARIA snapshot
3. Get DOM snapshot
4. Test structured actions
5. Demonstrate human-like behaviors

---

## Files

- **`browser_interactions.py`** - Core interaction module
  - `format_aria_tree()` - Extract ARIA snapshot
  - `get_dom_snapshot()` - Extract DOM tree
  - `get_page_state()` - Combined snapshots
  - `execute_action()` - Action dispatcher

- **`solace_browser_server.py`** - Main server with new methods
  - `get_aria_snapshot()` - Browser method
  - `get_dom_snapshot()` - Browser method
  - `get_page_snapshot()` - Browser method
  - `act()` - Unified action executor
  - HTTP endpoints: `/api/aria-snapshot`, `/api/dom-snapshot`, `/api/page-snapshot`, `/api/act`

- **`test_aria_interactions.py`** - Interactive test

---

## Summary

Solace Browser now has **OpenClaw-like structured interaction** with:
- 🎯 **Element references** (n1, n2, n3...) instead of CSS selectors
- 🐢 **Human-like behaviors** (slow typing, hover, delays)
- 🤖 **Rich interaction model** (modifiers, smart waiting, multiple action types)
- 📊 **Accessibility-first design** (ARIA snapshots for AI)

This makes browser automation more effective, human-like, and easier for AI to work with! 🚀
