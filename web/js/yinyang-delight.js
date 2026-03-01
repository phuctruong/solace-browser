/**
 * Yinyang Delight Engine — Solace Browser
 * v1.0.0 | Auth: 65537
 *
 * Core delight library for celebrations, warm tokens, holidays, easter eggs.
 * Loads CDN dependencies on first use (lazy). Plugin architecture for extensions.
 *
 * Dependencies (loaded via CDN on demand):
 *   canvas-confetti  4.2KB  — confetti()
 *   js-confetti      2.4KB  — emoji rain
 *   notyf            3.0KB  — toast notifications
 *
 * Usage:
 *   YinyangDelight.init();
 *   YinyangDelight.celebrate('first_run_complete');
 *   YinyangDelight.respond({ mode: 'celebrate', trigger: 'milestone' });
 *   YinyangDelight.joke();
 *   YinyangDelight.fact();
 */

/* global confetti, JSConfetti, Notyf */

const YinyangDelight = (() => {
  'use strict';

  // ---------------------------------------------------------------------------
  // State
  // ---------------------------------------------------------------------------
  let _initialized = false;
  let _notyf = null;
  let _jsConfetti = null;
  let _seenJokes = new Set();
  let _seenFacts = new Set();
  let _seenSmallTalk = new Set();
  let _plugins = [];
  let _databases = { jokes: null, facts: null, smalltalk: null, holidays: null, celebrations: null };

  // ---------------------------------------------------------------------------
  // CDN Loader (lazy, once)
  // ---------------------------------------------------------------------------
  const _cdnLoaded = {};

  function _loadCDN(url) {
    if (_cdnLoaded[url]) return _cdnLoaded[url];
    _cdnLoaded[url] = new Promise((resolve, reject) => {
      if (url.endsWith('.css')) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = url;
        link.onload = resolve;
        link.onerror = reject;
        document.head.appendChild(link);
      } else {
        const script = document.createElement('script');
        script.src = url;
        script.onload = resolve;
        script.onerror = reject;
        document.head.appendChild(script);
      }
    });
    return _cdnLoaded[url];
  }

  async function _ensureConfetti() {
    if (typeof confetti === 'undefined') {
      await _loadCDN('https://cdn.jsdelivr.net/npm/canvas-confetti@1.9.3/dist/confetti.browser.min.js');
    }
  }

  async function _ensureEmojiConfetti() {
    if (typeof JSConfetti === 'undefined') {
      await _loadCDN('https://cdn.jsdelivr.net/npm/js-confetti@latest/dist/js-confetti.browser.js');
    }
    if (!_jsConfetti) _jsConfetti = new JSConfetti();
  }

  async function _ensureToast() {
    if (typeof Notyf === 'undefined') {
      await _loadCDN('https://cdn.jsdelivr.net/npm/notyf@3/notyf.min.css');
      await _loadCDN('https://cdn.jsdelivr.net/npm/notyf@3/notyf.min.js');
    }
    if (!_notyf) _notyf = new Notyf({ duration: 4000, position: { x: 'right', y: 'top' }, ripple: true });
  }

  // ---------------------------------------------------------------------------
  // Sound (Web Audio API — zero dependencies)
  // ---------------------------------------------------------------------------
  function _playSound(type) {
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain);
      gain.connect(ctx.destination);
      gain.gain.value = 0.15;

      if (type === 'fanfare') {
        osc.frequency.value = 523; // C5
        osc.start();
        osc.frequency.setValueAtTime(659, ctx.currentTime + 0.15); // E5
        osc.frequency.setValueAtTime(784, ctx.currentTime + 0.30); // G5
        osc.frequency.setValueAtTime(1047, ctx.currentTime + 0.45); // C6
        osc.stop(ctx.currentTime + 0.6);
      } else if (type === 'ding') {
        osc.frequency.value = 880; // A5
        osc.start();
        gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.3);
        osc.stop(ctx.currentTime + 0.3);
      } else if (type === 'birthday') {
        // Happy birthday melody snippet (C-C-D-C-F-E)
        const notes = [262, 262, 294, 262, 349, 330];
        const dur = 0.2;
        osc.start();
        notes.forEach((freq, i) => {
          osc.frequency.setValueAtTime(freq, ctx.currentTime + i * dur);
        });
        osc.stop(ctx.currentTime + notes.length * dur);
      }
    } catch (_) {
      // Audio not available — silent degradation is acceptable for delight
    }
  }

  // ---------------------------------------------------------------------------
  // Effects
  // ---------------------------------------------------------------------------
  async function _fireConfetti(config) {
    await _ensureConfetti();
    confetti(config || { particleCount: 100, spread: 70 });
  }

  async function _fireEmojiRain(emojis) {
    await _ensureEmojiConfetti();
    _jsConfetti.addConfetti({ emojis: emojis || ['🎉', '🎊', '🥳', '✨'] });
  }

  async function _fireSparkles() {
    await _ensureConfetti();
    const end = Date.now() + 800;
    (function frame() {
      confetti({ particleCount: 3, angle: 60, spread: 55, origin: { x: 0, y: 0.7 }, colors: ['#ffbf69', '#ffd700', '#ff6b6b'] });
      confetti({ particleCount: 3, angle: 120, spread: 55, origin: { x: 1, y: 0.7 }, colors: ['#ffbf69', '#ffd700', '#ff6b6b'] });
      if (Date.now() < end) requestAnimationFrame(frame);
    })();
  }

  async function _fireFireworks() {
    await _ensureConfetti();
    const end = Date.now() + 2000;
    (function frame() {
      confetti({ particleCount: 30, startVelocity: 40, spread: 360,
        origin: { x: Math.random(), y: Math.random() * 0.4 },
        colors: ['#ff0000', '#ffbf69', '#00ff00', '#0000ff', '#ff69b4'] });
      if (Date.now() < end) requestAnimationFrame(frame);
    })();
  }

  async function _toast(message, type) {
    await _ensureToast();
    if (type === 'success') _notyf.success(message);
    else if (type === 'error') _notyf.error(message);
    else _notyf.open({ type: 'info', message: message, background: '#7c3aed' });
  }

  // ---------------------------------------------------------------------------
  // Database Loaders
  // ---------------------------------------------------------------------------
  async function _loadDB(name) {
    if (_databases[name]) return _databases[name];
    try {
      const resp = await fetch(`/data/default/yinyang/${name}.json`);
      if (resp.ok) _databases[name] = await resp.json();
    } catch (_) {
      // Database not available
    }
    return _databases[name];
  }

  function _pickUnseen(items, seenSet, idField) {
    idField = idField || 'id';
    const unseen = items.filter(item => !seenSet.has(item[idField]));
    if (unseen.length === 0) {
      seenSet.clear(); // Reset if all seen
      return items[Math.floor(Math.random() * items.length)];
    }
    const pick = unseen[Math.floor(Math.random() * unseen.length)];
    seenSet.add(pick[idField]);
    return pick;
  }

  // ---------------------------------------------------------------------------
  // Holiday Detection
  // ---------------------------------------------------------------------------
  function _detectHoliday() {
    const now = new Date();
    const mmdd = String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
    const db = _databases.holidays;
    if (!db || !db.holidays) return null;
    return db.holidays.find(h => {
      if (h.start > h.end) {
        // Year-wrap (e.g., Dec 31 → Jan 2)
        return mmdd >= h.start || mmdd <= h.end;
      }
      return mmdd >= h.start && mmdd <= h.end;
    }) || null;
  }

  // ---------------------------------------------------------------------------
  // Konami Code Easter Egg
  // ---------------------------------------------------------------------------
  function _initKonami() {
    const konami = [38, 38, 40, 40, 37, 39, 37, 39, 66, 65];
    let pos = 0;
    document.addEventListener('keydown', (e) => {
      pos = e.keyCode === konami[pos] ? pos + 1 : 0;
      if (pos === konami.length) {
        _fireEmojiRain(['🏆', '👑', '⭐', '🎮']);
        _toast('You found the easter egg!', 'success');
        _playSound('fanfare');
        pos = 0;
      }
    });
  }

  // ---------------------------------------------------------------------------
  // Public API
  // ---------------------------------------------------------------------------
  return {
    /**
     * Initialize the delight engine. Call once on page load.
     */
    async init() {
      if (_initialized) return;
      _initialized = true;

      // Preload databases
      await Promise.all([
        _loadDB('jokes'), _loadDB('facts'), _loadDB('smalltalk'),
        _loadDB('holidays'), _loadDB('celebrations')
      ]);

      // Activate easter eggs
      _initKonami();

      // Check for holiday on load
      const holiday = _detectHoliday();
      if (holiday) {
        setTimeout(() => {
          _fireEmojiRain(holiday.emojis);
          _toast(holiday.greetings[Math.floor(Math.random() * holiday.greetings.length)], 'info');
        }, 2000);
      }
    },

    /**
     * Respond to a warm_token from the Triple-Twin Phase 1 smalltalk twin.
     * @param {Object} warmToken — { mode: string, trigger: string }
     */
    async respond(warmToken) {
      if (!warmToken || !warmToken.mode) return;
      const mode = warmToken.mode;

      if (mode === 'celebrate') {
        await _fireConfetti({ particleCount: 100, spread: 70 });
        _playSound('fanfare');
      } else if (mode === 'encourage') {
        await _fireSparkles();
        _playSound('ding');
        const db = await _loadDB('smalltalk');
        if (db && db.encouragement) {
          const pick = _pickUnseen(db.encouragement, _seenSmallTalk);
          await _toast(pick.text, 'success');
        }
      } else if (mode === 'birthday') {
        await _fireEmojiRain(['🎂', '🎁', '🎈', '🥳']);
        _playSound('birthday');
        await _toast('Happy birthday!', 'success');
      } else if (mode === 'holiday') {
        const holiday = _detectHoliday();
        if (holiday) {
          await _fireEmojiRain(holiday.emojis);
          await _toast(holiday.greetings[0], 'info');
        }
      } else if (mode === 'warm_friendly') {
        // Subtle — just a warm greeting, no fireworks
        const db = await _loadDB('smalltalk');
        if (db && db.greetings_return) {
          const pick = _pickUnseen(db.greetings_return, _seenSmallTalk);
          await _toast(pick.text, 'info');
        }
      }
      // suppress_humor and neutral_professional: no effect (intentional)
    },

    /**
     * Trigger a celebration by key moment name.
     * @param {string} trigger — e.g., 'first_run_complete', 'milestone_100_runs'
     * @param {Object} data — optional data (e.g., { amount: '$2.50' })
     */
    async celebrate(trigger, data) {
      const db = await _loadDB('celebrations');
      if (!db || !db.celebrations) return;
      const celebration = db.celebrations.find(c => c.trigger === trigger);
      if (!celebration) return;

      let message = celebration.message;
      if (data) {
        Object.keys(data).forEach(key => {
          message = message.replace('${' + key + '}', data[key]);
        });
      }

      // Fire effect
      if (celebration.effect === 'confetti') {
        await _fireConfetti(celebration.confetti_config);
      } else if (celebration.effect === 'emoji_rain') {
        await _fireEmojiRain(celebration.emojis);
      } else if (celebration.effect === 'sparkles') {
        await _fireSparkles();
      } else if (celebration.effect === 'fireworks') {
        await _fireFireworks();
      }

      // Fire sound
      if (celebration.sound && celebration.sound !== 'none') {
        _playSound(celebration.sound);
      }

      // Fire toast
      if (message) {
        await _toast(message, 'success');
      }
    },

    /**
     * Get a random joke. Never repeats within session.
     * @returns {string|null}
     */
    async joke() {
      const db = await _loadDB('jokes');
      if (!db || !db.jokes) return null;
      const pick = _pickUnseen(db.jokes, _seenJokes);
      return pick ? pick.text : null;
    },

    /**
     * Get a random fun fact. Never repeats within session.
     * @returns {string|null}
     */
    async fact() {
      const db = await _loadDB('facts');
      if (!db || !db.facts) return null;
      const pick = _pickUnseen(db.facts, _seenFacts);
      return pick ? pick.text : null;
    },

    /**
     * Get a contextual greeting based on time of day and visit status.
     * @param {boolean} isReturning — true if user has visited before
     * @returns {string|null}
     */
    async greeting(isReturning) {
      const db = await _loadDB('smalltalk');
      if (!db) return null;

      const pool = isReturning ? db.greetings_return : db.greetings_first;
      if (!pool) return null;

      const pick = _pickUnseen(pool, _seenSmallTalk);
      return pick ? pick.text : null;
    },

    /**
     * Get a time-of-day appropriate message.
     * @returns {string|null}
     */
    async timeGreeting() {
      const db = await _loadDB('smalltalk');
      if (!db || !db.time_of_day) return null;

      const hour = new Date().getHours();
      const day = new Date().getDay();
      let timeKey;
      if (day === 5) timeKey = 'friday';
      else if (hour < 12) timeKey = 'morning';
      else if (hour < 17) timeKey = 'afternoon';
      else if (hour < 21) timeKey = 'evening';
      else timeKey = 'night';

      const matches = db.time_of_day.filter(s => s.time === timeKey);
      if (matches.length === 0) return null;

      const pick = _pickUnseen(matches, _seenSmallTalk);
      return pick ? pick.text : null;
    },

    /**
     * Register a delight plugin.
     * @param {Object} plugin — { name, triggers: { celebrate: fn, encourage: fn, ... } }
     */
    registerPlugin(plugin) {
      if (plugin && plugin.name) _plugins.push(plugin);
    },

    /**
     * Check if today is a holiday and return info.
     * @returns {Object|null}
     */
    holiday() {
      return _detectHoliday();
    },

    /**
     * Manually fire effects for testing or custom triggers.
     */
    effects: {
      confetti: _fireConfetti,
      emojiRain: _fireEmojiRain,
      sparkles: _fireSparkles,
      fireworks: _fireFireworks,
      toast: _toast,
      sound: _playSound
    }
  };
})();

// Auto-init when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => YinyangDelight.init());
} else {
  YinyangDelight.init();
}
