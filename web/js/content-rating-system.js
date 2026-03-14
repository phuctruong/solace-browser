// Diagram: 02-dashboard-login
/* Content Rating System — Task 114 */
(function () {
  'use strict';

  var panel = document.getElementById('crs-panel');
  var status = document.getElementById('crs-status');

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setStatus(msg) { status.textContent = msg; }

  function apiFetch(method, path, body) {
    var opts = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (body) { opts.body = JSON.stringify(body); }
    return fetch(path, opts).then(function (r) { return r.json(); });
  }

  function renderRatings(ratings) {
    if (!ratings || ratings.length === 0) {
      panel.innerHTML = '<div class="crs-empty">No ratings submitted yet.</div>';
      return;
    }
    var html = '';
    ratings.forEach(function (r) {
      html += '<div class="crs-card">'
        + '<span class="crs-card-id">' + escHtml(r.rating_id) + '</span>'
        + '<span class="crs-card-criterion">' + escHtml(r.criterion) + '</span>'
        + '<span class="crs-card-score">&#9733; ' + escHtml(r.score) + '/5</span>'
        + '<span class="crs-card-quality">' + escHtml(r.quality_level) + '</span>'
        + '<button class="crs-btn crs-btn-danger" onclick="crsDelete(\'' + escHtml(r.rating_id) + '\')">Delete</button>'
        + '</div>';
    });
    panel.innerHTML = html;
  }

  function renderStats(data) {
    var html = '<div class="crs-stats-grid">'
      + '<div class="crs-stat-box"><div class="crs-stat-val">' + escHtml(data.total_ratings) + '</div><div class="crs-stat-lbl">Total Ratings</div></div>'
      + '<div class="crs-stat-box"><div class="crs-stat-val">' + escHtml(data.avg_score) + '</div><div class="crs-stat-lbl">Avg Score</div></div>'
      + '</div>';
    panel.innerHTML = html;
  }

  function renderCriteria(criteria) {
    var html = '<div class="crs-criteria-grid">';
    criteria.forEach(function (c) {
      html += '<div class="crs-criterion-box">' + escHtml(c) + '</div>';
    });
    html += '</div>';
    panel.innerHTML = html;
  }

  function renderAddForm(criteria) {
    var opts = criteria.map(function (c) {
      return '<option value="' + escHtml(c) + '">' + escHtml(c) + '</option>';
    }).join('');
    var scoreOpts = [1, 2, 3, 4, 5].map(function (n) {
      return '<option value="' + n + '">' + n + '</option>';
    }).join('');
    panel.innerHTML = '<div class="crs-form">'
      + '<label>Content URL<input id="crs-url" type="url" placeholder="https://article.com/post"></label>'
      + '<label>Criterion<select id="crs-criterion">' + opts + '</select></label>'
      + '<label>Score (1-5)<select id="crs-score">' + scoreOpts + '</select></label>'
      + '<label>Notes (optional)<textarea id="crs-notes" rows="2" placeholder="Optional comments..."></textarea></label>'
      + '<div class="crs-form-row">'
      + '<button class="crs-btn crs-btn-secondary" onclick="crsLoadRatings()">Cancel</button>'
      + '<button class="crs-btn crs-btn-primary" onclick="crsSubmit()">Submit Rating</button>'
      + '</div></div>';
  }

  window.crsLoadRatings = function () {
    setStatus('Loading ratings...');
    apiFetch('GET', '/api/v1/content-rating/ratings').then(function (d) {
      renderRatings(d.ratings || []);
      setStatus(d.total + ' ratings.');
    });
  };

  window.crsLoadStats = function () {
    setStatus('Loading stats...');
    apiFetch('GET', '/api/v1/content-rating/stats').then(function (d) {
      renderStats(d);
      setStatus('Stats loaded.');
    });
  };

  window.crsLoadCriteria = function () {
    apiFetch('GET', '/api/v1/content-rating/criteria').then(function (d) {
      renderCriteria(d.criteria || []);
      setStatus(d.criteria.length + ' criteria available.');
    });
  };

  window.crsShowAddForm = function () {
    apiFetch('GET', '/api/v1/content-rating/criteria').then(function (d) {
      renderAddForm(d.criteria || []);
      setStatus('');
    });
  };

  window.crsDelete = function (rid) {
    apiFetch('DELETE', '/api/v1/content-rating/ratings/' + rid).then(function (d) {
      if (d.status === 'deleted') {
        setStatus('Deleted ' + rid);
        window.crsLoadRatings();
      } else {
        setStatus('Error: ' + escHtml(d.error || 'unknown'));
      }
    });
  };

  window.crsSubmit = function () {
    var url = document.getElementById('crs-url').value.trim();
    var criterion = document.getElementById('crs-criterion').value;
    var score = parseInt(document.getElementById('crs-score').value, 10);
    var notes = document.getElementById('crs-notes').value.trim();
    if (!url) { setStatus('Content URL is required.'); return; }
    var body = { url: url, criterion: criterion, score: score };
    if (notes) { body.notes = notes; }
    apiFetch('POST', '/api/v1/content-rating/ratings', body).then(function (d) {
      if (d.rating) {
        setStatus('Submitted: ' + escHtml(d.rating.rating_id) + ' (' + escHtml(d.rating.quality_level) + ')');
        window.crsLoadRatings();
      } else {
        setStatus('Error: ' + escHtml(d.error || 'unknown'));
      }
    });
  };

  document.getElementById('btn-crs-ratings').addEventListener('click', window.crsLoadRatings);
  document.getElementById('btn-crs-stats').addEventListener('click', window.crsLoadStats);
  document.getElementById('btn-crs-criteria').addEventListener('click', window.crsLoadCriteria);
  document.getElementById('btn-crs-add').addEventListener('click', window.crsShowAddForm);

  window.crsLoadRatings();
})();
