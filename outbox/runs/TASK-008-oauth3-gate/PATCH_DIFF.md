# PATCH DIFF — TASK-008-oauth3-gate

- Added an OAuth3 consent gate in the Yinyang sidebar before agent actions are sent.
- Read bearer tokens from `localStorage` using OAuth3/bearer key fallbacks and JSON token parsing.
- Sent approved agent actions over WebSocket as `{type: "action", bearer, action}`.
- Logged denied agent actions as sealed `DENIED` evidence events and rendered them in the Now tab evidence list.
- Added sidebar HTML/CSS for the consent prompt and quick-action review controls.

## Files Changed

- `source/src/chrome/browser/resources/solace/sidepanel.js`
- `source/src/chrome/browser/resources/solace/sidepanel.html`
- `source/src/chrome/browser/resources/solace/sidepanel.css`

## Key Snippets

```diff
+  const OAUTH3_BEARER_STORAGE_KEYS = [
+    'solace.oauth3.bearer',
+    'solace_oauth3_bearer',
+    'oauth3_bearer',
+    'yinyang_bearer',
+    'bearer'
+  ];
+
+  function approvePendingConsentAction() {
+    const bearer = getOauth3Bearer();
+    if (!send({ type: 'action', bearer: bearer, action: pendingConsentAction.action })) {
+      ...
+    }
+  }
+
+  function logDeniedConsentEvent(consentAction) {
+    const payload = {
+      event_type: 'DENIED',
+      action: consentAction.action,
+      ...
+    };
+  }
+
+          <div id="consent-card" class="yy-consent-card">
+            <p id="consent-empty" class="yy-empty">No pending agent actions.</p>
+            <div id="consent-dialog" hidden>
+              <p id="consent-prompt" class="yy-consent-prompt">Allow agent to perform this action?</p>
+              <div class="yy-consent-actions">
+                <button type="button" id="consent-allow" class="yy-btn">Allow</button>
+                <button type="button" id="consent-deny" class="yy-btn yy-btn-danger">Deny</button>
+              </div>
+            </div>
+          </div>
+
+.yy-consent-card,
+.yy-action-item {
+  background: var(--yy-bg-card);
+  border: 1px solid var(--yy-border);
+  border-radius: var(--yy-radius);
+  padding: 10px;
+}
```
