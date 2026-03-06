/**
 * onboarding.js — Solace Browser first-run LLM setup
 *
 * 4 paths offered:
 *   1. Auto-Detect AI Agents — scans for installed CLIs, auto-mounts webservices
 *   2. AI Agent Mode (MCP) — manual MCP config
 *   3. BYOK — paste your own API key (free forever)
 *   4. Managed — Solace handles it ($8/mo Starter)
 *
 * On first boot: auto-detect runs automatically, shows activation cards.
 * Cache persists in ~/.solace/cli-agents-cache.json (server) + localStorage (client).
 *
 * Storage: localStorage['solace_llm_configured'] = '1'
 * Force re-show: ?onboard=1
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'solace_llm_configured';
  const AGENTS_KEY = 'solace_cli_agents';
  const CLOUD = 'https://www.solaceagi.com';

  function shouldShow() {
    const params = new URLSearchParams(window.location.search);
    if (params.get('onboard') === '1') return true;
    if (localStorage.getItem(STORAGE_KEY) === '1') return false;
    if (localStorage.getItem('sb_tutorial_v1') === 'done') return false;
    const path = window.location.pathname.replace(/\/$/, '') || '/';
    if (path !== '/' && path !== '/home') return false;
    return true;
  }

  const CSS = `
    #sbOnboard {
      position: fixed; inset: 0; z-index: 9999;
      background: rgba(2,8,18,0.92);
      backdrop-filter: blur(12px);
      display: flex; align-items: center; justify-content: center;
      padding: 24px;
      opacity: 0; transition: opacity 0.3s ease;
    }
    #sbOnboard.is-visible { opacity: 1; }
    #sbOnboard.is-exit { opacity: 0; }

    #sbOnboardCard {
      background: linear-gradient(160deg, #0d1a26 0%, #081019 100%);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 20px;
      padding: 32px 36px;
      max-width: 520px;
      width: 100%;
      box-shadow: 0 32px 80px rgba(0,0,0,0.6);
      position: relative;
      transform: translateY(20px); opacity: 0;
      transition: transform 0.4s ease, opacity 0.4s ease;
    }
    #sbOnboard.is-visible #sbOnboardCard {
      transform: translateY(0); opacity: 1;
    }

    .ob-yy {
      display: block; margin: 0 auto 12px;
      width: 64px; height: 64px;
      border-radius: 50%; overflow: hidden;
      box-shadow: 0 0 24px rgba(100,196,255,0.25);
    }
    .ob-yy img { width: 100%; height: 100%; object-fit: cover; object-position: center; }

    .ob-title {
      margin: 0 0 6px;
      font-size: 1.2rem; font-weight: 800;
      text-align: center; color: #fff;
    }
    .ob-sub {
      margin: 0 0 20px;
      font-size: 0.82rem; color: rgba(255,255,255,0.45);
      text-align: center; line-height: 1.4;
    }

    .ob-paths { display: flex; flex-direction: column; gap: 8px; margin-bottom: 16px; }
    .ob-path {
      display: flex; align-items: center; gap: 12px;
      padding: 14px 16px; border-radius: 12px;
      border: 1px solid rgba(255,255,255,0.08);
      cursor: pointer; transition: all 0.15s;
      background: rgba(255,255,255,0.02);
    }
    .ob-path:hover { border-color: rgba(100,196,255,0.3); background: rgba(100,196,255,0.03); }
    .ob-path__icon { font-size: 1.3rem; flex-shrink: 0; width: 32px; text-align: center; }
    .ob-path__info h4 { margin: 0; font-size: 0.85rem; font-weight: 700; color: #fff; }
    .ob-path__info p { margin: 2px 0 0; font-size: 0.72rem; color: rgba(255,255,255,0.4); }
    .ob-path__price {
      margin-left: auto;
      font-size: 0.7rem; font-weight: 700;
      padding: 3px 8px; border-radius: 4px;
      background: rgba(0,200,150,0.12); color: #00c896;
      white-space: nowrap;
    }

    /* Detection overlay */
    .ob-detect {
      display: none; text-align: center;
    }
    .ob-detect.is-active { display: block; }

    .ob-detect__splash {
      width: 120px; height: 120px;
      margin: 0 auto 16px;
      border-radius: 50%;
      overflow: hidden;
      box-shadow: 0 0 40px rgba(100,196,255,0.3);
      animation: ob-pulse 2s ease-in-out infinite;
    }
    .ob-detect__splash img { width: 100%; height: 100%; object-fit: cover; }

    @keyframes ob-pulse {
      0%, 100% { box-shadow: 0 0 40px rgba(100,196,255,0.3); }
      50% { box-shadow: 0 0 60px rgba(100,196,255,0.5); }
    }

    .ob-detect__status {
      font-size: 0.9rem; font-weight: 700; color: #fff;
      margin: 0 0 4px;
    }
    .ob-detect__sub {
      font-size: 0.72rem; color: rgba(255,255,255,0.4);
      margin: 0 0 20px;
    }

    .ob-agents-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 8px;
      margin-bottom: 20px;
    }

    .ob-agent-card {
      padding: 12px;
      border-radius: 10px;
      border: 1px solid rgba(255,255,255,0.06);
      background: rgba(255,255,255,0.02);
      text-align: left;
      opacity: 0.3;
      transform: scale(0.95);
      transition: all 0.4s ease;
    }
    .ob-agent-card.is-scanning {
      opacity: 0.5;
      border-color: rgba(100,196,255,0.2);
    }
    .ob-agent-card.is-found {
      opacity: 1;
      transform: scale(1);
      border-color: rgba(0,200,150,0.4);
      background: rgba(0,200,150,0.05);
    }
    .ob-agent-card.is-missing {
      opacity: 0.25;
    }

    .ob-agent-card__head {
      display: flex; align-items: center; gap: 8px; margin-bottom: 4px;
    }
    .ob-agent-card__icon {
      width: 28px; height: 28px;
      border-radius: 6px;
      background: rgba(255,255,255,0.06);
      display: flex; align-items: center; justify-content: center;
      font-size: 0.7rem; font-weight: 800; color: rgba(255,255,255,0.5);
      flex-shrink: 0;
    }
    .ob-agent-card.is-found .ob-agent-card__icon {
      background: rgba(0,200,150,0.15);
      color: #00c896;
    }
    .ob-agent-card__name {
      font-size: 0.78rem; font-weight: 700; color: #fff;
    }
    .ob-agent-card__status {
      font-size: 0.65rem; color: rgba(255,255,255,0.3);
      margin: 0;
    }
    .ob-agent-card.is-found .ob-agent-card__status {
      color: #00c896;
    }
    .ob-agent-card.is-scanning .ob-agent-card__status {
      color: rgba(100,196,255,0.6);
    }

    .ob-detect__done {
      font-size: 0.85rem; font-weight: 700; color: #00c896;
      margin: 0 0 12px;
    }
    .ob-detect__continue {
      padding: 10px 24px; border-radius: 10px; border: none;
      background: linear-gradient(135deg, #00c896, #00a87a);
      color: #000; font-size: 0.85rem; font-weight: 700;
      cursor: pointer; width: 100%;
      transition: opacity 0.15s;
    }
    .ob-detect__continue:hover { opacity: 0.88; }

    .ob-detect__rescan {
      display: inline-block; margin-top: 8px;
      color: rgba(255,255,255,0.3); font-size: 0.68rem;
      cursor: pointer; background: none; border: none; padding: 4px 8px;
    }
    .ob-detect__rescan:hover { color: rgba(255,255,255,0.5); }

    /* BYOK expand */
    .ob-byok { display: none; padding: 12px 0 0; }
    .ob-byok.is-active { display: block; }
    .ob-byok label { display: block; font-size: 0.72rem; color: rgba(255,255,255,0.35); margin-bottom: 4px; }
    .ob-byok select, .ob-byok input {
      width: 100%; padding: 8px 10px; border-radius: 8px;
      border: 1px solid rgba(255,255,255,0.1);
      background: rgba(255,255,255,0.04); color: #fff;
      font-size: 0.82rem; margin-bottom: 6px; box-sizing: border-box;
    }
    .ob-byok input:focus, .ob-byok select:focus { outline: none; border-color: rgba(0,200,150,0.5); }
    .ob-byok-save {
      margin-top: 6px; padding: 8px 16px; border-radius: 8px; border: none;
      background: #00c896; color: #000; font-size: 0.82rem; font-weight: 700;
      cursor: pointer; width: 100%;
    }
    .ob-byok-save:hover { opacity: 0.88; }

    .ob-skip {
      display: block; text-align: center; margin-top: 8px;
      color: rgba(255,255,255,0.2); font-size: 0.7rem;
      cursor: pointer; background: none; border: none; width: 100%; padding: 4px;
    }
    .ob-skip:hover { color: rgba(255,255,255,0.4); }

    .ob-back {
      position: absolute; top: 16px; left: 16px;
      color: rgba(255,255,255,0.3); font-size: 0.72rem;
      cursor: pointer; background: none; border: none; padding: 4px 8px;
    }
    .ob-back:hover { color: rgba(255,255,255,0.5); }

    @media (max-width: 520px) {
      #sbOnboardCard { padding: 24px 20px; }
      .ob-agents-grid { grid-template-columns: 1fr; }
    }
  `;

  /* ── Agent Card Definitions ── */
  const AGENT_CARDS = [
    { id: 'claude', name: 'Claude Code', icon: 'A', provider: 'Anthropic' },
    { id: 'codex', name: 'OpenAI Codex', icon: 'O', provider: 'OpenAI' },
    { id: 'gemini', name: 'Gemini CLI', icon: 'G', provider: 'Google' },
    { id: 'copilot', name: 'GitHub Copilot', icon: 'C', provider: 'GitHub' },
    { id: 'antigravity', name: 'Antigravity', icon: 'AG', provider: 'Antigravity' },
    { id: 'cursor', name: 'Cursor', icon: 'Cu', provider: 'Cursor' },
    { id: 'aider', name: 'Aider', icon: 'Ai', provider: 'Multiple' },
  ];

  /* ── Render: Path selection screen ── */
  function renderPaths() {
    const name = (localStorage.getItem('solace_user_email') || '').split('@')[0];
    const greeting = name ? "Hi " + name + "! One quick thing." : "One quick thing before we start.";

    return '<div class="ob-yy"><img src="/images/yinyang/yinyang-rotating_70pct_256px.gif" alt="YinYang"></div>' +
      '<h2 class="ob-title">' + greeting + '</h2>' +
      '<p class="ob-sub">How do you want to power Solace Browser?</p>' +
      '<div class="ob-paths">' +

        '<div class="ob-path" id="obAutoDetect">' +
          '<div class="ob-path__icon"><img src="/images/ai-brain.png" alt="" style="width:28px;height:28px;border-radius:6px"></div>' +
          '<div class="ob-path__info">' +
            '<h4>Auto-Detect My AI Agents</h4>' +
            '<p>Scans for Claude Code, Codex, Gemini, Copilot, Cursor, Aider &amp; more</p>' +
          '</div>' +
          '<span class="ob-path__price">Free</span>' +
        '</div>' +

        '<div class="ob-path" id="obBYOK">' +
          '<div class="ob-path__icon">&#x1f511;</div>' +
          '<div class="ob-path__info">' +
            '<h4>Bring Your Own Key</h4>' +
            '<p>Paste your OpenRouter, Claude, or OpenAI API key</p>' +
          '</div>' +
          '<span class="ob-path__price">Free</span>' +
        '</div>' +

        '<div class="ob-path" id="obManaged">' +
          '<div class="ob-path__icon">&#x26a1;</div>' +
          '<div class="ob-path__info">' +
            '<h4>Solace Managed</h4>' +
            '<p>We handle LLM, team sync, eSign, FDA compliance</p>' +
          '</div>' +
          '<span class="ob-path__price">From $8/mo (Starter)</span>' +
        '</div>' +

      '</div>' +

      '<div class="ob-byok" id="obByokFields">' +
        '<label>Provider</label>' +
        '<select id="obProvider">' +
          '<option value="openrouter">OpenRouter (recommended — all models)</option>' +
          '<option value="anthropic">Anthropic (Claude)</option>' +
          '<option value="openai">OpenAI (GPT-4o)</option>' +
        '</select>' +
        '<label>API Key</label>' +
        '<input type="password" id="obApiKey" placeholder="sk-or-v1-..." autocomplete="off">' +
        '<button class="ob-byok-save" id="obSave">Save & Continue</button>' +
      '</div>' +

      '<button class="ob-skip" id="obSkip">I\'ll set this up later</button>';
  }

  /* ── Render: Auto-detect screen ── */
  function renderDetect() {
    let cards = '';
    for (let i = 0; i < AGENT_CARDS.length; i++) {
      const a = AGENT_CARDS[i];
      cards += '<div class="ob-agent-card" id="obCard_' + a.id + '">' +
        '<div class="ob-agent-card__head">' +
          '<div class="ob-agent-card__icon">' + a.icon + '</div>' +
          '<span class="ob-agent-card__name">' + a.name + '</span>' +
        '</div>' +
        '<p class="ob-agent-card__status">Waiting...</p>' +
      '</div>';
    }

    return '<button class="ob-back" id="obBack">&larr; Back</button>' +
      '<div class="ob-detect is-active" id="obDetectPanel">' +
        '<div class="ob-detect__splash"><img src="/images/ai-brain.png" alt="AI Detection"></div>' +
        '<p class="ob-detect__status" id="obDetectStatus">Detecting your AI agents...</p>' +
        '<p class="ob-detect__sub" id="obDetectSub">Scanning for installed CLI tools. This only takes a moment.</p>' +
        '<div class="ob-agents-grid" id="obAgentsGrid">' + cards + '</div>' +
        '<p class="ob-detect__done" id="obDetectDone" style="display:none"></p>' +
        '<button class="ob-detect__continue" id="obDetectContinue" style="display:none">Continue with detected agents</button>' +
        '<button class="ob-detect__rescan" id="obRescan" style="display:none">&#x1f504; Rescan</button>' +
      '</div>';
  }

  /* ── Detection logic ── */
  function runDetection(rescan) {
    const url = '/api/cli-agents' + (rescan ? '?rescan=1' : '');
    const statusEl = document.getElementById('obDetectStatus');
    const subEl = document.getElementById('obDetectSub');
    const doneEl = document.getElementById('obDetectDone');
    const continueBtn = document.getElementById('obDetectContinue');
    const rescanBtn = document.getElementById('obRescan');

    // Reset all cards to scanning
    for (let i = 0; i < AGENT_CARDS.length; i++) {
      const card = document.getElementById('obCard_' + AGENT_CARDS[i].id);
      if (card) {
        card.className = 'ob-agent-card is-scanning';
        card.querySelector('.ob-agent-card__status').textContent = 'Scanning...';
      }
    }

    statusEl.textContent = 'Detecting your AI agents...';
    subEl.textContent = 'Scanning for installed CLI tools. This only takes a moment.';
    doneEl.style.display = 'none';
    continueBtn.style.display = 'none';
    rescanBtn.style.display = 'none';

    fetch(url)
      .then(function(r) { return r.json(); })
      .then(function(data) {
        const agents = data.agents || [];
        let found = 0;
        let delay = 0;

        // Animate cards one by one
        agents.forEach(function(agent) {
          delay += 200;
          setTimeout(function() {
            const card = document.getElementById('obCard_' + agent.id);
            if (!card) return;
            const statusP = card.querySelector('.ob-agent-card__status');
            if (agent.installed) {
              found++;
              card.className = 'ob-agent-card is-found';
              statusP.textContent = '✓ Active — ' + agent.path.split('/').pop();
            } else {
              card.className = 'ob-agent-card is-missing';
              statusP.textContent = 'Not installed';
            }
          }, delay);
        });

        // Show results after all cards animate
        setTimeout(function() {
          const installed = data.installed_count || 0;
          if (installed > 0) {
            statusEl.textContent = 'Ready to go!';
            subEl.textContent = installed + ' AI agent' + (installed > 1 ? 's' : '') + ' detected and integrated.';
            doneEl.textContent = installed + '/' + agents.length + ' agents activated — each app can pick its own AI backend';
            doneEl.style.display = 'block';
            continueBtn.style.display = 'block';
            continueBtn.textContent = 'Continue with ' + installed + ' agent' + (installed > 1 ? 's' : '');
          } else {
            statusEl.textContent = 'No AI agents found';
            subEl.textContent = 'Install Claude Code, Codex, or Gemini CLI to use agent mode.';
            continueBtn.style.display = 'block';
            continueBtn.textContent = 'Continue without agents';
          }
          rescanBtn.style.display = 'inline-block';

          // Cache to localStorage
          localStorage.setItem(AGENTS_KEY, JSON.stringify(data));
        }, delay + 300);
      })
      .catch(function() {
        statusEl.textContent = 'Detection failed';
        subEl.textContent = 'Could not reach the server. Make sure Solace Browser is running.';
        rescanBtn.style.display = 'inline-block';
      });
  }

  /* ── Screen switching ── */
  function showDetectScreen() {
    const card = document.getElementById('sbOnboardCard');
    card.innerHTML = renderDetect();
    bindDetectEvents();
    runDetection(false);
  }

  function showPathScreen() {
    const card = document.getElementById('sbOnboardCard');
    card.innerHTML = renderPaths();
    bindPathEvents();
  }

  function bindDetectEvents() {
    document.getElementById('obBack').addEventListener('click', showPathScreen);
    document.getElementById('obDetectContinue').addEventListener('click', function() {
      localStorage.setItem('solace_onboard_path', 'agent');
      finish();
    });
    document.getElementById('obRescan').addEventListener('click', function() {
      runDetection(true);
    });
  }

  function bindPathEvents() {
    document.getElementById('obAutoDetect').addEventListener('click', showDetectScreen);

    document.getElementById('obBYOK').addEventListener('click', function() {
      document.getElementById('obByokFields').classList.toggle('is-active');
    });

    document.getElementById('obManaged').addEventListener('click', function() {
      // Mark as managed preference, the setup wizard handles plan selection
      localStorage.setItem('solace_onboard_path', 'managed');
      finish();
    });

    document.getElementById('obSave').addEventListener('click', function() {
      const apiKey = (document.getElementById('obApiKey').value || '').trim();
      if (!apiKey) {
        document.getElementById('obApiKey').style.borderColor = '#ff6b6b';
        document.getElementById('obApiKey').focus();
        return;
      }
      const provider = document.getElementById('obProvider').value;
      saveBYOK(provider, apiKey);
    });

    document.getElementById('obSkip').addEventListener('click', finish);
  }

  function saveBYOK(provider, apiKey) {
    fetch('/api/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        llm: {
          backend: provider,
          byok_key: apiKey,
          model: provider === 'openrouter'
            ? 'meta-llama/llama-3.3-70b-instruct'
            : (provider === 'anthropic' ? 'claude-haiku-4-5-20251001' : 'gpt-4o-mini'),
        }
      })
    }).then(function() { finish(); }).catch(function() { finish(); });
  }

  function finish() {
    localStorage.setItem(STORAGE_KEY, '1');
    localStorage.setItem('sb_tutorial_v1', 'done');
    const overlay = document.getElementById('sbOnboard');
    if (overlay) {
      overlay.classList.add('is-exit');
      setTimeout(function() { overlay.parentNode && overlay.parentNode.removeChild(overlay); }, 300);
    }
  }

  function init() {
    if (!shouldShow()) return;
    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);
    const overlay = document.createElement('div');
    overlay.id = 'sbOnboard';
    overlay.innerHTML = '<div id="sbOnboardCard">' + renderPaths() + '</div>';
    document.body.appendChild(overlay);
    bindPathEvents();
    requestAnimationFrame(function() {
      requestAnimationFrame(function() { overlay.classList.add('is-visible'); });
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
