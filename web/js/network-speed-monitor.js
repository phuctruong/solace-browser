/* Network Speed Monitor — Task 155 — IIFE, no eval() */
(function () {
  'use strict';

  var BASE = '/api/v1/network-speed';

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function showMsg(text) {
    var el = document.getElementById('nsm-msg');
    if (el) { el.textContent = text; }
  }

  function loadStats() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', BASE + '/stats');
    xhr.onload = function () {
      if (xhr.status !== 200) { return; }
      var d;
      try { d = JSON.parse(xhr.responseText); } catch (e) { return; }
      var el = document.getElementById('nsm-stats');
      if (!el) { return; }
      el.innerHTML = '<div class="nsm-stats-grid">' +
        '<div class="nsm-stat"><div class="nsm-stat-val">' + escHtml(d.total_measurements) + '</div><div class="nsm-stat-lbl">Total</div></div>' +
        '<div class="nsm-stat"><div class="nsm-stat-val">' + escHtml(d.avg_download_mbps) + '</div><div class="nsm-stat-lbl">Avg DL Mbps</div></div>' +
        '<div class="nsm-stat"><div class="nsm-stat-val">' + escHtml(d.avg_upload_mbps) + '</div><div class="nsm-stat-lbl">Avg UL Mbps</div></div>' +
        '<div class="nsm-stat"><div class="nsm-stat-val">' + escHtml(d.avg_latency_ms) + '</div><div class="nsm-stat-lbl">Avg Latency ms</div></div>' +
        '</div>';
    };
    xhr.send();
  }

  function loadMeasurements() {
    var xhr = new XMLHttpRequest();
    xhr.open('GET', BASE + '/measurements');
    xhr.onload = function () {
      if (xhr.status !== 200) { return; }
      var d;
      try { d = JSON.parse(xhr.responseText); } catch (e) { return; }
      var el = document.getElementById('nsm-panel');
      if (!el) { return; }
      if (!d.measurements || d.measurements.length === 0) {
        el.innerHTML = '<p>No measurements recorded yet.</p>';
        return;
      }
      var html = '';
      d.measurements.slice().reverse().forEach(function (m) {
        html += '<div class="nsm-item">' +
          '<div>' +
            '<div class="nsm-item-meta">' +
              '<span class="nsm-badge">' + escHtml(m.connection_type) + '</span> ' +
              'DL: <strong>' + escHtml(m.download_mbps) + '</strong> Mbps &nbsp;' +
              'UL: <strong>' + escHtml(m.upload_mbps) + '</strong> Mbps &nbsp;' +
              'Latency: ' + escHtml(m.latency_ms) + 'ms &nbsp;' +
              'Loss: ' + escHtml(m.packet_loss_pct) + '%' +
            '</div>' +
            '<div class="nsm-item-id">' + escHtml(m.measurement_id) + ' — ' + escHtml(m.measured_at) + '</div>' +
          '</div>' +
          '<div class="nsm-actions">' +
            '<button class="nsm-btn nsm-btn-del" data-id="' + escHtml(m.measurement_id) + '">Delete</button>' +
          '</div>' +
        '</div>';
      });
      el.innerHTML = html;
      el.querySelectorAll('.nsm-btn-del').forEach(function (btn) {
        btn.addEventListener('click', function () {
          var id = btn.getAttribute('data-id');
          deleteMeasurement(id);
        });
      });
    };
    xhr.send();
  }

  function deleteMeasurement(id) {
    var xhr = new XMLHttpRequest();
    xhr.open('DELETE', BASE + '/measurements/' + id);
    xhr.onload = function () {
      if (xhr.status === 200) {
        showMsg('Deleted.');
        loadStats();
        loadMeasurements();
      } else {
        showMsg('Delete failed.');
      }
    };
    xhr.send();
  }

  function init() {
    loadStats();
    loadMeasurements();

    var form = document.getElementById('nsm-form');
    if (!form) { return; }
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var body = JSON.stringify({
        connection_type: document.getElementById('nsm-connection-type').value,
        download_mbps: document.getElementById('nsm-download').value,
        upload_mbps: document.getElementById('nsm-upload').value,
        latency_ms: parseInt(document.getElementById('nsm-latency').value, 10) || 0,
        jitter_ms: parseInt(document.getElementById('nsm-jitter').value, 10) || 0,
        packet_loss_pct: document.getElementById('nsm-packet-loss').value
      });
      var xhr = new XMLHttpRequest();
      xhr.open('POST', BASE + '/measurements');
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.onload = function () {
        if (xhr.status === 201) {
          showMsg('Measurement recorded.');
          loadStats();
          loadMeasurements();
        } else {
          var d;
          try { d = JSON.parse(xhr.responseText); } catch (ex) { d = {}; }
          showMsg('Error: ' + escHtml(d.error || 'unknown'));
        }
      };
      xhr.send(body);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
