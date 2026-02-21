#!/usr/bin/env python3
"""
Solace Browser UI Server
Port: 9223
Python stdlib only -- no pip dependencies
"""

import json
import os
import pathlib
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BASE_DIR = pathlib.Path(__file__).parent
LOGS_DIR = BASE_DIR / "logs"
ARTIFACTS_DIR = BASE_DIR / "artifacts"
SESSIONS_DIR = BASE_DIR / "sessions"
PRIMEWIKI_DIR = BASE_DIR / "primewiki"
CHECKPOINTS_DIR = BASE_DIR / "checkpoints"
ACTIVITY_LOG = LOGS_DIR / "activity.jsonl"
TASK_QUEUE = ARTIFACTS_DIR / "task_queue.jsonl"

SITES = [
    {"id": "linkedin",   "name": "LinkedIn",    "icon": "L", "domain": "linkedin.com"},
    {"id": "gmail",      "name": "Gmail",       "icon": "G", "domain": "gmail.com"},
    {"id": "reddit",     "name": "Reddit",      "icon": "R", "domain": "reddit.com"},
    {"id": "hackernews", "name": "Hacker News", "icon": "H", "domain": "news.ycombinator.com"},
    {"id": "github",     "name": "GitHub",      "icon": "Gh", "domain": "github.com"},
    {"id": "google",     "name": "Google",      "icon": "Go", "domain": "google.com"},
]

SITE_EMOJIS = {
    "linkedin": "\U0001f535",
    "gmail": "\U0001f4e7",
    "reddit": "\U0001f534",
    "hackernews": "\U0001f7e0",
    "github": "\u26ab",
    "google": "\U0001f535",
}

RECIPES_BY_SITE = {
    "linkedin": [
        {"id": "linkedin-discover-posts", "name": "Discover Posts"},
        {"id": "linkedin-create-post",    "name": "Create Post"},
        {"id": "linkedin-edit-post",      "name": "Edit Post"},
        {"id": "linkedin-delete-post",    "name": "Delete Post"},
        {"id": "linkedin-react-post",     "name": "React to Post"},
        {"id": "linkedin-comment-post",   "name": "Comment on Post"},
    ],
    "gmail": [
        {"id": "gmail-send-email",  "name": "Send Email"},
        {"id": "gmail-oauth-login", "name": "OAuth Login"},
    ],
    "reddit": [
        {"id": "reddit-upvote-workflow",  "name": "Upvote"},
        {"id": "reddit-comment-workflow", "name": "Comment"},
        {"id": "reddit-create-post",      "name": "Create Post"},
    ],
    "hackernews": [
        {"id": "hackernews-upvote-workflow",  "name": "Upvote"},
        {"id": "hackernews-comment-workflow", "name": "Comment"},
        {"id": "hackernews-hide-workflow",    "name": "Hide"},
    ],
    "github": [
        {"id": "github-create-issue", "name": "Create Issue"},
    ],
    "google": [
        {"id": "google-search-proof-of-concept", "name": "Search"},
    ],
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ensure_dirs():
    for d in [LOGS_DIR, ARTIFACTS_DIR, SESSIONS_DIR, PRIMEWIKI_DIR, CHECKPOINTS_DIR]:
        d.mkdir(parents=True, exist_ok=True)
    if not ACTIVITY_LOG.exists():
        ACTIVITY_LOG.write_text("")
    if not TASK_QUEUE.exists():
        TASK_QUEUE.write_text("")


def _raw_read_jsonl(path):
    lines = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        lines.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
    except FileNotFoundError:
        pass
    return lines


def read_jsonl(path):
    raw = _raw_read_jsonl(path)
    tasks = {}
    order = []
    for entry in raw:
        tid = entry.get("task_id")
        if tid:
            if tid not in tasks:
                order.append(tid)
            if entry.get("_is_update"):
                if tid in tasks:
                    tasks[tid]["status"] = entry.get("status", tasks[tid].get("status"))
                    if "updated_at" in entry:
                        tasks[tid]["updated_at"] = entry["updated_at"]
            else:
                tasks[tid] = dict(list(tasks.get(tid, {}).items()) + list(entry.items()))
    return [tasks[tid] for tid in order if tid in tasks]


def append_jsonl(path, obj):
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj) + "\n")


def get_session_status(site_id):
    candidates = [
        SESSIONS_DIR / (site_id + "_session.json"),
        ARTIFACTS_DIR / (site_id + "_session.json"),
    ]
    for p in candidates:
        if p.exists():
            try:
                mtime = p.stat().st_mtime
                age_hours = (datetime.now(timezone.utc).timestamp() - mtime) / 3600
                if age_hours < 120:
                    return {"status": "active", "age_hours": round(age_hours, 1)}
                if age_hours < 168:
                    return {"status": "expiring", "age_hours": round(age_hours, 1)}
                return {"status": "expired", "age_hours": round(age_hours, 1)}
            except OSError:
                pass
    return {"status": "none", "age_hours": None}


def format_age(hours):
    if hours is None:
        return ""
    if hours < 1:
        return str(int(hours * 60)) + "m ago"
    if hours < 24:
        return str(int(hours)) + "h ago"
    return str(int(hours / 24)) + "d ago"


def get_last_activity(site_id=None, limit=3):
    entries = _raw_read_jsonl(ACTIVITY_LOG)
    if site_id:
        entries = [e for e in entries if e.get("site") == site_id]
    return entries[-limit:]


def find_mmd_files(site_id=None):
    results = []
    for d in [ARTIFACTS_DIR, CHECKPOINTS_DIR]:
        if d.exists():
            for p in sorted(d.rglob("*.mmd")):
                if site_id is None or site_id in p.name:
                    results.append(p)
    return results


