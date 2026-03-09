# PATCH DIFF — TASK-007-evidence-pipeline

- Added SHA-256 sealing for inbound Yinyang WebSocket messages in the sidebar.
- Emitted browser evidence over the existing Yinyang socket as `{type: "evidence", event: {type, ts, url, hash}}`.
- Stored the latest five sealed evidence records in sidebar state and rendered them in the Now tab.
- Reused existing sidebar list styles; no extra CSS or extension APIs added.

## Unified Diff

```diff
diff --git a/source/src/chrome/browser/resources/solace/sidepanel.js b/source/src/chrome/browser/resources/solace/sidepanel.js
--- a/source/src/chrome/browser/resources/solace/sidepanel.js
+++ b/source/src/chrome/browser/resources/solace/sidepanel.js
@@
   const WS_LABEL = 'Yinyang Server';
   const WS_URL = 'ws://localhost:8888/ws/yinyang';
   const RECONNECT_DELAY_MS = 3000;
   const MAX_RECONNECT_DELAY_MS = 30000;
+  const MAX_EVIDENCE_EVENTS = 5;
@@
   let ws = null;
   let reconnectDelay = RECONNECT_DELAY_MS;
   let reconnectTimer = null;
+  let evidenceEvents = [];
@@
   function onMessage(event) {
@@
-    handleMessage(msg);
+    emitEvidenceEvent(msg);
+    handleMessage(msg);
   }
@@
-    } else if (type === 'pong') {
+    } else if (type === 'pong') {
       // Heartbeat acknowledged — connection alive
+    } else if (type === 'evidence') {
+      recordEvidenceEvent(normalizeIncomingEvidence(msg.event || msg));
     }
   }
@@
   function renderRuns(runs) {
@@
     container.innerHTML = items.join('');
   }
+
+  function renderEvidenceEvents(events) {
+    const container = document.getElementById('evidence-list');
+    if (!container) return;
+
+    if (!events || events.length === 0) {
+      container.innerHTML = '<p class="yy-empty">No evidence events sealed yet.</p>';
+      return;
+    }
+
+    const items = events.map(function (entry) {
+      const eventType = safeText(entry.event_type || 'unknown');
+      const timestamp = safeText(formatEvidenceTimestamp(entry.timestamp));
+      const pageUrl = safeText(entry.page_url || 'about:blank');
+      const sha256 = safeText(entry.sha256 || '');
+
+      return [
+        '<div class="yy-app-item">',
+        '<div>',
+        '<span class="yy-app-name">' + eventType + '</span>',
+        '<div class="yy-about-text">' + timestamp + '</div>',
+        '<div class="yy-about-text">' + pageUrl + '</div>',
+        '</div>',
+        '<span title="' + sha256 + '">' + sha256.slice(0, 12) + '…</span>',
+        '</div>'
+      ].join('');
+    });
+
+    container.innerHTML = items.join('');
+  }
+
+  function recordEvidenceEvent(entry) {
+    if (!entry || !entry.sha256) {
+      return;
+    }
+
+    evidenceEvents = [entry].concat(evidenceEvents).slice(0, MAX_EVIDENCE_EVENTS);
+    renderEvidenceEvents(evidenceEvents);
+  }
+
+  function normalizeIncomingEvidence(entry) {
+    const normalized = entry || {};
+    return {
+      event_type: normalized.event_type || normalized.type || 'unknown',
+      timestamp: normalized.timestamp || normalized.ts || new Date().toISOString(),
+      page_url: normalized.page_url || normalized.url || getEvidencePageUrl(normalized),
+      sha256: normalized.sha256 || normalized.hash || ''
+    };
+  }
+
+  function emitEvidenceEvent(msg) {
+    const msgType = msg && msg.type;
+    if (!msgType || msgType === 'pong' || msgType === 'evidence') {
+      return;
+    }
+
+    const eventType = 'websocket_message_received:' + msgType;
+    const timestamp = new Date().toISOString();
+    const pageUrl = getEvidencePageUrl(msg);
+    const payload = {
+      event_type: eventType,
+      timestamp: timestamp,
+      page_url: pageUrl,
+      message: msg
+    };
+
+    sealEvidencePayload(payload).then(function (sha256) {
+      const sealedEvent = {
+        event_type: eventType,
+        timestamp: timestamp,
+        page_url: pageUrl,
+        sha256: sha256
+      };
+
+      recordEvidenceEvent(sealedEvent);
+      send({
+        type: 'evidence',
+        event: {
+          type: sealedEvent.event_type,
+          ts: sealedEvent.timestamp,
+          url: sealedEvent.page_url,
+          hash: sealedEvent.sha256
+        }
+      });
+    }).catch(function () {
+      updateConnectionUi('error', 'Evidence error', 'Failed to seal evidence for ' + msgType + '.');
+    });
+  }
+
+  function getEvidencePageUrl(msg) {
+    if (msg && typeof msg.url === 'string' && msg.url) {
+      return msg.url;
+    }
+
+    if (msg && typeof msg.page_url === 'string' && msg.page_url) {
+      return msg.page_url;
+    }
+
+    return window.location.href;
+  }
+
+  function sealEvidencePayload(payload) {
+    const json = stableStringify(payload);
+    const bytes = new TextEncoder().encode(json);
+
+    return window.crypto.subtle.digest('SHA-256', bytes).then(function (buffer) {
+      const hashBytes = Array.from(new Uint8Array(buffer));
+      return hashBytes.map(function (value) {
+        return value.toString(16).padStart(2, '0');
+      }).join('');
+    });
+  }
+
+  function stableStringify(value) {
+    if (Array.isArray(value)) {
+      return '[' + value.map(stableStringify).join(',') + ']';
+    }
+
+    if (value && typeof value === 'object') {
+      const keys = Object.keys(value).sort();
+      const entries = keys.map(function (key) {
+        return JSON.stringify(key) + ':' + stableStringify(value[key]);
+      });
+      return '{' + entries.join(',') + '}';
+    }
+
+    return JSON.stringify(value);
+  }
+
+  function formatEvidenceTimestamp(timestamp) {
+    const date = new Date(timestamp);
+    if (Number.isNaN(date.getTime())) {
+      return timestamp;
+    }
+
+    return date.toLocaleString();
+  }
@@
   document.addEventListener('DOMContentLoaded', function () {
     updateConnectionUi('connecting', 'Connecting...', 'Opening WebSocket to ' + WS_URL);
+    renderEvidenceEvents(evidenceEvents);
     connect();
 diff --git a/source/src/chrome/browser/resources/solace/sidepanel.html b/source/src/chrome/browser/resources/solace/sidepanel.html
--- a/source/src/chrome/browser/resources/solace/sidepanel.html
+++ b/source/src/chrome/browser/resources/solace/sidepanel.html
@@
         <div class="yy-section">
           <h3 class="yy-section-title">Quick Actions</h3>
           <div id="quick-actions" class="yy-actions"></div>
         </div>
+        <div class="yy-section">
+          <h3 class="yy-section-title">Evidence</h3>
+          <div id="evidence-list" class="yy-runs-list">
+            <p class="yy-empty">No evidence events sealed yet.</p>
+          </div>
+        </div>
       </section>
```
