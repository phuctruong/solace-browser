// Diagram: 02-dashboard-login
(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function showBanner(msg, isError) {
    var b = document.getElementById("status-banner");
    b.textContent = msg;
    b.className = "status-banner" + (isError ? " banner-error" : "");
    b.classList.remove("hidden");
    setTimeout(function () { b.classList.add("hidden"); }, 3000);
  }

  function truncateUrl(url, max) {
    max = max || 60;
    return url.length > max ? url.slice(0, max) + "..." : url;
  }

  function loadTabs() {
    fetch("/api/v1/tabs")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var tabs = data.tabs || [];
        document.getElementById("tab-count").textContent = tabs.length;

        var sessions = {};
        tabs.forEach(function (t) {
          if (t.session_id) { sessions[t.session_id] = true; }
        });
        var sel = document.getElementById("session-filter");
        var current = sel.value;
        sel.innerHTML = "<option value=''>All sessions</option>";
        Object.keys(sessions).forEach(function (sid) {
          var opt = document.createElement("option");
          opt.value = sid;
          opt.textContent = sid;
          if (sid === current) { opt.selected = true; }
          sel.appendChild(opt);
        });

        var filterVal = sel.value;
        if (filterVal) {
          tabs = tabs.filter(function (t) { return t.session_id === filterVal; });
        }

        var list = document.getElementById("tabs-list");
        list.innerHTML = "";
        if (tabs.length === 0) {
          list.innerHTML = "<li class='empty'>No tabs tracked</li>";
          return;
        }
        tabs.forEach(function (tab) {
          var li = document.createElement("li");
          li.className = "tab-item";
          li.innerHTML =
            "<span class='tab-title'>" + escHtml(tab.title || "(no title)") + "</span>" +
            "<span class='tab-url'>" + escHtml(truncateUrl(tab.url || "")) + "</span>" +
            "<span class='tab-status status-" + escHtml(tab.status) + "'>" + escHtml(tab.status) + "</span>" +
            (tab.session_id ? "<span class='tab-session'>" + escHtml(tab.session_id) + "</span>" : "") +
            "<button class='btn btn-sm btn-focus' data-id='" + escHtml(tab.tab_id) + "'>Focus</button>" +
            "<button class='btn btn-sm btn-danger' data-id='" + escHtml(tab.tab_id) + "' data-action='close'>Close</button>";
          list.appendChild(li);
        });

        list.querySelectorAll(".btn-focus").forEach(function (btn) {
          btn.addEventListener("click", function () { focusTab(btn.dataset.id); });
        });
        list.querySelectorAll("[data-action='close']").forEach(function (btn) {
          btn.addEventListener("click", function () {
            if (confirm("Close this tab?")) { closeTab(btn.dataset.id); }
          });
        });
      })
      .catch(function () { showBanner("Failed to load tabs", true); });
  }

  function focusTab(tabId) {
    fetch("/api/v1/tabs/" + encodeURIComponent(tabId) + "/focus", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
      .then(function (r) { return r.json(); })
      .then(function () { showBanner("Tab focused"); loadTabs(); })
      .catch(function () { showBanner("Focus failed", true); });
  }

  function closeTab(tabId) {
    fetch("/api/v1/tabs/" + encodeURIComponent(tabId), { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function () { showBanner("Tab closed"); loadTabs(); })
      .catch(function () { showBanner("Close failed", true); });
  }

  document.getElementById("session-filter").addEventListener("change", loadTabs);

  loadTabs();
})();
