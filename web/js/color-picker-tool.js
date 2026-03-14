// Diagram: 02-dashboard-login
/* color-picker-tool.js — Color Picker Tool | Task 097 | IIFE + escHtml */
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

  const API = '/api/v1/color-picker';

  async function loadColors() {
    const res = await fetch(API + '/colors');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('cp-colors-list');
    if (!list) return;
    list.innerHTML = data.colors.map(c =>
      `<div class="cp-item"><span>${escHtml(c.color_id)}</span> <span>${escHtml(c.format)}</span></div>`
    ).join('');
  }

  async function loadPalettes() {
    const res = await fetch(API + '/palettes');
    if (!res.ok) return;
    const data = await res.json();
    const list = document.getElementById('cp-palettes-list');
    if (!list) return;
    list.innerHTML = data.palettes.map(p =>
      `<div class="cp-item"><span>${escHtml(p.palette_id)}</span> <span>size: ${escHtml(String(p.size))}</span></div>`
    ).join('');
  }

  function init() {
    loadColors();
    loadPalettes();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
}());
