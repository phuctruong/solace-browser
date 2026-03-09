# GREEN GATE — TASK-008-oauth3-gate

## Step 1 — Consent markers in sidebar JS

a) Command

grep -n "consent\|bearer\|oauth3" source/src/chrome/browser/resources/solace/sidepanel.js

b) Output

```
15:    'solace.oauth3.bearer',
16:    'solace_oauth3_bearer',
17:    'oauth3_bearer',
18:    'yinyang_bearer',
19:    'bearer'
23:    'consent_request',
35:  let consentStatusOverride = null;
188:  // ── OAuth3 consent gate ───────────────────────────────────────────────────
225:    if (rawAction.__consentDescriptor === true) {
245:      __consentDescriptor: true,
260:    const consentAction = normalizeConsentAction(rawAction, sourceType);
261:    if (!consentAction) {
266:    queuedConsentActions.push(consentAction);
284:    const bearer = getOauth3Bearer();
285:    if (!bearer) {
286:      setConsentStatus('missing', 'OAuth3 bearer missing from localStorage.');
290:    if (!send({ type: 'action', bearer: bearer, action: pendingConsentAction.action })) {
309:  function logDeniedConsentEvent(consentAction) {
379:    const emptyEl = document.getElementById('consent-empty');
380:    const dialogEl = document.getElementById('consent-dialog');
381:    const promptEl = document.getElementById('consent-prompt');
382:    const detailEl = document.getElementById('consent-detail');
383:    const statusEl = document.getElementById('consent-status');
384:    const allowButton = document.getElementById('consent-allow');
396:    const bearer = getOauth3Bearer();
399:      text: 'OAuth3 bearer ready from localStorage.'
402:      text: 'OAuth3 bearer missing from localStorage.'
411:    allowButton.disabled = !bearer;
430:      const bearer = normalizeBearerValue(rawValue);
458:      return parsed.bearer || parsed.access_token || parsed.token || '';
709:    const allowButton = document.getElementById('consent-allow');
710:    const denyButton = document.getElementById('consent-deny');
```

## Step 2 — Kill checks

a) Command

rg -n "9222|Companion App" source/src/chrome/browser/resources/solace/sidepanel.js source/src/chrome/browser/resources/solace/sidepanel.html source/src/chrome/browser/resources/solace/sidepanel.css

b) Output

```
NO MATCHES
```

## Step 3 — Parse check

a) Command

node --check source/src/chrome/browser/resources/solace/sidepanel.js

b) Output

```
exit 0
```

## Step 4 — `gn gen` verify

a) Command

export PATH="/home/phuc/projects/solace-browser/depot_tools:$PATH"
gn_bin="source/src/buildtools/linux64/gn"
$gn_bin gen source/src/out/Solace --root=source/src --args="is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true"

b) Output

```
Done. Made 28708 targets from 4511 files in 3054ms
```

## Oracle Sweep

- consent in JS: FOUND
- bearer in JS: FOUND
- oauth3 in JS: FOUND
- 9222: NOT FOUND
- Companion App: NOT FOUND
- gn gen: PASS
