/* page-diff-tracker.js — Page Diff Tracker | Task 098 | IIFE + escHtml */
(function () {
  'use strict';

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  const API = '/api/v1/page-diff';

  async function loadSnapshots() {
    const res = await fetch(API + '/snapshots');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('pd-snapshots-list');
    if (!list) return;
    list.innerHTML = data.snapshots.map(s =>
      `<div class="pd-item"><span>${escHtml(s.snapshot_id)}</span> <span>words: ${escHtml(String(s.word_count))}</span></div>`
    ).join('');
  }

  async function compareSnapshots() {
    const idA = document.getElementById('pd-snap-a').value.trim();
    const idB = document.getElementById('pd-snap-b').value.trim();
    if (!idA || !idB) return;
    const res = await fetch(API + '/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ snapshot_id_a: idA, snapshot_id_b: idB }),
    });
    const data = await res.json();
    const result = document.getElementById('pd-compare-result');
    if (!result) return;
    if (res.ok) {
      result.textContent = `Change type: ${escHtml(data.change_type)}, count: ${escHtml(String(data.change_count))}`;
    } else {
      result.textContent = escHtml(data.error || 'Error');
    }
  }

  function init() {
    loadSnapshots();
    const btn = document.getElementById('pd-compare-btn');
    if (btn) btn.addEventListener('click', compareSnapshots);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
