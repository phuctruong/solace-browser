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

  function loadRules() {
    fetch("/api/v1/budget/alert-rules")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("rules-list");
        list.innerHTML = "";
        (data.rules || []).forEach(function (rule) {
          var li = document.createElement("li");
          li.className = "rule-item";
          li.innerHTML =
            "<span class='rule-metric'>" + escHtml(rule.metric) + "</span>" +
            " &gt; <span class='rule-threshold'>" + escHtml(rule.threshold) + "</span>" +
            " → <span class='rule-action'>" + escHtml(rule.action) + "</span>" +
            " <button class='btn btn-danger btn-sm' data-id='" + escHtml(rule.alert_id) + "'>Delete</button>";
          list.appendChild(li);
        });
        list.querySelectorAll("[data-id]").forEach(function (btn) {
          btn.addEventListener("click", function () {
            deleteRule(btn.dataset.id);
          });
        });
      })
      .catch(function () { showBanner("Failed to load rules", true); });
  }

  function loadTriggered() {
    fetch("/api/v1/budget/alert-rules/triggered")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var list = document.getElementById("triggered-list");
        list.innerHTML = "";
        if (!data.triggered || data.triggered.length === 0) {
          list.innerHTML = "<li class='empty'>No triggered alerts</li>";
          return;
        }
        data.triggered.forEach(function (alert) {
          var li = document.createElement("li");
          li.className = "triggered-item";
          li.innerHTML =
            "<span>" + escHtml(alert.alert_id) + "</span>" +
            (alert.acknowledged ? " <span class='acked'>(Acknowledged)</span>" : "") +
            " <button class='btn btn-sm btn-ack' data-id='" + escHtml(alert.alert_id) + "'>Acknowledge</button>";
          list.appendChild(li);
        });
        list.querySelectorAll(".btn-ack").forEach(function (btn) {
          btn.addEventListener("click", function () { acknowledgeAlert(btn.dataset.id); });
        });
      })
      .catch(function () {});
  }

  function deleteRule(alertId) {
    fetch("/api/v1/budget/alert-rules/" + encodeURIComponent(alertId), { method: "DELETE" })
      .then(function (r) { return r.json(); })
      .then(function () {
        showBanner("Rule deleted");
        loadRules();
      })
      .catch(function () { showBanner("Delete failed", true); });
  }

  function acknowledgeAlert(alertId) {
    fetch("/api/v1/budget/alert-rules/" + encodeURIComponent(alertId) + "/acknowledge", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: "{}",
    })
      .then(function (r) { return r.json(); })
      .then(function () {
        showBanner("Acknowledged");
        loadTriggered();
      })
      .catch(function () { showBanner("Acknowledge failed", true); });
  }

  document.getElementById("alert-form").addEventListener("submit", function (e) {
    e.preventDefault();
    var metric = document.getElementById("alert-metric").value;
    var threshold = document.getElementById("alert-threshold").value;
    var action = document.getElementById("alert-action").value;
    fetch("/api/v1/budget/alert-rules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ metric: metric, threshold: threshold, action: action }),
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.status === "created") {
          showBanner("Alert rule created");
          document.getElementById("alert-form").reset();
          loadRules();
        } else {
          showBanner(data.error || "Failed", true);
        }
      })
      .catch(function () { showBanner("Request failed", true); });
  });

  loadRules();
  loadTriggered();
})();
