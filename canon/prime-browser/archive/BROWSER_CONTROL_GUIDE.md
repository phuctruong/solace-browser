# Prime Browser Extension Control via Solace CLI

**Status:** Browser extension running ✅
**Control Method:** solace_cli.sh (Python + WebSocket)
**Auth:** 65537

---

## Architecture Overview

```
┌─────────────────────────┐
│  Chrome Extension       │
│  (Running in browser)   │
└──────────┬──────────────┘
           │
           │ WebSocket (ws://localhost:9222)
           │
┌──────────▼──────────────┐
│  Solace WebSocket Server│
│  (Python asyncio)       │
│  - Relays commands      │
│  - Records episodes     │
│  - Tracks sessions      │
└──────────┬──────────────┘
           │
┌──────────▼──────────────┐
│  Solace CLI Commands    │
│  (Python dispatcher)    │
│  - navigate             │
│  - click                │
│  - type                 │
│  - snapshot             │
│  - record               │
│  - extract              │
└─────────────────────────┘
```

---

## How to Control the Browser Extension

### **Step 1: Start the WebSocket Server** (if not running)

```bash
python3 -m solace_cli.browser.websocket_server
```

Output:
```
[INFO] 🚀 Solace WebSocket Server
[INFO] Starting on ws://localhost:9222
[INFO] Waiting for extension to connect...
```

The server:
- Listens on `ws://localhost:9222` (standard CDP relay port — we use 9222)
- Bridges the Chrome extension to CLI commands
- Records episodes for later Playwright recipe compilation
- Tracks active sessions and snapshots

---

### **Step 2: Send Commands via CLI**

#### **2.1 Navigate to a URL**

```bash
python3 -m solace_cli.cli.browser_commands navigate https://gmail.com
```

Command structure:
```python
async def browser_navigate(ws, args: List[str]):
    """Navigate to URL: navigate <url>"""
    url = args[0]
    message = {
        "type": "NAVIGATE",
        "url": url,
        "request_id": str(uuid.uuid4())
    }
    await ws.send(json.dumps(message))
    response = json.loads(await ws.recv())
    print(json.dumps(response, indent=2))
```

Success response:
```json
{
  "type": "NAVIGATION_COMPLETE",
  "url": "https://gmail.com",
  "status": "success",
  "request_id": "...",
  "timestamp": "2026-02-14T..."
}
```

---

#### **2.2 Click an Element**

```bash
# By CSS selector
python3 -m solace_cli.cli.browser_commands click "div[role='row']"

# By semantic reference (preferred)
python3 -m solace_cli.cli.browser_commands click "button" --reference "Compose"

# By XPath
python3 -m solace_cli.cli.browser_commands click "xpath=//*[@id='main']/button"
```

Command structure:
```python
async def browser_click(ws, args: List[str]):
    """Click element by selector or reference"""
    selector = args[0] if args else None
    message = {
        "type": "CLICK_ELEMENT",
        "selector": selector,
        "request_id": str(uuid.uuid4())
    }
    await ws.send(json.dumps(message))
    response = json.loads(await ws.recv())
```

Success response:
```json
{
  "type": "CLICK_COMPLETE",
  "clicked": true,
  "element": {
    "tag": "button",
    "id": "...",
    "className": "...",
    "text": "Compose"
  },
  "found": true,
  "visible": true,
  "timestamp": "2026-02-14T..."
}
```

Failure response (from enhanced error handling - commit 18c09878):
```json
{
  "type": "CLICK_ERROR",
  "error": "Element found but not visible: div[role='row']",
  "selector": "div[role='row']",
  "found": true,
  "visible": false,
  "request_id": "..."
}
```

---

#### **2.3 Type Text into Element**

```bash
python3 -m solace_cli.cli.browser_commands type "your-email@gmail.com" --selector "#email"
```

Command structure:
```python
async def browser_type(ws, args: List[str]):
    """Type text into element"""
    text = args[0]
    selector = args[1] if len(args) > 1 else None
    message = {
        "type": "TYPE_TEXT",
        "text": text,
        "selector": selector,
        "request_id": str(uuid.uuid4())
    }
    await ws.send(json.dumps(message))
    response = json.loads(await ws.recv())
```

