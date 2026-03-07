#!/usr/bin/env python3
"""
Solace Browser — Schedule Cron Runner
Runs every minute via OS crontab.
  Scheduled runs: trigger apps at their configured time (daily@08:00, etc.).

Note: Keep-alive was removed (GLOW 204). Session persistence will be handled
by the companion app (Tauri) which has proper multi-tab awareness.

Install (crontab -e):
  * * * * * python3 /home/phuc/projects/solace-browser/scripts/cron_runner.py >> ~/.solace/cron.log 2>&1
"""

import json
import time
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

SETTINGS_PATH = Path.home() / ".solace" / "settings.json"
BROWSER_API   = "http://127.0.0.1:9222"
WEB_API       = "http://127.0.0.1:8791"


# ── Helpers ──────────────────────────────────────────────────────────────────

def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def read_settings() -> dict:
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return {}

def write_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")

def api_get(url: str, timeout: int = 5) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError, TimeoutError):
        return None

def api_post(url: str, payload: dict, timeout: int = 30) -> dict | None:
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except (urllib.error.URLError, OSError, json.JSONDecodeError, ValueError, TimeoutError) as e:
        log(f"POST {url} failed: {e}")
        return None

def is_browser_running() -> bool:
    s = api_get(f"{BROWSER_API}/api/status")
    return bool(s and s.get("running"))

def get_current_url() -> str:
    s = api_get(f"{BROWSER_API}/api/status")
    return (s or {}).get("current_url", "")


# ── Scheduled Runs ────────────────────────────────────────────────────────────

def parse_pattern(pattern: str) -> tuple[str, str]:
    """'daily@08:00' → ('daily', '08:00')"""
    if "@" in pattern:
        f, t = pattern.split("@", 1)
        return f.strip(), t.strip()
    return pattern.strip(), "00:00"

def is_due(cfg: dict) -> bool:
    if not cfg.get("enabled", False):
        return False
    pattern = cfg.get("pattern", "manual")
    if pattern == "manual":
        return False

    freq, time_str = parse_pattern(pattern)
    now = datetime.now()

    try:
        target_h, target_m = map(int, time_str.split(":"))
    except (ValueError, TypeError):
        return False

    # Respect next_run — if set and in the future, not due
    next_run_str = cfg.get("next_run")
    if next_run_str:
        try:
            if now < datetime.fromisoformat(next_run_str):
                return False
        except (ValueError, TypeError):
            pass

    if freq == "daily":
        return now.hour == target_h and now.minute == target_m
    if freq == "hourly":
        return now.minute == 0
    if freq == "weekly":
        return now.weekday() == 0 and now.hour == target_h and now.minute == target_m
    return False

def update_next_run(settings: dict, app_id: str, pattern: str) -> None:
    freq, time_str = parse_pattern(pattern)
    try:
        h, m = map(int, time_str.split(":"))
    except (ValueError, TypeError):
        return
    now = datetime.now()
    if freq == "daily":
        nxt = (now + timedelta(days=1)).replace(hour=h, minute=m, second=0, microsecond=0)
    elif freq == "hourly":
        nxt = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    elif freq == "weekly":
        nxt = (now + timedelta(days=7 - now.weekday())).replace(
            hour=h, minute=m, second=0, microsecond=0)
    else:
        return
    settings.setdefault("schedule", {})[app_id]["next_run"] = nxt.isoformat()


# ── App Runners ───────────────────────────────────────────────────────────────

def run_gmail_triage() -> dict:
    log("Running Gmail inbox triage...")

    nav = api_post(f"{BROWSER_API}/api/navigate", {
        "url": "https://mail.google.com/mail/u/0/#inbox",
        "wait_for": "networkidle",
    })
    if not (nav and nav.get("success")):
        return {"ok": False, "error": "navigation_failed"}

    time.sleep(3)

    result = api_post(f"{BROWSER_API}/api/evaluate", {"expression": """
        (function() {
            var rows = Array.from(document.querySelectorAll('tr.zA')).slice(0, 20);
            return rows.map(function(r) {
                var se = r.querySelector('span[email]');
                var sender = se ? (se.getAttribute('email') || se.textContent.trim())
                               : (r.querySelector('.yW') || {textContent:''}).textContent.trim();
                var bog = r.querySelector('.a4W .bog') || r.querySelector('.bog');
                var snip = r.querySelector('.y2');
                var dt = r.querySelector('.xW span[title]');
                return {
                    sender:    sender,
                    subject:   bog  ? bog.textContent.trim()  : '',
                    snippet:   snip ? snip.textContent.trim().slice(0,150) : '',
                    is_unread: r.classList.contains('zE'),
                    date:      dt   ? dt.getAttribute('title') : ''
                };
            });
        })()
    """})

    if not (result and result.get("success")):
        return {"ok": False, "error": "extraction_failed"}

    emails  = result.get("result", [])
    unread  = [e for e in emails if e.get("is_unread")]
    run_id  = datetime.now().strftime("%Y%m%d-%H%M%S")

    # Persist to app inbox
    inbox_dir = Path(__file__).parent.parent / "data" / "default" / "apps" \
                / "gmail-inbox-triage" / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / f"run-{run_id}.json").write_text(
        json.dumps({"run_id": run_id, "timestamp": datetime.now().isoformat(),
                    "emails": emails, "total": len(emails), "unread": len(unread)},
                   indent=2),
        encoding="utf-8")

    # YinYang notification
    api_post(f"{WEB_API}/api/yinyang/notify", {
        "type": "success",
        "message": f"Gmail triage: {len(unread)} unread / {len(emails)} total. Open Schedule to review.",
        "priority": "low",
        "app_id": "gmail-inbox-triage",
        "run_id": run_id,
    })

    log(f"Gmail triage done: {len(emails)} emails ({len(unread)} unread), run_id={run_id}")
    return {"ok": True, "run_id": run_id, "emails": len(emails), "unread": len(unread)}


# Add more app runners here as apps grow:
# def run_slack_triage() -> dict: ...
# def run_linkedin_outreach() -> dict: ...

APP_RUNNERS = {
    "gmail-inbox-triage": run_gmail_triage,
}


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    settings = read_settings()

    # Nothing to do if browser isn't running
    if not is_browser_running():
        return

    changed = False

    # Scheduled runs
    for app_id, cfg in settings.get("schedule", {}).items():
        if is_due(cfg):
            log(f"Scheduled run due: {app_id} ({cfg.get('pattern')})")
            runner = APP_RUNNERS.get(app_id)
            if runner:
                try:
                    result = runner()
                    if result.get("ok"):
                        log(f"  ✓ {app_id} done: {result}")
                        settings = read_settings()  # re-read to avoid race
                        update_next_run(settings, app_id, cfg.get("pattern", ""))
                        changed = True
                    else:
                        log(f"  ✗ {app_id} failed: {result}")
                except (OSError, ValueError, KeyError, RuntimeError) as e:
                    log(f"  ✗ {app_id} exception: {e}")
            else:
                log(f"  (no runner for {app_id} yet)")

    if changed:
        write_settings(settings)


if __name__ == "__main__":
    main()