def get_primewiki_content(site_id):
    candidates = [
        PRIMEWIKI_DIR / (site_id + ".primewiki.json"),
        PRIMEWIKI_DIR / site_id / (site_id + ".primewiki.json"),
        PRIMEWIKI_DIR / (site_id + ".md"),
    ]
    for p in candidates:
        if p.exists():
            try:
                if p.suffix == ".json":
                    data = json.loads(p.read_text(encoding="utf-8"))
                    return data.get("content", json.dumps(data, indent=2))
                return p.read_text(encoding="utf-8")
            except Exception:
                pass
    return None


def h(text):
    """HTML-escape a string."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))


# ---------------------------------------------------------------------------
# HTML Shell
# ---------------------------------------------------------------------------

TAILWIND = '<script src="https://cdn.tailwindcss.com"></script>'
MARKED   = '<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>'
MERMAID  = '<script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>'


def html_page(title, body, cdns=""):
    return (
        "<!DOCTYPE html>\n"
        "<html lang=\"en\">\n"
        "<head>\n"
        "<meta charset=\"UTF-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">\n"
        "<title>" + h(title) + " - Solace Browser</title>\n"
        + TAILWIND + "\n"
        + cdns + "\n"
        "</head>\n"
        "<body class=\"bg-gray-950 text-gray-100 min-h-screen\">\n"
        + body +
        "\n</body>\n</html>"
    )


def nav_bar(back=False, extra=""):
    back_html = ""
    if back:
        back_html = '<a href="/" class="text-gray-400 hover:text-white text-sm">&#8592; Back</a>'
    return (
        '<nav class="bg-gray-900 border-b border-gray-700 px-6 py-3 flex items-center justify-between">'
        '<div class="flex items-center gap-3">'
        + back_html +
        '<span class="text-xl font-bold text-blue-400">Solace Browser</span>'
        '</div>'
        '<div class="flex items-center gap-3">'
        '<span class="text-xs text-gray-400">&#9679; Server Running</span>'
        + extra +
        '</div>'
        '</nav>'
    )


# ---------------------------------------------------------------------------
# Feature 1: Home Page
# ---------------------------------------------------------------------------

def build_home_page():
    activity_entries = get_last_activity(limit=3)

    cards_html = ""
    for site in SITES:
        sid = site["id"]
        sname = site["name"]
        emoji = SITE_EMOJIS.get(sid, "?")
        sess = get_session_status(sid)
        status = sess["status"]
        age = sess["age_hours"]

        if status == "active":
            badge = ('<span class="inline-block w-2 h-2 rounded-full bg-green-400 mr-1"></span>'
                     '<span class="text-green-400 text-xs">Active</span>')
            age_str = '<p class="text-gray-400 text-xs mt-1">' + format_age(age) + "</p>"
            buttons = (
                '<div class="mt-3 flex flex-col gap-1">'
                '<a href="/activity?site=' + sid + '" class="block bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded text-center">Activity</a>'
                '<button onclick="openRecipeModal(\'' + sid + '\')" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-1 rounded">Run Recipe</button>'
                '</div>'
            )
        elif status == "expiring":
            badge = ('<span class="inline-block w-2 h-2 rounded-full bg-yellow-400 mr-1"></span>'
                     '<span class="text-yellow-400 text-xs">Expiring</span>')
            age_str = '<p class="text-gray-400 text-xs mt-1">' + format_age(age) + "</p>"
            buttons = (
                '<div class="mt-3 flex flex-col gap-1">'
                '<a href="/activity?site=' + sid + '" class="block bg-blue-600 hover:bg-blue-500 text-white text-xs px-3 py-1 rounded text-center">Activity</a>'
                '<button onclick="openRecipeModal(\'' + sid + '\')" class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-1 rounded">Run Recipe</button>'
                '</div>'
            )
        else:
            badge = ('<span class="inline-block w-2 h-2 rounded-full bg-gray-500 mr-1"></span>'
                     '<span class="text-gray-400 text-xs">No session</span>')
            age_str = ""
            buttons = (
                '<div class="mt-3">'
                '<button onclick="openConnectModal(\'' + sid + '\',\'' + sname + '\')" '
                'class="bg-gray-600 hover:bg-gray-500 text-white text-xs px-3 py-1 rounded w-full">Connect</button>'
                '</div>'
            )

        cards_html += (
            '<div class="bg-gray-800 border border-gray-700 rounded-xl p-4 hover:border-gray-500 transition-colors">'
            '<div class="flex items-center gap-2 mb-2">'
            '<span class="text-2xl">' + emoji + '</span>'
            '<span class="font-semibold text-sm">' + sname + '</span>'
            '</div>'
            '<div class="flex items-center">' + badge + '</div>'
            + age_str + buttons +
            '</div>'
        )

    if activity_entries:
        rows = ""
        for e in reversed(activity_entries):
            ts = e.get("ts", "")
            ts_short = ts[:19] if ts else ""
            sname2 = e.get("site", "")
            summary = e.get("summary", e.get("recipe_id", ""))
            s = e.get("status", "")
            icon = "&#10003;" if s == "done" else "&#10007;" if s == "failed" else "&#8226;"
            rows += (
                '<div class="flex gap-3 text-sm py-1 border-b border-gray-800">'
                '<span class="text-gray-500 text-xs w-40 flex-shrink-0">' + h(ts_short) + '</span>'
                '<span class="text-blue-300">' + h(sname2) + '</span>'
                '<span class="text-gray-300">' + icon + ' ' + h(summary) + '</span>'
                '</div>'
            )
        activity_section = (
            '<section class="mt-8">'
            '<h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Recent Activity</h2>'
            '<div class="bg-gray-800 border border-gray-700 rounded-xl p-4">'
            + rows +
            '</div></section>'
        )
    else:
        activity_section = (
            '<section class="mt-8">'
            '<h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Recent Activity</h2>'
            '<div class="bg-gray-800 border border-gray-700 rounded-xl p-4 text-gray-500 text-sm">'
            'No activity yet -- run a recipe to get started.'
            '</div></section>'
        )

    all_recipes_json = json.dumps(RECIPES_BY_SITE)

    body = (
        nav_bar() +
        '<main class="max-w-5xl mx-auto px-6 py-8">'
        '<div class="flex items-center justify-between mb-6">'
        '<h1 class="text-2xl font-bold text-white">Supported Sites</h1>'
        '<a href="/kanban" class="bg-gray-700 hover:bg-gray-600 text-white text-sm px-4 py-2 rounded-lg">Task Queue</a>'
        '</div>'
        '<div class="grid grid-cols-2 md:grid-cols-3 gap-4">'
        + cards_html +
        '</div>'
        + activity_section +
        '</main>'

        # Recipe Modal
        '<div id="recipeModal" class="hidden fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">'
        '<div class="bg-gray-800 border border-gray-600 rounded-xl p-6 w-96 max-w-full">'
        '<h3 class="text-lg font-semibold mb-4">Run Recipe -- <span id="modalSiteName"></span></h3>'
        '<select id="recipeSelect" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm mb-3"></select>'
        '<textarea id="recipeParams" placeholder=\'Optional params JSON, e.g. {"text":"Hello"}\''
        ' class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm h-20 mb-3 font-mono resize-none"></textarea>'
        '<div class="flex gap-2 justify-end">'
        '<button onclick="closeModal(\'recipeModal\')" class="bg-gray-600 hover:bg-gray-500 text-white text-sm px-4 py-2 rounded">Cancel</button>'
        '<button onclick="submitRecipe()" class="bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded">Add to Queue</button>'
        '</div></div></div>'

        # Connect Modal
        '<div id="connectModal" class="hidden fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">'
        '<div class="bg-gray-800 border border-gray-600 rounded-xl p-6 w-96 max-w-full">'
        '<h3 class="text-lg font-semibold mb-3">Connect -- <span id="connectSiteName"></span></h3>'
        '<div class="text-sm text-gray-300 space-y-2">'
        '<p>To capture a session:</p>'
        '<ol class="list-decimal list-inside space-y-1 text-gray-400">'
        '<li>Open browser at <code class="text-blue-300">http://localhost:9222</code></li>'
        '<li>Log in to the site manually</li>'
        '<li>Run the session capture recipe</li>'
        '<li>Session file will appear in <code class="text-blue-300">sessions/</code></li>'
        '</ol></div>'
        '<div class="flex justify-end mt-4">'
        '<button onclick="closeModal(\'connectModal\')" class="bg-gray-600 hover:bg-gray-500 text-white text-sm px-4 py-2 rounded">Close</button>'
        '</div></div></div>'

        '<script>\n'
        'const RECIPES = ' + all_recipes_json + ';\n'
        'let currentSite = null;\n'
        'function openRecipeModal(siteId) {\n'
        '  currentSite = siteId;\n'
        '  document.getElementById("modalSiteName").textContent = siteId;\n'
        '  const sel = document.getElementById("recipeSelect");\n'
        '  sel.innerHTML = "";\n'
        '  (RECIPES[siteId] || []).forEach(r => {\n'
        '    const opt = document.createElement("option");\n'
        '    opt.value = r.id; opt.textContent = r.name;\n'
        '    sel.appendChild(opt);\n'
        '  });\n'
        '  document.getElementById("recipeModal").classList.remove("hidden");\n'
        '}\n'
        'function openConnectModal(siteId, siteName) {\n'
        '  document.getElementById("connectSiteName").textContent = siteName;\n'
        '  document.getElementById("connectModal").classList.remove("hidden");\n'
        '}\n'
        'function closeModal(id) { document.getElementById(id).classList.add("hidden"); }\n'
        'async function submitRecipe() {\n'
        '  const recipeId = document.getElementById("recipeSelect").value;\n'
        '  const paramsRaw = document.getElementById("recipeParams").value.trim();\n'
        '  let params = {};\n'
        '  if (paramsRaw) { try { params = JSON.parse(paramsRaw); } catch(e) { alert("Invalid JSON params"); return; } }\n'
        '  const resp = await fetch("/tasks", {\n'
        '    method: "POST",\n'
        '    headers: { "Content-Type": "application/json" },\n'
        '    body: JSON.stringify({ site: currentSite, recipe_id: recipeId, params })\n'
        '  });\n'
        '  if (resp.ok) { closeModal("recipeModal"); window.location.href = "/kanban"; }\n'
        '  else { alert("Failed to add task"); }\n'
        '}\n'
        '</script>'
    )

    return html_page("Home", body)


# ---------------------------------------------------------------------------
# Feature 2: Activity View
# ---------------------------------------------------------------------------

def build_activity_page(site_id):
    site = next((s for s in SITES if s["id"] == site_id), None)
    if site is None:
        return None

    sname = site["name"]
    emoji = SITE_EMOJIS.get(site_id, "?")
    sess = get_session_status(site_id)
    status = sess["status"]

    # Status badge
    if status == "active":
        status_badge = ('<span class="inline-block w-2 h-2 rounded-full bg-green-400 mr-1"></span>'
                        '<span class="text-green-400 text-xs">Active</span>')
    elif status == "expiring":
        status_badge = ('<span class="inline-block w-2 h-2 rounded-full bg-yellow-400 mr-1"></span>'
                        '<span class="text-yellow-400 text-xs">Expiring</span>')
    else:
        status_badge = ('<span class="inline-block w-2 h-2 rounded-full bg-gray-500 mr-1"></span>'
                        '<span class="text-gray-400 text-xs">No session</span>')

    # Activity rows
    activity_entries = get_last_activity(site_id, limit=50)
    activity_rows = ""
    if activity_entries:
        for e in reversed(activity_entries):
            ts = e.get("ts", "")
            ts_short = ts[:19] if ts else ""
            recipe = e.get("recipe_id", "unknown")
            summary = e.get("summary", "")
            s = e.get("status", "")
            icon = "&#10003;" if s == "done" else "&#10007;" if s == "failed" else "&#8226;"
            color = "text-green-400" if s == "done" else "text-red-400" if s == "failed" else "text-gray-400"
            tid = e.get("task_id", "")
            art = e.get("artifact_path", "")
            artifact_link = ""
            if art and tid:
                artifact_link = '<a href="/tasks/' + tid + '/result" class="text-blue-400 text-xs hover:underline ml-2">View artifacts</a>'
            activity_rows += (
                '<div class="border-b border-gray-800 py-3">'
                '<div class="flex items-start gap-3">'
                '<span class="' + color + ' font-bold text-sm w-4">' + icon + '</span>'
                '<div>'
                '<div class="flex items-center gap-2">'
                '<span class="text-sm font-medium text-gray-200">' + h(recipe) + '</span>'
                + artifact_link +
                '</div>'
                '<p class="text-gray-400 text-xs mt-0.5">' + h(summary) + '</p>'
                '<p class="text-gray-600 text-xs mt-0.5">' + h(ts_short) + '</p>'
                '</div></div></div>'
            )
    else:
        activity_rows = '<p class="text-gray-500 text-sm py-4">No activity yet. Run a recipe to get started.</p>'

    # Wiki content
    wiki_content = get_primewiki_content(site_id)
    wiki_content_json = json.dumps(wiki_content or "")
    wiki_placeholder_html = ""
    if not wiki_content:
        wiki_placeholder_html = '<p class="text-gray-500">No knowledge graph yet -- run a discovery recipe to build it.</p>'

    # Mermaid diagrams
    mmd_files = find_mmd_files(site_id)
    mmd_options = ""
    for i, p in enumerate(mmd_files):
        mmd_options += '<option value="' + str(i) + '">' + h(p.name) + '</option>'

    mmd_select_html = ""
    if mmd_files:
        mmd_select_html = ('<select id="mmd-select" onchange="loadMmd(this.value)" '
                           'class="bg-gray-700 border border-gray-600 rounded px-3 py-1 text-sm mb-4">'
                           + mmd_options + '</select>')
    mmd_render_html = ""
    if mmd_files:
        mmd_render_html = '<div id="mermaid-render" class="mermaid"></div>'
    else:
        mmd_render_html = '<p class="text-gray-500 text-sm">No state diagrams yet -- run a recipe to generate one.</p>'

    # Quick recipe shortcuts
    recipes_for_site = RECIPES_BY_SITE.get(site_id, [])
    recipe_shortcuts = ""
    for r in recipes_for_site:
        recipe_shortcuts += (
            '<button onclick="addTask(\'' + site_id + '\',\'' + r["id"] + '\')" '
            'class="block w-full text-left text-xs text-blue-300 hover:text-blue-200 py-0.5">'
            + r["name"] + '</button>'
        )

    recipe_options_html = ""
    for r in recipes_for_site:
        recipe_options_html += '<option value="' + r["id"] + '">' + r["name"] + '</option>'

    mmd_files_json = json.dumps([str(p) for p in mmd_files])
    all_recipes_json = json.dumps(RECIPES_BY_SITE)

    run_btn = ('<button onclick="openRecipeModal()" '
               'class="bg-indigo-600 hover:bg-indigo-500 text-white text-xs px-3 py-1.5 rounded">Run Recipe</button>'
               '<button class="bg-gray-700 hover:bg-gray-600 text-white text-xs px-3 py-1.5 rounded ml-2">Sync</button>')

    body = (
        nav_bar(back=True, extra=run_btn) +

        '<div class="flex" style="height: calc(100vh - 57px)">'

        # Sidebar
        '<aside class="w-48 bg-gray-900 border-r border-gray-700 flex-shrink-0 overflow-y-auto p-4">'
        '<div class="mb-4">'
        '<div class="text-xl mb-1">' + emoji + '</div>'
        '<div class="font-semibold text-sm">' + sname + '</div>'
        '<div class="flex items-center mt-1">' + status_badge + '</div>'
        '</div>'
        '<hr class="border-gray-700 mb-3">'
        '<div class="text-xs text-gray-500 uppercase tracking-wide mb-2">Quick Recipes</div>'
        + recipe_shortcuts +
        '</aside>'

        # Main content
        '<main class="flex-1 overflow-y-auto">'

        # Tab bar
        '<div class="bg-gray-900 border-b border-gray-700 px-6 flex">'
        '<button onclick="switchTab(\'activity\')" id="tab-activity" '
        'class="px-4 py-3 text-sm border-b-2 border-blue-500 text-blue-400">Activity Feed</button>'
        '<button onclick="switchTab(\'wiki\')" id="tab-wiki" '
        'class="px-4 py-3 text-sm border-b-2 border-transparent text-gray-400 hover:text-gray-200">PrimeWiki</button>'
        '<button onclick="switchTab(\'diagram\')" id="tab-diagram" '
        'class="px-4 py-3 text-sm border-b-2 border-transparent text-gray-400 hover:text-gray-200">State Diagram</button>'
        '<button onclick="switchTab(\'html\')" id="tab-html" '
        'class="px-4 py-3 text-sm border-b-2 border-transparent text-gray-400 hover:text-gray-200">HTML Viewer</button>'
        '</div>'

        # Pane: Activity
        '<div id="pane-activity" class="p-6">'
        '<h2 class="text-lg font-semibold mb-4">Activity Feed -- ' + sname + '</h2>'
        + activity_rows +
        '</div>'

        # Pane: Wiki
        '<div id="pane-wiki" class="p-6 hidden">'
        '<h2 class="text-lg font-semibold mb-4">PrimeWiki -- ' + sname + '</h2>'
        '<div id="wiki-content" class="prose prose-invert max-w-none text-gray-300">'
        + wiki_placeholder_html +
        '</div></div>'

        # Pane: Diagram
        '<div id="pane-diagram" class="p-6 hidden">'
        '<h2 class="text-lg font-semibold mb-4">State Diagram -- ' + sname + '</h2>'
        + mmd_select_html +
        '<div id="mermaid-container" class="bg-gray-800 rounded-xl p-4">'
        + mmd_render_html +
        '</div></div>'

        # Pane: HTML Viewer
        '<div id="pane-html" class="p-6 hidden">'
        '<h2 class="text-lg font-semibold mb-4">HTML Viewer</h2>'
        '<div class="flex gap-2 mb-4">'
        '<input id="html-url" type="text" placeholder="https://www.linkedin.com/feed/" '
        'class="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm font-mono">'
        '<button onclick="fetchHtml()" class="bg-blue-600 hover:bg-blue-500 text-white text-sm px-4 py-2 rounded">Fetch &amp; Display</button>'
        '<button onclick="viewRaw()" class="bg-gray-600 hover:bg-gray-500 text-white text-sm px-4 py-2 rounded">View Raw</button>'
        '</div>'
        '<iframe id="html-frame" sandbox="allow-scripts allow-same-origin" '
        'class="w-full rounded-xl border border-gray-700 bg-white" style="height:60vh;"></iframe>'
        '<pre id="html-raw" class="hidden mt-4 bg-gray-900 border border-gray-700 rounded-xl p-4 '
        'text-xs text-gray-300 overflow-auto" style="max-height:40vh;"></pre>'
        '</div>'

        '</main></div>'

        # Recipe Modal
        '<div id="recipeModal" class="hidden fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">'
        '<div class="bg-gray-800 border border-gray-600 rounded-xl p-6 w-96">'
        '<h3 class="text-lg font-semibold mb-4">Run Recipe -- ' + sname + '</h3>'
        '<select id="recipeSelect" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm mb-3">'
        + recipe_options_html +
        '</select>'
        '<textarea id="recipeParams" placeholder="Optional params JSON" '
        'class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm h-20 mb-3 font-mono resize-none"></textarea>'
        '<div class="flex gap-2 justify-end">'
        '<button onclick="document.getElementById(\'recipeModal\').classList.add(\'hidden\')" '
        'class="bg-gray-600 hover:bg-gray-500 text-white text-sm px-4 py-2 rounded">Cancel</button>'
        '<button onclick="submitRecipe()" '
        'class="bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded">Add to Queue</button>'
        '</div></div></div>'

        '<script>\n'
        'const SITE_ID = ' + json.dumps(site_id) + ';\n'
        'const MMD_FILES = ' + mmd_files_json + ';\n'
        'const WIKI_CONTENT = ' + wiki_content_json + ';\n'
        '\n'
        'function switchTab(name) {\n'
        '  ["activity","wiki","diagram","html"].forEach(t => {\n'
        '    document.getElementById("pane-" + t).classList.toggle("hidden", t !== name);\n'
        '    const btn = document.getElementById("tab-" + t);\n'
        '    btn.classList.toggle("border-blue-500", t === name);\n'
        '    btn.classList.toggle("text-blue-400", t === name);\n'
        '    btn.classList.toggle("border-transparent", t !== name);\n'
        '    btn.classList.toggle("text-gray-400", t !== name);\n'
        '  });\n'
        '  if (name === "wiki" && WIKI_CONTENT) {\n'
        '    document.getElementById("wiki-content").innerHTML = marked.parse(WIKI_CONTENT);\n'
        '  }\n'
        '  if (name === "diagram" && MMD_FILES.length > 0) { renderMermaid(0); }\n'
        '}\n'
        '\n'
        'let mmdCache = {};\n'
        'async function renderMermaid(idx) {\n'
        '  if (mmdCache[idx] !== undefined) {\n'
        '    const el = document.getElementById("mermaid-render");\n'
        '    el.removeAttribute("data-processed");\n'
        '    el.textContent = mmdCache[idx];\n'
        '    mermaid.run({ nodes: [el] });\n'
        '    return;\n'
        '  }\n'
        '  const resp = await fetch("/api/mmd?path=" + encodeURIComponent(MMD_FILES[idx]));\n'
        '  if (resp.ok) {\n'
        '    const text = await resp.text();\n'
        '    mmdCache[idx] = text;\n'
        '    const el = document.getElementById("mermaid-render");\n'
        '    el.removeAttribute("data-processed");\n'
        '    el.textContent = text;\n'
        '    mermaid.run({ nodes: [el] });\n'
        '  }\n'
        '}\n'
        'function loadMmd(idx) { renderMermaid(parseInt(idx)); }\n'
        '\n'
        'let lastHtml = "";\n'
        'async function fetchHtml() {\n'
        '  const url = document.getElementById("html-url").value.trim();\n'
        '  if (!url) return;\n'
        '  const resp = await fetch("http://localhost:9222/html-clean?url=" + encodeURIComponent(url));\n'
        '  if (resp.ok) {\n'
        '    lastHtml = await resp.text();\n'
        '    document.getElementById("html-frame").srcdoc = lastHtml;\n'
        '    document.getElementById("html-raw").classList.add("hidden");\n'
        '  } else {\n'
        '    alert("Failed to fetch HTML (is port 9222 running?)");\n'
        '  }\n'
        '}\n'
        'function viewRaw() {\n'
        '  const raw = document.getElementById("html-raw");\n'
        '  raw.textContent = lastHtml || "(no content fetched yet)";\n'
        '  raw.classList.toggle("hidden");\n'
        '}\n'
        '\n'
        'function openRecipeModal() { document.getElementById("recipeModal").classList.remove("hidden"); }\n'
        'async function submitRecipe() {\n'
        '  const recipeId = document.getElementById("recipeSelect").value;\n'
        '  const paramsRaw = document.getElementById("recipeParams").value.trim();\n'
        '  let params = {};\n'
        '  if (paramsRaw) { try { params = JSON.parse(paramsRaw); } catch(e) { alert("Invalid JSON"); return; } }\n'
        '  const resp = await fetch("/tasks", {\n'
        '    method: "POST",\n'
        '    headers: { "Content-Type": "application/json" },\n'
        '    body: JSON.stringify({ site: SITE_ID, recipe_id: recipeId, params })\n'
        '  });\n'
        '  if (resp.ok) { window.location.href = "/kanban"; }\n'
        '  else { alert("Failed to add task"); }\n'
        '}\n'
        'async function addTask(siteId, recipeId) {\n'
        '  const resp = await fetch("/tasks", {\n'
        '    method: "POST",\n'
        '    headers: { "Content-Type": "application/json" },\n'
        '    body: JSON.stringify({ site: siteId, recipe_id: recipeId, params: {} })\n'
        '  });\n'
        '  if (resp.ok) { window.location.href = "/kanban"; }\n'
        '}\n'
        '\n'
        'mermaid.initialize({ startOnLoad: false, theme: "dark" });\n'
        '</script>'
    )

    return html_page(sname + " Activity", body, cdns=MARKED + "\n" + MERMAID)


# ---------------------------------------------------------------------------
# Feature 3: Kanban Board
# ---------------------------------------------------------------------------

def build_kanban_page():
    all_recipes_json = json.dumps(RECIPES_BY_SITE)
    sites_json = json.dumps([{"id": s["id"], "name": s["name"]} for s in SITES])

    add_btn = '<button onclick="openAddModal()" class="bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded">+ Add Task</button>'

    body = (
        nav_bar(back=True, extra=add_btn) +

        '<main class="p-6">'
        '<h1 class="text-2xl font-bold mb-6">Recipe Queue</h1>'
        '<div class="grid grid-cols-4 gap-4">'

        '<div>'
        '<h2 class="text-sm font-semibold text-gray-400 uppercase tracking-wide mb-3">'
        'Queue <span id="count-queued" class="text-gray-600 normal-case font-normal">(0)</span></h2>'
        '<div id="col-queued" class="space-y-3 min-h-16"></div>'
        '</div>'

        '<div>'
        '<h2 class="text-sm font-semibold text-yellow-400 uppercase tracking-wide mb-3">'
        'Running <span id="count-running" class="text-gray-600 normal-case font-normal">(0)</span></h2>'
        '<div id="col-running" class="space-y-3 min-h-16"></div>'
        '</div>'

        '<div>'
        '<h2 class="text-sm font-semibold text-green-400 uppercase tracking-wide mb-3">'
        'Done <span id="count-done" class="text-gray-600 normal-case font-normal">(0)</span></h2>'
        '<div id="col-done" class="space-y-3 min-h-16"></div>'
        '</div>'

        '<div>'
        '<h2 class="text-sm font-semibold text-red-400 uppercase tracking-wide mb-3">'
        'Failed <span id="count-failed" class="text-gray-600 normal-case font-normal">(0)</span></h2>'
        '<div id="col-failed" class="space-y-3 min-h-16"></div>'
        '</div>'

        '</div>'
        '<p id="empty-msg" class="hidden text-center text-gray-600 mt-12">No tasks yet. Click "+ Add Task" to get started.</p>'
        '</main>'

        # Add Task Modal
        '<div id="addModal" class="hidden fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">'
        '<div class="bg-gray-800 border border-gray-600 rounded-xl p-6 w-96">'
        '<h3 class="text-lg font-semibold mb-4">Add Task</h3>'
        '<label class="block text-xs text-gray-400 mb-1">Site</label>'
        '<select id="modal-site" onchange="updateRecipes()" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm mb-3"></select>'
        '<label class="block text-xs text-gray-400 mb-1">Recipe</label>'
        '<select id="modal-recipe" class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm mb-3"></select>'
        '<label class="block text-xs text-gray-400 mb-1">Params (optional JSON)</label>'
        '<textarea id="modal-params" placeholder=\'{"text":"Hello world"}\' '
        'class="w-full bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm h-16 font-mono resize-none mb-4"></textarea>'
        '<div class="flex gap-2 justify-end">'
        '<button onclick="closeModal()" class="bg-gray-600 hover:bg-gray-500 text-white text-sm px-4 py-2 rounded">Cancel</button>'
        '<button onclick="addTask()" class="bg-indigo-600 hover:bg-indigo-500 text-white text-sm px-4 py-2 rounded">Add to Queue</button>'
        '</div></div></div>'

        # Detail Modal
        '<div id="detailModal" class="hidden fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-50">'
        '<div class="bg-gray-800 border border-gray-600 rounded-xl p-6 max-w-2xl w-full mx-4 max-h-screen overflow-y-auto">'
        '<h3 class="text-lg font-semibold mb-4" id="detail-title">Task Detail</h3>'
        '<pre id="detail-content" class="text-xs text-gray-300 bg-gray-900 rounded p-4 overflow-auto max-h-96"></pre>'
        '<div class="flex justify-end mt-4">'
        '<button onclick="document.getElementById(\'detailModal\').classList.add(\'hidden\')" '
        'class="bg-gray-600 hover:bg-gray-500 text-white text-sm px-4 py-2 rounded">Close</button>'
        '</div></div></div>'

        '<script>\n'
        'const RECIPES = ' + all_recipes_json + ';\n'
        'const SITES_LIST = ' + sites_json + ';\n'
        '\n'
        'function openAddModal() {\n'
        '  const siteSel = document.getElementById("modal-site");\n'
        '  siteSel.innerHTML = "";\n'
        '  SITES_LIST.forEach(s => {\n'
        '    const opt = document.createElement("option");\n'
        '    opt.value = s.id; opt.textContent = s.name;\n'
        '    siteSel.appendChild(opt);\n'
        '  });\n'
        '  updateRecipes();\n'
        '  document.getElementById("addModal").classList.remove("hidden");\n'
        '}\n'
        'function updateRecipes() {\n'
        '  const siteId = document.getElementById("modal-site").value;\n'
        '  const sel = document.getElementById("modal-recipe");\n'
        '  sel.innerHTML = "";\n'
        '  (RECIPES[siteId] || []).forEach(r => {\n'
        '    const opt = document.createElement("option");\n'
        '    opt.value = r.id; opt.textContent = r.name;\n'
        '    sel.appendChild(opt);\n'
        '  });\n'
        '}\n'
        'function closeModal() { document.getElementById("addModal").classList.add("hidden"); }\n'
        '\n'
        'async function addTask() {\n'
        '  const site = document.getElementById("modal-site").value;\n'
        '  const recipeId = document.getElementById("modal-recipe").value;\n'
        '  const paramsRaw = document.getElementById("modal-params").value.trim();\n'
        '  let params = {};\n'
        '  if (paramsRaw) { try { params = JSON.parse(paramsRaw); } catch(e) { alert("Invalid JSON params"); return; } }\n'
        '  const resp = await fetch("/tasks", {\n'
        '    method: "POST",\n'
        '    headers: { "Content-Type": "application/json" },\n'
        '    body: JSON.stringify({ site, recipe_id: recipeId, params })\n'
        '  });\n'
        '  if (resp.ok) { closeModal(); loadTasks(); }\n'
        '  else { alert("Failed to add task"); }\n'
        '}\n'
        '\n'
        'async function cancelTask(id) {\n'
        '  await fetch("/tasks/" + id + "/cancel", { method: "POST" });\n'
        '  loadTasks();\n'
        '}\n'
        'async function retryTask(id) {\n'
        '  await fetch("/tasks/" + id + "/retry", { method: "POST" });\n'
        '  loadTasks();\n'
        '}\n'
        'function showDetail(taskJson) {\n'
        '  const task = JSON.parse(taskJson);\n'
        '  document.getElementById("detail-title").textContent = task.recipe_id;\n'
        '  document.getElementById("detail-content").textContent = JSON.stringify(task, null, 2);\n'
        '  document.getElementById("detailModal").classList.remove("hidden");\n'
        '}\n'
        '\n'
        'function makeCard(task) {\n'
        '  const borderColor = { queued: "border-gray-600", running: "border-yellow-500", done: "border-green-600", failed: "border-red-600", cancelled: "border-gray-700" };\n'
        '  const border = borderColor[task.status] || "border-gray-600";\n'
        '  const progress = (task.status === "running" && task.progress_pct)\n'
        '    ? `<div class="mt-2 bg-gray-700 rounded-full h-1.5"><div class="bg-yellow-400 h-1.5 rounded-full" style="width:${task.progress_pct}%"></div></div><p class="text-xs text-gray-500 mt-0.5">${task.progress_pct}%</p>`\n'
        '    : "";\n'
        '  const error = task.error ? `<p class="text-red-400 text-xs mt-1 truncate" title="${task.error}">${task.error}</p>` : "";\n'
        '  const summary = task.summary ? `<p class="text-gray-400 text-xs mt-1">${task.summary}</p>` : "";\n'
        '  const ts = (task.completed_at || task.started_at || task.created_at || "").slice(0,19).replace("T"," ");\n'
        '  let buttons = "";\n'
        '  if (task.status === "queued" || task.status === "running") {\n'
        '    buttons += `<button onclick="cancelTask(${JSON.stringify(task.task_id)})" class="text-xs text-red-400 hover:text-red-300">Cancel</button>`;\n'
        '  } else if (task.status === "failed") {\n'
        '    buttons += `<button onclick="retryTask(${JSON.stringify(task.task_id)})" class="text-xs text-blue-400 hover:text-blue-300">Retry</button>`;\n'
        '  }\n'
        '  const taskJson = JSON.stringify(task).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");\n'
        '  buttons += ` <button onclick="showDetail(this.dataset.task)" data-task="${taskJson}" class="text-xs text-gray-400 hover:text-gray-300 ml-2">Detail</button>`;\n'
        '  const recipeShort = task.recipe_id.replace(/^[a-z]+-/,"").replace(/-/g," ");\n'
        '  return `<div class="bg-gray-800 border ${border} rounded-lg p-3">`\n'
        '    + `<div class="text-xs text-gray-500 mb-0.5">${task.site}</div>`\n'
        '    + `<div class="text-sm font-medium text-gray-100">${task.recipe_id}</div>`\n'
        '    + summary + error + progress\n'
        '    + `<div class="text-xs text-gray-600 mt-1">${ts}</div>`\n'
        '    + `<div class="mt-2 flex gap-1">${buttons}</div>`\n'
        '    + "</div>";\n'
        '}\n'
        '\n'
        'async function loadTasks() {\n'
        '  const resp = await fetch("/tasks");\n'
        '  if (!resp.ok) return;\n'
        '  const tasks = await resp.json();\n'
        '  const cols = { queued: [], running: [], done: [], failed: [] };\n'
        '  tasks.forEach(t => { const b = cols[t.status]; if (b) b.push(t); });\n'
        '  let total = 0;\n'
        '  for (const [status, items] of Object.entries(cols)) {\n'
        '    const col = document.getElementById("col-" + status);\n'
        '    const count = document.getElementById("count-" + status);\n'
        '    if (col) col.innerHTML = items.map(makeCard).join("");\n'
        '    if (count) count.textContent = "(" + items.length + ")";\n'
        '    total += items.length;\n'
        '  }\n'
        '  document.getElementById("empty-msg").classList.toggle("hidden", total > 0);\n'
        '}\n'
        '\n'
        'loadTasks();\n'
        'setInterval(loadTasks, 5000);\n'
        '</script>'
    )

    return html_page("Kanban", body)


# ---------------------------------------------------------------------------
# HTTP Handler
# ---------------------------------------------------------------------------

class SolaceUIHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        print("[%s] %s" % (self.address_string(), fmt % args))

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def send_html(self, html, code=200):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_json(self, obj, code=200):
        body = json.dumps(obj, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def send_text(self, text, code=200, content_type="text/plain"):
        body = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            return self.rfile.read(length)
        return b""

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_cors_headers()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)

        try:
            if path == "/":
                self.send_html(build_home_page())

            elif path == "/activity":
                site_id = qs.get("site", ["linkedin"])[0]
                html = build_activity_page(site_id)
                if html is None:
                    self.send_html("<h1>Unknown site</h1>", 404)
                else:
                    self.send_html(html)

            elif path == "/kanban":
                self.send_html(build_kanban_page())

            elif path == "/tasks":
                status_filter = qs.get("status", [None])[0]
                tasks = read_jsonl(TASK_QUEUE)
                if status_filter:
                    tasks = [t for t in tasks if t.get("status") == status_filter]
                self.send_json(tasks)

            elif path.startswith("/tasks/") and path.endswith("/result"):
                parts = path.split("/")
                if len(parts) >= 3:
                    task_id = parts[2]
                    tasks = read_jsonl(TASK_QUEUE)
                    task = next((t for t in tasks if t.get("task_id") == task_id), None)
                    if task is None:
                        self.send_json({"error": "task not found"}, 404)
                    else:
                        artifact = task.get("artifact_path")
                        if artifact and pathlib.Path(artifact).exists():
                            data = json.loads(pathlib.Path(artifact).read_text())
                            self.send_json(data)
                        else:
                            self.send_json({"task": task, "artifact": None})
                else:
                    self.send_json({"error": "bad request"}, 400)

            elif path == "/api/sites":
                sites_with_status = []
                for s in SITES:
                    sess = get_session_status(s["id"])
                    merged = dict(list(s.items()) + list(sess.items()))
                    sites_with_status.append(merged)
                self.send_json(sites_with_status)

            elif path == "/api/mmd":
                file_path = qs.get("path", [""])[0]
                p = pathlib.Path(file_path)
                try:
                    p.resolve().relative_to(BASE_DIR.resolve())
                except ValueError:
                    self.send_text("Forbidden", 403)
                    return
                if p.exists() and p.suffix == ".mmd":
                    self.send_text(p.read_text(encoding="utf-8"), content_type="text/plain")
                else:
                    self.send_text("Not found", 404)

            elif path == "/health":
                self.send_json({"status": "ok", "server": "solace-ui", "port": 9223})

            else:
                self.send_html("<h1>404 Not Found</h1>", 404)

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print("ERROR: %s\n%s" % (e, tb))
            self.send_html("<h1>500 Internal Server Error</h1><pre>" + tb + "</pre>", 500)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        try:
            body = self.read_body()

            if path == "/tasks":
                data = json.loads(body) if body else {}
                site = data.get("site", "unknown")
                recipe_id = data.get("recipe_id", "unknown")
                params = data.get("params", {})
                recipe_name = recipe_id.replace("-", " ").title()
                task = {
                    "task_id": str(uuid.uuid4()),
                    "site": site,
                    "recipe_id": recipe_id,
                    "recipe_name": recipe_name,
                    "params": params,
                    "status": "queued",
                    "progress_pct": 0,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "started_at": None,
                    "completed_at": None,
                    "summary": None,
                    "error": None,
                    "artifact_path": None,
                }
                append_jsonl(TASK_QUEUE, task)
                self.send_json(task, 201)

            elif "/tasks/" in path and path.endswith("/cancel"):
                parts = path.split("/")
                if len(parts) >= 3:
                    task_id = parts[2]
                    update = {
                        "task_id": task_id,
                        "status": "cancelled",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "_is_update": True,
                    }
                    append_jsonl(TASK_QUEUE, update)
                    self.send_json({"ok": True})
                else:
                    self.send_json({"error": "bad request"}, 400)

            elif "/tasks/" in path and path.endswith("/retry"):
                parts = path.split("/")
                if len(parts) >= 3:
                    task_id = parts[2]
                    tasks = read_jsonl(TASK_QUEUE)
                    original = next((t for t in tasks if t.get("task_id") == task_id), None)
                    if original is None:
                        self.send_json({"error": "task not found"}, 404)
                        return
                    new_task = {
                        "task_id": str(uuid.uuid4()),
                        "site": original.get("site", "unknown"),
                        "recipe_id": original.get("recipe_id", "unknown"),
                        "recipe_name": original.get("recipe_name", ""),
                        "params": original.get("params", {}),
                        "status": "queued",
                        "progress_pct": 0,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "started_at": None,
                        "completed_at": None,
                        "summary": None,
                        "error": None,
                        "artifact_path": None,
                    }
                    append_jsonl(TASK_QUEUE, new_task)
                    self.send_json(new_task, 201)
                else:
                    self.send_json({"error": "bad request"}, 400)

            else:
                self.send_json({"error": "not found"}, 404)

        except json.JSONDecodeError:
            self.send_json({"error": "invalid JSON"}, 400)
        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            print("ERROR: %s\n%s" % (e, tb))
            self.send_json({"error": str(e)}, 500)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    ensure_dirs()
    PORT = 9223
    server = HTTPServer(("0.0.0.0", PORT), SolaceUIHandler)
    print("Solace Browser UI Server running on http://localhost:" + str(PORT))
    print("  GET /          -- Home page")
    print("  GET /activity  -- Activity view (add ?site=linkedin)")
    print("  GET /kanban    -- Kanban board")
    print("  GET /tasks     -- Task list JSON")
    print("  POST /tasks    -- Create task")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
