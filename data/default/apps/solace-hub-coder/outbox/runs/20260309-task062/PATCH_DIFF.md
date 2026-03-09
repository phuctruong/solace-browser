# Task 062 Patch Diff

## yinyang_server.py
     # Task 062 — App Onboarding: Grey-to-Green 4-State Lifecycle UI
     # ---------------------------------------------------------------------------
 
+    def _app_name(self, app_id: str) -> str:
+        return app_id.replace("-", " ").title()
+
+    def _app_icon(self, app_id: str) -> str:
+        normalized = app_id.lower()
+        if "gmail" in normalized:
+            return "📧"
+        if "slack" in normalized:
+            return "💬"
+        if "drive" in normalized:
+            return "📁"
+        if "linkedin" in normalized:
+            return "💼"
+        return "📦"
+
+    def _app_setup_fields(self, app_id: str) -> list[dict[str, Any]]:
+        normalized = app_id.lower()
+        if "gmail" in normalized:
+            return [{
+                "name": "oauth_token",
+                "type": "oauth",
+                "required": True,
+                "description": "Gmail OAuth token",
+                "placeholder": "Paste Gmail OAuth token",
+            }]
+        if "slack" in normalized:
+            return [{
+                "name": "oauth_token",
+                "type": "oauth",
+                "required": True,
+                "description": "Slack OAuth token",
+                "placeholder": "Paste Slack OAuth token",
+            }]
+        if "drive" in normalized:
+            return [{
+                "name": "oauth_token",
+                "type": "oauth",
+                "required": True,
+                "description": "Google Drive OAuth token",
+                "placeholder": "Paste Google Drive OAuth token",
+            }]
+        if "linkedin" in normalized:
+            return [{
+                "name": "oauth_token",
+                "type": "oauth",
+                "required": True,
+                "description": "LinkedIn OAuth token",
+                "placeholder": "Paste LinkedIn OAuth token",
+            }]
+        return []
+
+    def _app_setup_requirements_payload(self, app_id: str) -> dict[str, Any]:
+        fields = self._app_setup_fields(app_id)
+        vault_key = f"oauth3:{app_id}" if any(field.get("type") == "oauth" for field in fields) else None
+        return {
+            "app_id": app_id,
+            "fields": fields,
+            "vault_key": vault_key,
+        }
+
+    def _app_config_path(self, app_id: str) -> Path:
+        return Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
+
+    def _app_config_key(self, app_id: str) -> bytes:
+        session_token_sha256 = getattr(self.server, "session_token_sha256", "")
+        normalized_token = session_token_sha256 if _SHA256_HEX_RE.fullmatch(session_token_sha256) else ("0" * 64)
+        salt_hex = hashlib.sha256(app_id.encode("utf-8")).hexdigest()
+        kdf = PBKDF2HMAC(
+            algorithm=hashes.SHA256(),
+            length=32,
+            salt=bytes.fromhex(salt_hex),
+            iterations=OAUTH3_PBKDF2_ITERATIONS,
+        )
+        return kdf.derive(normalized_token.encode("utf-8"))
+
+    def _encrypt_app_config(self, app_id: str, config: dict[str, Any]) -> dict[str, Any]:
+        plaintext = json.dumps(
+            {"app_id": app_id, "config": config},
+            sort_keys=True,
+            separators=(",", ":"),
+        ).encode("utf-8")
+        nonce = secrets.token_bytes(12)
+        ciphertext = AESGCM(self._app_config_key(app_id)).encrypt(nonce, plaintext, None)
+        return {
+            "app_id": app_id,
+            "cipher": "AES-256-GCM",
+            "nonce_b64": base64.b64encode(nonce).decode("ascii"),
+            "ciphertext_b64": base64.b64encode(ciphertext).decode("ascii"),
+            "ciphertext_sha256": hashlib.sha256(ciphertext).hexdigest(),
+            "kdf": {
+                "algorithm": "PBKDF2-HMAC-SHA256",
+                "iterations": OAUTH3_PBKDF2_ITERATIONS,
+                "salt_hex": hashlib.sha256(app_id.encode("utf-8")).hexdigest(),
+            },
+        }
+
+    def _app_config_complete(self, app_id: str) -> bool:
+        config_path = self._app_config_path(app_id)
+        try:
+            envelope = json.loads(config_path.read_text())
+        except FileNotFoundError:
+            return False
+        except json.JSONDecodeError:
+            return False
+        except OSError:
+            return False
+        if not isinstance(envelope, dict):
+            return False
+        required_keys = {"cipher", "nonce_b64", "ciphertext_b64", "ciphertext_sha256", "kdf"}
+        return envelope.get("cipher") == "AES-256-GCM" and required_keys.issubset(envelope)
+
     def _handle_apps_lifecycle(self) -> None:
         """GET /api/v1/apps/lifecycle — list all apps with their current state."""
         if not self._check_auth():
             return
         apps = getattr(self.server, "apps", [])
         result = []
         for app_id in (apps if isinstance(apps, list) else []):
