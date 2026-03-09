/* Browser History Analytics — Task 112 */
(function () {
  'use strict';

  var panel = document.getElementById('bha-panel');
  var status = document.getElementById('bha-status');

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setStatus(msg) {
    status.textContent = msg;
  }

  function apiFetch(method, path, body) {
    var opts = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (body) { opts.body = JSON.stringify(body); }
    return fetch(path, opts).then(function (r) { return r.json(); });
  }

  function renderVisits(visits) {
    if (!visits || visits.length === 0) {
      panel.innerHTML = '<div class="bha-empty">No visits recorded yet.</div>';
      return;
    }
    var html = '';
    visits.forEach(function (v) {
      html += '<div class="bha-card">'
        + '<span class="bha-card-id">' + escHtml(v.visit_id) + '</span>'
        + '<span class="bha-card-cat">' + escHtml(v.category) + '</span>'
        + '<span class="bha-card-dur">' + escHtml(v.duration_seconds) + 's</span>'
        + '<button class="bha-btn bha-btn-danger" onclick="bhaDeleteVisit(\'' + escHtml(v.visit_id) + '\')">Delete</button>'
        + '</div>';
    });
    panel.innerHTML = html;
  }

  function renderStats(data) {
    var html = '<div class="bha-stats-grid">'
      + '<div class="bha-stat-box"><div class="bha-stat-val">' + escHtml(data.total_visits) + '</div><div class="bha-stat-lbl">Total Visits</div></div>'
      + '<div class="bha-stat-box"><div class="bha-stat-val">' + escHtml(data.total_unique_domains) + '</div><div class="bha-stat-lbl">Unique Domains</div></div>'
      + '</div>';
    panel.innerHTML = html;
  }

  function renderCategories(cats) {
    var html = '<div class="bha-stats-grid">';
    cats.forEach(function (c) {
      html += '<div class="bha-stat-box"><div class="bha-stat-lbl">' + escHtml(c) + '</div></div>';
    });
    html += '</div>';
    panel.innerHTML = html;
  }

  function renderAddForm(categories) {
    var opts = categories.map(function (c) {
      return '<option value="' + escHtml(c) + '">' + escHtml(c) + '</option>';
    }).join('');
    panel.innerHTML = '<div class="bha-form">'
      + '<label>URL<input id="bha-url" type="url" placeholder="https://example.com"></label>'
      + '<label>Domain<input id="bha-domain" type="text" placeholder="example.com"></label>'
      + '<label>Category<select id="bha-category">' + opts + '</select></label>'
      + '<label>Duration (seconds)<input id="bha-duration" type="number" min="0" value="0"></label>'
      + '<div class="bha-form-row">'
      + '<button class="bha-btn bha-btn-secondary" onclick="bhaLoadVisits()">Cancel</button>'
      + '<button class="bha-btn bha-btn-primary" onclick="bhaSubmitVisit()">Record</button>'
      + '</div>'
      + '</div>';
  }

  window.bhaLoadVisits = function () {
    setStatus('Loading visits...');
    apiFetch('GET', '/api/v1/history-analytics/visits').then(function (d) {
      renderVisits(d.visits || []);
      setStatus('Showing ' + (d.total || 0) + ' visits.');
    });
  };

  window.bhaLoadStats = function () {
    setStatus('Loading stats...');
    apiFetch('GET', '/api/v1/history-analytics/stats').then(function (d) {
      renderStats(d);
      setStatus('Stats loaded.');
    });
  };

  window.bhaLoadCategories = function () {
    apiFetch('GET', '/api/v1/history-analytics/categories').then(function (d) {
      renderCategories(d.categories || []);
      setStatus(d.categories.length + ' categories available.');
    });
  };

  window.bhaDeleteVisit = function (visitId) {
    apiFetch('DELETE', '/api/v1/history-analytics/visits/' + visitId).then(function (d) {
      if (d.status === 'deleted') {
        setStatus('Deleted ' + visitId);
        window.bhaLoadVisits();
      } else {
        setStatus('Error: ' + (d.error || 'unknown'));
      }
    });
  };

  window.bhaShowAddForm = function () {
    apiFetch('GET', '/api/v1/history-analytics/categories').then(function (d) {
      renderAddForm(d.categories || []);
      setStatus('');
    });
  };

  window.bhaSubmitVisit = function () {
    var url = document.getElementById('bha-url').value.trim();
    var domain = document.getElementById('bha-domain').value.trim();
    var category = document.getElementById('bha-category').value;
    var duration = parseInt(document.getElementById('bha-duration').value, 10);
    if (!url) { setStatus('URL is required.'); return; }
    apiFetch('POST', '/api/v1/history-analytics/visits', {
      url: url, domain: domain, category: category, duration_seconds: duration
    }).then(function (d) {
      if (d.visit) {
        setStatus('Visit recorded: ' + escHtml(d.visit.visit_id));
        window.bhaLoadVisits();
      } else {
        setStatus('Error: ' + escHtml(d.error || 'unknown'));
      }
    });
  };

  document.getElementById('btn-bha-visits').addEventListener('click', window.bhaLoadVisits);
  document.getElementById('btn-bha-stats').addEventListener('click', window.bhaLoadStats);
  document.getElementById('btn-bha-categories').addEventListener('click', window.bhaLoadCategories);
  document.getElementById('btn-bha-add').addEventListener('click', window.bhaShowAddForm);

  window.bhaLoadVisits();
})();
