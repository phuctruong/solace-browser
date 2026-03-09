/* DOM Change Monitor — Task 160. IIFE. No eval(). escHtml required. */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function msg(text) {
    var el = document.getElementById('dcm-msg');
    if (el) el.textContent = text;
  }

  function loadStats() {
    fetch('/api/v1/dom-monitor/monitor-stats', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var el = document.getElementById('dcm-stats');
        if (!el) return;
        el.innerHTML = '<div class="dcm-stats-grid">' +
          '<div class="dcm-stat"><div class="dcm-stat-val">' + escHtml(d.total_events) + '</div><div class="dcm-stat-lbl">Total Events</div></div>' +
          '<div class="dcm-stat"><div class="dcm-stat-val">' + escHtml(d.avg_changes) + '</div><div class="dcm-stat-lbl">Avg Changes</div></div>' +
          '<div class="dcm-stat"><div class="dcm-stat-val">' + escHtml(d.total_nodes_added) + '</div><div class="dcm-stat-lbl">Nodes Added</div></div>' +
          '<div class="dcm-stat"><div class="dcm-stat-val">' + escHtml(d.total_nodes_removed) + '</div><div class="dcm-stat-lbl">Nodes Removed</div></div>' +
          '</div>';
      })
      .catch(function (e) { msg('Stats error: ' + e.message); });
  }

  function loadEvents() {
    fetch('/api/v1/dom-monitor/monitor-events', { headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') } })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var panel = document.getElementById('dcm-panel');
        if (!panel) return;
        if (!d.events || d.events.length === 0) { panel.innerHTML = '<p>No events recorded.</p>'; return; }
        panel.innerHTML = d.events.map(function (e) {
          return '<div class="dcm-item">' +
            '<div><div class="dcm-item-meta"><span class="dcm-badge">' + escHtml(e.mutation_type) + '</span> ' +
            escHtml(e.change_count) + ' changes | +' + escHtml(e.nodes_added) + ' -' + escHtml(e.nodes_removed) + '</div>' +
            '<div class="dcm-item-id">' + escHtml(e.event_id) + '</div></div>' +
            '<div class="dcm-actions"><button class="dcm-btn dcm-btn-del" data-id="' + escHtml(e.event_id) + '">Delete</button></div>' +
            '</div>';
        }).join('');
        panel.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteEvent(btn.dataset.id); });
        });
      })
      .catch(function (e) { msg('Load error: ' + e.message); });
  }

  function deleteEvent(id) {
    fetch('/api/v1/dom-monitor/monitor-events/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') }
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadEvents(); loadStats(); })
      .catch(function (e) { msg('Delete error: ' + e.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadStats();
    loadEvents();

    var form = document.getElementById('dcm-form');
    if (form) {
      form.addEventListener('submit', function (ev) {
        ev.preventDefault();
        var payload = {
          url: document.getElementById('dcm-url').value,
          selector: document.getElementById('dcm-selector').value,
          mutation_type: document.getElementById('dcm-mutation-type').value,
          change_count: parseInt(document.getElementById('dcm-change-count').value, 10),
          nodes_added: parseInt(document.getElementById('dcm-nodes-added').value, 10),
          nodes_removed: parseInt(document.getElementById('dcm-nodes-removed').value, 10),
        };
        fetch('/api/v1/dom-monitor/monitor-events', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + (window._solaceToken || '')
          },
          body: JSON.stringify(payload)
        })
          .then(function (r) { return r.json(); })
          .then(function (d) {
            if (d.event) { msg('Recorded: ' + d.event.event_id); loadEvents(); loadStats(); }
            else { msg('Error: ' + (d.error || 'unknown')); }
          })
          .catch(function (e) { msg('Submit error: ' + e.message); });
      });
    }
  });
}());
