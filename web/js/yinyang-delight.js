'use strict';

const DELIGHT_MILESTONES = Object.freeze({
  first_run_complete: { emoji: '🎉', message: 'First automation complete!', effect: 'confetti' },
  task_complete: { emoji: '✅', message: 'Task done!', effect: 'toast' },
  milestone_100_runs: { emoji: '🏆', message: '100 automations!', effect: 'confetti' },
  streak_7_days: { emoji: '🔥', message: '7-day streak!', effect: 'confetti' },
  budget_saved: { emoji: '💰', message: 'Budget under limit!', effect: 'toast' },
  celebration: { emoji: '🎊', message: 'Celebrating!', effect: 'confetti' },
  milestone: { emoji: '🏆', message: 'Milestone reached!', effect: 'confetti' }
});

const DELIGHT_SETTINGS = Object.freeze({
  pieceCount: 80,
  maxFrames: 200,
  toastLifetimeMs: 3500,
  driftAmount: 0.8,
  gravity: 0.045,
  spinRange: 0.18
});

let _activeToast = null;
let _activeToastTimer = 0;
let _activeCanvas = null;
let _activeFrame = 0;
let _resizeHandler = null;

function _mountRoot() {
  return document.body || document.documentElement;
}

function _readThemeToken(name, fallback) {
  const value = window.getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return value || fallback;
}

function _confettiPalette() {
  const palette = [
    _readThemeToken('--delight-confetti-a', ''),
    _readThemeToken('--delight-confetti-b', ''),
    _readThemeToken('--delight-confetti-c', ''),
    _readThemeToken('--delight-confetti-d', ''),
    _readThemeToken('--delight-confetti-e', '')
  ].filter(Boolean);

  if (palette.length > 0) {
    return palette;
  }

  return ['white', 'silver', 'gray'];
}

function _removeConfettiCanvas() {
  if (_activeFrame) {
    window.cancelAnimationFrame(_activeFrame);
    _activeFrame = 0;
  }
  if (_resizeHandler) {
    window.removeEventListener('resize', _resizeHandler);
    _resizeHandler = null;
  }
  if (_activeCanvas && _activeCanvas.parentNode) {
    _activeCanvas.parentNode.removeChild(_activeCanvas);
  }
  _activeCanvas = null;
}

function _launchConfetti() {
  _removeConfettiCanvas();

  const mount = _mountRoot();
  if (!mount) {
    return;
  }

  const canvas = document.createElement('canvas');
  canvas.className = 'delight-confetti-canvas';
  mount.appendChild(canvas);

  const ctx = canvas.getContext('2d');
  if (!ctx) {
    canvas.remove();
    return;
  }

  const palette = _confettiPalette();
  const pieces = [];

  function sizeCanvas() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }

  sizeCanvas();
  _resizeHandler = sizeCanvas;
  window.addEventListener('resize', _resizeHandler);

  for (let index = 0; index < DELIGHT_SETTINGS.pieceCount; index += 1) {
    pieces.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height - canvas.height,
      width: Math.random() * 10 + 5,
      height: Math.random() * 5 + 3,
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: (Math.random() - 0.5) * DELIGHT_SETTINGS.spinRange,
      velocityX: (Math.random() - 0.5) * DELIGHT_SETTINGS.driftAmount,
      velocityY: Math.random() * 3 + 2,
      gravity: Math.random() * DELIGHT_SETTINGS.gravity,
      color: palette[Math.floor(Math.random() * palette.length)]
    });
  }

  _activeCanvas = canvas;
  let frame = 0;

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    let active = false;

    for (let index = 0; index < pieces.length; index += 1) {
      const piece = pieces[index];
      piece.x += piece.velocityX + Math.sin((frame + index) / 14) * 0.25;
      piece.y += piece.velocityY;
      piece.velocityY += piece.gravity;
      piece.rotation += piece.rotationSpeed;

      if (piece.y < canvas.height + 24) {
        active = true;
      }

      ctx.save();
      ctx.translate(piece.x, piece.y);
      ctx.rotate(piece.rotation);
      ctx.fillStyle = piece.color;
      ctx.fillRect(-piece.width / 2, -piece.height / 2, piece.width, piece.height);
      ctx.restore();
    }

    frame += 1;
    if (active && frame < DELIGHT_SETTINGS.maxFrames) {
      _activeFrame = window.requestAnimationFrame(animate);
      return;
    }

    _removeConfettiCanvas();
  }

  _activeFrame = window.requestAnimationFrame(animate);
}

function _removeToast() {
  if (_activeToastTimer) {
    window.clearTimeout(_activeToastTimer);
    _activeToastTimer = 0;
  }
  if (_activeToast && _activeToast.parentNode) {
    _activeToast.parentNode.removeChild(_activeToast);
  }
  _activeToast = null;
}

function _showDelightToast(emoji, message) {
  const mount = _mountRoot();
  if (!mount) {
    return;
  }

  _removeToast();

  const toast = document.createElement('div');
  toast.className = 'delight-toast';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');

  const emojiEl = document.createElement('span');
  emojiEl.className = 'delight-toast__emoji';
  emojiEl.textContent = emoji;

  const messageEl = document.createElement('span');
  messageEl.className = 'delight-toast__msg';
  messageEl.textContent = message;

  toast.appendChild(emojiEl);
  toast.appendChild(messageEl);
  mount.appendChild(toast);

  _activeToast = toast;
  _activeToastTimer = window.setTimeout(_removeToast, DELIGHT_SETTINGS.toastLifetimeMs);
}

function triggerDelight(milestone, metadata) {
  const details = metadata || {};
  const config = DELIGHT_MILESTONES[milestone] || DELIGHT_MILESTONES.celebration;
  const message = typeof details.message === 'string' && details.message.trim() ? details.message : config.message;

  if (config.effect === 'confetti' || config.effect === 'rain') {
    _launchConfetti();
  }

  _showDelightToast(config.emoji, message);
}

function handleNotificationDelight(notif) {
  if (!notif || (notif.type !== 'celebration' && notif.type !== 'milestone')) {
    return;
  }

  const milestone = notif.metadata && notif.metadata.milestone_type
    ? notif.metadata.milestone_type
    : notif.type;

  triggerDelight(milestone, { message: notif.message });
}

window.SolaceDelight = {
  triggerDelight,
  handleNotificationDelight
};
