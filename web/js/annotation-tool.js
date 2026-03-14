// Diagram: 02-dashboard-login
/* annotation-tool.js — Annotation Tool | Task 093 | IIFE + escHtml */
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showMsg(el, text, isError) {
    el.textContent = text;
    el.style.color = isError ? 'var(--hub-danger)' : 'var(--hub-success)';
    el.hidden = false;
    setTimeout(function () { el.hidden = true; }, 4000);
  }

  function sha256Hex(str) {
    var encoder = new TextEncoder();
    var data = encoder.encode(str);
    return crypto.subtle.digest('SHA-256', data).then(function (buf) {
      return Array.from(new Uint8Array(buf)).map(function (b) {
        return b.toString(16).padStart(2, '0');
      }).join('');
    });
  }

  function loadAnnotations() {
    var list = document.getElementById('at-list');
    fetch('/api/v1/annotations', {
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = '';
        (d.annotations || []).forEach(function (a) {
          items += '<div class="at-item"><div>' +
            '<div class="at-item-type">' +
            '<span class="at-color-dot"></span>' +
            escHtml(a.annotation_type) + ' (' + escHtml(a.color) + ')' +
            '</div>' +
            '<div class="at-item-meta">' + escHtml(a.created_at) + '</div>' +
            '</div>' +
            '<button class="at-btn at-btn-danger" data-id="' + escHtml(a.annotation_id) + '">Delete</button>' +
            '</div>';
        });
        list.innerHTML = items || '<p class="at-loading">No annotations yet.</p>';
        list.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteAnnotation(btn.dataset.id); });
        });
      })
      .catch(function () { list.textContent = 'Failed to load annotations.'; });
  }

  function deleteAnnotation(annotationId) {
    fetch('/api/v1/annotations/' + encodeURIComponent(annotationId), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function () { loadAnnotations(); });
  }

  document.getElementById('at-create-btn').addEventListener('click', function () {
    var annotationType = document.getElementById('at-type').value;
    var color = document.getElementById('at-color').value;
    var pageUrl = document.getElementById('at-page-url').value.trim() || 'unknown';
    var text = document.getElementById('at-text').value.trim() || 'unknown';
    var selector = document.getElementById('at-selector').value.trim() || 'unknown';
    var msg = document.getElementById('at-create-msg');
    Promise.all([
      sha256Hex(pageUrl),
      sha256Hex(text),
      sha256Hex(selector),
    ]).then(function (hashes) {
      return fetch('/api/v1/annotations', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': 'Bearer ' + (window._solaceToken || ''),
        },
        body: JSON.stringify({
          annotation_type: annotationType,
          color: color,
          page_hash: hashes[0],
          text_hash: hashes[1],
          selector_hash: hashes[2],
        }),
      });
    }).then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status === 'created') {
          showMsg(msg, 'Annotation created!', false);
          loadAnnotations();
        } else {
          showMsg(msg, d.error || 'Error', true);
        }
      })
      .catch(function () { showMsg(msg, 'Network error', true); });
  });

  loadAnnotations();
}());
