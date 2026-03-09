"use strict";
/* Voice Notes — Task 067 */
(function () {
  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  var VN = {
    async showNotes() {
      var r = await fetch("/api/v1/voice-notes");
      var data = await r.json();
      var el = document.getElementById("vn-content");
      if (!el) return;
      if (!data.notes || data.notes.length === 0) {
        el.textContent = "No voice notes yet.";
        return;
      }
      el.innerHTML = data.notes.map(function (note) {
        return '<div class="vn-note">' +
          '<span class="vn-note-title">' + escHtml(note.title || note.note_id) + "</span>" +
          '<span class="vn-note-format">' + escHtml(note.format) + "</span>" +
          '<span class="vn-note-dur">' + escHtml(note.duration_seconds) + "s</span>" +
          '<span class="vn-note-status">' + escHtml(note.status) + "</span>" +
          "</div>";
      }).join("");
      var statusEl = document.getElementById("vn-status");
      if (statusEl) statusEl.textContent = "Total notes: " + data.total;
    },
    async showStats() {
      var r = await fetch("/api/v1/voice-notes/stats");
      var data = await r.json();
      var el = document.getElementById("vn-status");
      if (el) {
        el.textContent = "Total: " + data.total +
          " | Recorded: " + data.recorded +
          " | Transcribed: " + data.transcribed +
          " | Duration: " + data.total_duration_seconds + "s";
      }
    },
    init() {
      var btnList = document.getElementById("btn-vn-list");
      if (btnList) btnList.addEventListener("click", function () { VN.showNotes(); });
      var btnStats = document.getElementById("btn-vn-stats");
      if (btnStats) btnStats.addEventListener("click", function () { VN.showStats(); });
      VN.showNotes();
    },
  };

  document.addEventListener("DOMContentLoaded", function () { VN.init(); });
})();
