(function () {
  "use strict";

  function escHtml(str) {
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  var API_COMMANDS = "/api/v1/commands";
  var API_EXECUTE = "/api/v1/commands/execute";
  var API_HISTORY = "/api/v1/commands/history";

  var _allCommands = [];
  var _selectedIdx = 0;

  function buildItem(cmd) {
    var li = document.createElement("li");
    li.className = "cp-item";
    li.setAttribute("role", "option");
    li.setAttribute("data-cmd-id", cmd.cmd_id);
    var shortcutHtml = cmd.shortcut
      ? '<span class="cp-item-shortcut">' + escHtml(cmd.shortcut) + "</span>"
      : "";
    li.innerHTML =
      '<span class="cp-item-name">' + escHtml(cmd.name) + "</span>" +
      '<span class="cp-item-category">' + escHtml(cmd.category) + "</span>" +
      shortcutHtml;
    li.addEventListener("click", function () { executeCommand(cmd.cmd_id); });
    return li;
  }

  function renderList(commands, listId) {
    var ul = document.getElementById(listId);
    if (!ul) { return; }
    ul.innerHTML = "";
    commands.forEach(function (cmd) { ul.appendChild(buildItem(cmd)); });
    _selectedIdx = 0;
    highlightSelected(listId);
  }

  function highlightSelected(listId) {
    var ul = document.getElementById(listId);
    if (!ul) { return; }
    var items = ul.querySelectorAll(".cp-item");
    items.forEach(function (it, i) {
      if (i === _selectedIdx) { it.classList.add("cp-active"); }
      else { it.classList.remove("cp-active"); }
    });
  }

  function filterCommands(q) {
    if (!q) { return _allCommands; }
    var lq = q.toLowerCase();
    return _allCommands.filter(function (c) {
      return c.name.toLowerCase().indexOf(lq) !== -1 ||
             c.category.toLowerCase().indexOf(lq) !== -1;
    });
  }

  function executeCommand(cmdId) {
    fetch(API_EXECUTE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cmd_id: cmdId }),
    })
      .then(function (r) { return r.json(); })
      .then(function () { loadRecent(); })
      .catch(function () {});
  }

  function loadAll() {
    fetch(API_COMMANDS)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        _allCommands = data.commands || [];
        renderList(_allCommands, "cp-list");
      })
      .catch(function () {});
  }

  function loadRecent() {
    fetch(API_HISTORY)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var recent = (data.history || []).slice(0, 5);
        renderList(recent, "cp-recent-list");
      })
      .catch(function () {});
  }

  document.addEventListener("DOMContentLoaded", function () {
    loadAll();
    loadRecent();

    var input = document.getElementById("cp-input");
    if (input) {
      input.focus();
      input.addEventListener("input", function () {
        var filtered = filterCommands(input.value.trim());
        _selectedIdx = 0;
        renderList(filtered, "cp-list");
      });

      input.addEventListener("keydown", function (e) {
        var ul = document.getElementById("cp-list");
        var items = ul ? ul.querySelectorAll(".cp-item") : [];
        if (e.key === "Escape") {
          var bd = document.getElementById("cp-backdrop");
          if (bd) { bd.style.display = "none"; }
        } else if (e.key === "ArrowDown") {
          e.preventDefault();
          _selectedIdx = Math.min(_selectedIdx + 1, items.length - 1);
          highlightSelected("cp-list");
        } else if (e.key === "ArrowUp") {
          e.preventDefault();
          _selectedIdx = Math.max(_selectedIdx - 1, 0);
          highlightSelected("cp-list");
        } else if (e.key === "Enter") {
          if (items[_selectedIdx]) {
            var id = items[_selectedIdx].getAttribute("data-cmd-id");
            if (id) { executeCommand(id); }
          }
        }
      });
    }

    var backdrop = document.getElementById("cp-backdrop");
    if (backdrop) {
      backdrop.addEventListener("click", function (e) {
        if (e.target === backdrop) { backdrop.style.display = "none"; }
      });
    }

    document.addEventListener("keydown", function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === "k") {
        e.preventDefault();
        var bd = document.getElementById("cp-backdrop");
        if (bd) {
          bd.style.display = "flex";
          var inp = document.getElementById("cp-input");
          if (inp) { inp.focus(); }
        }
      }
    });
  });
})();
