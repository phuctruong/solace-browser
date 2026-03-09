(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  function apiGet(path) {
    return fetch(path).then(function (r) { return r.json(); });
  }

  function apiPost(path, body) {
    return fetch(path, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    }).then(function (r) { return r.json(); });
  }

  function apiDelete(path) {
    return fetch(path, { method: 'DELETE' }).then(function (r) { return r.json(); });
  }

  function loadJobs() {
    apiGet('/api/v1/scheduler/jobs').then(function (data) {
      var list = document.getElementById('rs-jobs-list');
      if (!list) return;
      var jobs = data.jobs || [];
      if (jobs.length === 0) {
        list.innerHTML = '<p class="rs-empty">No scheduled jobs yet.</p>';
        return;
      }
      list.innerHTML = jobs.map(function (job) {
        return '<div class="rs-job-row">' +
          '<div class="rs-job-info">' +
          '<div class="rs-job-name">' + escHtml(job.name) + '</div>' +
          '<div class="rs-job-meta">' + escHtml(job.recipe_id) + ' &bull; ' + escHtml(job.cron_preset) + ' &bull; ' + (job.enabled ? 'enabled' : 'disabled') + '</div>' +
          '</div>' +
          '<div class="rs-job-actions">' +
          '<button class="rs-btn rs-btn-secondary" onclick="window._rsRunNow(\'' + escHtml(job.job_id) + '\')">Run Now</button>' +
          '<button class="rs-btn" onclick="window._rsHistory(\'' + escHtml(job.job_id) + '\')">History</button>' +
          '<button class="rs-btn rs-btn-danger" onclick="window._rsDelete(\'' + escHtml(job.job_id) + '\')">Delete</button>' +
          '</div>' +
          '</div>';
      }).join('');
    });
  }

  window._rsDelete = function (jobId) {
    apiDelete('/api/v1/scheduler/jobs/' + jobId).then(function () { loadJobs(); });
  };

  window._rsRunNow = function (jobId) {
    apiPost('/api/v1/scheduler/jobs/' + jobId + '/run-now', {}).then(function (data) {
      if (data.run_id) {
        window._rsHistory(jobId);
      }
    });
  };

  window._rsHistory = function (jobId) {
    apiGet('/api/v1/scheduler/jobs/' + jobId + '/history').then(function (data) {
      var panel = document.getElementById('rs-history-panel');
      if (!panel) return;
      var runs = data.history || [];
      if (runs.length === 0) {
        panel.innerHTML = '<p class="rs-empty">No runs yet for this job.</p>';
        return;
      }
      panel.innerHTML = '<strong>Job: ' + escHtml(jobId) + '</strong>' +
        runs.map(function (run) {
          return '<div class="rs-history-row">' +
            '<span class="rs-badge">' + escHtml(run.status) + '</span>' +
            '<span>' + escHtml(run.started_at) + '</span>' +
            '<span>$' + escHtml(run.cost_usd) + '</span>' +
            '</div>';
        }).join('');
    });
  };

  var addForm = document.getElementById('rs-add-form');
  if (addForm) {
    addForm.addEventListener('submit', function (e) {
      e.preventDefault();
      var name = document.getElementById('rs-name').value.trim();
      var recipe = document.getElementById('rs-recipe').value;
      var cron = document.getElementById('rs-cron').value;
      var status = document.getElementById('rs-add-status');
      apiPost('/api/v1/scheduler/jobs', { name: name, recipe_id: recipe, cron_preset: cron }).then(function (data) {
        if (status) {
          status.textContent = data.job_id ? 'Created: ' + data.job_id : 'Error: ' + (data.error || 'unknown');
        }
        loadJobs();
      });
    });
  }

  loadJobs();
}());
