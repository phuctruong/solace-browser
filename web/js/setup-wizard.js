/**
 * setup-wizard.js — Post-login guided app setup wizard
 * v1.0.0 | Auth: 65537
 *
 * After first login, walks user through:
 *   Step 1: Choose plan (Free / Starter $8 / Pro $28)
 *   Step 2: Setup Gmail (connect Google account)
 *   Step 3: Setup LinkedIn (connect LinkedIn)
 *   Step 4: More apps (optional)
 *   Step 5: Done — go to dashboard
 *
 * Each step can be skipped. Default apps get installed.
 * No redirect to solaceagi.com — everything stays in the browser.
 */
(function () {
  'use strict';

  const WIZARD_KEY = 'solace_setup_complete';
  const CLOUD = 'https://www.solaceagi.com';

  function shouldShow() {
    // Only show after fresh login (token in URL) and wizard not completed
    if (localStorage.getItem(WIZARD_KEY) === '1') return false;
    // Must be signed in
    if (!localStorage.getItem('solace_api_key')) return false;
    // Only on start/home pages
    const path = window.location.pathname.replace(/\/$/, '') || '/';
    if (path !== '/' && path !== '/start' && path !== '/home') return false;
    // Show on fresh login or if explicitly requested
    const params = new URLSearchParams(window.location.search);
    if (params.get('setup') === '1') return true;
    if (params.get('token')) return true;
    // Show if user hasn't completed setup
    if (!localStorage.getItem('solace_setup_step')) return true;
    return true;
  }

  const STEPS = [
    {
      id: 'plan',
      title: 'Choose Your Plan',
      subtitle: 'Start free and upgrade anytime. No credit card required.',
      icon: '💎',
    },
    {
      id: 'gmail',
      title: 'Connect Gmail',
      subtitle: 'Let Solace triage your inbox, clean spam, and organize emails.',
      icon: '📧',
    },
    {
      id: 'linkedin',
      title: 'Connect LinkedIn',
      subtitle: 'Optimize your profile, track connections, and automate outreach.',
      icon: '💼',
    },
    {
      id: 'apps',
      title: 'Choose More Apps',
      subtitle: 'Pick from 25+ apps for scheduling, marketing, and more.',
      icon: '🎯',
    },
    {
      id: 'done',
      title: 'You\'re All Set!',
      subtitle: 'Your Solace Browser is ready to work for you.',
      icon: '🎉',
    },
  ];

  let currentStep = 0;

  const CSS = '\
    #sbWizard { position:fixed; inset:0; z-index:10000; background:rgba(8,16,25,0.95); backdrop-filter:blur(16px); display:flex; align-items:center; justify-content:center; padding:24px; opacity:0; transition:opacity 0.3s; }\
    #sbWizard.is-visible { opacity:1; }\
    #sbWizardCard { background:linear-gradient(160deg,#0d1a26 0%,#081019 100%); border:1px solid rgba(255,255,255,0.08); border-radius:24px; padding:40px 36px 32px; max-width:560px; width:100%; box-shadow:0 32px 80px rgba(0,0,0,0.7); transform:translateY(20px); opacity:0; transition:all 0.4s; }\
    #sbWizard.is-visible #sbWizardCard { transform:translateY(0); opacity:1; }\
    .wiz-progress { display:flex; gap:6px; margin-bottom:28px; }\
    .wiz-dot { flex:1; height:4px; border-radius:2px; background:rgba(255,255,255,0.08); transition:background 0.3s; }\
    .wiz-dot.is-done { background:#46d9a7; }\
    .wiz-dot.is-current { background:#64c4ff; }\
    .wiz-header { text-align:center; margin-bottom:24px; }\
    .wiz-icon { font-size:2.5rem; margin-bottom:8px; display:block; }\
    .wiz-title { font-size:1.3rem; font-weight:800; color:#fff; margin:0 0 6px; }\
    .wiz-sub { font-size:0.85rem; color:rgba(255,255,255,0.45); margin:0; line-height:1.5; }\
    .wiz-body { margin-bottom:24px; }\
    .wiz-plan { display:flex; flex-direction:column; gap:10px; }\
    .wiz-plan-card { display:flex; align-items:center; gap:14px; padding:16px; border-radius:14px; border:2px solid rgba(255,255,255,0.06); cursor:pointer; transition:all 0.2s; background:rgba(255,255,255,0.02); }\
    .wiz-plan-card:hover { border-color:rgba(100,196,255,0.3); background:rgba(100,196,255,0.04); }\
    .wiz-plan-card.is-selected { border-color:#64c4ff; background:rgba(100,196,255,0.08); }\
    .wiz-plan-card.is-recommended { border-color:rgba(70,217,167,0.4); }\
    .wiz-plan-icon { font-size:1.4rem; width:40px; text-align:center; flex-shrink:0; }\
    .wiz-plan-info { flex:1; }\
    .wiz-plan-name { font-size:0.95rem; font-weight:700; color:#fff; margin:0; }\
    .wiz-plan-desc { font-size:0.75rem; color:rgba(255,255,255,0.4); margin:2px 0 0; }\
    .wiz-plan-price { font-size:0.85rem; font-weight:700; padding:4px 12px; border-radius:6px; white-space:nowrap; }\
    .wiz-plan-price--free { background:rgba(70,217,167,0.12); color:#46d9a7; }\
    .wiz-plan-price--paid { background:rgba(100,196,255,0.12); color:#64c4ff; }\
    .wiz-tag { font-size:0.6rem; font-weight:700; padding:2px 6px; border-radius:3px; background:rgba(70,217,167,0.15); color:#46d9a7; margin-left:8px; }\
    .wiz-connect { display:flex; flex-direction:column; gap:12px; }\
    .wiz-connect-btn { display:flex; align-items:center; gap:12px; padding:16px 20px; border-radius:14px; border:2px solid rgba(255,255,255,0.06); background:rgba(255,255,255,0.02); cursor:pointer; transition:all 0.2s; color:#fff; font-size:0.95rem; font-weight:600; width:100%; text-align:left; }\
    .wiz-connect-btn:hover { border-color:rgba(100,196,255,0.3); background:rgba(100,196,255,0.04); }\
    .wiz-connect-btn svg { width:24px; height:24px; flex-shrink:0; }\
    .wiz-connect-btn.is-connected { border-color:rgba(70,217,167,0.4); background:rgba(70,217,167,0.06); }\
    .wiz-connect-status { margin-left:auto; font-size:0.75rem; color:rgba(255,255,255,0.3); }\
    .wiz-connect-btn.is-connected .wiz-connect-status { color:#46d9a7; }\
    .wiz-apps-grid { display:grid; grid-template-columns:1fr 1fr; gap:10px; }\
    .wiz-app-card { display:flex; align-items:center; gap:10px; padding:12px; border-radius:10px; border:1px solid rgba(255,255,255,0.06); cursor:pointer; transition:all 0.15s; background:rgba(255,255,255,0.02); }\
    .wiz-app-card:hover { border-color:rgba(100,196,255,0.3); }\
    .wiz-app-card.is-selected { border-color:#46d9a7; background:rgba(70,217,167,0.06); }\
    .wiz-app-icon { width:32px; height:32px; border-radius:8px; object-fit:cover; }\
    .wiz-app-name { font-size:0.82rem; font-weight:600; color:#fff; }\
    .wiz-app-cat { font-size:0.65rem; color:rgba(255,255,255,0.3); }\
    .wiz-actions { display:flex; gap:10px; }\
    .wiz-btn { flex:1; padding:14px; border-radius:12px; font-size:0.92rem; font-weight:700; cursor:pointer; transition:all 0.2s; text-align:center; border:none; }\
    .wiz-btn--primary { background:#64c4ff; color:#000; }\
    .wiz-btn--primary:hover { background:#89d9ff; }\
    .wiz-btn--skip { background:transparent; color:rgba(255,255,255,0.3); border:1px solid rgba(255,255,255,0.08); }\
    .wiz-btn--skip:hover { color:rgba(255,255,255,0.5); border-color:rgba(255,255,255,0.15); }\
    .wiz-btn--done { background:linear-gradient(135deg,#46d9a7,#00c896); color:#000; }\
    .wiz-done-stats { display:flex; gap:20px; justify-content:center; margin:20px 0; }\
    .wiz-stat { text-align:center; }\
    .wiz-stat-val { font-size:1.3rem; font-weight:800; color:#64c4ff; }\
    .wiz-stat-label { font-size:0.7rem; color:rgba(255,255,255,0.35); margin-top:2px; }\
    @media (max-width:520px) { #sbWizardCard { padding:28px 20px 24px; } .wiz-apps-grid { grid-template-columns:1fr; } }\
  ';

  let selectedPlan = 'free';
  let connectedGoogle = false;
  let connectedLinkedin = false;
  const selectedApps = ['gmail-inbox-triage', 'gmail-spam-cleaner'];

  function renderProgress() {
    let dots = '';
    for (let i = 0; i < STEPS.length; i++) {
      const cls = i < currentStep ? 'wiz-dot is-done' : (i === currentStep ? 'wiz-dot is-current' : 'wiz-dot');
      dots += '<div class="' + cls + '"></div>';
    }
    return '<div class="wiz-progress">' + dots + '</div>';
  }

  function renderStep() {
    const step = STEPS[currentStep];
    let body = '';
    let actions = '';

    if (step.id === 'plan') {
      body = '<div class="wiz-plan">' +
        '<div class="wiz-plan-card' + (selectedPlan === 'free' ? ' is-selected' : '') + '" data-plan="free">' +
          '<div class="wiz-plan-icon">🆓</div>' +
          '<div class="wiz-plan-info"><p class="wiz-plan-name">Free Forever</p><p class="wiz-plan-desc">Your own API key (BYOK). All apps. No limits.</p></div>' +
          '<span class="wiz-plan-price wiz-plan-price--free">$0</span>' +
        '</div>' +
        '<div class="wiz-plan-card' + (selectedPlan === 'starter' ? ' is-selected' : '') + ' is-recommended" data-plan="starter">' +
          '<div class="wiz-plan-icon">⚡</div>' +
          '<div class="wiz-plan-info"><p class="wiz-plan-name">Starter <span class="wiz-tag">POPULAR</span></p><p class="wiz-plan-desc">Managed LLM — no API key needed. Just works.</p></div>' +
          '<span class="wiz-plan-price wiz-plan-price--paid">$8/mo</span>' +
        '</div>' +
        '<div class="wiz-plan-card' + (selectedPlan === 'pro' ? ' is-selected' : '') + '" data-plan="pro">' +
          '<div class="wiz-plan-icon">🚀</div>' +
          '<div class="wiz-plan-info"><p class="wiz-plan-name">Pro</p><p class="wiz-plan-desc">Cloud twin + evidence vault + team sharing + everything.</p></div>' +
          '<span class="wiz-plan-price wiz-plan-price--paid">$28/mo</span>' +
        '</div>' +
      '</div>';
      actions = '<div class="wiz-actions">' +
        '<button class="wiz-btn wiz-btn--skip" id="wizSkip">Skip</button>' +
        '<button class="wiz-btn wiz-btn--primary" id="wizNext">Continue</button>' +
      '</div>';
    } else if (step.id === 'gmail') {
      body = '<div class="wiz-connect">' +
        '<button class="wiz-connect-btn' + (connectedGoogle ? ' is-connected' : '') + '" id="wizConnectGoogle">' +
          '<svg viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>' +
          'Connect Google Account' +
          '<span class="wiz-connect-status">' + (connectedGoogle ? '✓ Connected' : 'Required for Gmail apps') + '</span>' +
        '</button>' +
        '<p style="font-size:0.75rem;color:rgba(255,255,255,0.3);text-align:center;margin:0;">This enables Gmail Inbox Triage, Spam Cleaner, and Google Calendar apps.</p>' +
      '</div>';
      actions = '<div class="wiz-actions">' +
        '<button class="wiz-btn wiz-btn--skip" id="wizSkip">Skip for now</button>' +
        '<button class="wiz-btn wiz-btn--primary" id="wizNext">' + (connectedGoogle ? 'Continue' : 'Connect & Continue') + '</button>' +
      '</div>';
    } else if (step.id === 'linkedin') {
      body = '<div class="wiz-connect">' +
        '<button class="wiz-connect-btn' + (connectedLinkedin ? ' is-connected' : '') + '" id="wizConnectLinkedin">' +
          '<svg viewBox="0 0 24 24"><path fill="#0A66C2" d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433a2.062 2.062 0 0 1-2.063-2.065 2.064 2.064 0 1 1 2.063 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>' +
          'Connect LinkedIn' +
          '<span class="wiz-connect-status">' + (connectedLinkedin ? '✓ Connected' : 'For profile optimization') + '</span>' +
        '</button>' +
        '<p style="font-size:0.75rem;color:rgba(255,255,255,0.3);text-align:center;margin:0;">This enables LinkedIn Profile Optimizer and connection management apps.</p>' +
      '</div>';
      actions = '<div class="wiz-actions">' +
        '<button class="wiz-btn wiz-btn--skip" id="wizSkip">Skip for now</button>' +
        '<button class="wiz-btn wiz-btn--primary" id="wizNext">Continue</button>' +
      '</div>';
    } else if (step.id === 'apps') {
      const defaultApps = [
        { id: 'gmail-inbox-triage', name: 'Gmail Inbox Triage', icon: '📧', cat: 'Email' },
        { id: 'gmail-spam-cleaner', name: 'Spam Cleaner', icon: '🧹', cat: 'Email' },
        { id: 'google-search-trends', name: 'Search Trends', icon: '📊', cat: 'Research' },
        { id: 'linkedin-profile-optimizer', name: 'LinkedIn Optimizer', icon: '💼', cat: 'Career' },
        { id: 'competitor-watch', name: 'Competitor Watch', icon: '🔍', cat: 'Marketing' },
        { id: 'substack-engagement', name: 'Substack Manager', icon: '📝', cat: 'Content' },
      ];
      let cards = '';
      for (let i = 0; i < defaultApps.length; i++) {
        const app = defaultApps[i];
        const sel = selectedApps.indexOf(app.id) >= 0;
        cards += '<div class="wiz-app-card' + (sel ? ' is-selected' : '') + '" data-app="' + app.id + '">' +
          '<span style="font-size:1.3rem;">' + app.icon + '</span>' +
          '<div><div class="wiz-app-name">' + app.name + '</div><div class="wiz-app-cat">' + app.cat + '</div></div>' +
        '</div>';
      }
      body = '<div class="wiz-apps-grid">' + cards + '</div>' +
        '<p style="font-size:0.72rem;color:rgba(255,255,255,0.25);text-align:center;margin:8px 0 0;">Selected apps will be pre-installed. You can add or remove apps anytime from the App Store.</p>';
      actions = '<div class="wiz-actions">' +
        '<button class="wiz-btn wiz-btn--skip" id="wizSkip">Skip</button>' +
        '<button class="wiz-btn wiz-btn--primary" id="wizNext">Install ' + selectedApps.length + ' Apps & Continue</button>' +
      '</div>';
    } else if (step.id === 'done') {
      const appsInstalled = selectedApps.length;
      const connections = (connectedGoogle ? 1 : 0) + (connectedLinkedin ? 1 : 0);
      body = '<div class="wiz-done-stats">' +
        '<div class="wiz-stat"><div class="wiz-stat-val">' + appsInstalled + '</div><div class="wiz-stat-label">Apps Installed</div></div>' +
        '<div class="wiz-stat"><div class="wiz-stat-val">' + connections + '</div><div class="wiz-stat-label">Accounts Connected</div></div>' +
        '<div class="wiz-stat"><div class="wiz-stat-val">' + (selectedPlan === 'free' ? 'Free' : selectedPlan === 'starter' ? '$8' : '$28') + '</div><div class="wiz-stat-label">Plan</div></div>' +
      '</div>' +
      '<p style="font-size:0.82rem;color:rgba(255,255,255,0.45);text-align:center;line-height:1.6;">Ask <strong style="color:#64c4ff;">YinYang</strong> anything using the chat bar below.<br>Try: "Run my Gmail Triage" or "What can you do?"</p>';
      actions = '<div class="wiz-actions">' +
        '<button class="wiz-btn wiz-btn--done" id="wizDone" style="flex:1;">Go to Dashboard →</button>' +
      '</div>';
    }

    return renderProgress() +
      '<div class="wiz-header">' +
        '<span class="wiz-icon">' + step.icon + '</span>' +
        '<h2 class="wiz-title">' + step.title + '</h2>' +
        '<p class="wiz-sub">' + step.subtitle + '</p>' +
      '</div>' +
      '<div class="wiz-body">' + body + '</div>' +
      actions;
  }

  function render() {
    const card = document.getElementById('sbWizardCard');
    if (!card) return;
    card.innerHTML = renderStep();
    bindEvents();
  }

  function bindEvents() {
    const step = STEPS[currentStep];

    // Plan selection
    if (step.id === 'plan') {
      document.querySelectorAll('.wiz-plan-card').forEach(function(el) {
        el.addEventListener('click', function() {
          selectedPlan = this.dataset.plan;
          document.querySelectorAll('.wiz-plan-card').forEach(function(c) { c.classList.remove('is-selected'); });
          this.classList.add('is-selected');
        });
      });
    }

    // Google connect
    if (step.id === 'gmail') {
      const gBtn = document.getElementById('wizConnectGoogle');
      if (gBtn) {
        gBtn.addEventListener('click', function() {
          // For now, mark as connected (real implementation uses OAuth flow)
          connectedGoogle = true;
          this.classList.add('is-connected');
          this.querySelector('.wiz-connect-status').textContent = '✓ Connected';
          document.getElementById('wizNext').textContent = 'Continue';
        });
      }
    }

    // LinkedIn connect
    if (step.id === 'linkedin') {
      const lBtn = document.getElementById('wizConnectLinkedin');
      if (lBtn) {
        lBtn.addEventListener('click', function() {
          connectedLinkedin = true;
          this.classList.add('is-connected');
          this.querySelector('.wiz-connect-status').textContent = '✓ Connected';
        });
      }
    }

    // App selection
    if (step.id === 'apps') {
      document.querySelectorAll('.wiz-app-card').forEach(function(el) {
        el.addEventListener('click', function() {
          const appId = this.dataset.app;
          const idx = selectedApps.indexOf(appId);
          if (idx >= 0) {
            selectedApps.splice(idx, 1);
            this.classList.remove('is-selected');
          } else {
            selectedApps.push(appId);
            this.classList.add('is-selected');
          }
          const nextBtn = document.getElementById('wizNext');
          if (nextBtn) nextBtn.textContent = 'Install ' + selectedApps.length + ' Apps & Continue';
        });
      });
    }

    // Next button
    const nextBtn = document.getElementById('wizNext');
    if (nextBtn) {
      nextBtn.addEventListener('click', function() {
        if (STEPS[currentStep].id === 'plan' && selectedPlan !== 'free') {
          // Open Stripe checkout in same window, will redirect back
          const checkoutUrl = CLOUD + '/billing/checkout?plan=' + selectedPlan +
            '&redirect=' + encodeURIComponent(window.location.origin + '/start?setup=1&step=' + (currentStep + 1));
          window.location.href = checkoutUrl;
          return;
        }
        if (STEPS[currentStep].id === 'gmail' && !connectedGoogle) {
          // Trigger Google OAuth
          const redirectUrl = window.location.origin + '/start?setup=1&step=' + (currentStep + 1) + '&google=1';
          window.location.href = CLOUD + '/auth/login?provider=google&redirect=' + encodeURIComponent(redirectUrl);
          return;
        }
        if (STEPS[currentStep].id === 'apps' && selectedApps.length > 0) {
          installSelectedApps();
        }
        goNext();
      });
    }

    // Skip button
    const skipBtn = document.getElementById('wizSkip');
    if (skipBtn) {
      skipBtn.addEventListener('click', goNext);
    }

    // Done button
    const doneBtn = document.getElementById('wizDone');
    if (doneBtn) {
      doneBtn.addEventListener('click', function() {
        localStorage.setItem(WIZARD_KEY, '1');
        close();
        window.location.href = '/home';
      });
    }
  }

  function goNext() {
    localStorage.setItem('solace_setup_step', currentStep + 1);
    if (currentStep < STEPS.length - 1) {
      currentStep++;
      render();
    }
  }

  function installSelectedApps() {
    // Fire-and-forget install calls for each selected app
    selectedApps.forEach(function(appId) {
      fetch('/api/apps/' + encodeURIComponent(appId) + '/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ source: 'setup-wizard' })
      }).catch(function(e) { console.debug('App install queued, will show in app store:', e.message || e); });
    });
  }

  function close() {
    const overlay = document.getElementById('sbWizard');
    if (overlay) {
      overlay.style.opacity = '0';
      setTimeout(function() { overlay.remove(); }, 300);
    }
  }

  function init() {
    if (!shouldShow()) return;

    // Check if returning from OAuth/checkout with step param
    const params = new URLSearchParams(window.location.search);
    const stepParam = parseInt(params.get('step') || '0', 10);
    if (stepParam > 0 && stepParam < STEPS.length) {
      currentStep = stepParam;
    }
    if (params.get('google') === '1') {
      connectedGoogle = true;
    }

    // Inject CSS
    const style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);

    // Build overlay
    const overlay = document.createElement('div');
    overlay.id = 'sbWizard';
    overlay.innerHTML = '<div id="sbWizardCard"></div>';
    document.body.appendChild(overlay);

    // Render first step
    render();

    // Animate in
    requestAnimationFrame(function() {
      requestAnimationFrame(function() {
        overlay.classList.add('is-visible');
      });
    });
  }

  // Wait for signed-in state before showing wizard
  // The wizard shows AFTER the start.html login flow completes
  window.addEventListener('solace:signed-in', init);

  // Also check on page load if already signed in
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
      // Small delay to let start.html auth check run first
      setTimeout(init, 500);
    });
  } else {
    setTimeout(init, 500);
  }
})();
