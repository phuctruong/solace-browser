#!/usr/bin/env python3
"""
Solace Browser — Schedule Cron Runner
Runs every minute via OS crontab. Checks scheduled apps and triggers due runs.

Usage (crontab -e):
  * * * * * python3 /home/phuc/projects/solace-browser/scripts/cron_runner.py >> ~/.solace/cron.log 2>&1
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path

SETTINGS_PATH = Path.home() / ".solace" / "settings.json"
BROWSER_API = "http://127.0.0.1:9222"
WEB_API = "http://127.0.0.1:8791"
LOG_PATH = Path.home() / ".solace" / "cron.log"

def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)

def read_settings() -> dict:
    if not SETTINGS_PATH.exists():
        return {}
    try:
        return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def write_settings(settings: dict) -> None:
    SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")

def api_get(url: str, timeout: int = 5) -> dict | None:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return None

def api_post(url: str, payload: dict, timeout: int = 30) -> dict | None:
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"POST {url} failed: {e}")
        return None

def is_browser_running() -> bool:
    status = api_get(f"{BROWSER_API}/api/status")
    return status is not None and status.get("running", False)

def parse_pattern(pattern: str) -> tuple[str, str]:
    """Parse 'daily@08:00' → ('daily', '08:00')"""
    if "@" in pattern:
        parts = pattern.split("@", 1)
        return parts[0].strip(), parts[1].strip()
    return pattern, "00:00"

def is_due(app_id: str, cfg: dict) -> bool:
    """Check if a scheduled app is due to run now."""
    if not cfg.get("enabled", False):
        return False
    pattern = cfg.get("pattern", "manual")
    if pattern == "manual":
        return False

    freq, time_str = parse_pattern(pattern)
    now = datetime.now()

    # Parse target time
    try:
        target_h, target_m = map(int, time_str.split(":"))
    except Exception:
        return False

    # Check next_run — if already ran today at target time, skip
    next_run_str = cfg.get("next_run")
    if next_run_str:
        try:
            next_run = datetime.fromisoformat(next_run_str)
            if now < next_run:
                return False  # not yet due
        except Exception:
            pass

    # Daily: due if current time is within the target hour:minute (within 1-minute window)
    if freq == "daily":
        due = now.hour == target_h and now.minute == target_m
        return due

    # Hourly: due every hour at :00
    if freq == "hourly":
        return now.minute == 0

    # Weekly: due on Monday at target time
    if freq == "weekly":
        return now.weekday() == 0 and now.hour == target_h and now.minute == target_m

    return False

def run_gmail_triage() -> dict:
    """Run the Gmail inbox triage via browser API."""
    log("Running Gmail inbox triage...")

    # Step 1: Check browser status and current URL
    status = api_get(f"{BROWSER_API}/api/status")
    if not status:
        return {"ok": False, "error": "browser_not_available"}

    # Step 2: Navigate to Gmail inbox
    nav = api_post(f"{BROWSER_API}/api/navigate", {
        "url": "https://mail.google.com/mail/u/0/#inbox",
        "wait_for": "networkidle"
    })
    if not nav or not nav.get("success"):
        return {"ok": False, "error": "navigation_failed"}

    # Step 3: Wait for inbox to load
    import time; time.sleep(3)

    # Step 4: Extract emails
    result = api_post(f"{BROWSER_API}/api/evaluate", {
        "expression": """(function() {
            var rows = Array.from(document.querySelectorAll('tr.zA')).slice(0, 20);
            return rows.map(function(r) {
                var senderEl = r.querySelector('span[email]');
                var sender = senderEl ? (senderEl.getAttribute('email') || senderEl.textContent.trim()) :
                             (r.querySelector('.yW') ? r.querySelector('.yW').textContent.trim() : '');
                var bogEl = r.querySelector('.a4W .bog') || r.querySelector('.bog');
                var subject = bogEl ? bogEl.textContent.trim() : '';
                var snippetEl = r.querySelector('.y2');
                var snippet = snippetEl ? snippetEl.textContent.trim().slice(0, 150) : '';
                var dateEl = r.querySelector('.xW span[title]');
                var date = dateEl ? dateEl.getAttribute('title') : (r.querySelector('.xW') ? r.querySelector('.xW').textContent.trim() : '');
                return {
                    sender: sender,
                    subject: subject,
                    snippet: snippet,
                    is_unread: r.classList.contains('zE'),
                    date: date
                };
            });
        })()"""
    })

    if not result or not result.get("success"):
        return {"ok": False, "error": "email_extraction_failed"}

    emails = result.get("result", [])
    unread = [e for e in emails if e.get("is_unread")]

    log(f"Extracted {len(emails)} emails ({len(unread)} unread)")

    # Step 5: Write to app inbox folder
    inbox_dir = Path(__file__).parent.parent / "data" / "default" / "apps" / "gmail-inbox-triage" / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    inbox_file = inbox_dir / f"run-{run_id}.json"
    inbox_data = {
        "run_id": run_id,
        "timestamp": datetime.now().isoformat(),
        "emails": emails,
        "total": len(emails),
        "unread": len(unread),
    }
    inbox_file.write_text(json.dumps(inbox_data, indent=2), encoding="utf-8")
    log(f"Saved inbox data to {inbox_file}")

    # Step 6: Notify user via YinYang if web server is up
    notify_msg = f"Gmail triage complete: {len(unread)} unread emails across {len(emails)} total. Open Schedule to review."
    api_post(f"{WEB_API}/api/yinyang/notify", {
        "type": "success",
        "message": notify_msg,
        "priority": "low",
        "app_id": "gmail-inbox-triage",
        "run_id": run_id
    })

    return {"ok": True, "run_id": run_id, "emails": len(emails), "unread": len(unread)}

def run_app(app_id: str) -> dict:
    """Dispatch app run by app_id."""
    dispatch = {
        "gmail-inbox-triage": run_gmail_triage,
    }
    runner = dispatch.get(app_id)
    if runner:
        return runner()
    log(f"No cron runner defined for app: {app_id}")
    return {"ok": False, "error": f"no_runner_for_{app_id}"}

def update_next_run(settings: dict, app_id: str, pattern: str) -> None:
    """Set next_run to tomorrow's target time after a successful run."""
    freq, time_str = parse_pattern(pattern)
    try:
        target_h, target_m = map(int, time_str.split(":"))
    except Exception:
        return
    now = datetime.now()
    if freq == "daily":
        from datetime import timedelta
        next_run = now.replace(hour=target_h, minute=target_m, second=0, microsecond=0) + timedelta(days=1)
    elif freq == "hourly":
        from datetime import timedelta
        next_run = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    elif freq == "weekly":
        from datetime import timedelta
        days_ahead = 7 - now.weekday()
        next_run = (now + timedelta(days=days_ahead)).replace(hour=target_h, minute=target_m, second=0, microsecond=0)
    else:
        return
    settings.setdefault("schedule", {})[app_id]["next_run"] = next_run.isoformat()

def main() -> None:
    settings = read_settings()
    schedule_cfg = settings.get("schedule", {})

    if not schedule_cfg:
        return  # Nothing scheduled

    # Check if any app is due
    due_apps = [(app_id, cfg) for app_id, cfg in schedule_cfg.items() if is_due(app_id, cfg)]

    if not due_apps:
        return  # Nothing due right now

    # Verify browser is running
    if not is_browser_running():
        log(f"Browser not running — skipping {len(due_apps)} scheduled runs")
        return

    for app_id, cfg in due_apps:
        log(f"Running scheduled app: {app_id} (pattern: {cfg.get('pattern')})")
        try:
            result = run_app(app_id)
            if result.get("ok"):
                log(f"SUCCESS {app_id}: {result}")
                # Update next_run to prevent double-running
                settings = read_settings()  # Re-read to avoid conflicts
                update_next_run(settings, app_id, cfg.get("pattern", "daily@08:00"))
                write_settings(settings)
            else:
                log(f"FAILED {app_id}: {result}")
        except Exception as e:
            log(f"ERROR running {app_id}: {e}")

if __name__ == "__main__":
    main()
