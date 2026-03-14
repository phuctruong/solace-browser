// Diagram: 02-dashboard-login
(function () {
  "use strict";

  var activeTag = "";

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

  function loadTags() {
    fetch("/api/v1/bookmarks/tags")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var chips = document.getElementById("tag-chips");
        chips.innerHTML = "";
        var allChip = document.createElement("button");
        allChip.className = "tag-chip" + (activeTag === "" ? " active" : "");
        allChip.textContent = "All";
        allChip.addEventListener("click", function () { activeTag = ""; loadBookmarks(); loadTags(); });
        chips.appendChild(allChip);
        (data.tags || []).forEach(function (tag) {
          var chip = document.createElement("button");
          chip.className = "tag-chip" + (activeTag === tag ? " active" : "");
          chip.textContent = escHtml(tag);
          chip.addEventListener("click", function () { activeTag = tag; loadBookmarks(); loadTags(); });
          chips.appendChild(chip);
        });
      })
      .catch(function () {});
  }

  function loadBookmarks(query) {
    var url = "/api/v1/bookmarks";
    if (query) {
      url = "/api/v1/bookmarks/search?q=" + encodeURIComponent(query);
    } else if (activeTag) {
      url = "/api/v1/bookmarks?tag=" + encodeURIComponent(activeTag);
    }
    fetch(url)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("bm-list");
        list.innerHTML = "";
        var bms = data.bookmarks || [];
        if (bms.length === 0) {
          list.innerHTML = "<li class='empty'>No bookmarks found</li>";
          return;
        }
        bms.forEach(function (bm) {
          var li = document.createElement("li");
          li.className = "bm-item";
          var tags = (bm.tags || []).map(function (t) {
            return "<span class='bm-tag'>" + escHtml(t) + "</span>";
          }).join("");
          li.innerHTML =
            "<span class='bm-favicon'>&#128278;</span>" +
            "<div class='bm-info'>" +
              "<a href='" + escHtml(bm.url) + "' class='bm-title' target='_blank' rel='noreferrer'>" + escHtml(bm.title || bm.url) + "</a>" +
              "<span class='bm-url'>" + escHtml(bm.url) + "</span>" +
              "<div class='bm-tags'>" + tags + "</div>" +
            "</div>" +
            "<button class='btn btn-sm btn-danger' data-id='" + escHtml(bm.bookmark_id) + "'>Delete</button>";
          list.appendChild(li);
        });
        list.querySelectorAll(".btn-danger").forEach(function (btn) {
          btn.addEventListener("click", function () {
            deleteBookmark(btn.dataset.id);
          });
        });
      })
      .catch(function () { showBanner("Failed to load bookmarks", true); });
  }

  function deleteBookmark(bmId) {
    fetch("/api/v1/bookmarks/" + encodeURIComponent(bmId), { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function () { showBanner("Bookmark deleted"); loadBookmarks(); loadTags(); })
      .catch(function () { showBanner("Delete failed", true); });
  }

  document.getElementById("bm-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var url = document.getElementById("bm-url").value.trim();
    var title = document.getElementById("bm-title").value.trim();
    var tagsRaw = document.getElementById("bm-tags").value.trim();
    var tags = tagsRaw ? tagsRaw.split(",").map(function (t) { return t.trim(); }).filter(Boolean) : [];
    fetch("/api/v1/bookmarks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: url, title: title, tags: tags }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.status === "added") {
          showBanner("Bookmark added");
          document.getElementById("bm-form").reset();
          loadBookmarks();
          loadTags();
        } else {
          showBanner(data.error || "Failed", true);
        }
      })
      .catch(function () { showBanner("Request failed", true); });
  });

  var searchTimer;
  document.getElementById("bm-search").addEventListener("input", function () {
    var q = this.value.trim();
    clearTimeout(searchTimer);
    searchTimer = setTimeout(function () { loadBookmarks(q || null); }, 300);
  });

  loadBookmarks();
  loadTags();
})();
