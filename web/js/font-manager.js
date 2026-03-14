// Diagram: 02-dashboard-login
/* font-manager.js — Font Manager | Task 091 | IIFE + escHtml */
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

  function loadActive() {
    var panel = document.getElementById('fm-active');
    fetch('/api/v1/font-manager/active', {
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var f = d.active_font || {};
        panel.innerHTML = '<strong>Family:</strong> ' + escHtml(f.family || 'system-ui') +
          ' &nbsp; <strong>Weight:</strong> ' + escHtml(f.weight || '400') +
          ' &nbsp; <strong>Size:</strong> ' + escHtml(f.size || '16') + 'px';
      })
      .catch(function () { panel.textContent = 'Failed to load active font.'; });
  }

  function loadFonts() {
    var list = document.getElementById('fm-fonts');
    fetch('/api/v1/font-manager/fonts')
      .then(function (r) { return r.json(); })
      .then(function (d) {
        var items = '';
        (d.builtin || []).forEach(function (name) {
          items += '<div class="fm-font-item"><div>' +
            '<div class="fm-font-name">' + escHtml(name) + '</div>' +
            '<div class="fm-font-meta">Built-in</div></div></div>';
        });
        (d.custom || []).forEach(function (f) {
          items += '<div class="fm-font-item"><div>' +
            '<div class="fm-font-name">' + escHtml(f.family) + '</div>' +
            '<div class="fm-font-meta">Weight: ' + escHtml(f.weight) + ', Size: ' + escHtml(String(f.size)) + 'px</div>' +
            '</div><button class="fm-btn fm-btn-danger" data-id="' + escHtml(f.font_id) + '">Remove</button></div>';
        });
        list.innerHTML = items || '<p class="fm-loading">No custom fonts added.</p>';
        list.querySelectorAll('[data-id]').forEach(function (btn) {
          btn.addEventListener('click', function () { deleteFont(btn.dataset.id); });
        });
      })
      .catch(function () { list.textContent = 'Failed to load fonts.'; });
  }

  function deleteFont(fontId) {
    fetch('/api/v1/font-manager/fonts/' + encodeURIComponent(fontId), {
      method: 'DELETE',
      headers: { 'Authorization': 'Bearer ' + (window._solaceToken || '') },
    })
      .then(function () { loadFonts(); });
  }

  document.getElementById('fm-apply-btn').addEventListener('click', function () {
    var family = document.getElementById('fm-family').value.trim();
    var weight = document.getElementById('fm-weight').value;
    var size = parseInt(document.getElementById('fm-size').value, 10);
    var msg = document.getElementById('fm-apply-msg');
    fetch('/api/v1/font-manager/apply', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + (window._solaceToken || ''),
      },
      body: JSON.stringify({ family: family, weight: weight, size: size }),
    })
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (d.status === 'applied') {
          showMsg(msg, 'Font applied!', false);
          loadActive();
        } else {
          showMsg(msg, d.error || 'Error', true);
        }
      })
      .catch(function () { showMsg(msg, 'Network error', true); });
  });

  loadActive();
  loadFonts();
}());
