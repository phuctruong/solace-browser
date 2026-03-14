// Diagram: 02-dashboard-login
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function authHeaders() {
    var token = window.__SOLACE_TOKEN__ || '';
    return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + token };
  }

  function loadEventTypes() {
    fetch('/api/v1/search-suggestions/event-types')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('sgt-event-type');
        (data.event_types || []).forEach(function (et) {
          var opt = document.createElement('option');
          opt.value = et;
          opt.textContent = et;
          sel.appendChild(opt);
        });
      });
  }

  function loadStats() {
    fetch('/api/v1/search-suggestions/stats', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('sgt-stats');
        el.innerHTML = [
          ['Total Events', data.total_events],
          ['Click-Through Rate', data.click_through_rate],
          ['Avg Position', data.avg_position],
        ].map(function (pair) {
          return '<div class="sgt-stat-card"><div class="sgt-stat-value">' + escHtml(String(pair[1])) +
            '</div><div class="sgt-stat-label">' + escHtml(pair[0]) + '</div></div>';
        }).join('');
      });
  }

  function loadList() {
    fetch('/api/v1/search-suggestions/events', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('sgt-list');
        var events = data.events || [];
        if (!events.length) {
          el.innerHTML = '<p style="color:var(--hub-text-muted)">No events yet.</p>';
          return;
        }
        el.innerHTML = events.map(function (e) {
          return '<div class="sgt-item">' +
            '<div class="sgt-item-meta">' +
            '<span class="sgt-badge">' + escHtml(e.event_type) + '</span>' +
            '<span>pos ' + escHtml(e.position) + '</span>' +
            (e.engine ? '<span class="sgt-badge">' + escHtml(e.engine) + '</span>' : '') +
            '<span style="color:var(--hub-text-muted);font-size:0.75rem">' + escHtml(e.recorded_at) + '</span>' +
            '</div>' +
            '<button class="sgt-delete-btn" data-id="' + escHtml(e.event_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('.sgt-delete-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteEvent(btn.getAttribute('data-id'));
          });
        });
      });
  }

  function deleteEvent(id) {
    fetch('/api/v1/search-suggestions/events/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(function () { refresh(); });
  }

  function refresh() {
    loadStats();
    loadList();
  }

  document.getElementById('sgt-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var eventType = document.getElementById('sgt-event-type').value;
    var query = document.getElementById('sgt-query').value;
    var suggestion = document.getElementById('sgt-suggestion').value;
    var position = parseInt(document.getElementById('sgt-position').value, 10) || 1;
    var engine = document.getElementById('sgt-engine').value;
    fetch('/api/v1/search-suggestions/events', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ event_type: eventType, query: query, suggestion: suggestion, position: position, engine: engine }),
    }).then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.event_id) { refresh(); }
        else { alert('Error: ' + (data.error || 'unknown')); }
      });
  });

  loadEventTypes();
  refresh();
}());