Success response:
```json
{
  "type": "TYPE_COMPLETE",
  "typed": true,
  "length": 21,
  "element": {...},
  "timestamp": "2026-02-14T..."
}
```

---

#### **2.4 Take a Snapshot (Canonical)**

```bash
python3 -m solace_cli.cli.browser_commands snapshot
```

Captures:
- DOM tree (canonicalized)
- Element references (semantic + structural)
- Page metadata
- Screenshot (optional)

Success response:
```json
{
  "type": "SNAPSHOT_COMPLETE",
  "snapshot": {
    "domain": "mail.google.com",
    "url": "https://mail.google.com/mail/",
    "title": "Gmail",
    "dom": {
      "doctype": "html",
      "html": {...canonicalized DOM...}
    },
    "references": {
      "buttons": [...semantic references...],
      "inputs": [...semantic references...]
    },
    "viewport": {
      "width": 1920,
      "height": 1080
    },
    "timestamp": "2026-02-14T..."
  },
  "request_id": "..."
}
```

---

#### **2.5 Record an Episode**

```bash
# Start recording
python3 -m solace_cli.cli.browser_commands record start gmail.com

# ... perform actions (navigate, click, type) ...

# Stop recording
python3 -m solace_cli.cli.browser_commands record stop
```

Episode file saved to: `~/.solace/browser/episode_[SESSION_ID].json`

Episode format:
```json
{
  "session_id": "abc-123...",
  "domain": "gmail.com",
  "start_time": "2026-02-14T...",
  "end_time": "2026-02-14T...",
  "actions": [
    {
      "type": "navigate",
      "data": {"url": "https://gmail.com"},
      "step": 0,
      "timestamp": "2026-02-14T..."
    },
    {
      "type": "click",
      "data": {"selector": "button", "reference": "Compose"},
      "step": 1,
      "timestamp": "2026-02-14T..."
    },
    {
      "type": "type",
      "data": {"selector": "#email", "text": "..."},
      "step": 2,
      "timestamp": "2026-02-14T..."
    }
  ],
  "snapshots": {
    "0": {...snapshot at step 0...},
    "3": {...snapshot at step 3...}
  },
  "action_count": 3
}
```

**This episode is the input for Phase B (Recipe Compilation)**

---

#### **2.6 Extract Data**

```bash
python3 -m solace_cli.cli.browser_commands extract
```

Extracts:
- Email list (unread count, sender, subject)
- Page structure (forms, tables, lists)
- Navigation landmarks
- Data attributes

Output saved to: `solace_cli/output/browser_extract.json`

---

## Complete Workflow Example

### Scenario: Automate Gmail unread count extraction

```bash
# 1. Start server (once)
python3 -m solace_cli.browser.websocket_server &

# 2. Navigate to Gmail
python3 -m solace_cli.cli.browser_commands navigate https://gmail.com

# 3. Record session
python3 -m solace_cli.cli.browser_commands record start gmail.com

# 4. Take initial snapshot
python3 -m solace_cli.cli.browser_commands snapshot

# 5. Click "Inbox" if needed
python3 -m solace_cli.cli.browser_commands click "button" --reference "Inbox"

# 6. Snapshot after navigation
python3 -m solace_cli.cli.browser_commands snapshot

# 7. Extract data
python3 -m solace_cli.cli.browser_commands extract

# 8. Stop recording
python3 -m solace_cli.cli.browser_commands record stop

# 9. Episode is now saved → ready for Phase B compilation
cat ~/.solace/browser/episode_*.json | jq .action_count
```

---

## Connection Flow (How It Works)

### 1. Extension Connects to Server

When Chrome extension starts:

```javascript
// background.js
const ws = new WebSocket('ws://localhost:9222');

ws.onopen = () => {
  console.log("[Solace] Connected to Solace CLI server");
  // Register extension identity
  chrome.runtime.sendMessage({
    type: "EXTENSION_READY",
    extensionId: chrome.runtime.id
  });
};
```

