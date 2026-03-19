// Diagram: 04-hub-lifecycle
// Extracted from index.html inline <script> block
(function() {
  'use strict';
  var API = 'http://localhost:8888';
  function get(p){return fetch(API+p).then(function(r){return r.json()});}
  function $(id){return document.getElementById(id);}
  function esc(s){var d=document.createElement('div');d.textContent=String(s||'');return d.innerHTML;}
  function toast(m,t){var c=$('toast-container'),e=document.createElement('div');e.className='sb-toast sb-toast--'+(t||'success');e.textContent=m;c.appendChild(e);setTimeout(function(){e.remove();},4000);}

  // Theme
  document.querySelectorAll('.sb-theme-btn').forEach(function(b){b.addEventListener('click',function(){document.documentElement.setAttribute('data-theme',b.dataset.theme);document.querySelectorAll('.sb-theme-btn').forEach(function(x){x.classList.toggle('sb-theme-btn--active',x===b);});});});

  // Language
  var lt=$('languageToggle'),lm=$('languageMenu');
  if(lt){lt.addEventListener('click',function(e){e.stopPropagation();var o=!lm.classList.contains('active');if(o)lm.removeAttribute('hidden');lm.classList.toggle('active',o);if(!o)lm.setAttribute('hidden','');});document.addEventListener('click',function(e){if(!lt.contains(e.target)&&!lm.contains(e.target)){lm.classList.remove('active');lm.setAttribute('hidden','');}});}

  // ─── SCAN + GATE LOGIC ───
  // EMERGENCY: force UI visible immediately to debug
  document.addEventListener('DOMContentLoaded', function() {
    setTimeout(function() {
      var sp = document.getElementById('scan-phase');
      if (sp) sp.style.display = 'none';
      var ht = document.getElementById('hub-tabs');
      if (ht) ht.style.display = 'block';
      var hh = document.getElementById('hub-header');
      if (hh) hh.style.display = 'block';
      var rp = document.getElementById('results-phase');
      if (rp) rp.style.display = 'block';
    }, 2000);
  });
  var hasLLM = false;
  // Simplest persistence: save/load via POST/GET to evidence endpoint
  // On Connect CLIs success: POST an evidence event with cli count
  // On load: check if agents are installed AND we have a recent cli_connected evidence
  var savedCLIs = null;

  function showMainUI() {
    $('scan-phase').style.opacity = '0';
    setTimeout(function() {
      $('scan-phase').style.display = 'none';
      if ($('hub-tabs')) $('hub-tabs').style.display = 'block';
      if ($('hub-header')) $('hub-header').style.display = 'block';
      if ($('results-phase')) $('results-phase').style.display = 'block';
      try { loadVersionInfo(); } catch(e) {}
      try { loadSettingsInfo(); } catch(e) {}
      try { loadRemoteStatus(); } catch(e) {}
      get('/api/v1/system/status').then(function(s) {
        var count = s.app_count || 0;
        var el = $('app-discovery-count');
        if (el) el.textContent = count + ' apps ready';
      }).catch(function(){});
    }, 500);
  }

  function runScan() {
    // Always show main UI after 3 seconds even if API calls fail
    var transitionTimer = setTimeout(function() { showMainUI(); }, 3000);

    get('/api/v1/agents').then(function(d) {
      var agents = d.agents || [];
      var installed = agents.filter(function(a){return a.installed;});
      // Don't set hasLLM here — CLIs on PATH doesn't mean connected
      // hasLLM only becomes true after: Connect CLIs verified, BYOK saved, or signed in

      // Transition: merge → rotate → reveal
      $('scan-img').src = '/media/yinyang-rotating_70pct_128px.gif';
      $('scan-text').textContent = installed.length + ' AI tools found!';
      $('scan-text').style.color = installed.length > 0 ? 'var(--sb-success)' : 'var(--sb-danger)';

      // Source 1: Local CLI — if found, auto-connect in background
      if (installed.length > 0) {
        $('src-local').innerHTML = '<span class="sb-pill sb-pill--info">' + installed.length + ' found — connecting...</span>';
        $('src-local-action').innerHTML = '';
        // Auto-connect (same as clicking Connect CLIs)
        setTimeout(function() { connectCLIs(); }, 100);
      } else {
        $('src-local').innerHTML = '<span class="sb-pill sb-pill--danger">✗ None found</span>';
        $('src-local-action').innerHTML = '<span class="sb-text-muted" style="font-size:0.8rem">Install claude, codex, or gemini</span>';
      }

      // Auth pill + account status + remote
      var auth = ($('topbar-user')||{});
      var acct = $('llm-account');
      // Source 2 + 3: BYOK + Managed status
      get('/api/v1/cloud/status').then(function(c) {
        var on = c.connected && c.config && c.config.paid_user;
        $('dot-remote').className = 'sb-topbar-dot sb-topbar-dot--' + (on ? 'on' : 'off');
        $('dot-tunnel').className = 'sb-topbar-dot sb-topbar-dot--' + (on ? 'on' : 'off');
        $('dot-sync').className = 'sb-topbar-dot sb-topbar-dot--' + (c.connected ? 'on' : 'off');
        $('dot-esign').className = 'sb-topbar-dot sb-topbar-dot--' + (on ? 'on' : 'off');
        $('dot-team').className = 'sb-topbar-dot sb-topbar-dot--' + (on ? 'on' : 'off');
        $('dot-twin').className = 'sb-topbar-dot sb-topbar-dot--' + (on ? 'on' : 'off');
        $('dot-fleet').className = 'sb-topbar-dot sb-topbar-dot--' + (on ? 'on' : 'off');
        if (c.connected && c.config) {
          var email = c.config.user_email || 'User';
          var isPaid = c.config.paid_user;

          // Show username in top bar (matching solaceagi.com pattern)
          $('topbar-signin').style.display = 'none';
          $('topbar-user-info').style.display = 'flex';
          $('topbar-user').textContent = email;

          var yGif = '<img src="/media/yinyang-rotating_70pct_128px.gif" style="height:48px;width:auto;vertical-align:middle">';

          if (email === 'byok@local') {
            // BYOK key set
            $('src-byok').innerHTML = '<span class="sb-pill sb-pill--success">✓ Active</span>';
            $('src-byok-gif').innerHTML = yGif;
            auth.textContent = 'BYOK Active';
            auth.className = 'sb-pill sb-pill--success';
          } else if (isPaid) {
            // Managed LLM
            $('src-managed').innerHTML = '<span class="sb-pill sb-pill--success">✓ ' + esc(email) + '</span>';
            $('src-managed-gif').innerHTML = yGif;
            auth.textContent = 'Managed LLM';
            auth.className = 'sb-pill sb-pill--success';
            acct.style.display = 'block';
            acct.innerHTML = '<span class="sb-pill sb-pill--success">● ' + esc(email) + '</span> <span class="sb-text-muted">Powered by Managed LLM + 47 uplifts</span>';
          } else {
            // Free account — connected but not paying for managed LLM
            $('src-managed').innerHTML = '<span class="sb-pill sb-pill--success">' + esc(email) + '</span> <span class="sb-text-muted" style="font-size:0.75rem">Free account</span>';
            auth.textContent = esc(email);
            auth.className = 'sb-pill sb-pill--success';
            acct.style.display = 'block';
            acct.innerHTML = '<span class="sb-pill sb-pill--success">● ' + esc(email) + '</span> <span class="sb-text-muted">Managed LLM off</span>';
          }
          hasLLM = true;
        } else {
          // Not signed in — launch button stays disabled until CLI connected or BYOK set
          $('topbar-signin').style.display = 'inline-flex';
          $('topbar-user-info').style.display = 'none';
          auth.textContent = 'Setup required';
          auth.className = 'sb-pill sb-pill--warning';
          hasLLM = false;

        }
      });

      clearTimeout(transitionTimer);
      setTimeout(function() {
        showMainUI();

          if (hasLLM) {
            // Signed in or BYOK set — ready to launch
            $('llm-card').classList.add('hub-ready');
            $('llm-card').classList.remove('hub-blocked');
            // btn-launch stays enabled (hasLLM is true from cloud/byok)
          } else if (!installed.length) {
            // No CLIs AND no cloud — show setup prompts
            $('llm-gate').innerHTML =
              '<div class="hub-gate">' +
              '<div class="hub-gate-msg">Solace Browser requires an LLM to power it.</div>' +
              '<div class="sb-flex sb-gap-sm" style="justify-content:center;flex-wrap:wrap">' +
              '<button class="sb-btn sb-btn--primary" data-action="promptBYOK">Enter API Key (BYOK)</button>' +
              '<button class="sb-btn" data-action="openManagedLLM">Sign Up for Managed LLM</button>' +
              '</div>' +
              '<div class="sb-text-muted sb-mt-md" style="font-size:0.8rem">Or install claude, codex, or gemini CLI on your PATH</div>' +
              '</div>';
            $('llm-card').classList.add('hub-blocked');

          }
        }, 500);
      }, 1200);
    });
  }

  // ─── Session Mode ───
  var multiMode = false;
  var singleSessionId = null;

  function setSessionMode(isMulti) {
    // Close all sessions + browsers when switching modes (no orphans)
    get('/api/v1/browser/sessions').then(function(d) {
      (d.sessions || []).forEach(function(s) {
        fetch('/api/v1/browser/close/' + s.session_id, {method:'POST'}).catch(function(){});
      });
      singleSessionId = null;
      $('single-session-info').style.display = 'none';
    }).catch(function(){});

    multiMode = isMulti;
    $('single-mode').style.display = isMulti ? 'none' : 'block';
    $('multi-mode').style.display = isMulti ? 'block' : 'none';
    // Show/hide "+ New Session" in Sessions tab based on mode
    var sessNewBtn = $('sessions-tab-new-btn');
    if (sessNewBtn) { sessNewBtn.classList.toggle('hidden', !isMulti); if (isMulti) sessNewBtn.style.display = 'inline-flex'; }
    try { localStorage.setItem('solace_multi_session', isMulti ? '1' : '0'); } catch(e) {}
    setTimeout(refreshSessions, 500);
  }

  // ─── Launch Browser (Single Mode) ───
  window.launchBrowser = function() {
    $('dot-sidebar').className = 'sb-topbar-dot sb-topbar-dot--on';
    fetch('/api/v1/browser/launch', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({})})
      .then(function(r){return r.json();})
      .then(function(d) {
        if (d.deduped && d.session) {
          toast('Solace Browser already running', 'success');
          showSingleSession(d.session);
        } else if (d.session) {
          toast('Solace Browser launched!', 'success');
          showSingleSession(d.session);
        } else if (d.error) {
          toast(d.error, 'danger');
        }
      })
      .catch(function(e) { toast('Launch failed: ' + e, 'danger'); });
  };

  function showSingleSession(session) {
    singleSessionId = session.session_id;
    $('single-session-info').style.display = 'block';
    $('single-pid-pill').textContent = 'PID ' + session.pid + ' · ' + (session.profile || 'default');
  }

  window.closeSingleSession = function() {
    if (!singleSessionId) return;
    fetch('/api/v1/browser/close/' + singleSessionId, {method:'POST'})
      .then(function(r){return r.json();})
      .then(function() {
        toast('Browser closed', 'success');
        singleSessionId = null;
        $('single-session-info').style.display = 'none';
      }).catch(function(e) { toast('Error: ' + e, 'danger'); });
  };

  // ─── New Session (Multi Mode) ───
  window.newSession = function() {
    var name = prompt('Session profile name:', 'session-' + Date.now());
    if (!name) return;
    fetch('/api/v1/browser/launch', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({profile: name, allow_duplicate: true})
    }).then(function(r){return r.json();}).then(function(d) {
      if (d.session) toast('Session "' + name + '" launched!', 'success');
      else if (d.error) toast(d.error, 'danger');
      refreshSessions();
    }).catch(function(e) { toast('Failed: ' + e, 'danger'); });
  };

  // ─── Refresh Sessions ───
  function refreshSessions() {
    get('/api/v1/browser/sessions').then(function(d) {
      var sessions = d.sessions || [];

      // Single mode: check if our session is still alive
      if (!multiMode) {
        if (singleSessionId) {
          var alive = sessions.some(function(s) { return s.session_id === singleSessionId; });
          if (!alive) {
            singleSessionId = null;
            $('single-session-info').style.display = 'none';
          }
        }
        // If there's a session but we don't know about it (e.g. page reload), pick it up
        if (!singleSessionId && sessions.length > 0) {
          showSingleSession(sessions[0]);
        }
        return;
      }

      // Multi mode: render table
      var tbody = $('multi-sessions-body');
      var empty = $('multi-sessions-empty');
      if (!sessions.length) {
        tbody.innerHTML = '';
        empty.style.display = 'block';
        return;
      }
      empty.style.display = 'none';
      tbody.innerHTML = sessions.map(function(s) {
        var started = s.started_at ? s.started_at.substring(11, 19) : '?';
        var urlShort = (s.url || '').replace('http://','').replace('https://','').substring(0,30);
        return '<tr>' +
          '<td><strong>' + esc(s.profile) + '</strong></td>' +
          '<td class="sb-text-mono" style="font-size:0.8rem">' + esc(urlShort) + '</td>' +
          '<td class="sb-text-muted">' + (s.pid || '?') + '</td>' +
          '<td class="sb-text-muted" style="font-size:0.8rem">' + started + '</td>' +
          '<td>' +
            '<button class="sb-btn sb-btn--sm sb-btn--danger" data-action="closeSession" data-session-id="' + esc(s.session_id) + '">Close</button>' +
          '</td>' +
          '</tr>';
      }).join('');
    });
  }

  window.reloadSessions = function() {
    var btn = $('reload-btn');
    if (btn) { btn.textContent = 'Refreshing...'; btn.disabled = true; }
    refreshSessions();
    setTimeout(function() {
      if (btn) { btn.textContent = 'Refresh'; btn.disabled = false; }
    }, 1000);
  };

  window.focusSession = function(id) {
    fetch('/api/v1/browser/focus/' + id, {method:'POST'})
      .then(function(r){return r.json();})
      .then(function(d) {
        if (d.focused) toast('Browser window focused', 'success');
        else toast('Could not focus: ' + (d.reason || 'unknown'), 'warning');
      }).catch(function(e) { toast('Error: ' + e, 'danger'); });
  };

  // ─── BYOK inline edit ───
  (function() {
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

    display.addEventListener('click', startEdit);
    pen.addEventListener('click', startEdit);

    function saveKey() {
      el.classList.remove('sb-editable--editing');
      var key = input.value.trim();
      if (key && key.length > 4) {
        var masked = key.substring(0, 4) + '...' + key.substring(key.length - 4);
        display.textContent = masked;
        display.style.color = 'var(--sb-success)';
        fetch('/api/v1/cloud/connect', {method:'POST', headers:{'Content-Type':'application/json'},
          body:JSON.stringify({api_key:key, user_email:'byok@local', device_id:'local', paid_user:false})
        }).then(function(){
          toast('BYOK key saved!', 'success');
          $('src-byok-gif').innerHTML = '<img src="/media/yinyang-rotating_70pct_128px.gif" style="height:48px;width:auto">';
          enableLaunchButton();
          ($('topbar-user')||{}).textContent = 'BYOK Active';
          ($('topbar-user')||{}).className = 'sb-pill sb-pill--success';
        });
      } else if (key) {
        toast('Key too short', 'warning');
        display.textContent = 'Not set — click to enter key';
      }
    }

    input.addEventListener('blur', saveKey);
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') input.blur();
      if (e.key === 'Escape') { el.classList.remove('sb-editable--editing'); }
    });
  })();

  // ─── Connect CLIs — user clicks button, we validate each CLI+model ───
  window.connectCLIs = function() {
    $('src-local-action').innerHTML = '<span class="sb-text-muted">Connecting...</span>';
    $('src-local').innerHTML = '<span class="sb-pill sb-pill--warning">⏳ Connecting...</span>';
    $('cli-details-row').style.display = '';

    get('/api/v1/agents').then(function(d) {
      var agents = (d.agents || []).filter(function(a){return a.installed;});
      if (!agents.length) {
        $('cli-models-area').innerHTML = '<span class="sb-text-muted">No CLIs found on PATH</span>';
        return;
      }

      // Build model checklist with ⏳ status
      var html = '';
      agents.forEach(function(a) {
        html += '<div style="margin-bottom:0.5rem"><strong>' + esc(a.id) + '</strong> <span id="cli-status-'+esc(a.id)+'" class="sb-pill sb-pill--warning" style="font-size:0.65rem">⏳ testing</span>';
        html += '<div style="margin-left:1rem;margin-top:0.25rem">';
        (a.models||[]).forEach(function(m) {
          var short = m.replace('claude-','').replace('gpt-','').replace('-20251001','');
          html += '<label style="display:inline-flex;align-items:center;gap:4px;margin-right:1rem;font-size:0.85rem;cursor:pointer">';
          html += '<input type="checkbox" checked style="accent-color:var(--sb-accent)" data-cli="'+esc(a.id)+'" data-model="'+esc(m)+'">';
          html += '<span class="sb-text-mono">' + esc(short) + '</span></label>';
        });
        html += '</div></div>';
      });
      $('cli-models-area').innerHTML = html;

      // Validate each CLI (default model ping)
      var verified = 0;
      var total = agents.length;
      agents.forEach(function(a) {
        fetch('/api/v1/agents/generate', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body:JSON.stringify({agent_id:a.id, prompt:'respond with ok', timeout:15})
        }).then(function(r){return r.json();}).then(function(d) {
          var cell = $('cli-status-'+a.id);
          if (d.response || d.output || d.text) {
            if (cell) cell.innerHTML = '✓ verified'; cell.className = 'sb-pill sb-pill--success';
            cell.style.fontSize = '0.65rem';
            verified++;
          } else {
            if (cell) cell.innerHTML = '✗ ' + esc((d.error||'failed').substring(0,30)); cell.className = 'sb-pill sb-pill--danger';
            cell.style.fontSize = '0.65rem';
          }
        }).catch(function() {
          var cell = $('cli-status-'+a.id);
          if (cell) { cell.innerHTML = '✗ timeout'; cell.className = 'sb-pill sb-pill--danger'; cell.style.fontSize = '0.65rem'; }
        }).finally(function() {
          total--;
          if (total <= 0) {
            // All done
            if (verified > 0) {
              $('src-local').innerHTML = '<span class="sb-pill sb-pill--success">✓ ' + verified + ' connected</span> <a href="#" data-action="connectCLIs" style="font-size:0.75rem;color:var(--sb-text-muted)">rerun</a>';
              $('src-local-action').innerHTML = '<img src="/media/yinyang-rotating_70pct_128px.gif" style="height:48px;width:auto">';
              hasLLM = true;
              enableLaunchButton();
              // Persist validated state
              var chipsHTML = $('cli-models-area').innerHTML;
              try { localStorage.setItem('solace_validated_clis', JSON.stringify({count:verified, chips:chipsHTML})); } catch(e) {}
              ($('topbar-user')||{}).textContent = verified + ' Local LLMs';
              ($('topbar-user')||{}).className = 'sb-pill sb-pill--success';
            } else {
              $('src-local').innerHTML = '<span class="sb-pill sb-pill--danger">✗ No working CLIs</span>';
              $('src-local-action').innerHTML = '<button class="sb-btn sb-btn--sm" data-action="connectCLIs">Retry</button>';
            }
          }
        });
      });
    });
  };

  window.promptBYOK = function() {
    var el = $('byok-editable');
    if (el) {
      el.classList.add('sb-editable--editing');
      $('byok-input').value = '';
      $('byok-input').focus();
    }
  };

  window.openManagedLLM = function() {
    window.open('https://solaceagi.com/dashboard', '_blank');
  };

  // ─── Sign In (launches browser to solaceagi.com/dashboard) ───
  window.signIn = function() {
    toast('Opening browser — complete sign-in there. Hub will detect automatically.', 'success');
    // Show waiting state in LLM card
    var managedGif = $('src-managed-gif');
    if (managedGif) managedGif.innerHTML = '<span class="sb-text-muted" style="font-size:0.8rem">Waiting for sign-in...</span>';
    fetch('/api/v1/browser/launch', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url:'https://solaceagi.com/dashboard', allow_duplicate:true})
    }).then(function(r){return r.json();}).then(function(d) {
      if (d.session_id || d.deduped) toast('Browser opened to solaceagi.com', 'success');
      else if (d.error) toast(d.error, 'danger');
    }).catch(function(){
      // Fallback: open in default browser
      window.open('https://solaceagi.com/dashboard', '_blank');
    });
    // Poll for login completion (bridge will POST cloud/connect)
    var loginPoll = setInterval(function() {
      get('/api/v1/cloud/status').then(function(c) {
        if (c.connected && c.config) {
          clearInterval(loginPoll);
          toast('Signed in as ' + (c.config.user_email || 'user'), 'success');
          // Refresh UI
          $('topbar-signin').style.display = 'none';
          $('topbar-user-info').style.display = 'flex';
          $('topbar-user').textContent = c.config.user_email || 'Connected';
          loadSettingsInfo();
          loadRemoteStatus();
        }
      }).catch(function(){});
    }, 3000);
    // Stop polling after 5 minutes
    setTimeout(function() { clearInterval(loginPoll); }, 300000);
  };

  // ─── Sign Out (disconnects cloud, reverts to gate state) ───
  window.signOut = function() {
    fetch('/api/v1/cloud/disconnect', {method:'POST'}).then(function(r){return r.json();}).then(function() {
      toast('Signed out', 'success');
      $('topbar-signin').style.display = 'inline-flex';
      $('topbar-user-info').style.display = 'none';
      $('src-managed').innerHTML = '<span class="sb-pill sb-pill--warning">Not signed in</span>';
      $('src-managed-gif').innerHTML = '<button class="sb-btn sb-btn--sm" data-action="signIn">Sign In</button>';
      loadSettingsInfo();
    }).catch(function(e) { toast('Sign out failed: ' + e.message, 'error'); });
  };

  // ─── Ollama inline edit ───
  (function() {
    var el = $('ollama-editable');
    if (!el) return;
    var display = el.querySelector('.sb-editable-display');
    var input = el.querySelector('.sb-editable-input');
    var pen = el.querySelector('.sb-editable-pen');
    function startEdit() { el.classList.add('sb-editable--editing'); input.value = ''; input.focus(); }
    display.addEventListener('click', startEdit);
    pen.addEventListener('click', startEdit);
    function saveUrl() {
      el.classList.remove('sb-editable--editing');
      var url = input.value.trim();
      if (url && url.startsWith('http')) {
        display.textContent = url;
        display.style.color = 'var(--sb-success)';
        $('src-ollama-gif').innerHTML = '<img src="/media/yinyang-rotating_70pct_128px.gif" style="height:48px;width:auto">';
        hasLLM = true;
        enableLaunchButton();
        toast('Ollama URL saved!', 'success');
      } else if (url) {
        toast('URL must start with http', 'warning');
      }
    }
    input.addEventListener('blur', saveUrl);
    input.addEventListener('keydown', function(e) { if (e.key === 'Enter') input.blur(); if (e.key === 'Escape') el.classList.remove('sb-editable--editing'); });
  })();

  // ─── Delegated click handler for data-action attributes and dynamic buttons ───
  document.addEventListener('click', function(e) {
    // data-action delegation
    var actionEl = e.target.closest('[data-action]');
    if (actionEl) {
      var action = actionEl.dataset.action;
      if (action === 'closeSession') {
        e.preventDefault();
        var sessionId = actionEl.dataset.sessionId;
        if (sessionId) window.closeSession(sessionId);
        return;
      }
      if (action === 'connectCLIs') { e.preventDefault(); connectCLIs(); return; }
      if (typeof window[action] === 'function') {
        e.preventDefault();
        window[action](e);
        return;
      }
    }
    // Fallback: text-based delegation for dynamically created buttons
    var btn = e.target.closest('button');
    if (!btn) return;
    var text = btn.textContent.trim();
    if (text === 'Launch Solace Browser') { e.preventDefault(); launchBrowser(); }
    else if (text === 'Sign In' && btn.closest('#src-managed-gif')) { e.preventDefault(); signIn(); }
    else if (text === 'Connect CLIs') { e.preventDefault(); connectCLIs(); }
    else if (text === 'Add Key') { e.preventDefault(); promptBYOK(); }
    else if (text === 'Retry') { e.preventDefault(); connectCLIs(); }
  });

  // ─── Enable Launch Button (single mode) ───
  function enableLaunchButton() {
    $('launch-btn-area').innerHTML = '<button class="sb-btn sb-btn--primary hub-launch" data-action="launchBrowser">Launch Solace Browser</button>';
  }

  // ─── Mode Toggle ───
  var modeInitialized = false;
  var toggle = $('multi-session-toggle');
  if (toggle) {
    var saved = '0';
    try { saved = localStorage.getItem('solace_multi_session') || '0'; } catch(e) {}
    toggle.checked = saved === '1';
    // On init: just set UI, don't close sessions
    multiMode = toggle.checked;
    $('single-mode').style.display = multiMode ? 'none' : 'block';
    $('multi-mode').style.display = multiMode ? 'block' : 'none';
    var sessNewBtnInit = $('sessions-tab-new-btn');
    if (sessNewBtnInit) sessNewBtnInit.style.display = multiMode ? 'inline-flex' : 'none';
    modeInitialized = true;
    toggle.addEventListener('change', function() { setSessionMode(toggle.checked); });
  }

  // ─── Close Session ───
  window.closeSession = function(id) {
    fetch('/api/v1/browser/close/' + id, {method:'POST'})
      .then(function(r){return r.json();})
      .then(function(d) {
        toast('Session closed: ' + (d.profile || id), 'success');
        if (id === singleSessionId) {
          singleSessionId = null;
          $('single-session-info').style.display = 'none';
        }
        refreshSessions();
        refreshSessionsTab();
      }).catch(function(e) { toast('Error: ' + e, 'danger'); });
  };

  // ─── Sessions Tab (full view) ───
  function refreshSessionsTab() {
    get('/api/v1/browser/sessions').then(function(d) {
      var sessions = d.sessions || [];
      var tbody = $('sessions-tab-body');
      var empty = $('sessions-tab-empty');
      if (!sessions.length) { tbody.innerHTML = ''; empty.style.display = 'block'; empty.textContent = 'No active sessions. Click "Launch Default" or "+ New Session".'; return; }
      empty.style.display = 'none';
      tbody.innerHTML = sessions.map(function(s) {
        var started = s.started_at ? s.started_at.substring(0, 19).replace('T',' ') : '?';
        return '<tr>' +
          '<td><strong>' + esc(s.profile) + '</strong></td>' +
          '<td class="sb-text-mono" style="font-size:0.8rem">' + esc(s.url || '') + '</td>' +
          '<td class="sb-text-muted">' + (s.pid || '?') + '</td>' +
          '<td class="sb-text-muted" style="font-size:0.8rem">' + started + '</td>' +
          '<td><button class="sb-btn sb-btn--sm sb-btn--danger" data-action="closeSession" data-session-id="' + esc(s.session_id) + '">Close</button></td>' +
          '</tr>';
      }).join('');
    });
    get('/api/v1/browser/profiles').then(function(d) {
      var profiles = d.profiles || [];
      $('profiles-list').innerHTML = profiles.map(function(p) {
        return '<span class="hub-llm-chip">' + esc(p) + '</span>';
      }).join('');
    });
  }

  // ─── Events Tab (DataTables) ───
  var eventsTable = null;
  window.refreshEvents = function() {
    $('events-empty').textContent = 'Loading...';
    get('/api/v1/events').then(function(d) {
      var events = d.events || [];
      var empty = $('events-empty');
      if (!events.length) { empty.style.display = 'block'; empty.textContent = 'No events yet. Heartbeat events will appear here.'; return; }
      empty.style.display = 'none';

      // Destroy existing DataTable if any
      if (eventsTable) { eventsTable.destroy(); eventsTable = null; }

      var levelColors = {L1:'info',L2:'success',L3:'warning',L4:'danger',L5:'danger'};
      var tbody = $('events-body');
      tbody.innerHTML = events.map(function(ev) {
        var ts = (ev.timestamp || '').substring(0, 19).replace('T',' ');
        var lvl = ev.level || 'L1';
        var cls = levelColors[lvl] || 'info';
        var evType = ev.type || ev.event_type || '?';
        var domain = ev.domain || '';
        var appId = ev.app_id || '';
        var detail = ev.message || ev.details || '';
        if (!detail && ev.data) detail = JSON.stringify(ev.data).substring(0,120);
        var eventUrl = '/dashboard#event-' + (ev.id || ev.timestamp || '');
        var sessionShort = ev.session_id ? ev.session_id.substring(0,8) : '';
        return '<tr class="hub-event-row" data-action="openEventDetail" data-event-url="' + esc(eventUrl) + '">' +
          '<td class="sb-text-muted" style="white-space:nowrap">' + ts + '</td>' +
          '<td><span class="sb-pill sb-pill--' + cls + '" style="font-size:0.65rem">' + lvl + '</span></td>' +
          '<td>' + esc(evType) + '</td>' +
          '<td class="sb-text-muted">' + esc(domain) + '</td>' +
          '<td class="sb-text-muted">' + esc(appId) + '</td>' +
          '<td class="sb-text-mono sb-text-muted" style="font-size:0.75rem">' + sessionShort + '</td>' +
          '<td style="font-size:0.8rem;max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">' + esc(detail) + '</td>' +
          '</tr>';
      }).join('');

      // Initialize DataTable if jQuery + DataTables available
      if (window.jQuery && jQuery.fn.DataTable) {
        eventsTable = jQuery('#events-datatable').DataTable({
          order: [[0, 'desc']],
          pageLength: 25,
          dom: 'frtip',
          language: { search: 'Filter:' }
        });
        // Level filter dropdown
        var levelFilter = $('events-level-filter');
        if (levelFilter) {
          levelFilter.onchange = function() {
            if (eventsTable) eventsTable.column(1).search(this.value).draw();
          };
        }
      }
    }).catch(function() {
      $('events-empty').textContent = 'Failed to load events';
      $('events-empty').style.display = 'block';
    });
  };

  // Open event detail in Solace Browser
  window.openEventDetail = function(e) {
    var row = e.target.closest('[data-event-url]');
    var url = row ? row.dataset.eventUrl : null;
    if (!url) return;
    var fullUrl = 'http://localhost:8888' + url;
    fetch('/api/v1/browser/launch', {method:'POST', headers:{'Content-Type':'application/json'},
      body:JSON.stringify({url: fullUrl})
    }).then(function(r){return r.json();}).then(function(d) {
      if (d.deduped) toast('Opened in existing browser', 'success');
      else if (d.session) toast('Browser opened to event', 'success');
    }).catch(function(){ window.open(fullUrl, '_blank'); });
  };

  // ─── Settings Tab ───
  function refreshSettings() {
    get('/health').then(function(d) {
      if (d.pid) $('settings-pid').textContent = d.pid;
      if (d.server) $('settings-binary').textContent = d.server;
    });
    get('/api/v1/agents').then(function(d) {
      var agents = d.agents || [];
      var installed = agents.filter(function(a){return a.installed;});
      $('settings-llm').innerHTML = installed.length ?
        installed.map(function(a) {
          return '<div style="margin:0.3rem 0"><strong>' + esc(a.id) + '</strong> — ' + (a.models||[]).join(', ') + '</div>';
        }).join('') :
        '<span class="sb-text-muted">No LLM CLIs detected</span>';
    });
  }

  // ─── Tab Switching ───
  document.querySelectorAll('.sb-tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
      document.querySelectorAll('.sb-tab').forEach(function(t) { t.classList.remove('sb-tab--active'); t.setAttribute('aria-selected','false'); });
      tab.classList.add('sb-tab--active');
      tab.setAttribute('aria-selected','true');
      var target = tab.dataset.tab;
      document.querySelectorAll('.hub-tab-panel').forEach(function(p) { p.style.display = 'none'; });
      var panel = $('tab-' + target);
      if (panel) panel.style.display = 'block';
      // Refresh data when switching tabs
      if (target === 'sessions') refreshSessionsTab();
      if (target === 'events') refreshEvents();
      if (target === 'settings') refreshSettings();
    });
  });

  // ─── Signoffs (L3+ pending approvals) ───
  function refreshSignoffs() {
    get('/api/v1/notifications').then(function(d) {
      var items = (d.notifications || []).filter(function(n) { return n.action_required || n.level >= 3; });
      var banner = $('signoffs-banner');
      var badge = $('events-badge');
      if (!items.length) { banner.classList.add('hidden'); if (badge) badge.style.display = 'none'; return; }
      banner.classList.remove('hidden');
      $('signoffs-count').textContent = items.length;
      if (badge) { badge.textContent = items.length; badge.style.display = 'inline'; }
      $('signoffs-list').innerHTML = items.map(function(n) {
        return '<div style="display:flex;align-items:center;justify-content:space-between;padding:0.4rem 0;border-bottom:1px solid var(--sb-border)">' +
          '<div><span class="sb-pill sb-pill--warning" style="font-size:0.6rem">L' + (n.level || 3) + '</span> ' + esc(n.message || n.title || 'Action required') +
          (n.session_id ? ' <span class="sb-text-muted" style="font-size:0.75rem">[' + esc(n.session_id.substring(0,8)) + ']</span>' : '') +
          '</div>' +
          '<div class="sb-flex sb-gap-sm">' +
          '<button class="sb-btn sb-btn--sm sb-btn--primary" data-action="approveSignoff" data-signoff-id="' + esc(n.id || '') + '">Approve</button>' +
          '<button class="sb-btn sb-btn--sm sb-btn--danger" data-action="rejectSignoff" data-signoff-id="' + esc(n.id || '') + '">Reject</button>' +
          '</div></div>';
      }).join('');
    }).catch(function(){});
  }

  window.approveSignoff = function(e) {
    var el = e.target.closest('[data-signoff-id]');
    var id = el ? el.dataset.signoffId : '';
    if (!id) return;
    fetch('/api/v1/notifications/' + id + '/read', {method:'POST'}).then(function() {
      toast('Approved', 'success'); refreshSignoffs();
    });
  };
  window.rejectSignoff = function(e) {
    var el = e.target.closest('[data-signoff-id]');
    var id = el ? el.dataset.signoffId : '';
    if (!id) return;
    fetch('/api/v1/notifications/' + id + '/read', {method:'POST'}).then(function() {
      toast('Rejected', 'warning'); refreshSignoffs();
    });
  };

  window.disconnectRemote = function() {
    fetch('/api/v1/tunnel/disconnect', {method:'POST'}).then(function(r){return r.json()}).then(function(d) {
      toast('Remote access disconnected', 'success');
      loadRemoteStatus();
    }).catch(function(e) { toast('Disconnect failed: ' + e.message, 'error'); });
  };

  // ─── Init ───
  runScan();
  // Refresh sessions on load and every 10s
  setTimeout(refreshSessions, 2000);
  setInterval(refreshSessions, 10000);
  // Signoffs poll every 5s
  setTimeout(refreshSignoffs, 3000);
  setInterval(refreshSignoffs, 5000);

  function loadVersionInfo() {
    get('/health').then(function(d) {
      var v = d.version || '?';
      var badge = $('hub-version-badge');
      if (badge) badge.textContent = 'v' + v;
      var sv = $('settings-version');
      if (sv) sv.textContent = v;
    }).catch(function(){});

    get('/api/v1/system/updates').then(function(d) {
      if ($('settings-autoupdate')) $('settings-autoupdate').textContent = d.auto_update_enabled ? 'ON' : 'OFF';
      if ($('settings-latest')) $('settings-latest').textContent = d.latest_version || 'up to date';
      if ($('settings-last-check')) $('settings-last-check').textContent = d.last_check ? d.last_check.substring(0,19).replace('T',' ') : '—';
      if (d.update_available) {
        var badge = $('hub-version-badge');
        if (badge) { badge.textContent = 'v' + d.current_version + ' → v' + d.latest_version; badge.className = 'sb-pill sb-pill--warning'; }
      }
    }).catch(function(){});
  }

  function loadRemoteStatus() {
    get('/api/v1/tunnel/status').then(function(d) {
      var connected = d.tunnel_connected;
      var consent = d.consent_active || (d.consent && d.consent !== null);
      var dot = $('remote-status-dot');
      var text = $('remote-status-text');
      var detail = $('remote-status-detail');
      var consentBtn = $('remote-consent-btn');
      var disconnectBtn = $('remote-disconnect-btn');
      if (connected || consent) {
        if (dot) dot.style.background = 'var(--sb-warning, #f59e0b)';
        if (text) text.textContent = 'Remote access: ACTIVE';
        if (detail) detail.textContent = connected ? 'Tunnel connected. Remote agent can control your browser.' : 'Consent signed. Waiting for connection.';
        if (consentBtn) consentBtn.style.display = 'none';
        if (disconnectBtn) { disconnectBtn.classList.remove('hidden'); disconnectBtn.style.display = 'inline-flex'; }
      } else {
        if (dot) dot.style.background = 'var(--sb-success, #22c55e)';
        if (text) text.textContent = 'Remote access: OFF';
        if (detail) detail.textContent = 'No active consent. Your machine is private.';
        if (consentBtn) consentBtn.style.display = 'inline-flex';
        if (disconnectBtn) { disconnectBtn.classList.add('hidden'); disconnectBtn.style.display = ''; }
      }
    }).catch(function(){});

    get('/api/v1/tunnel/audit').then(function(d) {
      var entries = d.entries || [];
      var list = $('remote-audit-list');
      if (!list) return;
      if (!entries.length) { list.innerHTML = '<p class="sb-text-muted" style="text-align:center;padding:1rem">No remote actions recorded</p>'; return; }
      var html = '<table class="sb-table" style="font-size:0.8rem"><thead><tr><th>Event</th><th>Actor</th><th>Time</th><th>Hash</th></tr></thead><tbody>';
      entries.slice(0,20).forEach(function(e) {
        html += '<tr><td>' + esc(e.event||'?') + '</td><td>' + esc(e.actor||'?') + '</td><td style="font-size:0.75rem">' + esc((e.timestamp||'').substring(0,19)) + '</td><td style="font-family:var(--sb-font-mono);font-size:0.7rem">' + esc((e.hash||'').substring(0,12)) + '...</td></tr>';
      });
      html += '</tbody></table>';
      list.innerHTML = html;
    }).catch(function(){});
  }

  function loadSettingsInfo() {
    get('/api/v1/cloud/status').then(function(d) {
      if (d.connected && d.config) {
        if ($('settings-auth-status')) $('settings-auth-status').textContent = 'Connected';
        if ($('settings-auth-status')) $('settings-auth-status').style.color = 'var(--sb-success, #22c55e)';
        if ($('settings-auth-email')) $('settings-auth-email').textContent = d.config.user_email || '—';
        if ($('settings-device-id')) $('settings-device-id').textContent = d.config.device_id || '—';
        if ($('settings-plan')) $('settings-plan').textContent = d.config.paid_user ? 'Paid' : 'Free';
        // Update managed LLM sign-in button to show connected state
        if ($('src-managed-gif') && d.config.user_email) {
          $('src-managed-gif').innerHTML = '<span class="sb-pill sb-pill--success" style="font-size:0.75rem">Connected</span>';
        }
      } else {
        if ($('settings-auth-status')) $('settings-auth-status').textContent = 'Not connected';
        if ($('settings-auth-status')) $('settings-auth-status').style.color = 'var(--sb-text-muted)';
      }
    }).catch(function(){});
  }

})();
