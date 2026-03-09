/* Tab Productivity Scorer — Task 156 — IIFE, no eval() */
(function () {
  'use strict';

  var BASE = '/api/v1/tab-productivity';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showMsg(text) {
    var el = document.getElementById('tps-msg');
    if (el) { el.textContent = text; }
  }

  function loadStats() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', BASE + '/stats');
    xhr.onload = function () {
      if (xhr.status !== 200) { return; }
      var d;
      try { d = JSON.parse(xhr.responseText); } catch (e) { return; }
      var el = document.getElementById('tps-stats');
      if (!el) { return; }
      el.innerHTML = '<div class="tps-stats-grid">' +
        '<div class="tps-stat"><div class="tps-stat-val">' + escHtml(d.total_scores) + '</div><div class="tps-stat-lbl">Total Scores</div></div>' +
        '<div class="tps-stat"><div class="tps-stat-val">' + escHtml(d.productive_count) + '</div><div class="tps-stat-lbl">Productive</div></div>' +
        '<div class="tps-stat"><div class="tps-stat-val">' + escHtml(d.unproductive_count) + '</div><div class="tps-stat-lbl">Unproductive</div></div>' +
        '<div class="tps-stat"><div class="tps-stat-val">' + escHtml(d.avg_productivity_score) + '</div><div class="tps-stat-lbl">Avg Score</div></div>' +
        '<div class="tps-stat"><div class="tps-stat-val">' + escHtml(d.total_time_minutes) + '</div><div class="tps-stat-lbl">Total Mins</div></div>' +
        '</div>';
    };
    xhr.send();
  }

  function loadScores() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', BASE + '/scores');
    xhr.onload = function () {
      if (xhr.status !== 200) { return; }
      var d;
      try { d = JSON.parse(xhr.responseText); } catch (e) { return; }
      var el = document.getElementById('tps-panel');
      if (!el) { return; }
      if (!d.scores || d.scores.length === 0) {
        el.innerHTML = '<p>No scores recorded yet.</p>';
        return;
      }
      var html = '';
      d.scores.slice().reverse().forEach(function (s) {
        var badgeCls = s.is_productive ? 'tps-badge-productive' : 'tps-badge-unproductive';
        var badgeTxt = s.is_productive ? 'Productive' : 'Unproductive';
        html += '<div class="tps-item">' +
          '<div>' +
            '<div class="tps-item-meta">' +
              '<span class="tps-badge ' + badgeCls + '">' + escHtml(badgeTxt) + '</span> ' +
              escHtml(s.category) + ' &nbsp;Score: <strong>' + escHtml(s.productivity_score) + '/10</strong>' +
              ' &nbsp;' + escHtml(s.time_spent_minutes) + ' min' +
              ' &nbsp;' + escHtml(s.tab_count) + ' tab(s)' +
            '</div>' +
            '<div class="tps-item-id">' + escHtml(s.score_id) + '</div>' +
          '</div>' +
          '<div class="tps-actions">' +
            '<button class="tps-btn tps-btn-del" data-id="' + escHtml(s.score_id) + '">Delete</button>' +
          '</div>' +
        '</div>';
      });
      el.innerHTML = html;
      el.querySelectorAll('.tps-btn-del').forEach(function (btn) {
        btn.addEventListener('click', function () {
          deleteScore(btn.getAttribute('data-id'));
        });
      });
    };
    xhr.send();
  }

  function deleteScore(id) {
    var xhr = new XMLHttpRequest();
    xhr.open('DELETE', BASE + '/scores/' + id);
    xhr.onload = function () {
      if (xhr.status === 200) {
        showMsg('Deleted.');
        loadStats();
        loadScores();
      } else {
        showMsg('Delete failed.');
      }
    };
    xhr.send();
  }

  function init() {
    loadStats();
    loadScores();

    var form = document.getElementById('tps-form');
    if (!form) { return; }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var body = JSON.stringify({
        category: document.getElementById('tps-category').value,
        url: document.getElementById('tps-url').value,
        time_spent_minutes: parseInt(document.getElementById('tps-time').value, 10) || 0,
        productivity_score: parseInt(document.getElementById('tps-score').value, 10) || 0,
        tab_count: parseInt(document.getElementById('tps-tabs').value, 10) || 1
      });
      var xhr = new XMLHttpRequest();
      xhr.open('POST', BASE + '/scores');
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.onload = function () {
        if (xhr.status === 201) {
          showMsg('Score recorded.');
          loadStats();
          loadScores();
        } else {
          var d;
          try { d = JSON.parse(xhr.responseText); } catch (ex) { d = {}; }
          showMsg('Error: ' + escHtml(d.error || 'unknown'));
        }
      };
      xhr.send(body);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
