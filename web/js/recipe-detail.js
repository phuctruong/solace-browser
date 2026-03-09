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

  function getRecipeId() {
    var params = new URLSearchParams(window.location.search);
    return params.get("id") || "";
  }

  function loadRecipeDetail() {
    var recipeId = getRecipeId();
    if (!recipeId) {
      document.getElementById("recipe-title").textContent = "No recipe selected.";
      return;
    }
    fetch("/api/v1/recipe-detail/" + encodeURIComponent(recipeId))
      .then(function (r) { return r.json(); })
      .then(function (data) {
        document.getElementById("recipe-title").innerHTML = escHtml(data.name || "");
        document.getElementById("recipe-description").innerHTML = escHtml(data.description || "");
        var steps = data.steps || [];
        var stepsHtml = steps.map(function (s) {
          return "<li>" + escHtml(s) + "</li>";
        }).join("");
        document.getElementById("recipe-steps").innerHTML = "<ol>" + stepsHtml + "</ol>";
      })
      .catch(function () {
        document.getElementById("recipe-title").textContent = "Failed to load recipe.";
      });
  }

  document.getElementById("run-btn").addEventListener("click", function () {
    var recipeId = getRecipeId();
    if (!recipeId) { return; }
    fetch("/api/v1/recipe-detail/" + encodeURIComponent(recipeId) + "/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var banner = document.getElementById("status-banner");
        banner.textContent = "Run started: " + escHtml(data.run_id || "");
        banner.classList.remove("hidden");
      })
      .catch(function () {});
  });

  loadRecipeDetail();
})();