-            config_path = Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
-            is_configured = config_path.exists()
+            setup_requirements = self._app_setup_requirements_payload(app_id)
+            is_configured = self._app_config_complete(app_id)
             result.append({
                 "app_id": app_id,
-                "name": app_id.replace("-", " ").title(),
-                "icon": "\U0001F4E6",
+                "name": self._app_name(app_id),
+                "icon": self._app_icon(app_id),
                 "state": "activated" if is_configured else "installed",
-                "config_required": [],
+                "config_required": [field["name"] for field in setup_requirements["fields"] if field.get("required")],
                 "config_complete": is_configured,
             })
         self._send_json({"apps": result})
 
     def _handle_app_setup_requirements(self, app_id: str) -> None:
         """GET /api/v1/apps/{app_id}/setup-requirements — fields needed to activate."""
         if not self._check_auth():
             return
-        self._send_json({
-            "app_id": app_id,
-            "fields": [],
-            "vault_key": None,
-        })
+        self._send_json(self._app_setup_requirements_payload(app_id))
 
     def _handle_app_activate(self, app_id: str) -> None:
         """POST /api/v1/apps/{app_id}/activate — store encrypted config, mark activated."""
         if not self._check_auth():
             return
-        try:
-            content_length = int(self.headers.get("Content-Length", 0))
-            body = json.loads(self.rfile.read(content_length) or b"{}") if content_length else {}
-        except json.JSONDecodeError:
-            self._send_json({"error": "Invalid JSON"}, 400)
+        body = self._read_json_body()
+        if body is None:
+            return
+        config = body.get("config", {})
+        if not isinstance(config, dict):
+            self._send_json({"error": "config must be an object"}, 400)
             return
-        config_dir = Path.home() / ".solace" / "app-configs"
+        required_fields = [field["name"] for field in self._app_setup_fields(app_id) if field.get("required")]
+        missing_fields = []
+        for field_name in required_fields:
+            value = config.get(field_name)
+            if value is None or (isinstance(value, str) and not value.strip()):
+                missing_fields.append(field_name)
+        if missing_fields:
+            self._send_json({"error": "missing required config fields", "missing_fields": missing_fields}, 400)
+            return
+        config_path = self._app_config_path(app_id)
         try:
-            config_dir.mkdir(parents=True, exist_ok=True)
+            config_path.parent.mkdir(parents=True, exist_ok=True)
         except OSError as e:
             self._send_json({"error": f"Could not create config dir: {e}"}, 500)
             return
-        config_path = config_dir / f"{app_id}.json"
+        envelope = self._encrypt_app_config(app_id, config)
         try:
-            config_path.write_text(json.dumps({"app_id": app_id, "configured": True}))
+            config_path.write_text(json.dumps(envelope, sort_keys=True, separators=(",", ":")))
         except OSError as e:
             self._send_json({"error": f"Could not save config: {e}"}, 500)
             return
