// Diagram: 02-dashboard-login
(function () {
  'use strict';

  var API_FRAMES = '/api/v1/iframe-tracker/frames';
  var API_STATS = '/api/v1/iframe-tracker/stats';
  var API_TYPES = '/api/v1/iframe-tracker/frame-types';
  var sandboxAttrs = ['allow-scripts', 'allow-same-origin', 'allow-forms', 'allow-popups', 'allow-top-navigation'];

  function escHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(message) {
    var el = document.getElementById('ifr-status');
    if (el) el.textContent = message;
  }

  function renderSandboxOptions() {
    var host = document.getElementById('ifr-sandbox-list');
    if (!host) return;
    host.innerHTML = sandboxAttrs.map(function (attr) {
      return '<label class="ifr-check"><input type="checkbox" value="' + escHtml(attr) + '"> ' + escHtml(attr) + '</label>';
    }).join('');
  }

  function loadTypes() {
    fetch(API_TYPES)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var select = document.getElementById('ifr-frame-type');
        if (!select) return;
        select.innerHTML = (data.frame_types || []).map(function (item) {
          return '<option value="' + escHtml(item) + '">' + escHtml(item) + '</option>';
        }).join('');
      })
      .catch(function (error) { setStatus('Type load failed: ' + error.message); });
  }

  function loadStats() {
    fetch(API_STATS)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var el = document.getElementById('ifr-stats');
        if (!el) return;
        el.innerHTML = [
          ['Total Frames', data.total_frames || 0],
          ['Cross Origin', data.cross_origin_count || 0],
          ['Cross Origin Rate', data.cross_origin_rate || '0.00'],
          ['Avg Load (ms)', data.avg_load_ms || '0.00']
        ].map(function (entry) {
          return '<div class="ifr-stat"><span>' + escHtml(entry[0]) + '</span><strong>' + escHtml(entry[1]) + '</strong></div>';
        }).join('');
      })
      .catch(function (error) { setStatus('Stats load failed: ' + error.message); });
  }

  function loadFrames() {
    fetch(API_FRAMES)
      .then(function (response) { return response.json(); })
      .then(function (data) {
        var el = document.getElementById('ifr-frames');
        var frames = data.frames || [];
        if (!el) return;
        if (!frames.length) {
          el.innerHTML = '<div class="ifr-row"><div class="ifr-meta">No frames recorded.</div></div>';
          return;
        }
        el.innerHTML = frames.map(function (frame) {
          return '<article class="ifr-row">' +
            '<div class="ifr-row-head"><div><div class="ifr-tag">' + escHtml(frame.frame_type) + '</div><div class="ifr-meta">' + escHtml(frame.frame_id) + '</div></div>' +
            '<button class="ifr-delete" data-id="' + escHtml(frame.frame_id) + '">Delete</button></div>' +
            '<div class="ifr-meta">page ' + escHtml(String(frame.page_url_hash || '').slice(0, 16)) + '…</div>' +
            '<div class="ifr-meta">src ' + escHtml(String(frame.src_url_hash || '').slice(0, 16)) + '…</div>' +
            '<div class="ifr-meta">sandbox: ' + escHtml((frame.sandbox_attrs || []).join(', ') || 'none') + '</div>' +
          '</article>';
        }).join('');
        el.querySelectorAll('[data-id]').forEach(function (button) {
          button.addEventListener('click', function () {
            deleteFrame(button.getAttribute('data-id'));
          });
        });
      })
      .catch(function (error) { setStatus('Frame load failed: ' + error.message); });
  }

  function deleteFrame(frameId) {
    fetch(API_FRAMES + '/' + encodeURIComponent(frameId), { method: 'DELETE' })
      .then(function (response) { return response.json(); })
      .then(function () {
        setStatus('Deleted ' + frameId);
        loadFrames();
        loadStats();
      })
      .catch(function (error) { setStatus('Delete failed: ' + error.message); });
  }

  function bindForm() {
    var form = document.getElementById('ifr-form');
    if (!form) return;
    form.addEventListener('submit', function (event) {
      event.preventDefault();
      var sandbox = Array.prototype.slice.call(document.querySelectorAll('#ifr-sandbox-list input:checked')).map(function (input) {
        return input.value;
      });
      fetch(API_FRAMES, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          frame_type: document.getElementById('ifr-frame-type').value,
          page_url: document.getElementById('ifr-page-url').value.trim(),
          src_url: document.getElementById('ifr-src-url').value.trim(),
          is_cross_origin: document.getElementById('ifr-cross-origin').checked,
          sandbox_attrs: sandbox,
          load_time_ms: Number(document.getElementById('ifr-load-time').value || 0)
        })
      })
        .then(function (response) { return response.json(); })
        .then(function (data) {
          if (data.frame_id) {
            form.reset();
            renderSandboxOptions();
            setStatus('Recorded ' + data.frame_id);
            loadFrames();
            loadStats();
            return;
          }
          setStatus(data.error || 'Unable to record frame');
        })
        .catch(function (error) { setStatus('Save failed: ' + error.message); });
    });
  }

  document.addEventListener('DOMContentLoaded', function () {
    renderSandboxOptions();
    loadTypes();
    loadStats();
    loadFrames();
    bindForm();
  });
})();
