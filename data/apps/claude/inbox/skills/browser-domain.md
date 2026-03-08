=== SKILL: BROWSER-DOMAIN (Solace Browser Specific) ===

KEY SECURITY CONSTRAINTS:
- CDP (Chrome DevTools Protocol): NO raw Runtime.evaluate. Only server-side action templates.
  Allowlisted methods: Page.navigate, Page.screenshot, DOM.getDocument, DOM.querySelector,
  Input.dispatchMouseEvent, Input.dispatchKeyEvent, Input.insertText, Emulation.setViewportSize,
  Network.getResponseBody (max 1MB, strip auth headers)
- ALL params must be schema-validated before proxying to CDP
- OAuth3 is our PROPRIETARY protocol (extends OAuth 2.0 with scoped TTL tokens, step-up auth)
- Yinyang sidebar is compiled natively into the Chromium binary as C++ WebUI — NOT a Chrome extension
- Sidebar communicates with Yinyang Server (localhost:8888) via WebSocket — no Native Messaging, no MV3
- No service workers — native binary has direct IPC; sidebar lifetime = browser lifetime

EVIDENCE CHAIN:
- Every automation action produces: before_snapshot, action, after_snapshot, SHA-256 hash
- Hash-chained, tamper-evident, append-only audit log in SQLite
- Screenshots/DOM on filesystem, hashes in DB (no BLOB bloat)

RECIPE ENGINE:
- First run: LLM generates action plan -> user approves -> plan sealed
- Replay: deterministic execution from sealed plan ($0 LLM cost)
- Target: 70% recipe hit rate by month 6
