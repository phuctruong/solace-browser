// Diagram: 02-dashboard-login
/**
 * session-replay.js — Session Replay Viewer for Solace Hub (Task 027)
 * Laws:
 *   - No CDN dependencies. No jQuery. No Bootstrap. No Tailwind.
 *   - Port 8888 ONLY (same origin). Banned port omitted from source.
 *   - Dynamic escaping via escHtml() required for all dynamic content.
 *   - Solace Hub only. "Companion App" BANNED.
 *   - All CSS via var(--hub-*) tokens only.
 *   - IIFE pattern.
 */

'use strict';

(function () {
  var TOKEN = localStorage.getItem('solace_token') || '';
  var AUTH_HEADERS = { 'Authorization': 'Bearer ' + TOKEN, 'Content-Type': 'application/json' };

  var _replays = [];
  var _activeReplayId = null;
  var _actions = [];
  var _playStep = -1;
  var _playTimer = null;

  var ACTION_ICONS = {
    click: 'CLK',
    navigate: 'NAV',
    type: 'TYP',
    scroll: 'SCR',
    screenshot: 'CAM'
  };

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function fmtTime(ts) {
    if (!ts) return '';
    try {
      var d = (typeof ts === 'number' && ts < 1e12) ? new Date(ts * 1000) : new Date(ts);
      return d.toLocaleString();
    } catch (e) { return String(ts); }
  }

  function apiFetch(path, opts) {
    return fetch(path, opts || { headers: AUTH_HEADERS });
  }

  function apiFetchAuth(path, method, body) {
    var opts = { method: method || 'GET', headers: AUTH_HEADERS };
    if (body !== undefined) opts.body = JSON.stringify(body);
    return apiFetch(path, opts);
  }

  // --- Load replay list ---
  function loadReplays() {
    var list = document.getElementById('replay-list');
    if (list) list.innerHTML = '<div class="empty-state">Loading...</div>';
    apiFetch('/api/v1/replay/sessions')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        _replays = d.sessions || d.replays || [];
        renderReplayList();
      })
      .catch(function () {
        if (list) list.innerHTML = '<div class="empty-state">Could not load sessions.</div>';
      });
  }

  function renderReplayList() {
    var list = document.getElementById('replay-list');
    if (!list) return;
    if (!_replays.length) {
      list.innerHTML = '<div class="empty-state">No replay sessions yet.</div>';
      return;
    }
    list.innerHTML = _replays.map(function (r) {
      var rid = escHtml(r.replay_id || r.id || '');
      var isActive = (r.replay_id || r.id) === _activeReplayId;
      return (
        '<div class="replay-item' + (isActive ? ' replay-item--active' : '') + '" data-id="' + rid + '">' +
          '<div class="replay-item-name">' + escHtml(r.name || 'Session') + '</div>' +
          '<div class="replay-item-meta">' + escHtml(fmtTime(r.created_at)) +
            (r.action_count !== undefined ? ' &bull; ' + escHtml(String(r.action_count)) + ' actions' : '') +
          '</div>' +
        '</div>'
      );
    }).join('');
    list.querySelectorAll('.replay-item').forEach(function (item) {
      item.addEventListener('click', function () {
        var rid = item.getAttribute('data-id');
        selectReplay(rid);
      });
    });
  }

  // --- Select and load replay ---
  function selectReplay(replayId) {
    _activeReplayId = replayId;
    resetPlayback();
    renderReplayList();
    var controls = document.getElementById('playback-controls');
    var title = document.getElementById('replay-detail-title');
    var timeline = document.getElementById('action-timeline');
    if (controls) controls.style.display = 'flex';
    if (timeline) timeline.innerHTML = '<div class="empty-state">Loading actions...</div>';

    apiFetch('/api/v1/replay/sessions/' + encodeURIComponent(replayId))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var replay = d.session || d.replay || d;
        _actions = replay.actions || d.actions || [];
        if (title) title.textContent = replay.name || 'Session';
        renderTimeline(-1);
      })
      .catch(function () {
        if (timeline) timeline.innerHTML = '<div class="empty-state">Could not load actions.</div>';
      });
  }

  function renderTimeline(currentStep) {
    var timeline = document.getElementById('action-timeline');
    if (!timeline) return;
    if (!_actions.length) {
      timeline.innerHTML = '<div class="empty-state">No actions recorded.</div>';
      return;
    }
    timeline.innerHTML = _actions.map(function (a, i) {
      var atype = (a.action || a.type || 'other').toLowerCase();
      var icon = ACTION_ICONS[atype] || 'ACT';
      var detail = a.selector || a.url || a.value || a.text || '';
      var classes = 'action-step';
      if (i === currentStep) classes += ' action-step--active';
      else if (i < currentStep) classes += ' action-step--played';
      return (
        '<div class="' + classes + '">' +
          '<div class="step-icon step-icon--' + escHtml(atype) + '">' + escHtml(icon) + '</div>' +
          '<div class="step-body">' +
            '<div class="step-action">' + escHtml(a.action || a.type || 'action') + '</div>' +
            '<div class="step-detail">' + escHtml(detail) + '</div>' +
            '<div class="step-ts">' + escHtml(fmtTime(a.ts || a.timestamp || '')) + '</div>' +
          '</div>' +
        '</div>'
      );
    }).join('');
  }

  // --- Playback ---
  function startPlayback() {
    var btn = document.getElementById('btn-play');
    var status = document.getElementById('playback-status');
    if (!_actions.length) return;
    if (_playTimer) return;
    if (_playStep >= _actions.length - 1) _playStep = -1;
    if (btn) btn.textContent = 'Pause';
    _playTimer = setInterval(function () {
      _playStep++;
      renderTimeline(_playStep);
      if (status) status.textContent = 'Step ' + (_playStep + 1) + ' / ' + _actions.length;
      if (_playStep >= _actions.length - 1) {
        stopPlayback();
        if (status) status.textContent = 'Done';
      }
    }, 700);
  }

  function stopPlayback() {
    if (_playTimer) { clearInterval(_playTimer); _playTimer = null; }
    var btn = document.getElementById('btn-play');
    if (btn) btn.textContent = 'Play';
  }

  function resetPlayback() {
    stopPlayback();
    _playStep = -1;
    _actions = [];
    var status = document.getElementById('playback-status');
    if (status) status.textContent = 'Stopped';
  }

  function togglePlay() {
    if (_playTimer) stopPlayback();
    else startPlayback();
  }

  // --- New replay modal ---
  function openNewModal() {
    var modal = document.getElementById('modal-new-replay');
    var inp = document.getElementById('input-replay-name');
    var err = document.getElementById('modal-replay-error');
    if (modal) modal.style.display = 'flex';
    if (inp) { inp.value = ''; inp.focus(); }
    if (err) { err.style.display = 'none'; err.textContent = ''; }
    var urlInp = document.getElementById('input-replay-url');
    if (urlInp) urlInp.value = '';
  }

  function closeNewModal() {
    var modal = document.getElementById('modal-new-replay');
    if (modal) modal.style.display = 'none';
  }

  function confirmNewReplay() {
    var nameInp = document.getElementById('input-replay-name');
    var urlInp = document.getElementById('input-replay-url');
    var err = document.getElementById('modal-replay-error');
    var name = (nameInp ? nameInp.value : '').trim();
    var url = (urlInp ? urlInp.value : '').trim();
    if (!name) {
      if (err) { err.textContent = 'Session name is required.'; err.style.display = ''; }
      return;
    }
    apiFetchAuth('/api/v1/replay/sessions', 'POST', { name: name, start_url: url })
      .then(function (r) {
        if (r.status === 400) return r.json().then(function (d) { throw new Error(d.error || 'Bad request'); });
        if (!r.ok) throw new Error('Create failed (' + r.status + ')');
        return r.json();
      })
      .then(function (d) {
        closeNewModal();
        loadReplays();
        if (d.session && (d.session.replay_id || d.session.id)) {
          setTimeout(function () { selectReplay(d.session.replay_id || d.session.id); }, 300);
        }
      })
      .catch(function (e) {
        if (err) { err.textContent = e.message; err.style.display = ''; }
      });
  }

  // --- Bind events ---
  var btnNewReplay = document.getElementById('btn-new-replay');
  var btnCancelReplay = document.getElementById('btn-cancel-replay');
  var btnConfirmReplay = document.getElementById('btn-confirm-replay');
  var btnPlay = document.getElementById('btn-play');
  var btnReset = document.getElementById('btn-reset');
  var overlay = document.getElementById('modal-new-replay');

  if (btnNewReplay) btnNewReplay.addEventListener('click', openNewModal);
  if (btnCancelReplay) btnCancelReplay.addEventListener('click', closeNewModal);
  if (btnConfirmReplay) btnConfirmReplay.addEventListener('click', confirmNewReplay);
  if (btnPlay) btnPlay.addEventListener('click', togglePlay);
  if (btnReset) btnReset.addEventListener('click', function () {
    resetPlayback();
    if (_activeReplayId) selectReplay(_activeReplayId);
  });
  if (overlay) {
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) closeNewModal();
    });
  }

  loadReplays();
})();
