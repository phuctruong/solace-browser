// Diagram: 02-dashboard-login
"use strict";
/* Media Downloader — Task 064 */
(function () {
  function escHtml(s) {
    return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }

  var MD = {
    async showQueue() {
      var r = await fetch("/api/v1/media/queue");
      var data = await r.json();
      var el = document.getElementById("md-content");
      if (!el) return;
      if (!data.queue || data.queue.length === 0) {
        el.textContent = "No items in queue.";
        return;
      }
      el.innerHTML = data.queue.map(function (item) {
        return '<div class="md-item">' +
          '<span class="md-item-name">' + escHtml(item.filename || item.url_hash.slice(0, 20)) + "</span>" +
          '<span class="md-item-type">' + escHtml(item.media_type) + "</span>" +
          '<span class="md-item-status">' + escHtml(item.status) + "</span>" +
          "</div>";
      }).join("");
    },
    async showStats() {
      var r = await fetch("/api/v1/media/stats");
      var data = await r.json();
      var el = document.getElementById("md-status");
      if (el) el.textContent = "Total: " + data.total + " | Queued: " + data.queued + " | Completed: " + data.completed + " | Failed: " + data.failed;
    },
    async showTypes() {
      var r = await fetch("/api/v1/media/types");
      var data = await r.json();
      var el = document.getElementById("md-status");
      if (el) el.textContent = "Types: " + (data.types || []).join(", ");
    },
    init() {
      var btnQueue = document.getElementById("btn-md-queue");
      if (btnQueue) btnQueue.addEventListener("click", function () { MD.showQueue(); });
      var btnStats = document.getElementById("btn-md-stats");
      if (btnStats) btnStats.addEventListener("click", function () { MD.showStats(); });
      var btnTypes = document.getElementById("btn-md-types");
      if (btnTypes) btnTypes.addEventListener("click", function () { MD.showTypes(); });
      MD.showQueue();
    },
  };

  document.addEventListener("DOMContentLoaded", function () { MD.init(); });
})();
