**Done**
- Added evidence sealing + emission in `source/src/chrome/browser/resources/solace/sidepanel.js:49`, `source/src/chrome/browser/resources/solace/sidepanel.js:202`, `source/src/chrome/browser/resources/solace/sidepanel.js:251`, `source/src/chrome/browser/resources/solace/sidepanel.js:405`.
- Incoming WebSocket messages now produce a sealed event `{event_type, timestamp, page_url, sha256}` and send `{type:"evidence", event:{type, ts, url, hash}}` over the Yinyang socket.
- Added a Now-tab evidence list showing the latest 5 events in `source/src/chrome/browser/resources/solace/sidepanel.html:53`.

**Verified**
- `grep -n "evidence" source/src/chrome/browser/resources/solace/sidepanel.js` passes.
- `node --check source/src/chrome/browser/resources/solace/sidepanel.js` exits `0`.
- `gn gen source/src/out/Solace --root=source/src --args="is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true"` exits `0`.
- No `9222` or `Companion App` in `source/src/chrome/browser/resources/solace/sidepanel.js:1` or `source/src/chrome/browser/resources/solace/sidepanel.html:1`.

**Outbox**
- Wrote `outbox/runs/TASK-007-evidence-pipeline/PATCH_DIFF.md:1`
- Wrote `outbox/runs/TASK-007-evidence-pipeline/GREEN_GATE.md:1`
- Wrote `outbox/runs/TASK-007-evidence-pipeline/EVIDENCE.json:1`

If you want, I can do the next step and wire `page_url` to the active browser tab via a WebUI/C++ bridge instead of the current message-url/sidebar fallback.