# GREEN GATE — TASK-007-evidence-pipeline

## Step 1 — Evidence marker in sidebar JS

a) Command

grep -n "evidence" source/src/chrome/browser/resources/solace/sidepanel.js

b) Output

```
18:  let evidenceEvents = [];
111:    } else if (type === 'evidence') {
203:    const container = document.getElementById('evidence-list');
207:      container.innerHTML = '<p class="yy-empty">No evidence events sealed yet.</p>';
237:    evidenceEvents = [entry].concat(evidenceEvents).slice(0, MAX_EVIDENCE_EVENTS);
238:    renderEvidenceEvents(evidenceEvents);
253:    if (!msgType || msgType === 'pong' || msgType === 'evidence') {
277:        type: 'evidence',
286:      updateConnectionUi('error', 'Evidence error', 'Failed to seal evidence for ' + msgType + '.');
407:    renderEvidenceEvents(evidenceEvents);
```

## Step 2 — Kill checks

a) Command

rg -n "9222|Companion App" source/src/chrome/browser/resources/solace/sidepanel.js source/src/chrome/browser/resources/solace/sidepanel.html

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

## Step 4 — gn gen verify

a) Command

export PATH="/home/phuc/projects/solace-browser/depot_tools:$PATH"
gn_bin="source/src/buildtools/linux64/gn"
$gn_bin gen source/src/out/Solace --root=source/src --args="is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true"

b) Output

```
Done. Made 28708 targets from 4511 files in 3229ms
```

## Oracle Sweep

- evidence in JS: FOUND
- 9222: NOT FOUND
- Companion App: NOT FOUND
- gn gen: PASS
