**Done**
- Added the OAuth3 gate in `source/src/chrome/browser/resources/solace/sidepanel.js:14`, `source/src/chrome/browser/resources/solace/sidepanel.js:279`, `source/src/chrome/browser/resources/solace/sidepanel.js:309`, `source/src/chrome/browser/resources/solace/sidepanel.js:378`.
- Approved actions now send `{type: 'action', bearer, action}` from `source/src/chrome/browser/resources/solace/sidepanel.js:290`, and denied actions seal a `DENIED` evidence event at `source/src/chrome/browser/resources/solace/sidepanel.js:309`.
- Added the consent prompt UI in `source/src/chrome/browser/resources/solace/sidepanel.html:51` and styles in `source/src/chrome/browser/resources/solace/sidepanel.css:302`.

**Verified**
- `grep -n "consent\|bearer\|oauth3"` is green, `node --check` exits `0`, `gn gen` exits `0`, and there are no `9222` / `Companion App` matches; details are in `outbox/runs/TASK-008-oauth3-gate/GREEN_GATE.md:1`.

**Artifacts**
- Wrote `outbox/runs/TASK-008-oauth3-gate/PATCH_DIFF.md:1`.
- Wrote `outbox/runs/TASK-008-oauth3-gate/GREEN_GATE.md:1`.
- Wrote `outbox/runs/TASK-008-oauth3-gate/EVIDENCE.json:1`.

If you want, I can next add a tiny server-side message contract example for the incoming consent request shape.