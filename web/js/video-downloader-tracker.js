// Diagram: 02-dashboard-login
/* video-downloader-tracker.js — Video Downloader Tracker | Task 133 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_DOWNLOADS = '/api/v1/video-tracker/downloads';
  var API_STATS     = '/api/v1/video-tracker/stats';
  var API_QUALITIES = '/api/v1/video-tracker/qualities';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('vdt-status');
    if (el) el.textContent = msg;
  }

  function authHeader() {
    return { Authorization: 'Bearer ' + (window._solaceToken || '') };
  }

  function loadQualities() {
    fetch(API_QUALITIES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var qualSel = document.getElementById('vdt-quality');
        if (qualSel) {
          qualSel.innerHTML = (data.qualities || []).map(function (q) {
            return '<option value="' + escHtml(q) + '">' + escHtml(q) + '</option>';
          }).join('');
        }
        var fmtSel = document.getElementById('vdt-format');
        if (fmtSel) {
          fmtSel.innerHTML = (data.formats || []).map(function (f) {
            return '<option value="' + escHtml(f) + '">' + escHtml(f) + '</option>';
          }).join('');
        }
        var stSel = document.getElementById('vdt-status-sel');
        if (stSel) {
          stSel.innerHTML = (data.statuses || []).map(function (s) {
            return '<option value="' + escHtml(s) + '">' + escHtml(s) + '</option>';
          }).join('');
        }
      })
      .catch(function (err) { setStatus('Error loading qualities: ' + err.message); });
  }

  function loadDownloads() {
    fetch(API_DOWNLOADS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('vdt-list');
        if (!el) return;
        var downloads = data.downloads || [];
        if (downloads.length === 0) { el.innerHTML = '<p>No downloads yet.</p>'; return; }
        el.innerHTML = downloads.slice().reverse().map(function (d) {
          return '<div class="vdt-item">' +
            '<div>' +
              '<span class="vdt-badge">' + escHtml(d.quality) + '</span> ' +
              '<span class="vdt-badge">' + escHtml(d.format) + '</span> ' +
              escHtml(d.download_id) + ' — ' + escHtml(d.status) +
            '</div>' +
            '<button class="vdt-btn vdt-btn-danger" data-id="' + escHtml(d.download_id) + '">Delete</button>' +
            '</div>';
        }).join('');
        el.querySelectorAll('button[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteDownload(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { setStatus('Error loading downloads: ' + err.message); });
  }

  function loadStats() {
    fetch(API_STATS, { headers: authHeader() })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('vdt-stats');
        if (!el) return;
        el.innerHTML =
          '<div class="vdt-stat-card"><div class="vdt-stat-value">' + escHtml(String(data.total_downloads || 0)) + '</div><div class="vdt-stat-label">Total Downloads</div></div>' +
          '<div class="vdt-stat-card"><div class="vdt-stat-value">' + escHtml(String(data.total_size_bytes || 0)) + '</div><div class="vdt-stat-label">Total Bytes</div></div>';
      })
      .catch(function (err) { setStatus('Error loading stats: ' + err.message); });
  }

  function deleteDownload(id) {
    fetch(API_DOWNLOADS + '/' + encodeURIComponent(id), {
      method: 'DELETE',
      headers: authHeader(),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadDownloads(); loadStats(); setStatus('Download deleted.'); })
      .catch(function (err) { setStatus('Error: ' + err.message); });
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadQualities();
    loadDownloads();
    loadStats();

    var form = document.getElementById('vdt-form');
    if (form) {
      form.addEventListener('submit', function (e) {
        e.preventDefault();
        var payload = {
          url: document.getElementById('vdt-url').value.trim(),
          title: document.getElementById('vdt-title-input').value.trim(),
          quality: document.getElementById('vdt-quality').value,
          format: document.getElementById('vdt-format').value,
          status: document.getElementById('vdt-status-sel').value,
          file_size_bytes: parseInt(document.getElementById('vdt-size').value || '0', 10),
          duration_seconds: parseInt(document.getElementById('vdt-duration').value || '1', 10),
        };
        fetch(API_DOWNLOADS, {
          method: 'POST',
          headers: Object.assign({ 'Content-Type': 'application/json' }, authHeader()),
          body: JSON.stringify(payload),
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (data.error) { setStatus('Error: ' + data.error); return; }
            setStatus('Download recorded: ' + data.download.download_id);
            form.reset();
            loadDownloads();
            loadStats();
          })
          .catch(function (err) { setStatus('Error: ' + err.message); });
      });
    }
  });
})();