-        self._send_json({"activated": True, "app_id": app_id, "state": "activated"})
+        self._send_json({
+            "activated": True,
+            "app_id": app_id,
+            "state": "activated",
+            "local_storage": {"key": f"app:{app_id}:state", "value": "activated"},
+        })
 
     def _handle_app_deactivate(self, app_id: str) -> None:
         """DELETE /api/v1/apps/{app_id}/activate — reset to installed state."""
         if not self._check_auth():
             return
-        config_path = Path.home() / ".solace" / "app-configs" / f"{app_id}.json"
+        config_path = self._app_config_path(app_id)
         try:
             if config_path.exists():
                 config_path.unlink()
         except OSError as e:
             self._send_json({"error": f"Could not remove config: {e}"}, 500)
             return
-        self._send_json({"deactivated": True, "app_id": app_id, "state": "installed"})
+        self._send_json({
+            "deactivated": True,
+            "app_id": app_id,
+            "state": "installed",
+            "local_storage": {"key": f"app:{app_id}:state", "value": "installed"},
+        })
 
     def _handle_apps_html(self) -> None:

## web/js/apps.js
diff --git a/web/js/apps.js b/web/js/apps.js
index 6746357b..74ed649b 100644
--- a/web/js/apps.js
+++ b/web/js/apps.js
@@ -1,131 +1,244 @@
 'use strict';
+
 const TOKEN = localStorage.getItem('solace_token') || '';
 const APP_STATE_KEY = (appId) => `app:${appId}:state`;
-let _currentSetupAppId = null;
+const STATE_CLASSES = ['app-state--installed', 'app-state--setup', 'app-state--activated', 'app-state--running'];
+
+let currentSetupAppId = null;
+let currentApps = [];
+
+function apiFetch(path, options = {}) {
+  return fetch(path, {
+    ...options,
+    headers: {
+      Authorization: `Bearer ${TOKEN}`,
+      'Content-Type': 'application/json',
+      ...(options.headers || {}),
+    },
+  });
+}
 