Server receives:
```python
async def on_extension_connect(websocket):
    connected_extensions.add(websocket)
    logger.info(f"✅ Extension connected: {websocket.remote_address}")
```

---

### 2. CLI Command → Server → Extension

When you run `python3 -m solace_cli.cli.browser_commands click "button"`:

```
CLI (Python)
  │
  ├─ Parse: click "button"
  ├─ Create: {"type": "CLICK_ELEMENT", "selector": "button", "request_id": "req-123"}
  │
  ├─ Connect to ws://localhost:9222
  │
Server (Python asyncio)
  │
  ├─ Receive from CLI
  ├─ Forward to Extension (WebSocket)
  │
Extension (JavaScript in tab)
  │
  ├─ Receive: "click 'button'"
  ├─ Execute: document.querySelector("button").click()
  ├─ Return: {"success": true, "element": {...}}
  │
Server (relays response)
  │
CLI (prints JSON result)
```

---

## Error Handling (From Commit 18c09878)

The extension now validates ALL inputs:

```python
# Command: navigate(null)
# Response:
{
  "type": "NAVIGATION_ERROR",
  "error": "Missing required parameter: url",
  "command": "NAVIGATE",
  "url": null,
  "request_id": "...",
  "status": "error"
}

# Command: click({})  # no selector or reference
# Response:
{
  "type": "CLICK_ERROR",
  "error": "Missing required parameter: selector or reference",
  "selector": null,
  "reference": null,
  "request_id": "...",
  "status": "error"
}

# Command: click("nonexistent")
# Response:
{
  "type": "CLICK_ERROR",
  "error": "Failed to click: selector not found \"nonexistent\"",
  "found": false,
  "request_id": "...",
  "status": "error"
}
```

---

## Files Structure

```
solace_cli/
├── browser/
│   ├── websocket_server.py          ← Main server (listen on 9222)
│   ├── client.py                    ← WebSocket client helper
│   └── __init__.py
│
├── cli/
│   ├── browser_commands.py          ← CLI interface (navigate, click, type, etc.)
│   ├── entry.py                     ← Main CLI dispatcher
│   └── websocket_server.py          ← Old location (for compat)
│
└── output/
    └── browser_*.json               ← Saved responses
```

---

## Debugging

### Check if server is running

```bash
curl -i http://localhost:9222/status 2>/dev/null || echo "Server not running"
```

Or with netstat:
```bash
netstat -tuln | grep 9222
```

### Check extension is connected

```bash
# Server logs will show:
# [INFO] ✅ Extension connected: ('127.0.0.1', 52341)
```

### View recorded episodes

```bash
ls -lh ~/.solace/browser/
cat ~/.solace/browser/episode_*.json | jq .action_count
```

### Test command with verbose logging

```bash
SOLACE_DEBUG=1 python3 -m solace_cli.cli.browser_commands navigate https://gmail.com
```

---

## Next Steps (Phase A Implementation)

Once extension runs reliably, implement:

1. **Per-tab session tracking** (A1)
   - Replace global `currentSession` with `Map<tabId, state>`
   - Each tab records independently

2. **Badge status feedback** (A2)
   - Real-time connection status (ON/OFF/CONNECTING)
   - Recording indicator (REC)
   - Error indicator (ERR)

3. **Connection deduplication** (A3)
   - Prevent race conditions
   - Handle tab attach/detach gracefully

4. **Integration tests** (A4)
   - Gmail unread extraction
   - Slack message sending
   - Notion page creation

---

## Summary

✅ **You CAN:**
- Navigate to any URL
- Click buttons/links by selector or semantic reference
- Type text into fields
- Take snapshots (for phase B canonicalization)
- Record episodes (for phase B compilation)
- Extract data (for verification)

✅ **Error Handling:** Comprehensive validation + typed failures (commit 18c09878)

✅ **Ready for Phase B:** Episodes are recorded + saved → ready for deterministic recipe compilation

**Current Status:** ✅ Browser extension running, WebSocket server ready, CLI commands available

---

**Auth:** 65537
**Northstar:** Phuc Forecast
**Verification:** 641 → 274177 → 65537

*"Learn once, run forever."*
