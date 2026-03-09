/* Storage Quota Monitor — Task 113 */
(function () {
  'use strict';

  var panel = document.getElementById('sqm-panel');
  var status = document.getElementById('sqm-status');

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function setStatus(msg) { status.textContent = msg; }

  function apiFetch(method, path, body) {
    var opts = { method: method, headers: { 'Content-Type': 'application/json' } };
    if (body) { opts.body = JSON.stringify(body); }
    return fetch(path, opts).then(function (r) { return r.json(); });
  }

  function pctBar(pct) {
    var n = Math.min(100, Math.max(0, parseFloat(pct) || 0));
    return '<div class="sqm-bar-wrap"><div class="sqm-bar" style="width:' + escHtml(n) + '%"></div></div>';
  }

  function renderMeasurements(items) {
    if (!items || items.length === 0) {
      panel.innerHTML = '<div class="sqm-empty">No measurements recorded yet.</div>';
      return;
    }
    var html = '';
    items.forEach(function (m) {
      html += '<div class="sqm-card">'
        + '<span class="sqm-card-id">' + escHtml(m.measurement_id) + '</span>'
        + '<span class="sqm-card-type">' + escHtml(m.storage_type) + '</span>'
        + pctBar(m.pct_used)
        + '<span class="sqm-card-pct">' + escHtml(m.pct_used) + '%</span>'
        + '<button class="sqm-btn sqm-btn-danger" onclick="sqmDelete(\'' + escHtml(m.measurement_id) + '\')">Delete</button>'
        + '</div>';
    });
    panel.innerHTML = html;
  }

  function renderLatest(latest) {
    var keys = Object.keys(latest || {});
    if (keys.length === 0) {
      panel.innerHTML = '<div class="sqm-empty">No measurements yet.</div>';
      return;
    }
    var html = '<div class="sqm-types-grid">';
    keys.forEach(function (k) {
      var m = latest[k];
      html += '<div class="sqm-type-box">'
        + '<strong>' + escHtml(k) + '</strong>'
        + pctBar(m.pct_used)
        + '<div style="margin-top:6px">' + escHtml(m.pct_used) + '% used</div>'
        + '</div>';
    });
    html += '</div>';
    panel.innerHTML = html;
  }

  function renderTypes(types) {
    var html = '<div class="sqm-types-grid">';
    types.forEach(function (t) {
      html += '<div class="sqm-type-box">' + escHtml(t) + '</div>';
    });
    html += '</div>';
    panel.innerHTML = html;
  }

  function renderAddForm(types) {
    var opts = types.map(function (t) {
      return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
    }).join('');
    panel.innerHTML = '<div class="sqm-form">'
      + '<label>Storage Type<select id="sqm-type">' + opts + '</select></label>'
      + '<label>Used Bytes<input id="sqm-used" type="number" min="0" value="0"></label>'
      + '<label>Quota Bytes<input id="sqm-quota" type="number" min="1" value="10485760"></label>'
      + '<label>Site URL<input id="sqm-site" type="url" placeholder="https://example.com"></label>'
      + '<div class="sqm-form-row">'
      + '<button class="sqm-btn sqm-btn-secondary" onclick="sqmLoadList()">Cancel</button>'
      + '<button class="sqm-btn sqm-btn-primary" onclick="sqmSubmit()">Record</button>'
      + '</div></div>';
  }

  window.sqmLoadList = function () {
    setStatus('Loading...');
    apiFetch('GET', '/api/v1/storage-quota/measurements').then(function (d) {
      renderMeasurements(d.measurements || []);
      setStatus(d.total + ' measurements.');
    });
  };

  window.sqmLoadLatest = function () {
    setStatus('Loading latest...');
    apiFetch('GET', '/api/v1/storage-quota/measurements/latest').then(function (d) {
      renderLatest(d.latest || {});
      setStatus('Latest per storage type shown.');
    });
  };

  window.sqmLoadTypes = function () {
    apiFetch('GET', '/api/v1/storage-quota/storage-types').then(function (d) {
      renderTypes(d.storage_types || []);
      setStatus(d.storage_types.length + ' storage types.');
    });
  };

  window.sqmShowAddForm = function () {
    apiFetch('GET', '/api/v1/storage-quota/storage-types').then(function (d) {
      renderAddForm(d.storage_types || []);
      setStatus('');
    });
  };

  window.sqmDelete = function (mid) {
    apiFetch('DELETE', '/api/v1/storage-quota/measurements/' + mid).then(function (d) {
      if (d.status === 'deleted') {
        setStatus('Deleted ' + mid);
        window.sqmLoadList();
      } else {
        setStatus('Error: ' + escHtml(d.error || 'unknown'));
      }
    });
  };

  window.sqmSubmit = function () {
    var stype = document.getElementById('sqm-type').value;
    var used = parseInt(document.getElementById('sqm-used').value, 10);
    var quota = parseInt(document.getElementById('sqm-quota').value, 10);
    var site = document.getElementById('sqm-site').value.trim();
    if (quota <= 0) { setStatus('Quota must be positive.'); return; }
    apiFetch('POST', '/api/v1/storage-quota/measurements', {
      storage_type: stype, used_bytes: used, quota_bytes: quota, site_url: site
    }).then(function (d) {
      if (d.measurement) {
        setStatus('Recorded: ' + escHtml(d.measurement.measurement_id));
        window.sqmLoadList();
      } else {
        setStatus('Error: ' + escHtml(d.error || 'unknown'));
      }
    });
  };

  document.getElementById('btn-sqm-list').addEventListener('click', window.sqmLoadList);
  document.getElementById('btn-sqm-latest').addEventListener('click', window.sqmLoadLatest);
  document.getElementById('btn-sqm-types').addEventListener('click', window.sqmLoadTypes);
  document.getElementById('btn-sqm-add').addEventListener('click', window.sqmShowAddForm);

  window.sqmLoadList();
})();
