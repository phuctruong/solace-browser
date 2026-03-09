# GREEN GATE — TASK-005-websocket

## Step 1 — WebSocket URL check

a) Command

grep -n "8888\|9222\|ws/yinyang" source/src/chrome/browser/resources/solace/sidepanel.js

b) Output

```
2:// DNA: sidebar(ws) = connect(8888) × handle_messages × tab_switch × chat_send → native_ai_panel
4:// Connect: ws://localhost:8888/ws/yinyang
10:  const WS_URL = 'ws://localhost:8888/ws/yinyang';
```

## Step 2 — Four tabs present

a) Command

grep -n "now\|runs\|chat\|more" source/src/chrome/browser/resources/solace/sidepanel.html | head -20

b) Output

```
22:      <button class="yy-tab active" id="tab-now" role="tab" aria-selected="true" onclick="switchTab('now')">Now</button>
23:      <button class="yy-tab" id="tab-runs" role="tab" aria-selected="false" onclick="switchTab('runs')">Runs</button>
24:      <button class="yy-tab" id="tab-chat" role="tab" aria-selected="false" onclick="switchTab('chat')">Chat</button>
25:      <button class="yy-tab" id="tab-more" role="tab" aria-selected="false" onclick="switchTab('more')">More</button>
30:      <section id="panel-now" class="yy-panel active" role="tabpanel">
35:              <span id="now-status-dot" class="status-dot status-offline"></span>
36:              <span id="now-conn-status" class="yy-connection-status" aria-live="polite">Disconnected</span>
38:            <p id="now-conn-detail" class="yy-connection-detail" aria-live="polite">
55:      <!-- RUNS tab: Active and recent recipe runs -->
56:      <section id="panel-runs" class="yy-panel" role="tabpanel" aria-hidden="true">
59:          <div id="runs-list" class="yy-runs-list">
60:            <p class="yy-empty">No active runs.</p>
66:      <section id="panel-chat" class="yy-panel" role="tabpanel" aria-hidden="true">
67:        <div class="yy-chat-messages" id="chat-messages"></div>
68:        <form class="yy-chat-input" id="chat-form" onsubmit="sendChat(event)">
71:            id="chat-input"
82:      <section id="panel-more" class="yy-panel" role="tabpanel" aria-hidden="true">
```

## Step 3 — Kill checks

a) Command

grep -c "9222\|Companion App\|chrome\.runtime" source/src/chrome/browser/resources/solace/sidepanel.js

b) Output

```
0
```

## Step 4 — gn gen verify

a) Command

export PATH="/home/phuc/projects/solace-browser/depot_tools:$PATH"
gn_bin="source/src/buildtools/linux64/gn"
$gn_bin gen source/src/out/Solace --root=source/src --args="is_debug=false chrome_pgo_phase=0 is_component_build=true use_sysroot=true" 2>&1 | tail -3

b) Output

```
Done. Made 28708 targets from 4511 files in 2884ms
```

## Oracle Sweep

- ws/yinyang: FOUND
- 8888: FOUND
- 9222: NOT FOUND
- Companion App: NOT FOUND
- chrome.runtime: NOT FOUND
- chrome.sidePanel: NOT FOUND
- chrome.tabs: NOT FOUND
- silent fallback strings: NOT FOUND

```
NO MATCHES
```
