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

  function loadAnnotationTypes() {
    fetch('/api/v1/annotations/annotation-types')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var sel = document.getElementById('ann-type');
        (data.annotation_types || []).forEach(function (at) {
          var opt = document.createElement('option');
          opt.value = at;
          opt.textContent = at;
          sel.appendChild(opt);
        });
      });
  }

  function loadStats() {
    fetch('/api/v1/annotations/stats', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('ann-stats');
        el.innerHTML = [
          ['Total Annotations', data.total_annotations],
        ].map(function (pair) {
          return '<div class="ann-stat-card"><div class="ann-stat-value">' + escHtml(String(pair[1])) +
            '</div><div class="ann-stat-label">' + escHtml(pair[0]) + '</div></div>';
        }).join('');
      });
  }

  function loadList() {
    fetch('/api/v1/annotations/annotations', { headers: authHeaders() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('ann-list');
        var annotations = data.annotations || [];
        if (!annotations.length) {
          el.innerHTML = '<p style="color:var(--hub-text-muted)">No annotations yet.</p>';
          return;
        }
        el.innerHTML = annotations.map(function (a) {
          return '<div class="ann-item" data-color="' + escHtml(a.color) + '">' +
            '<div class="ann-item-meta">' +
            '<span class="ann-badge">' + escHtml(a.annotation_type) + '</span>' +
            '<span class="ann-badge">' + escHtml(a.color) + '</span>' +
            (a.note ? '<span>' + escHtml(a.note) + '</span>' : '') +
            '<span style="color:var(--hub-text-muted);font-size:0.75rem">' + escHtml(a.created_at) + '</span>' +
            '</div>' +
            '<button class="ann-delete-btn" data-id="' + escHtml(a.annotation_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('.ann-delete-btn').forEach(function (btn) {
          btn.addEventListener('click', function () {
            deleteAnnotation(btn.getAttribute('data-id'));
          });
        });
      });
  }

  function deleteAnnotation(id) {
    fetch('/api/v1/annotations/annotations/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeaders(),
    }).then(function () { refresh(); });
  }

  function refresh() {
    loadStats();
    loadList();
  }

  document.getElementById('ann-form').addEventListener('submit', function (e) {
    e.preventDefault();
    var annotationType = document.getElementById('ann-type').value;
    var color = document.getElementById('ann-color').value;
    var url = document.getElementById('ann-url').value;
    var selectedText = document.getElementById('ann-selected-text').value;
    var selectedTextLength = parseInt(document.getElementById('ann-text-length').value, 10) || 0;
    var note = document.getElementById('ann-note').value || null;
    fetch('/api/v1/annotations/annotations', {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({
        annotation_type: annotationType,
        color: color,
        url: url,
        selected_text: selectedText,
        selected_text_length: selectedTextLength,
        note: note,
      }),
    }).then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.annotation_id) { refresh(); }
        else { alert('Error: ' + (data.error || 'unknown')); }
      });
  });

  loadAnnotationTypes();
  refresh();
}());