-function apiFetch(path, opts = {}) {
-  return fetch(path, { headers: { Authorization: 'Bearer ' + TOKEN, 'Content-Type': 'application/json', ...opts.headers }, ...opts });
+function statusLabelForState(state) {
+  const statusMap = {
+    installed: 'Needs setup',
+    setup: 'Setting up...',
+    activated: 'Ready',
+    running: 'Running',
+  };
+  return statusMap[state] || state;
 }
 
 function saveAppState(appId, state) {
   localStorage.setItem(APP_STATE_KEY(appId), state);
   updateAppCardVisual(appId, state);
+  updateSetupBanner(currentApps);
+}
+
+function applyStateClass(card, state) {
+  STATE_CLASSES.forEach((className) => card.classList.remove(className));
+  card.classList.add(`app-state--${state}`);
 }
 
 function updateAppCardVisual(appId, state) {
   const card = document.querySelector(`[data-app-id="${appId}"]`);
-  if (!card) return;
-  card.className = card.className.replace(/app-state--\w+/g, '').trim();
-  card.classList.add(`app-state--${state}`);
-  const statusEl = card.querySelector('.app-card__status');
-  const statusMap = { installed: 'Needs setup', setup: 'Setting up...', activated: 'Ready', running: 'Running' };
-  if (statusEl) statusEl.textContent = statusMap[state] || state;
-  // Swap setup/run button
-  const setupBtn = card.querySelector('.app-card__setup-btn');
-  const runBtn = card.querySelector('.app-card__run-btn');
-  if (state === 'activated' || state === 'running') {
-    if (setupBtn) { setupBtn.style.display = 'none'; }
-    if (runBtn) { runBtn.style.display = 'block'; }
-  } else {
-    if (setupBtn) { setupBtn.style.display = 'block'; }
-    if (runBtn) { runBtn.style.display = 'none'; }
+  if (!card) {
+    return;
+  }
+
+  applyStateClass(card, state);
+
+  const statusElement = card.querySelector('.app-card__status');
+  if (statusElement) {
+    statusElement.textContent = statusLabelForState(state);
+  }
+
+  const setupButton = card.querySelector('.app-card__setup-btn');
+  const runButton = card.querySelector('.app-card__run-btn');
+  const isReady = state === 'activated' || state === 'running';
+
+  if (setupButton) {
+    setupButton.hidden = isReady;
+  }
+  if (runButton) {
+    runButton.hidden = !isReady;
   }
 }
 
-function loadAppStates() {
-  apiFetch('/api/v1/apps/lifecycle').then(r => r.json()).then(data => {
-    const apps = data.apps || data;
-    renderAppsGrid(apps);
-    apps.forEach(app => {
-      const localState = localStorage.getItem(APP_STATE_KEY(app.app_id));
-      const state = localState || app.state;
-      saveAppState(app.app_id, state);
-    });
-    updateSetupBanner(apps);
-  }).catch(() => {});
+function renderEmptyState() {
+  const grid = document.getElementById('apps-grid');
+  grid.innerHTML = '<p class="apps-empty-state">No apps installed.</p>';
 }
 
 function renderAppsGrid(apps) {
   const grid = document.getElementById('apps-grid');
-  if (!apps.length) { grid.innerHTML = '<p style="color:var(--hub-text-muted)">No apps installed.</p>'; return; }
-  grid.innerHTML = apps.map(app => {
-    const localState = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
-    const isReady = localState === 'activated' || localState === 'running';
+  if (!apps.length) {
+    renderEmptyState();
+    return;
+  }
+
+  grid.innerHTML = apps.map((app) => {
+    const state = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
+    const isReady = state === 'activated' || state === 'running';
     return `
-    <div class="app-card app-state--${localState}" data-app-id="${app.app_id}">
-      <span class="app-card__icon">${app.icon || '\u{1F4E6}'}</span>
-      <div class="app-card__name">${app.name}</div>
-      <div class="app-card__status">${isReady ? 'Ready' : 'Needs setup'}</div>
-      ${isReady
-        ? `<button class="app-card__run-btn" onclick="runApp('${app.app_id}')">Run</button>`
-        : `<button class="app-card__setup-btn" onclick="openSetupDrawer('${app.app_id}', '${app.name}')">Set up</button>`}
-    </div>`;
+      <div class="app-card app-state--${state}" data-app-id="${app.app_id}">
+        <span class="app-card__icon">${app.icon || '📦'}</span>
+        <div class="app-card__name">${app.name}</div>
+        <div class="app-card__status">${statusLabelForState(state)}</div>
+        <button class="app-card__setup-btn" data-action="setup" data-app-id="${app.app_id}" data-app-name="${app.name}"${isReady ? ' hidden' : ''}>Set up</button>
+        <button class="app-card__run-btn" data-action="run" data-app-id="${app.app_id}" data-app-name="${app.name}"${isReady ? '' : ' hidden'}>Run</button>
+      </div>
+    `;
   }).join('');
 }
 
 function updateSetupBanner(apps) {
-  const needSetup = apps.filter(a => {
-    const state = localStorage.getItem(APP_STATE_KEY(a.app_id)) || a.state;
+  const pendingApps = apps.filter((app) => {
+    const state = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
     return state === 'installed' || state === 'setup';
   });
+
   const banner = document.getElementById('setup-banner');
-  banner.hidden = needSetup.length === 0;
-  document.getElementById('setup-count').textContent = needSetup.length;
+  banner.hidden = pendingApps.length === 0;
+  document.getElementById('setup-count').textContent = String(pendingApps.length);
+}
+
+function renderSetupMessage(message, modifier = '') {
+  return `<p class="setup-form__message${modifier ? ` setup-form__message--${modifier}` : ''}">${message}</p>`;
+}
+
+function renderSetupFields(fields) {
+  if (!fields.length) {
+    return renderSetupMessage('No configuration needed for this app.');
+  }
+
+  return fields.map((field) => `
+    <div class="setup-form__field">
+      <label for="field-${field.name}">${field.description || field.name}${field.required ? ' *' : ''}</label>
+      <input id="field-${field.name}" name="${field.name}" type="${field.type === 'oauth' ? 'password' : 'text'}" placeholder="${field.placeholder || ''}"${field.required ? ' required' : ''}>
+    </div>
+  `).join('');
+}
+
+function closeSetupDrawer() {
+  document.getElementById('setup-drawer').hidden = true;
 }
 
 function openSetupDrawer(appId, appName) {
-  _currentSetupAppId = appId;
+  currentSetupAppId = appId;
   document.getElementById('setup-drawer-title').textContent = `Set up ${appName}`;
   document.getElementById('setup-drawer').hidden = false;
-  // Load fields
-  apiFetch(`/api/v1/apps/${appId}/setup-requirements`).then(r => r.json()).then(data => {
-    const form = document.getElementById('setup-form');
-    const fields = data.fields || [];
-    form.innerHTML = fields.length
-      ? fields.map(f => `
-          <div>
-            <label for="field-${f.name}">${f.description || f.name}${f.required ? ' *' : ''}</label>
-            <input id="field-${f.name}" name="${f.name}" type="${f.type === 'oauth' ? 'password' : 'text'}" placeholder="${f.placeholder || ''}" ${f.required ? 'required' : ''}>
-          </div>`).join('')
-      : '<p style="color:var(--hub-text-muted)">No configuration needed for this app.</p>';
-  }).catch(() => {
-    document.getElementById('setup-form').innerHTML = '<p style="color:var(--hub-text-muted)">Could not load setup requirements.</p>';
-  });
   saveAppState(appId, 'setup');
+
+  apiFetch(`/api/v1/apps/${appId}/setup-requirements`)
+    .then((response) => response.json())
+    .then((data) => {
+      const form = document.getElementById('setup-form');
+      const fields = Array.isArray(data.fields) ? data.fields : [];
+      form.innerHTML = renderSetupFields(fields);
+    })
+    .catch(() => {
+      document.getElementById('setup-form').innerHTML = renderSetupMessage('Could not load setup requirements.', 'error');
+    });
 }
 
-document.getElementById('setup-drawer-close').addEventListener('click', () => {
-  document.getElementById('setup-drawer').hidden = true;
+function applyServerState(data, appId, fallbackState) {
+  const localStorageUpdate = data.local_storage || {
+    key: APP_STATE_KEY(appId),
+    value: fallbackState,
+  };
+  localStorage.setItem(localStorageUpdate.key, localStorageUpdate.value);
+  updateAppCardVisual(appId, localStorageUpdate.value);
+  updateSetupBanner(currentApps);
+}
+
+function loadAppStates() {
+  apiFetch('/api/v1/apps/lifecycle')
+    .then((response) => response.json())
+    .then((data) => {
+      currentApps = Array.isArray(data.apps) ? data.apps : [];
+      renderAppsGrid(currentApps);
+      currentApps.forEach((app) => {
+        const state = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
+        saveAppState(app.app_id, state);
+      });
+      updateSetupBanner(currentApps);
+    })
+    .catch(() => {
+      currentApps = [];
+      renderEmptyState();
+      updateSetupBanner(currentApps);
+    });
+}
+
+function runApp(appId) {
+  saveAppState(appId, 'running');
+}
+
+document.getElementById('apps-grid').addEventListener('click', (event) => {
+  const button = event.target.closest('button[data-action]');
+  if (!button) {
+    return;
+  }
+
+  const appId = button.dataset.appId || '';
+  const appName = button.dataset.appName || appId;
+  if (button.dataset.action === 'setup') {
+    openSetupDrawer(appId, appName);
+    return;
+  }
+  if (button.dataset.action === 'run') {
+    runApp(appId);
+  }
 });
-document.getElementById('cancel-setup-btn').addEventListener('click', () => {
-  document.getElementById('setup-drawer').hidden = true;
+
+document.getElementById('setup-all-btn').addEventListener('click', () => {
+  const firstPendingApp = currentApps.find((app) => {
+    const state = localStorage.getItem(APP_STATE_KEY(app.app_id)) || app.state;
+    return state === 'installed' || state === 'setup';
+  });
+  if (firstPendingApp) {
+    openSetupDrawer(firstPendingApp.app_id, firstPendingApp.name);
+  }
 });
 
-document.getElementById('setup-form').addEventListener('submit', (e) => {
-  e.preventDefault();
-  if (!_currentSetupAppId) return;
-  const formData = new FormData(e.target);
+document.getElementById('setup-drawer-close').addEventListener('click', closeSetupDrawer);
+document.getElementById('cancel-setup-btn').addEventListener('click', closeSetupDrawer);
+
+document.getElementById('setup-form').addEventListener('submit', (event) => {
+  event.preventDefault();
+  if (!currentSetupAppId) {
+    return;
+  }
+
+  const formData = new FormData(event.target);
   const config = {};
-  formData.forEach((v, k) => { config[k] = v; });
-  apiFetch(`/api/v1/apps/${_currentSetupAppId}/activate`, {
+  formData.forEach((value, key) => {
+    config[key] = value;
+  });
+
+  apiFetch(`/api/v1/apps/${currentSetupAppId}/activate`, {
     method: 'POST',
-    body: JSON.stringify({ config })
-  }).then(r => r.json()).then(data => {
-    if (data.activated || data.state === 'activated') {
-      saveAppState(_currentSetupAppId, 'activated');
-      document.getElementById('setup-drawer').hidden = true;
+    body: JSON.stringify({ config }),
+  })
+    .then(async (response) => ({ ok: response.ok, data: await response.json() }))
+    .then(({ ok, data }) => {
+      if (!ok) {
+        document.getElementById('setup-form').insertAdjacentHTML(
+          'afterbegin',
+          renderSetupMessage(data.error || 'Activation failed.', 'error'),
+        );
+        return;
+      }
+      applyServerState(data, currentSetupAppId, 'activated');
+      closeSetupDrawer();
       loadAppStates();
-    }
-  }).catch(() => {});
+    })
+    .catch(() => {
+      document.getElementById('setup-form').insertAdjacentHTML(
+        'afterbegin',
+        renderSetupMessage('Activation failed.', 'error'),
+      );
+    });
 });
 
-function runApp(appId) {
-  saveAppState(appId, 'running');
-  // In production: POST /api/v1/apps/{app_id}/run
-}
-
-// State class map (app-state--installed | app-state--setup | app-state--activated | app-state--running)
-const _STATE_CLASSES = ['app-state--installed', 'app-state--setup', 'app-state--activated', 'app-state--running'];
-
-// Init
 loadAppStates();

## web/css/apps.css
diff --git a/web/css/apps.css b/web/css/apps.css
index a5d7d3fe..f0ef5828 100644
--- a/web/css/apps.css
+++ b/web/css/apps.css
@@ -43,13 +43,19 @@ body { margin: 0; background: var(--hub-bg); color: var(--hub-text); font-family
 .app-card__status { font-size: 0.75rem; color: var(--hub-text-muted); margin-bottom: 0.75rem; }
 .app-card__setup-btn, .app-card__run-btn {
   width: 100%; border: none; border-radius: 4px; padding: 0.4rem; cursor: pointer;
   font-size: 0.8rem;
 }
+.app-card__setup-btn[hidden], .app-card__run-btn[hidden] { display: none; }
 .app-card__setup-btn { background: var(--hub-warning); color: var(--hub-bg); }
 .app-card__run-btn { background: var(--hub-success); color: var(--hub-bg); }
 
+.apps-empty-state {
+  color: var(--hub-text-muted);
+  font-size: 0.9rem;
+}
+
 /* State: installed — grey icon, dotted border */
 .app-state--installed .app-card__icon { filter: grayscale(1); opacity: 0.6; }
 .app-state--installed { border-style: dashed; border-color: var(--hub-border); }
 
 /* State: setup — grey icon, pulsing border */
@@ -79,10 +85,18 @@ body { margin: 0; background: var(--hub-bg); color: var(--hub-text); font-family
 .setup-drawer[hidden] { display: none; }
 .setup-drawer__header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; }
 .setup-drawer__header h3 { color: var(--hub-text); margin: 0; }
 #setup-drawer-close { background: none; border: none; color: var(--hub-text-muted); cursor: pointer; font-size: 1.2rem; }
 .setup-drawer__form { display: flex; flex-direction: column; gap: 1rem; }
+.setup-form__field { display: flex; flex-direction: column; gap: 0.25rem; }
 .setup-drawer__form label { display: block; color: var(--hub-text-muted); font-size: 0.85rem; margin-bottom: 0.25rem; }
 .setup-drawer__form input { width: 100%; background: var(--hub-bg); color: var(--hub-text); border: 1px solid var(--hub-border); border-radius: 4px; padding: 0.5rem; }
+.setup-form__message {
+  color: var(--hub-text-muted);
+  font-size: 0.85rem;
+}
+.setup-form__message--error {
+  color: var(--hub-warning);
+}
 .setup-drawer__actions { display: flex; gap: 1rem; margin-top: 1.5rem; }
 #activate-btn { background: var(--hub-success); color: var(--hub-bg); border: none; border-radius: 4px; padding: 0.5rem 1rem; cursor: pointer; flex: 1; }
 #cancel-setup-btn { background: var(--hub-surface); color: var(--hub-text); border: 1px solid var(--hub-border); border-radius: 4px; padding: 0.5rem 1rem; cursor: pointer; }

## tests/test_app_onboarding.py
diff --git a/tests/test_app_onboarding.py b/tests/test_app_onboarding.py
index 95b229c1..bbc259f2 100644
--- a/tests/test_app_onboarding.py
+++ b/tests/test_app_onboarding.py
@@ -1,7 +1,8 @@
 """tests/test_app_onboarding.py — App Onboarding 4-State Lifecycle acceptance gate."""
 import json
+import re
 import sys
 import threading
 import time
 import urllib.error
 import urllib.request
@@ -38,10 +39,11 @@ def onboard_server(tmp_path, monkeypatch):
     import yinyang_server as ys
 
     for attr in ["EVIDENCE_PATH", "PORT_LOCK_PATH", "SETTINGS_PATH"]:
         monkeypatch.setattr(ys, attr, tmp_path / f"{attr.lower()}.json", raising=False)
     httpd = ys.build_server(0, str(tmp_path), session_token_sha256=VALID_TOKEN)
+    httpd.apps = ["gmail", "slack-triage"]
     thread = threading.Thread(target=httpd.serve_forever, daemon=True)
     thread.start()
     base = f"http://localhost:{httpd.server_port}"
     for _ in range(30):
         try:
@@ -59,10 +61,13 @@ def test_lifecycle_returns_state_for_all_apps(onboard_server):
     assert "apps" in data
     for app in data["apps"]:
         assert "app_id" in app
         assert "state" in app
         assert app["state"] in ("installed", "setup", "activated", "running")
+        assert "config_required" in app
+        assert isinstance(app["config_required"], list)
+        assert "config_complete" in app
 
 
 def test_activate_requires_auth(onboard_server):
     req = urllib.request.Request(
         onboard_server + "/api/v1/apps/gmail/activate",
@@ -75,23 +80,68 @@ def test_activate_requires_auth(onboard_server):
         assert False, "Expected 401"
     except urllib.error.HTTPError as e:
         assert e.code == 401
 
 
-def test_activate_returns_activated_state(onboard_server, tmp_path, monkeypatch):
+def test_activate_requires_all_required_fields(onboard_server, tmp_path, monkeypatch):
     monkeypatch.setattr(
         "pathlib.Path.home", lambda: tmp_path, raising=False
     )
     status, data = _req(
         onboard_server,
         "/api/v1/apps/gmail/activate",
         method="POST",
         payload={"config": {}},
     )
+    assert status == 400
+    assert data.get("error") == "missing required config fields"
+    assert data.get("missing_fields") == ["oauth_token"]
+
+
+def test_activate_returns_activated_state(onboard_server, tmp_path, monkeypatch):
+    monkeypatch.setattr(
+        "pathlib.Path.home", lambda: tmp_path, raising=False
+    )
+    status, data = _req(
+        onboard_server,
+        "/api/v1/apps/gmail/activate",
+        method="POST",
+        payload={"config": {"oauth_token": "gmail-oauth-token"}},
+    )
     assert status == 200
     assert data.get("activated") is True
+    assert data.get("app_id") == "gmail"
     assert data.get("state") == "activated"
+    assert data.get("local_storage") == {
+        "key": "app:gmail:state",
+        "value": "activated",
+    }
+
+
+def test_activate_stores_config_encrypted(onboard_server, tmp_path, monkeypatch):
+    monkeypatch.setattr(
+        "pathlib.Path.home", lambda: tmp_path, raising=False
+    )
+    secret = "gmail-oauth-token"
+    status, _ = _req(
+        onboard_server,
+        "/api/v1/apps/gmail/activate",
+        method="POST",
+        payload={"config": {"oauth_token": secret}},
+    )
+    assert status == 200
+
+    config_path = tmp_path / ".solace" / "app-configs" / "gmail.json"
+    stored = config_path.read_text()
+    assert secret not in stored
+    assert "oauth_token" not in stored
+
+    envelope = json.loads(stored)
+    assert envelope["cipher"] == "AES-256-GCM"
+    assert envelope["app_id"] == "gmail"
+    assert "nonce_b64" in envelope
+    assert "ciphertext_b64" in envelope
 
 
 def test_deactivate_resets_to_installed(onboard_server, tmp_path, monkeypatch):
     monkeypatch.setattr(
         "pathlib.Path.home", lambda: tmp_path, raising=False
@@ -99,11 +149,11 @@ def test_deactivate_resets_to_installed(onboard_server, tmp_path, monkeypatch):
     # First activate
     _req(
         onboard_server,
         "/api/v1/apps/gmail-test/activate",
         method="POST",
-        payload={"config": {}},
+        payload={"config": {"oauth_token": "token"}},
     )
     # Then deactivate
     status, data = _req(
         onboard_server, "/api/v1/apps/gmail-test/activate", method="DELETE"
     )
@@ -113,18 +163,30 @@ def test_deactivate_resets_to_installed(onboard_server, tmp_path, monkeypatch):
 
 
 def test_setup_requirements_has_config_fields(onboard_server):
     status, data = _req(onboard_server, "/api/v1/apps/gmail/setup-requirements")
     assert status == 200
-    assert "app_id" in data
+    assert data["app_id"] == "gmail"
     assert "fields" in data
     assert isinstance(data["fields"], list)
+    assert data["fields"] == [
+        {
+            "name": "oauth_token",
+            "type": "oauth",
+            "required": True,
+            "description": "Gmail OAuth token",
+            "placeholder": "Paste Gmail OAuth token",
+        }
+    ]
+    assert data["vault_key"] == "oauth3:gmail"
 
 
 def test_apps_css_no_hardcoded_hex():
     css = (PROJECT_ROOT / "web" / "css" / "apps.css").read_text()
     assert "var(--hub-" in css
+    state_blocks = "\n".join(line for line in css.splitlines() if ".app-state--" in line or "@keyframes" in line or "box-shadow" in line)
+    assert re.search(r"#[0-9a-fA-F]{3,6}", state_blocks) is None
 
 
 def test_apps_html_no_cdn():
     html = (PROJECT_ROOT / "web" / "apps.html").read_text()
     assert "cdn.jsdelivr" not in html
@@ -133,16 +195,19 @@ def test_apps_html_no_cdn():
 
 def test_state_classes_are_4_valid_values():
     js = (PROJECT_ROOT / "web" / "js" / "apps.js").read_text()
     for state in ["installed", "setup", "activated", "running"]:
         assert f"app-state--{state}" in js
+    assert "onclick=" not in js
+    assert ".style." not in js
 
 
 def test_setup_banner_shows_when_apps_not_activated():
     html = (PROJECT_ROOT / "web" / "apps.html").read_text()
     assert "setup-banner" in html
     assert "setup-count" in html
+    assert "setup-all-btn" in html
 
 
 def test_lifecycle_requires_auth(onboard_server):
     req = urllib.request.Request(onboard_server + "/api/v1/apps/lifecycle")
     try:
