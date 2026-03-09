'use strict';

const FA_API = '/api/v1/autofill';

function getToken() {
  return localStorage.getItem('solace_token') || '';
}

function authHeaders() {
  return { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + getToken() };
}

function setStatus(msg) {
  const el = document.getElementById('fa-status');
  if (el) el.textContent = msg;
}

async function loadProfiles() {
  const res = await fetch(FA_API + '/profiles');
  const data = await res.json();
  const list = document.getElementById('fa-list');
  if (!list) return;
  if (!data.profiles || data.profiles.length === 0) {
    list.innerHTML = '<p class="fa-empty">No autofill profiles yet.</p>';
    return;
  }
  list.innerHTML = data.profiles.map(p => `
    <div class="fa-profile" data-id="${p.profile_id}">
      <span class="fa-profile-name">${p.name}</span>
      <span class="fa-profile-fields">${Object.keys(p.fields).length} fields</span>
      <button class="fa-btn fa-btn-apply" data-id="${p.profile_id}">Apply</button>
      <button class="fa-btn fa-btn-danger fa-btn-delete" data-id="${p.profile_id}">Delete</button>
    </div>
  `).join('');

  list.querySelectorAll('.fa-btn-apply').forEach(btn => {
    btn.addEventListener('click', () => applyProfile(btn.dataset.id));
  });
  list.querySelectorAll('.fa-btn-delete').forEach(btn => {
    btn.addEventListener('click', () => deleteProfile(btn.dataset.id));
  });
}

async function applyProfile(profileId) {
  const domain = prompt('Domain to fill (e.g. example.com):') || '';
  const res = await fetch(FA_API + '/profiles/' + profileId + '/apply', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ domain }),
  });
  const data = await res.json();
  if (data.status === 'applied') {
    setStatus('Applied profile. Fields: ' + data.fields_count);
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
}

async function deleteProfile(profileId) {
  if (!confirm('Delete this autofill profile?')) return;
  const res = await fetch(FA_API + '/profiles/' + profileId, {
    method: 'DELETE',
    headers: authHeaders(),
  });
  const data = await res.json();
  if (data.status === 'deleted') {
    setStatus('Profile deleted.');
    await loadProfiles();
  }
}

async function loadHistory() {
  const res = await fetch(FA_API + '/history');
  const data = await res.json();
  const panel = document.getElementById('fa-history-panel');
  if (!panel) return;
  panel.hidden = false;
  if (!data.history || data.history.length === 0) {
    panel.innerHTML = '<p class="fa-empty">No apply history yet.</p>';
    return;
  }
  panel.innerHTML = '<h3>Apply History</h3>' + data.history.map(h =>
    `<div class="fa-history-entry">${h.profile_name} — ${h.applied_at} (${h.fields_count} fields)</div>`
  ).join('');
}

document.getElementById('btn-fa-add').addEventListener('click', async () => {
  const name = prompt('Profile name:');
  if (!name) return;
  const email = prompt('Email (optional):') || undefined;
  const firstName = prompt('First name (optional):') || undefined;
  const fields = {};
  if (email) fields.email = email;
  if (firstName) fields.first_name = firstName;

  const res = await fetch(FA_API + '/profiles', {
    method: 'POST',
    headers: authHeaders(),
    body: JSON.stringify({ name, fields }),
  });
  const data = await res.json();
  if (data.status === 'added') {
    setStatus('Profile added: ' + data.profile_id);
    await loadProfiles();
  } else {
    setStatus('Error: ' + (data.error || 'unknown'));
  }
});

document.getElementById('btn-fa-history').addEventListener('click', loadHistory);

loadProfiles();
