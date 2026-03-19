/* fun-packs.js — extracted from fun-packs.html */
'use strict';

var HUB_PORT = 8888;
var API_BASE = 'http://localhost:' + HUB_PORT;

function tokenValue() {
  return localStorage.getItem('solace_token_sha256') || localStorage.getItem('solace_token') || '';
}

async function apiFetch(path, options) {
  var headers = Object.assign(
    {
      'Content-Type': 'application/json',
      'Authorization': 'Bearer ' + tokenValue(),
    },
    (options && options.headers) || {}
  );
  var response = await fetch(API_BASE + path, Object.assign({}, options || {}, { headers: headers }));
  var payload = await response.json();
  return { status: response.status, data: payload };
}

function setStatus(message, isError) {
  var line = document.getElementById('status-line');
  line.textContent = message;
  line.className = isError ? 'status status--error' : 'status';
}

function renderActivePack(pack) {
  var meta = pack._meta || {};
  document.getElementById('active-pack-name').textContent = meta.name || meta.id || 'Unknown pack';
  document.getElementById('metric-locale').textContent = meta.locale || '\u2014';
  document.getElementById('metric-jokes').textContent = String((pack.jokes || []).length);
  document.getElementById('metric-facts').textContent = String((pack.facts || []).length);
}

function renderPreview(joke, fact) {
  document.getElementById('preview-joke-title').textContent = (joke.emoji || '\uD83D\uDE04') + ' Random Joke';
  document.getElementById('preview-joke-text').textContent = joke.text || 'No joke available.';
  document.getElementById('preview-fact-title').textContent = (fact.emoji || '\uD83D\uDCD8') + ' Random Fact';
  document.getElementById('preview-fact-text').textContent = fact.text || 'No fact available.';
}

function renderPackLibrary(packs, activePackId) {
  var container = document.getElementById('pack-library');
  if (!packs.length) {
    container.innerHTML = '<p class="empty">No installed packs found.</p>';
    return;
  }
  container.innerHTML = packs.map(function (pack) {
    var activeBadge = pack.id === activePackId ? '<span class="badge badge--active">Active</span>' : '<span class="badge">Installed</span>';
    var buttonLabel = pack.id === activePackId ? 'Active Now' : 'Activate';
    var buttonClass = pack.id === activePackId ? 'button button--ghost' : 'button button--accent';
    return '<article class="pack-card">' +
      '<div class="pack-card__head">' +
        '<div>' +
          '<h3>' + pack.name + '</h3>' +
          '<p>' + pack.locale.toUpperCase() + ' \u00B7 v' + pack.version + '</p>' +
        '</div>' +
        activeBadge +
      '</div>' +
      '<div class="pack-card__meta">' +
        '<span class="tag">' + pack.jokes_count + ' jokes</span>' +
        '<span class="tag">' + pack.facts_count + ' facts</span>' +
        '<span class="tag">' + pack.greetings_count + ' greetings</span>' +
      '</div>' +
      '<p>Warm, family-friendly content bundle for the Solace Hub delight layer.</p>' +
      '<p>' +
        '<button class="' + buttonClass + '" type="button" data-pack-id="' + pack.id + '">' + buttonLabel + '</button>' +
      '</p>' +
    '</article>';
  }).join('');

  Array.from(container.querySelectorAll('[data-pack-id]')).forEach(function (button) {
    button.addEventListener('click', async function () {
      var packId = button.getAttribute('data-pack-id');
      await activatePack(packId);
    });
  });
}

async function loadGreeting(timeOfDay, targetId) {
  var result = await apiFetch('/api/v1/fun-packs/greeting?time_of_day=' + encodeURIComponent(timeOfDay));
  if (result.status !== 200) {
    document.getElementById(targetId).textContent = 'Greeting unavailable right now.';
    return;
  }
  var greeting = result.data.greeting || {};
  document.getElementById(targetId).textContent = (greeting.emoji || '\u2728') + ' ' + (greeting.text || 'Greeting unavailable right now.');
}

async function refreshPreview() {
  var jokeResponse = await apiFetch('/api/v1/fun-packs/random-joke');
  var factResponse = await apiFetch('/api/v1/fun-packs/random-fact');
  if (jokeResponse.status !== 200 || factResponse.status !== 200) {
    setStatus('Preview content is unavailable right now.', true);
    return;
  }
  renderPreview(jokeResponse.data.joke || {}, factResponse.data.fact || {});
}

async function activatePack(packId) {
  var result = await apiFetch('/api/v1/fun-packs/' + encodeURIComponent(packId) + '/activate', {
    method: 'POST',
    body: JSON.stringify({})
  });
  if (result.status !== 200) {
    setStatus(result.data.error || 'Could not activate that pack.', true);
    return;
  }
  setStatus('Activated pack: ' + result.data.pack_id, false);
  await loadPage();
}

async function loadPage() {
  if (!tokenValue()) {
    setStatus('Bearer token missing. Save your Solace Hub token in localStorage first.', true);
    return;
  }

  var listResponse = await apiFetch('/api/v1/fun-packs');
  var activeResponse = await apiFetch('/api/v1/fun-packs/active');

  if (listResponse.status !== 200 || activeResponse.status !== 200) {
    var errorMessage = activeResponse.data.error || listResponse.data.error || 'Fun pack API unavailable.';
    setStatus(errorMessage, true);
    return;
  }

  renderActivePack(activeResponse.data.pack || {});
  renderPackLibrary(listResponse.data.packs || [], listResponse.data.active_pack_id || '');
  setStatus('Loaded ' + String(listResponse.data.count || 0) + ' installed pack(s).', false);

  await Promise.all([
    refreshPreview(),
    loadGreeting('morning', 'greeting-morning'),
    loadGreeting('afternoon', 'greeting-afternoon'),
    loadGreeting('evening', 'greeting-evening')
  ]);
}

document.getElementById('preview-btn').addEventListener('click', function () {
  refreshPreview();
});

loadPage();
