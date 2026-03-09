'use strict';

const TUTORIAL_KEY = 'sb_tutorial_v1';

const STEPS = [
  { icon: '☯', title: 'Welcome to Solace Browser', body: "I'm YinYang — your AI browser companion. I help you automate repetitive tasks, protect your privacy, and stay in control of every action I take." },
  { icon: '📱', title: 'Your App Library', body: "Solace comes with 22 apps: Gmail, LinkedIn, GitHub, Slack, and more. Each app knows exactly how to help you on that site." },
  { icon: '💰', title: 'Recipes Save You Money', body: "The first time YinYang does a task, it costs ~$0.05. Every repeat costs $0.001. Your library grows. Your costs fall toward zero." },
  { icon: '🔗', title: 'Evidence, Not Trust', body: "Every action is hash-chained to a tamper-evident log. You can always see exactly what happened and why. Trust, but verify." },
  { icon: '🛡️', title: "You're Always in Control", body: "I never act without your approval. You can pause me, reject any action, or revoke access anytime. You are always the authority." },
];

let _currentStep = 0;

function _shouldShow() {
  if (new URLSearchParams(window.location.search).get('tutorial') === 'skip') return false;
  const stored = localStorage.getItem(TUTORIAL_KEY);
  if (!stored) return true;
  try {
    const parsed = JSON.parse(stored);
    return parsed.status !== 'done' && parsed.status !== 'skipped';
  } catch (_) {
    return stored !== 'done' && stored !== 'skipped';
  }
}

function _render(step) {
  const data = STEPS[step];
  document.getElementById('step-counter').textContent = `Step ${step + 1} of ${STEPS.length}`;
  document.getElementById('tutorial-body').innerHTML = `
    <span class="tutorial-icon" aria-hidden="true">${data.icon}</span>
    <h2>${data.title}</h2>
    <p>${data.body}</p>`;

  const dotsEl = document.getElementById('tutorial-dots');
  dotsEl.innerHTML = STEPS.map((_, i) =>
    `<span class="tutorial-dot ${i === step ? 'active' : ''}" aria-label="Step ${i+1}"></span>`
  ).join('');

  document.getElementById('tutorial-back').hidden = step === 0;
  const nextBtn = document.getElementById('tutorial-next');
  nextBtn.textContent = step === STEPS.length - 1 ? "Get started! 🚀" : "Next →";
}

function _skip() {
  localStorage.setItem(TUTORIAL_KEY, 'skipped');
  document.getElementById('tutorial-overlay').hidden = true;
}

function _complete() {
  localStorage.setItem(TUTORIAL_KEY, JSON.stringify({
    status: 'done',
    completed_at: new Date().toISOString(),
    locale: navigator.language,
    version: 1
  }));
  document.getElementById('tutorial-overlay').hidden = true;
}

function initTutorial() {
  if (!_shouldShow()) return;
  const overlay = document.getElementById('tutorial-overlay');
  if (!overlay) return;
  overlay.hidden = false;
  _render(0);

  document.getElementById('tutorial-skip').addEventListener('click', _skip);
  document.getElementById('tutorial-next').addEventListener('click', () => {
    if (_currentStep === STEPS.length - 1) { _complete(); return; }
    _currentStep++;
    _render(_currentStep);
  });
  document.getElementById('tutorial-back').addEventListener('click', () => {
    if (_currentStep > 0) { _currentStep--; _render(_currentStep); }
  });

  overlay.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') _skip();
    else if (e.key === 'ArrowRight' || e.key === 'Enter') document.getElementById('tutorial-next').click();
    else if (e.key === 'ArrowLeft') document.getElementById('tutorial-back').click();
  });

  overlay.focus();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initTutorial);
} else {
  initTutorial();
}
