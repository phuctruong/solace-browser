// Diagram: 04-hub-lifecycle
// Dashboard Engine Chooser — extracted from hub-app.js for standalone use in Rust dashboard
// Self-contained: includes helpers, scan, connect, BYOK, Ollama, sign-in, launch
// Expects: HTML from dashboard-engine.html already in DOM
// Expects: a <div id="toast-container"></div> somewhere in the page

(function() {
  'use strict';

  // ─── Configuration ───
  var API = 'http://localhost:8888';

  // ─── Helpers (same pattern as hub-app.js) ───
  function get(p) { return fetch(API + p).then(function(r) { return r.json(); }); }
  function $(id) { return document.getElementById(id); }
  function esc(s) { var d = document.createElement('div'); d.textContent = String(s || ''); return d.innerHTML; }
  function toast(m, t) {
    var c = $('toast-container');
    if (!c) return;
    var e = document.createElement('div');
    e.className = 'sb-toast sb-toast--' + (t || 'success');
    e.textContent = m;
    c.appendChild(e);
    setTimeout(function() { e.remove(); }, 4000);
  }

  // ─── State ───
  var hasLLM = false;
  var yGif = '<img src="/media/yinyang-rotating_70pct_128px.gif" style="height:48px;width:auto;vertical-align:middle">';

  // ─── Enable Launch Button ───
  function enableLaunchButton() {
    var area = $('launch-btn-area');
    if (area) {
      area.innerHTML = '<button class="sb-btn sb-btn--primary hub-launch" data-action="launchBrowser">Launch Solace Browser</button>';
    }
  }

  // ─── Fetch Agents ───
  // Returns a promise resolving to {agents:[], installed:[]}
  function fetchAgents() {
    return get('/api/v1/agents').then(function(d) {
      var agents = d.agents || [];
      var installed = agents.filter(function(a) { return a.installed; });
      return { agents: agents, installed: installed };
    });
  }

  // ─── Connect CLIs — validate each CLI + model ───
  function connectCLIs() {
    if ($('src-local-action')) $('src-local-action').innerHTML = '<span class="sb-text-muted">Connecting...</span>';
    if ($('src-local')) $('src-local').innerHTML = '<span class="sb-pill sb-pill--warning">&#9203; Connecting...</span>';
    if ($('cli-details-row')) $('cli-details-row').style.display = '';

    get('/api/v1/agents').then(function(d) {
      var agents = (d.agents || []).filter(function(a) { return a.installed; });
      if (!agents.length) {
        if ($('cli-models-area')) $('cli-models-area').innerHTML = '<span class="sb-text-muted">No CLIs found on PATH</span>';
        return;
      }

      // Build model checklist with pending status
      var html = '';
      agents.forEach(function(a) {
        html += '<div style="margin-bottom:0.5rem"><strong>' + esc(a.id) + '</strong> <span id="cli-status-' + esc(a.id) + '" class="sb-pill sb-pill--warning" style="font-size:0.65rem">&#9203; testing</span>';
        html += '<div style="margin-left:1rem;margin-top:0.25rem">';
        (a.models || []).forEach(function(m) {
          var short = m.replace('claude-', '').replace('gpt-', '').replace('-20251001', '');
          html += '<label style="display:inline-flex;align-items:center;gap:4px;margin-right:1rem;font-size:0.85rem;cursor:pointer">';
          html += '<input type="checkbox" checked style="accent-color:var(--sb-accent)" data-cli="' + esc(a.id) + '" data-model="' + esc(m) + '">';
          html += '<span class="sb-text-mono">' + esc(short) + '</span></label>';
        });
        html += '</div></div>';
      });
      if ($('cli-models-area')) $('cli-models-area').innerHTML = html;

      // Validate each CLI (default model ping)
      var verified = 0;
      var total = agents.length;
      agents.forEach(function(a) {
        fetch(API + '/api/v1/agents/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ agent_id: a.id, prompt: 'respond with ok', timeout: 15 })
        }).then(function(r) { return r.json(); }).then(function(d) {
          var cell = $('cli-status-' + a.id);
          if (d.response || d.output || d.text) {
            if (cell) { cell.innerHTML = '&#10003; verified'; cell.className = 'sb-pill sb-pill--success'; cell.style.fontSize = '0.65rem'; }
            verified++;
          } else {
            if (cell) { cell.innerHTML = '&#10007; ' + esc((d.error || 'failed').substring(0, 30)); cell.className = 'sb-pill sb-pill--danger'; cell.style.fontSize = '0.65rem'; }
          }
        }).catch(function() {
          var cell = $('cli-status-' + a.id);
          if (cell) { cell.innerHTML = '&#10007; timeout'; cell.className = 'sb-pill sb-pill--danger'; cell.style.fontSize = '0.65rem'; }
        }).finally(function() {
          total--;
          if (total <= 0) {
            if (verified > 0) {
              if ($('src-local')) $('src-local').innerHTML = '<span class="sb-pill sb-pill--success">&#10003; ' + verified + ' connected</span> <a href="#" data-action="connectCLIs" style="font-size:0.75rem;color:var(--sb-text-muted)">rerun</a>';
              if ($('src-local-action')) $('src-local-action').innerHTML = yGif;
              hasLLM = true;
              enableLaunchButton();
              // Persist validated state
              var chipsHTML = $('cli-models-area') ? $('cli-models-area').innerHTML : '';
              try { localStorage.setItem('solace_validated_clis', JSON.stringify({ count: verified, chips: chipsHTML })); } catch (e) {}
            } else {
              if ($('src-local')) $('src-local').innerHTML = '<span class="sb-pill sb-pill--danger">&#10007; No working CLIs</span>';
              if ($('src-local-action')) $('src-local-action').innerHTML = '<button class="sb-btn sb-btn--sm" data-action="connectCLIs">Retry</button>';
            }
          }
        });
      });
    });
  }

  // ─── Sign In (launches browser to solaceagi.com/dashboard) ───
  function signIn() {
    toast('Opening browser — complete sign-in there. Hub will detect automatically.', 'success');
    var managedGif = $('src-managed-gif');
    if (managedGif) managedGif.innerHTML = '<span class="sb-text-muted" style="font-size:0.8rem">Waiting for sign-in...</span>';

    fetch(API + '/api/v1/browser/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'https://solaceagi.com/dashboard', allow_duplicate: true })
    }).then(function(r) { return r.json(); }).then(function(d) {
      if (d.session_id || d.deduped) toast('Browser opened to solaceagi.com', 'success');
      else if (d.error) toast(d.error, 'danger');
    }).catch(function() {
      // Fallback: open in default browser
      window.open('https://solaceagi.com/dashboard', '_blank');
    });

    // Poll for login completion
    var loginPoll = setInterval(function() {
      get('/api/v1/cloud/status').then(function(c) {
        if (c.connected && c.config) {
          clearInterval(loginPoll);
          var email = c.config.user_email || 'user';
          toast('Signed in as ' + email, 'success');
          // Update engine card UI
          if ($('src-managed')) $('src-managed').innerHTML = '<span class="sb-pill sb-pill--success">&#10003; ' + esc(email) + '</span>';
          if ($('src-managed-gif')) $('src-managed-gif').innerHTML = yGif;
          hasLLM = true;
          enableLaunchButton();
          var acct = $('llm-account');
          if (acct) {
            acct.style.display = 'block';
            acct.innerHTML = '<span class="sb-pill sb-pill--success">&#9679; ' + esc(email) + '</span> <span class="sb-text-muted">Managed LLM active</span>';
          }
        }
      }).catch(function() {});
    }, 3000);
    // Stop polling after 5 minutes
    setTimeout(function() { clearInterval(loginPoll); }, 300000);
  }

  // ─── Prompt BYOK (focus the inline edit field) ───
  function promptBYOK() {
    var el = $('byok-editable');
    if (el) {
      el.classList.add('sb-editable--editing');
      if ($('byok-input')) {
        $('byok-input').value = '';
        $('byok-input').focus();
      }
    }
  }

  // ─── Launch Browser ───
  function launchBrowser() {
    fetch(API + '/api/v1/browser/launch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    }).then(function(r) { return r.json(); }).then(function(d) {
      if (d.deduped && d.session) {
        toast('Solace Browser already running', 'success');
      } else if (d.session) {
        toast('Solace Browser launched!', 'success');
      } else if (d.error) {
        toast(d.error, 'danger');
      }
    }).catch(function(e) {
      toast('Launch failed: ' + e, 'danger');
    });
  }

  // ─── Run Scan (auto-detect agents + cloud status on load) ───
  function runScan() {
    fetchAgents().then(function(result) {
      var installed = result.installed;

      // Source 4: Local CLI
      if (installed.length > 0) {
        if ($('src-local')) $('src-local').innerHTML = '<span class="sb-pill sb-pill--info">' + installed.length + ' found — connecting...</span>';
        if ($('src-local-action')) $('src-local-action').innerHTML = '';
        // Auto-connect in background
        setTimeout(function() { connectCLIs(); }, 100);
      } else {
        if ($('src-local')) $('src-local').innerHTML = '<span class="sb-pill sb-pill--danger">&#10007; None found</span>';
        if ($('src-local-action')) $('src-local-action').innerHTML = '<span class="sb-text-muted" style="font-size:0.8rem">Install claude, codex, or gemini</span>';
      }

      // Source 1 + 2: Managed sign-in + BYOK via cloud status
      get('/api/v1/cloud/status').then(function(c) {
        if (c.connected && c.config) {
          var email = c.config.user_email || 'User';
          var isPaid = c.config.paid_user;

          if (email === 'byok@local') {
            // BYOK key set
            if ($('src-byok')) $('src-byok').innerHTML = '<span class="sb-pill sb-pill--success">&#10003; Active</span>';
            if ($('src-byok-gif')) $('src-byok-gif').innerHTML = yGif;
          } else if (isPaid) {
            // Managed LLM (paid)
            if ($('src-managed')) $('src-managed').innerHTML = '<span class="sb-pill sb-pill--success">&#10003; ' + esc(email) + '</span>';
            if ($('src-managed-gif')) $('src-managed-gif').innerHTML = yGif;
            var acct = $('llm-account');
            if (acct) {
              acct.style.display = 'block';
              acct.innerHTML = '<span class="sb-pill sb-pill--success">&#9679; ' + esc(email) + '</span> <span class="sb-text-muted">Powered by Managed LLM + 47 uplifts</span>';
            }
          } else {
            // Free account — connected but no managed LLM
            if ($('src-managed')) $('src-managed').innerHTML = '<span class="sb-pill sb-pill--success">' + esc(email) + '</span> <span class="sb-text-muted" style="font-size:0.75rem">Free account</span>';
            var acct2 = $('llm-account');
            if (acct2) {
              acct2.style.display = 'block';
              acct2.innerHTML = '<span class="sb-pill sb-pill--success">&#9679; ' + esc(email) + '</span> <span class="sb-text-muted">Managed LLM off</span>';
            }
          }
          hasLLM = true;
          enableLaunchButton();
          if ($('llm-card')) {
            $('llm-card').classList.add('hub-ready');
            $('llm-card').classList.remove('hub-blocked');
          }
        } else {
          // Not signed in — check sidebar state for BYOK detection (byok.json on disk)
          get('/api/v1/sidebar/state').then(function(ss) {
            if (ss.gate === 'byok' || ss.llm_mode === 'byok') {
              hasLLM = true;
              if ($('src-byok')) $('src-byok').innerHTML = '<span class="sb-pill sb-pill--success">&#10003; BYOK Active (file)</span>';
              enableLaunchButton();
            }
          }).catch(function() {});

          // If no CLIs and no cloud — show gate
          if (!installed.length) {
            var gate = $('llm-gate');
            if (gate) {
              gate.innerHTML =
                '<div class="hub-gate">' +
                '<div class="hub-gate-msg">Solace Browser requires an LLM to power it.</div>' +
                '<div class="sb-flex sb-gap-sm" style="justify-content:center;flex-wrap:wrap">' +
                '<button class="sb-btn sb-btn--primary" data-action="promptBYOK">Enter API Key (BYOK)</button>' +
                '<button class="sb-btn" data-action="signIn">Sign Up for Managed LLM</button>' +
                '</div>' +
                '<div class="sb-text-muted sb-mt-md" style="font-size:0.8rem">Or install claude, codex, or gemini CLI on your PATH</div>' +
                '</div>';
            }
            if ($('llm-card')) $('llm-card').classList.add('hub-blocked');
          }
        }
      }).catch(function() {});
    }).catch(function() {
      // API unreachable — show error state
      if ($('src-local')) $('src-local').innerHTML = '<span class="sb-pill sb-pill--danger">Runtime offline</span>';
    });
  }

  // ─── BYOK Inline Edit ───
  function initBYOKEdit() {
    var el = $('byok-editable');
    if (!el) return;
    var display = el.querySelector('.sb-editable-display');
    var input = el.querySelector('.sb-editable-input');
    var pen = el.querySelector('.sb-editable-pen');

    function startEdit() {
      el.classList.add('sb-editable--editing');
      input.value = '';
      input.focus();
    }

    if (display) display.addEventListener('click', startEdit);
    if (pen) pen.addEventListener('click', startEdit);

    function saveKey() {
      el.classList.remove('sb-editable--editing');
      var key = input.value.trim();
      if (key && key.length > 4) {
        var masked = key.substring(0, 4) + '...' + key.substring(key.length - 4);
        display.textContent = masked;
        display.style.color = 'var(--sb-success)';
        fetch(API + '/api/v1/cloud/connect', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ api_key: key, user_email: 'byok@local', device_id: 'local', paid_user: false })
        }).then(function() {
          toast('BYOK key saved!', 'success');
          if ($('src-byok-gif')) $('src-byok-gif').innerHTML = yGif;
          hasLLM = true;
          enableLaunchButton();
        });
      } else if (key) {
        toast('Key too short', 'warning');
        display.textContent = 'Not set — click to enter key';
      }
    }

    input.addEventListener('blur', saveKey);
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') input.blur();
      if (e.key === 'Escape') el.classList.remove('sb-editable--editing');
    });
  }

  // ─── Ollama Inline Edit ───
  function initOllamaEdit() {
    var el = $('ollama-editable');
    if (!el) return;
    var display = el.querySelector('.sb-editable-display');
    var input = el.querySelector('.sb-editable-input');
    var pen = el.querySelector('.sb-editable-pen');

    function startEdit() {
      el.classList.add('sb-editable--editing');
      input.value = '';
      input.focus();
    }

    if (display) display.addEventListener('click', startEdit);
    if (pen) pen.addEventListener('click', startEdit);

    function saveUrl() {
      el.classList.remove('sb-editable--editing');
      var url = input.value.trim();
      if (url && url.startsWith('http')) {
        display.textContent = url;
        display.style.color = 'var(--sb-success)';
        if ($('src-ollama-gif')) $('src-ollama-gif').innerHTML = yGif;
        hasLLM = true;
        enableLaunchButton();
        toast('Ollama URL saved!', 'success');
      } else if (url) {
        toast('URL must start with http', 'warning');
      }
    }

    input.addEventListener('blur', saveUrl);
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') input.blur();
      if (e.key === 'Escape') el.classList.remove('sb-editable--editing');
    });
  }

  // ─── Delegated Click Handler (data-action) ───
  document.addEventListener('click', function(e) {
    var actionEl = e.target.closest('[data-action]');
    if (!actionEl) return;
    var action = actionEl.dataset.action;
    if (action === 'signIn') { e.preventDefault(); signIn(); }
    else if (action === 'promptBYOK') { e.preventDefault(); promptBYOK(); }
    else if (action === 'connectCLIs') { e.preventDefault(); connectCLIs(); }
    else if (action === 'launchBrowser') { e.preventDefault(); launchBrowser(); }
    else if (action === 'openManagedLLM') { e.preventDefault(); window.open('https://solaceagi.com/dashboard', '_blank'); }
  });

  // ─── Expose for external use ───
  window.engineChooser = {
    runScan: runScan,
    fetchAgents: fetchAgents,
    connectCLIs: connectCLIs,
    signIn: signIn,
    promptBYOK: promptBYOK,
    launchBrowser: launchBrowser,
    enableLaunchButton: enableLaunchButton,
    hasLLM: function() { return hasLLM; }
  };

  // ─── Auto-init on DOMContentLoaded ───
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      initBYOKEdit();
      initOllamaEdit();
      runScan();
    });
  } else {
    // DOM already ready (script loaded async/deferred)
    initBYOKEdit();
    initOllamaEdit();
    runScan();
  }

})();
