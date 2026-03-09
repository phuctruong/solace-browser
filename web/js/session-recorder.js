/* Session Recorder — Task 088 */
(function () {
  'use strict';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  var panel = document.getElementById('sr-panel');
  var status = document.getElementById('sr-status');
  var activeRecordingId = null;

  function setStatus(msg) { status.textContent = msg; }

  function renderRecordings(recs) {
    if (!recs.length) {
      panel.innerHTML = '<p style="color:var(--hub-muted)">No recordings yet.</p>';
      return;
    }
    panel.innerHTML = recs.map(function (r) {
      return '<div class="sr-item">'
        + '<div class="sr-item-id">' + escHtml(r.recording_id) + '</div>'
        + '<div class="sr-item-meta">Started: ' + escHtml(r.started_at)
        + (r.duration_seconds !== null ? ' | Duration: ' + escHtml(r.duration_seconds) + 's' : ' | <span class="sr-recording">RECORDING</span>')
        + '</div>'
        + '</div>';
    }).join('');
  }

  function loadRecordings() {
    fetch('/api/v1/session-recorder/recordings')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderRecordings(data.recordings || []);
        setStatus('Recordings: ' + (data.total || 0));
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  }

  document.getElementById('btn-sr-start').addEventListener('click', function () {
    fetch('/api/v1/session-recorder/start', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.recording_id) {
          activeRecordingId = data.recording_id;
          setStatus('Recording started: ' + escHtml(data.recording_id));
        } else {
          setStatus('Error: ' + escHtml(data.error || 'unknown'));
        }
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  document.getElementById('btn-sr-stop').addEventListener('click', function () {
    fetch('/api/v1/session-recorder/stop', { method: 'POST' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        activeRecordingId = null;
        setStatus('Stopped: ' + escHtml(data.recording_id || ''));
        loadRecordings();
      })
      .catch(function (e) { setStatus('Error: ' + escHtml(String(e))); });
  });

  document.getElementById('btn-sr-list').addEventListener('click', loadRecordings);

  loadRecordings();
})();
