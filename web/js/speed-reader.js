// Diagram: 02-dashboard-login
/* speed-reader.js — Speed Reader | Task 125 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_SESSIONS    = '/api/v1/speed-reader/sessions';
  var API_PROGRESS    = '/api/v1/speed-reader/progress';
  var API_DIFFICULTY  = '/api/v1/speed-reader/difficulty-levels';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('srd-status');
    if (el) el.textContent = msg;
  }

  function loadDifficultyLevels() {
    fetch(API_DIFFICULTY)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var levels = data.difficulty_levels || [];
        var badgesEl = document.getElementById('srd-levels');
        var selectEl = document.getElementById('srd-difficulty');
        if (badgesEl) {
          badgesEl.innerHTML = levels.map(function (l) {
            return '<span class="srd-badge">' + escHtml(l) + '</span>';
          }).join('');
        }
        if (selectEl) {
          selectEl.innerHTML = levels.map(function (l) {
            return '<option value="' + escHtml(l) + '">' + escHtml(l) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading difficulty levels: ' + err.message); });
  }

  function loadProgress() {
    fetch(API_PROGRESS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('srd-progress');
        if (!el) return;
        var trendClass = 'srd-trend-' + (data.wpm_trend || 'stable');
        el.innerHTML =
          '<div class="srd-progress-stat">' +
            '<span class="srd-progress-label">Sessions</span>' +
            '<span class="srd-progress-value">' + escHtml(String(data.total_sessions || 0)) + '</span>' +
          '</div>' +
          '<div class="srd-progress-stat">' +
            '<span class="srd-progress-label">Avg WPM</span>' +
            '<span class="srd-progress-value">' + escHtml(String(data.avg_wpm || '0')) + '</span>' +
          '</div>' +
          '<div class="srd-progress-stat">' +
            '<span class="srd-progress-label">Avg Comprehension</span>' +
            '<span class="srd-progress-value">' + escHtml(String(data.avg_comprehension || '0')) + '%</span>' +
          '</div>' +
          '<div class="srd-progress-stat">' +
            '<span class="srd-progress-label">Trend</span>' +
            '<span class="srd-progress-value ' + escHtml(trendClass) + '">' + escHtml(data.wpm_trend || 'stable') + '</span>' +
          '</div>';
      })
      .catch(function (err) { setStatus('Progress error: ' + err.message); });
  }

  function renderSessions(sessions) {
    var el = document.getElementById('srd-sessions-list');
    if (!el) return;
    if (!sessions || sessions.length === 0) {
      el.innerHTML = '<p class="srd-empty">No sessions recorded yet.</p>';
      return;
    }
    el.innerHTML = sessions.map(function (s) {
      return '<div class="srd-row">' +
        '<div class="srd-row-meta">' +
        '<span class="srd-diff-tag">' + escHtml(s.difficulty) + '</span>' +
        '<span class="srd-wpm">' + escHtml(String(s.wpm)) + ' WPM</span>' +
        '<span>' + escHtml(String(s.word_count)) + ' words</span>' +
        '<span>' + escHtml(String(s.comprehension_score)) + '% comp.</span>' +
        '<span class="srd-hash">hash: ' + escHtml((s.text_hash || '').slice(0, 16)) + '&hellip;</span>' +
        '</div>' +
        '<button class="srd-btn srd-btn-danger" data-id="' + escHtml(s.session_id) + '">Delete</button>' +
        '</div>';
    }).join('');

    el.querySelectorAll('[data-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        deleteSession(btn.getAttribute('data-id'));
      });
    });
  }

  function loadSessions() {
    fetch(API_SESSIONS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderSessions(data.sessions || []);
        loadProgress();
      })
      .catch(function (err) { setStatus('Error loading sessions: ' + err.message); });
  }

  function deleteSession(sessionId) {
    fetch(API_SESSIONS + '/' + encodeURIComponent(sessionId), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () {
        setStatus('Deleted: ' + sessionId);
        loadSessions();
      })
      .catch(function (err) { setStatus('Delete error: ' + err.message); });
  }

  function initSessionForm() {
    var form = document.getElementById('srd-session-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var text = document.getElementById('srd-text').value.trim();
      var wordCount = parseInt(document.getElementById('srd-word-count').value, 10) || 0;
      var wpm = parseInt(document.getElementById('srd-wpm').value, 10) || 0;
      var comprehension = parseInt(document.getElementById('srd-comprehension').value, 10);
      var difficulty = document.getElementById('srd-difficulty').value;
      var duration = parseInt(document.getElementById('srd-duration').value, 10) || 0;
      fetch(API_SESSIONS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text,
          word_count: wordCount,
          wpm: wpm,
          comprehension_score: comprehension,
          difficulty: difficulty,
          duration_seconds: duration,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'recorded') {
            setStatus('Recorded: ' + data.session.session_id);
            loadSessions();
          } else {
            setStatus('Error: ' + (data.error || 'unknown'));
          }
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadDifficultyLevels();
    loadSessions();
    initSessionForm();
  });
})();
