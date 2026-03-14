// Diagram: 02-dashboard-login
/* pdf-viewer-notes.js — PDF Viewer Notes | Task 124 | IIFE pattern | no eval */
(function () {
  'use strict';

  var API_NOTES    = '/api/v1/pdf-notes/notes';
  var API_BY_PDF   = '/api/v1/pdf-notes/notes/by-pdf';
  var API_STATS    = '/api/v1/pdf-notes/stats';

  var NOTE_TYPES = ['text', 'highlight', 'bookmark', 'question', 'summary'];

  function escHtml(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function setStatus(msg) {
    var el = document.getElementById('pdn-status');
    if (el) el.textContent = msg;
  }

  function loadNoteTypes() {
    var sel = document.getElementById('pdn-note-type');
    if (!sel) return;
    sel.innerHTML = NOTE_TYPES.map(function (t) {
      return '<option value="' + escHtml(t) + '">' + escHtml(t) + '</option>';
    }).join('');
  }

  function loadStats() {
    fetch(API_STATS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById('pdn-stats');
        if (el) {
          el.textContent = 'Total notes: ' + (data.total_notes || 0) + ' | PDFs tracked: ' + (data.total_pdfs || 0);
        }
      })
      .catch(function (err) { setStatus('Stats error: ' + err.message); });
  }

  function renderNotes(notes) {
    var el = document.getElementById('pdn-notes-list');
    if (!el) return;
    if (!notes || notes.length === 0) {
      el.innerHTML = '<p class="pdn-empty">No notes found.</p>';
      return;
    }
    el.innerHTML = notes.map(function (n) {
      return '<div class="pdn-row">' +
        '<div class="pdn-row-meta">' +
        '<span class="pdn-type-tag">' + escHtml(n.note_type) + '</span>' +
        '<span>' + escHtml(n.note_id) + '</span>' +
        '<span class="pdn-page">p.' + escHtml(String(n.page_number)) + '</span>' +
        '<span class="pdn-hash">pdf: ' + escHtml((n.pdf_hash || '').slice(0, 16)) + '&hellip;</span>' +
        '<span class="pdn-hash">content: ' + escHtml((n.content_hash || '').slice(0, 16)) + '&hellip;</span>' +
        '</div>' +
        '<button class="pdn-btn pdn-btn-danger" data-id="' + escHtml(n.note_id) + '">Delete</button>' +
        '</div>';
    }).join('');

    el.querySelectorAll('[data-id]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        deleteNote(btn.getAttribute('data-id'));
      });
    });
  }

  function loadNotes() {
    fetch(API_NOTES)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        renderNotes(data.notes || []);
        loadStats();
      })
      .catch(function (err) { setStatus('Error loading notes: ' + err.message); });
  }

  function deleteNote(noteId) {
    fetch(API_NOTES + '/' + encodeURIComponent(noteId), { method: 'DELETE' })
      .then(function (r) { return r.json(); })
      .then(function () {
        setStatus('Deleted: ' + noteId);
        loadNotes();
      })
      .catch(function (err) { setStatus('Delete error: ' + err.message); });
  }

  function initNoteForm() {
    var form = document.getElementById('pdn-note-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var pdfUrl = document.getElementById('pdn-pdf-url').value.trim();
      var noteType = document.getElementById('pdn-note-type').value;
      var content = document.getElementById('pdn-content').value.trim();
      var pageNumber = parseInt(document.getElementById('pdn-page').value, 10) || 1;
      var position = document.getElementById('pdn-position').value.trim();
      fetch(API_NOTES, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          pdf_url: pdfUrl,
          note_type: noteType,
          content: content,
          page_number: pageNumber,
          position: position,
        }),
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data.status === 'saved') {
            setStatus('Saved: ' + data.note.note_id);
            loadNotes();
          } else {
            setStatus('Error: ' + (data.error || 'unknown'));
          }
        })
        .catch(function (err) { setStatus('Error: ' + err.message); });
    });
  }

  function initFilterForm() {
    var form = document.getElementById('pdn-filter-form');
    if (!form) return;
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      var hash = document.getElementById('pdn-filter-hash').value.trim();
      fetch(API_BY_PDF + '?pdf_hash=' + encodeURIComponent(hash))
        .then(function (r) { return r.json(); })
        .then(function (data) {
          renderNotes(data.notes || []);
          setStatus('Found ' + (data.total || 0) + ' note(s) for this PDF.');
        })
        .catch(function (err) { setStatus('Filter error: ' + err.message); });
    });

    var showAll = document.getElementById('pdn-show-all');
    if (showAll) {
      showAll.addEventListener('click', function () { loadNotes(); });
    }
  }

  document.addEventListener('DOMContentLoaded', function () {
    loadNoteTypes();
    loadNotes();
    initNoteForm();
    initFilterForm();
  });
})();
