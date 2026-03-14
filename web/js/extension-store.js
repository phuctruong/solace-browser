// Diagram: 02-dashboard-login
/* extension-store.js — Extension Store | Task 080 | IIFE pattern | no dangerous eval */
(function () {
  'use strict';

  var API_BASE = '/api/v1/extension-store';
  var currentTab = 'store';
  var categoryFilter = '';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function showMsg(msg) {
    var el = document.getElementById('es-publish-msg');
    el.textContent = msg;
    el.hidden = false;
  }

  function renderCard(ext, showInstall) {
    var html = '<div class="es-card">';
    html += '<div class="es-card-name">' + escHtml(ext.name || ext.ext_id) + '</div>';
    html += '<div class="es-card-meta">v' + escHtml(ext.version) + ' · ' + escHtml(ext.category) + '</div>';
    html += '<div class="es-card-meta">Installs: ' + escHtml(String(ext.install_count || 0)) + '</div>';
    html += '<div class="es-card-rating">Rating: ' + escHtml(ext.rating) + ' / 5.00</div>';
    html += '<div class="es-card-footer">';
    if (showInstall) {
      html += '<button class="es-btn es-btn-primary es-install-btn" data-id="' + escHtml(ext.ext_id) + '">Install</button>';
    } else {
      html += '<button class="es-btn es-btn-danger es-uninstall-btn" data-id="' + escHtml(ext.ext_id) + '">Uninstall</button>';
    }
    html += '</div>';
    html += '</div>';
    return html;
  }

  function loadListings() {
    fetch(API_BASE + '/listings')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('es-listings');
        var listings = data.listings || [];
        if (categoryFilter) {
          listings = listings.filter(function (e) { return e.category === categoryFilter; });
        }
        if (listings.length === 0) {
          container.innerHTML = '<p class="es-loading">No extensions found.</p>';
          return;
        }
        var html = '';
        listings.forEach(function (ext) { html += renderCard(ext, true); });
        container.innerHTML = html;
        container.querySelectorAll('.es-install-btn').forEach(function (btn) {
          btn.addEventListener('click', function () { installExt(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { console.error('listings error', err); });
  }

  function loadInstalled() {
    fetch(API_BASE + '/installed')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var container = document.getElementById('es-installed');
        var installed = data.installed || [];
        if (installed.length === 0) {
          container.innerHTML = '<p class="es-loading">No extensions installed.</p>';
          return;
        }
        var html = '';
        installed.forEach(function (ext) { html += renderCard(ext, false); });
        container.innerHTML = html;
        container.querySelectorAll('.es-uninstall-btn').forEach(function (btn) {
          btn.addEventListener('click', function () { uninstallExt(btn.getAttribute('data-id')); });
        });
      })
      .catch(function (err) { console.error('installed error', err); });
  }

  function installExt(extId) {
    fetch(API_BASE + '/install/' + encodeURIComponent(extId), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadListings(); })
      .catch(function (err) { console.error('install error', err); });
  }

  function uninstallExt(extId) {
    fetch(API_BASE + '/installed/' + encodeURIComponent(extId), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () { loadInstalled(); })
      .catch(function (err) { console.error('uninstall error', err); });
  }

  function publishExt() {
    fetch(API_BASE + '/listings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: document.getElementById('es-pub-name').value.trim(),
        category: document.getElementById('es-pub-category').value,
        version: document.getElementById('es-pub-version').value.trim(),
        manifest: document.getElementById('es-pub-manifest').value.trim(),
        rating: '0.00',
      }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        showMsg('Published: ' + (data.ext_id || ''));
        loadListings();
      })
      .catch(function (err) { console.error('publish error', err); });
  }

  function switchTab(tab) {
    currentTab = tab;
    ['store', 'installed', 'publish'].forEach(function (t) {
      var panel = document.getElementById('es-panel-' + t);
      var btn = document.getElementById('es-tab-' + t);
      if (panel) { panel.hidden = (t !== tab); }
      if (btn) {
        if (t === tab) {
          btn.classList.add('es-tab-active');
        } else {
          btn.classList.remove('es-tab-active');
        }
      }
    });
    if (tab === 'store') { loadListings(); }
    if (tab === 'installed') { loadInstalled(); }
  }

  document.querySelectorAll('.es-tab').forEach(function (btn) {
    btn.addEventListener('click', function () { switchTab(btn.getAttribute('data-tab')); });
  });

  document.getElementById('es-category-filter').addEventListener('change', function () {
    categoryFilter = this.value;
    loadListings();
  });

  document.getElementById('es-publish-btn').addEventListener('click', publishExt);

  loadListings();
}());
