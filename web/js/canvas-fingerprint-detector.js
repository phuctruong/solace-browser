(function () {
  'use strict';

  var API_DETECTIONS = '/api/v1/canvas-fp/detections';
  var API_STATS = '/api/v1/canvas-fp/stats';
  var API_TECHNIQUES = '/api/v1/canvas-fp/techniques';

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message) {
    var el = document.getElementById('cfp-status');
    if (el) el.textContent = message;
  }

  function loadTechniques() {
    fetch(API_TECHNIQUES)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var select = document.getElementById('cfp-technique');
        if (!select) return;
        select.innerHTML = (data.techniques || []).map(function (item) {
          return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
        }).join('');
      })
      .catch(function (error) { setStatus('Technique load failed: ' + error.message); });
  }

  function loadStats() {
    fetch(API_STATS)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var el = document.getElementById('cfp-stats');
        if (!el) return;
        el.innerHTML = [
          ['Total Detections', data.total_detections || 0],
          ['Blocked', data.blocked_count || 0],
          ['Block Rate', data.block_rate || '0.00'],
          ['Avg Confidence', data.avg_confidence || '0.00']
        ].map(function (entry) {
          return '<div class="cfp-stat"><span>' + escHtml(entry[0]) + '</span><strong>' + escHtml(entry[1]) + '</strong></div>';
        }).join('');
      })
      .catch(function (error) { setStatus('Stats load failed: ' + error.message); });
  }

  function loadDetections() {
    fetch(API_DETECTIONS)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var el = document.getElementById('cfp-detections');
        var detections = data.detections || [];
        if (!el) return;
        if (!detections.length) {
          el.innerHTML = '<div class="cfp-row"><div class="cfp-meta">No detections recorded.</div></div>';
          return;
        }
        el.innerHTML = detections.map(function (detection) {
          return '<article class="cfp-row">' +
            '<div class="cfp-row-head"><div><div class="cfp-tag">' + escHtml(detection.technique) + '</div><div class="cfp-meta">' + escHtml(detection.detection_id) + '</div></div>' +
            '<button class="cfp-delete" data-id="' + escHtml(detection.detection_id) + '">Delete</button></div>' +
            '<div class="cfp-meta">page ' + escHtml(String(detection.url_hash || '').slice(0, 16)) + '…</div>' +
            '<div class="cfp-meta">script ' + escHtml(String(detection.script_hash || 'none').slice(0, 16)) + '…</div>' +
          '</article>';
        }).join('');
        el.querySelectorAll('[data-id]').forEach(function (button) {
          button.addEventListener('click', function () {
            deleteDetection(button.getAttribute('data-id'));
          });
        });
      })
      .catch(function (error) { setStatus('Detection load failed: ' + error.message); });
  }

  function deleteDetection(detectionId) {
    fetch(API_DETECTIONS + '/' + encodeURIComponent(detectionId), { method: 'DELETE' })
      .then(function (response) { return response.json(); })
      .then(function () {
        setStatus('Deleted ' + detectionId);
        loadDetections();
        loadStats();
      })
      .catch(function (error) { setStatus('Delete failed: ' + error.message); });
  }

  function bindForm() {
    var form = document.getElementById('cfp-form');
    if (!form) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      fetch(API_DETECTIONS, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          technique: document.getElementById('cfp-technique').value,
          url: document.getElementById('cfp-url').value.trim(),
          script_url: document.getElementById('cfp-script-url').value.trim() || null,
          was_blocked: document.getElementById('cfp-blocked').checked,
          confidence_score: document.getElementById('cfp-confidence').value
        })
      })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (data.detection_id) {
            form.reset();
            setStatus('Recorded ' + data.detection_id);
            loadDetections();
            loadStats();
            return;
          }
          setStatus(data.error || 'Unable to record detection');
        })
        .catch(function (error) { setStatus('Save failed: ' + error.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadTechniques();
    loadStats();
    loadDetections();
    bindForm();
  });
})();
