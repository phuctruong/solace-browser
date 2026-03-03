#!/usr/bin/env python3
"""
run_solace_inspector.py — Solace Inspector Runner
Committee: James Bach · Elisabeth Hendrickson · Kent Beck · Cem Kaner · Michael Bolton
Auth: 65537 | Paper 42 | GLOW: L

ARCHITECTURE (Agent-Native):
  This runner does ZERO LLM API calls. It collects pure evidence (ARIA, DOM,
  heuristics, screenshots, CLI output) and produces a sealed report. The AI
  coding agent (Claude Code, Cursor, Codex, etc.) reads the report and applies
  its own model for analysis. Cost: $0 for the runner.

Usage:
    python3 scripts/run_solace_inspector.py --url http://localhost:8791/
    python3 scripts/run_solace_inspector.py --url https://myapp.com --persona cem_kaner
    python3 scripts/run_solace_inspector.py --self-diagnostic
    python3 scripts/run_solace_inspector.py --inbox
    python3 scripts/run_solace_inspector.py --cmd "python3 server.py --help" --cwd /path/to/project

Modes:
    web  — Navigate + ARIA + DOM + Heuristics + Screenshot → sealed report
    cli  — Subprocess + exit code + stdout/stderr + assert → sealed report
    api  — HTTP request + schema + timing + headers → sealed report

Requires (web mode): Solace Browser running on localhost:9222
Output: data/default/apps/solace-inspector/outbox/report-{run_id}.json
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid

import requests

BROWSER_API = "http://localhost:9222"
WEB_API = "http://localhost:8791"
APP_DIR = pathlib.Path(__file__).parent.parent / "data/default/apps/solace-inspector"
INBOX_DIR = APP_DIR / "inbox"
OUTBOX_DIR = APP_DIR / "outbox"
STATUS_FILE = APP_DIR / "STATUS.md"

SELF_DIAGNOSTIC_PAGES = [
    {"url": "http://localhost:8791/", "name": "Home"},
    {"url": "http://localhost:8791/app-store", "name": "App Store"},
    {"url": "http://localhost:8791/settings", "name": "Settings"},
    {"url": "http://localhost:8791/schedule", "name": "Schedule"},
    {"url": "http://localhost:8791/start", "name": "Start / Auth"},
]

# Persona prompts — injected into the report as agent_analysis_request.
# The AI coding agent reads this and applies its own model. No API call.
PERSONA_PROMPTS = {
    "james_bach": (
        "You are James Bach, world-class exploratory tester. "
        "Apply SBTM (Session-Based Test Management) and HICCUPPS oracle heuristics "
        "(History, Image, Comparable, Claims, User, Product, Purpose, Standards). "
        "Review the evidence below and identify quality risks, bugs, and testing insights. "
        "Be specific, direct, exploratory. Focus on what could go WRONG. "
        "Output: (1) Top 3 quality risks, (2) Bugs found, (3) Recommended fix proposals."
    ),
    "cem_kaner": (
        "You are Cem Kaner, context-driven testing expert and BBST author. "
        "Apply context-driven principles: value of any practice depends on context. "
        "What is the most important quality risk here? What's the purpose of this page "
        "and how well does it serve that purpose? "
        "Output: (1) Context assessment, (2) Top quality risk, (3) Fix proposals."
    ),
    "elisabeth_hendrickson": (
        "You are Elisabeth Hendrickson, agile testing expert and author of Explore It!. "
        "Apply charter-based exploration: what is the charter for this surface? "
        "What broken flows, missing error handling, and usability issues do you see? "
        "Think about what a user encounters when things go wrong. "
        "Output: (1) Exploration charter, (2) Broken flows found, (3) Fix proposals."
    ),
    "kent_beck": (
        "You are Kent Beck, creator of TDD and XP. "
        "Think about testability: what makes this surface hard to test? "
        "What behavior should be tested first? What do you fear is broken? "
        "If you had to write one test for this surface, what would it be? "
        "Output: (1) Testability assessment, (2) What to test first, (3) Fix proposals."
    ),
    "michael_bolton": (
        "You are Michael Bolton, RST practitioner and testing/checking distinction expert. "
        "Distinguish: what was CHECKED (automated assertions) vs what needs TESTING (human judgment)? "
        "What does the evidence reveal about product quality that the numbers don't show? "
        "Output: (1) Check vs test distinction, (2) Quality insights, (3) Fix proposals."
    ),
}


# ─── Browser helpers ────────────────────────────────────────────────────────

def _browser_available() -> bool:
    try:
        r = requests.get(f"{BROWSER_API}/api/status", timeout=3)
        return r.ok
    except Exception:
        return False


def navigate(url: str) -> dict:
    r = requests.post(f"{BROWSER_API}/api/navigate", json={"url": url}, timeout=20)
    r.raise_for_status()
    return r.json()


def screenshot(full_page: bool = True) -> str:
    r = requests.post(f"{BROWSER_API}/api/screenshot", json={"full_page": full_page}, timeout=15)
    r.raise_for_status()
    d = r.json()
    return d.get("path") or d.get("filename", "unknown.png")


def aria_snapshot() -> str:
    r = requests.get(f"{BROWSER_API}/api/aria-snapshot", timeout=10)
    r.raise_for_status()
    return r.json().get("snapshot", "")


def evaluate(script: str) -> dict:
    r = requests.post(f"{BROWSER_API}/api/evaluate", json={"script": script}, timeout=10)
    r.raise_for_status()
    result = r.json()
    return result.get("result", result)


def dom_snapshot() -> dict:
    script = """
(function() {
  var links = Array.from(document.querySelectorAll('a[href]')).map(a => ({
    text: a.textContent.trim().slice(0,80), href: a.href
  }));
  var images = Array.from(document.querySelectorAll('img')).map(img => ({
    src: img.src, alt: img.alt,
    loaded: img.complete && img.naturalWidth > 0
  }));
  var h1s = Array.from(document.querySelectorAll('h1')).map(h => h.textContent.trim());
  var forms = Array.from(document.querySelectorAll('form')).length;
  var title = document.title;
  return {
    title, h1s,
    links: links.slice(0,40),
    images: images.slice(0,20),
    forms,
    url: window.location.href
  };
})()
"""
    return evaluate(script)


def heuristic_check() -> dict:
    script = """
(function() {
  var issues = [];
  // ARIA-1: images missing alt
  document.querySelectorAll('img:not([alt])').forEach(function(img) {
    issues.push({severity:'warning', type:'accessibility',
      msg:'Image missing alt attribute: ' + (img.src || '').split('/').pop(),
      heuristic:'ARIA-1'});
  });
  // SEO-1: no H1
  var h1s = document.querySelectorAll('h1');
  if (h1s.length === 0) issues.push({severity:'error', type:'seo',
    msg:'No H1 heading found on page', heuristic:'SEO-1'});
  if (h1s.length > 1) issues.push({severity:'warning', type:'seo',
    msg: h1s.length + ' H1 headings (prefer 1)', heuristic:'SEO-2'});
  // MOBILE-1: no viewport
  if (!document.querySelector('meta[name=viewport]'))
    issues.push({severity:'error', type:'mobile',
      msg:'No viewport meta tag — will not render correctly on mobile', heuristic:'MOBILE-1'});
  // ARIA-2: required inputs without labels
  document.querySelectorAll('input[required]').forEach(function(inp) {
    if (!inp.id && !inp.getAttribute('aria-label'))
      issues.push({severity:'warning', type:'accessibility',
        msg:'Required input missing label: type=' + inp.type, heuristic:'ARIA-2'});
  });
  // CONTENT-1: very little text
  if ((document.body.innerText || '').length < 50)
    issues.push({severity:'warning', type:'content',
      msg:'Very little visible text content', heuristic:'CONTENT-1'});
  // BROKEN-1: broken images
  document.querySelectorAll('img').forEach(function(img) {
    if (img.complete && img.naturalWidth === 0 && img.src)
      issues.push({severity:'error', type:'visual',
        msg:'Broken image: ' + img.src.split('/').pop(), heuristic:'BROKEN-1'});
  });
  // LINK-1: empty links
  document.querySelectorAll('a[href]').forEach(function(a) {
    if (!a.textContent.trim() && !a.getAttribute('aria-label'))
      issues.push({severity:'warning', type:'accessibility',
        msg:'Empty link (no text/aria-label): ' + a.href.split('/').pop(), heuristic:'LINK-1'});
  });
  return {
    issues: issues,
    total_issues: issues.length,
    severity_counts: {
      error: issues.filter(function(i) { return i.severity === 'error'; }).length,
      warning: issues.filter(function(i) { return i.severity === 'warning'; }).length
    }
  };
})()
"""
    return evaluate(script)


# ─── Agent-native analysis request (NO API call) ────────────────────────────

def build_agent_analysis_request(
    persona: str,
    mode: str,
    evidence: dict,
) -> dict:
    """
    Build a structured analysis request for the AI coding agent.
    This is NOT an LLM API call. The agent reads this and applies its own model.
    Cost: $0. Quality: Higher (agent uses its full context, not a separate API call).
    """
    prompt = PERSONA_PROMPTS.get(persona, PERSONA_PROMPTS["james_bach"])
    return {
        "persona": persona,
        "system_prompt": prompt,
        "evidence_summary": evidence,
        "instruction": (
            "Read the evidence_summary above. Apply the persona's framework. "
            "Add your analysis to report.agent_analysis_response with: "
            "top_risks (list), bugs_found (list), fix_proposals (list of "
            "{description, severity, file_path (if known), priority})."
        ),
        "cost": "$0.00",
        "model": "agent-native (no API call — agent uses own model)",
    }


# ─── CLI mode ───────────────────────────────────────────────────────────────

def run_cli(
    cmd: str,
    cwd: str | None = None,
    checks: dict | None = None,
    persona: str = "kent_beck",
    spec_id: str | None = None,
) -> dict:
    """
    Run CLI mode inspection — subprocess + exit code + stdout/stderr + assert.
    """
    run_id = f"cli-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    checks = checks or {}

    print(f"\n{'='*60}")
    print(f"⚙️  Solace Inspector — CLI Mode")
    print(f"   Command: {cmd}")
    print(f"   CWD: {cwd or os.getcwd()}")
    print(f"   Persona: {persona}")
    print(f"   Run ID: {run_id}")
    print(f"{'='*60}")

    report: dict = {
        "run_id": run_id,
        "spec_id": spec_id or run_id,
        "mode": "cli",
        "target_cmd": cmd,
        "target_cwd": cwd or os.getcwd(),
        "persona_used": persona,
        "committee": ["kent_beck", "james_bach", "michael_bolton"],
        "run_at": datetime.datetime.utcnow().isoformat() + "Z",
        "steps_completed": [],
        "fix_proposals": [],
        "human_approved": False,
        "approved_at": None,
    }

    # Step 1: Execute
    print("  Step 1/7: Execute command…")
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30,
        )
        elapsed = time.time() - start_time
        report["exit_code"] = result.returncode
        report["stdout"] = result.stdout[:4000]  # cap at 4K chars
        report["stderr"] = result.stderr[:2000]
        report["duration_seconds"] = round(elapsed, 3)
        report["steps_completed"].append("execute")
        print(f"    → Exit code: {result.returncode} | Duration: {elapsed:.2f}s")
    except subprocess.TimeoutExpired:
        report["error"] = "Command timed out (30s)"
        report["exit_code"] = -1
        report["qa_score"] = 0
        report["belt"] = "White"
        return _seal_report(report, outbox=True)
    except Exception as exc:
        report["error"] = f"Execution failed: {exc}"
        report["qa_score"] = 0
        report["belt"] = "White"
        return _seal_report(report, outbox=True)

    # Step 2: Assert checks
    print("  Step 2/7: Assert checks…")
    assertions: list[dict] = []
    passed = 0

    # Check exit code
    expected_exit = checks.get("exit_code")
    if expected_exit is not None:
        ok = report["exit_code"] == expected_exit
        assertions.append({"check": "exit_code", "expected": expected_exit,
                           "actual": report["exit_code"], "passed": ok})
        if ok:
            passed += 1

    # Check stdout_contains
    for pattern in checks.get("stdout_contains", []):
        ok = pattern.lower() in report["stdout"].lower()
        assertions.append({"check": "stdout_contains", "pattern": pattern, "passed": ok})
        if ok:
            passed += 1

    # Check stderr_empty
    if "stderr_empty" in checks:
        expected_empty = checks["stderr_empty"]
        actual_empty = len(report["stderr"].strip()) == 0
        ok = actual_empty == expected_empty
        assertions.append({"check": "stderr_empty", "expected_empty": expected_empty,
                           "actual_empty": actual_empty, "passed": ok})
        if ok:
            passed += 1

    report["assertions"] = assertions
    report["assertions_passed"] = passed
    report["assertions_total"] = len(assertions)
    report["steps_completed"].append("assert")
    print(f"    → {passed}/{len(assertions)} assertions passed")

    # Step 3: Build agent analysis request
    print(f"  Step 3/7: Build agent analysis request ({persona})…")
    evidence = {
        "cmd": cmd,
        "exit_code": report["exit_code"],
        "stdout_first_500": report["stdout"][:500],
        "stderr_first_200": report["stderr"][:200],
        "duration_seconds": report["duration_seconds"],
        "assertions": assertions,
        "assertions_passed": f"{passed}/{len(assertions)}",
    }
    report["agent_analysis_request"] = build_agent_analysis_request(persona, "cli", evidence)
    report["agent_analysis_response"] = None  # AI coding agent fills this in
    report["steps_completed"].append("agent_analysis_request")
    print(f"    → Analysis request built (agent fills in response)")

    # Step 4: Compute QA score (heuristics only, no LLM)
    print("  Step 4/7: Compute QA score…")
    score, belt, glow = compute_qa_score_cli(passed, len(assertions), report.get("error"))
    report["qa_score"] = score
    report["belt"] = belt
    report["glow"] = glow
    report["steps_completed"].append("compute_score")
    print(f"    → Score: {score}/100 | Belt: {belt} | GLOW: {glow}")

    # Step 5: Seal report
    print("  Step 5/7: Seal with SHA-256…")
    report = _seal_report(report, outbox=True)

    print(f"\n  ✅ Report sealed: outbox/report-{run_id}.json")
    print(f"  📊 QA Score: {score}/100 ({belt} belt) | GLOW: {glow}")
    print(f"  🔐 Evidence: {report.get('evidence_hash', '—')[:30]}…")
    print(f"  🤖 Next: AI coding agent reads report and adds analysis_response")

    return report


def compute_qa_score_cli(passed: int, total: int, error: str | None) -> tuple[int, str, int]:
    """CLI mode QA score based on assertions passed."""
    if error:
        return 0, "White", 0
    if total == 0:
        return 75, "Orange", 78  # no assertions configured
    pct = passed / total
    score = int(pct * 100)
    belt = _score_to_belt(score)
    glow = score + {"Green": 5, "Orange": 3, "Yellow": 2, "White": 1}.get(belt, 1)
    return score, belt, glow


# ─── Web mode ───────────────────────────────────────────────────────────────

def compute_qa_score(heuristic_results: dict) -> tuple[int, str, int]:
    """Compute QA score from heuristics only. Zero LLM dependency."""
    base = 100
    errors = heuristic_results.get("severity_counts", {}).get("error", 0)
    warnings = heuristic_results.get("severity_counts", {}).get("warning", 0)
    score = max(0, min(100, base - (errors * 15) - (warnings * 5)))
    belt = _score_to_belt(score)
    glow = score + {"Green": 5, "Orange": 3, "Yellow": 2, "White": 1}.get(belt, 1)
    return score, belt, glow


def sha256_seal(data: dict) -> str:
    s = json.dumps(data, sort_keys=True, default=str)
    return "sha256:" + hashlib.sha256(s.encode()).hexdigest()


def _seal_report(report: dict, outbox: bool = False) -> dict:
    report["evidence_hash"] = sha256_seal(report)
    if outbox:
        OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
        run_id = report["run_id"]
        report_path = OUTBOX_DIR / f"report-{run_id}.json"
        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)
    return report


def _score_to_belt(score: float) -> str:
    if score >= 90:
        return "Green"
    if score >= 75:
        return "Orange"
    if score >= 60:
        return "Yellow"
    return "White"


def run_qa(
    target_url: str,
    page_name: str | None = None,
    persona: str = "james_bach",
    baseline_id: str | None = None,
    spec_id: str | None = None,
) -> dict:
    """
    Run the 8-step QA recipe on a single URL.
    Agent-native: no LLM API calls. Returns sealed report dict.
    """
    run_id = f"qa-{datetime.datetime.utcnow().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
    page_name = page_name or target_url.split("/")[-1] or "home"

    print(f"\n{'='*60}")
    print(f"🔍 Solace Inspector — Web Mode")
    print(f"   URL: {target_url}")
    print(f"   Persona: {persona}")
    print(f"   Run ID: {run_id}")
    print(f"   LLM cost: $0.00 (agent-native)")
    print(f"{'='*60}")

    report: dict = {
        "run_id": run_id,
        "spec_id": spec_id or run_id,
        "mode": "web",
        "target_url": target_url,
        "page_name": page_name,
        "persona_used": persona,
        "committee": [
            "james_bach", "elisabeth_hendrickson",
            "kent_beck", "cem_kaner", "michael_bolton",
        ],
        "run_at": datetime.datetime.utcnow().isoformat() + "Z",
        "steps_completed": [],
        "fix_proposals": [],
        "human_approved": False,
        "approved_at": None,
        "agent_analysis_response": None,  # AI coding agent fills this in
    }

    # Step 1: Navigate
    print("  Step 1/8: Navigate…")
    try:
        navigate(target_url)
        report["steps_completed"].append("navigate")
        time.sleep(1)
    except Exception as exc:
        report["error"] = f"Navigation failed: {exc}"
        report["qa_score"] = 0
        report["belt"] = "White"
        report["glow"] = 0
        return _seal_report(report, outbox=True)

    # Step 2: ARIA Snapshot
    print("  Step 2/8: ARIA snapshot…")
    try:
        aria_tree = aria_snapshot()
        report["aria_tree_length"] = len(str(aria_tree))
        report["aria_tree_excerpt"] = str(aria_tree)[:1000]
        report["steps_completed"].append("aria_snapshot")
    except Exception as exc:
        aria_tree = ""
        print(f"    ⚠️  ARIA snapshot failed: {exc}")

    # Step 3: DOM Snapshot
    print("  Step 3/8: DOM snapshot…")
    try:
        dom_data = dom_snapshot()
        report["dom_title"] = dom_data.get("title", "")
        report["dom_h1s"] = dom_data.get("h1s", [])
        report["dom_links_count"] = len(dom_data.get("links", []))
        report["dom_images_count"] = len(dom_data.get("images", []))
        report["dom_forms"] = dom_data.get("forms", 0)
        report["dom_links_sample"] = dom_data.get("links", [])[:10]
        report["steps_completed"].append("dom_snapshot")
    except Exception as exc:
        dom_data = {}
        print(f"    ⚠️  DOM snapshot failed: {exc}")

    # Step 4: Heuristic Check (HICCUPPS)
    print("  Step 4/8: Heuristic checks (HICCUPPS)…")
    try:
        heuristic_results = heuristic_check()
        issues = heuristic_results.get("issues", [])
        report["heuristic_issues"] = issues
        report["heuristic_error_count"] = heuristic_results.get("severity_counts", {}).get("error", 0)
        report["heuristic_warning_count"] = heuristic_results.get("severity_counts", {}).get("warning", 0)
        report["steps_completed"].append("heuristic_check")
        print(
            f"    → {len(issues)} issues: "
            f"{report['heuristic_error_count']} errors, "
            f"{report['heuristic_warning_count']} warnings"
        )
    except Exception as exc:
        heuristic_results = {"issues": [], "severity_counts": {}}
        issues = []
        print(f"    ⚠️  Heuristic check failed: {exc}")

    # Step 5: Screenshot
    print("  Step 5/8: Full-page screenshot…")
    try:
        shot_path = screenshot(full_page=True)
        report["screenshot_path"] = shot_path
        report["steps_completed"].append("screenshot")
        print(f"    → {shot_path}")
    except Exception as exc:
        report["screenshot_path"] = None
        print(f"    ⚠️  Screenshot failed: {exc}")

    # Step 6: Build agent analysis request (NO API call)
    print(f"  Step 6/8: Build agent analysis request ({persona})…")
    evidence = {
        "url": target_url,
        "page_name": page_name,
        "dom_title": report.get("dom_title", ""),
        "dom_h1s": report.get("dom_h1s", []),
        "dom_links_count": report.get("dom_links_count", 0),
        "dom_links_sample": report.get("dom_links_sample", []),
        "dom_images_count": report.get("dom_images_count", 0),
        "dom_forms": report.get("dom_forms", 0),
        "aria_tree_excerpt": report.get("aria_tree_excerpt", ""),
        "heuristic_issues": issues[:15],
        "heuristic_error_count": report.get("heuristic_error_count", 0),
        "heuristic_warning_count": report.get("heuristic_warning_count", 0),
        "screenshot_path": report.get("screenshot_path"),
    }
    report["agent_analysis_request"] = build_agent_analysis_request(persona, "web", evidence)
    report["steps_completed"].append("agent_analysis_request")
    print(f"    → Analysis request built (cost: $0.00 — agent uses own model)")

    # Step 7: Compute QA score (heuristics only, no LLM)
    print("  Step 7/8: Compute QA score…")
    score, belt, glow = compute_qa_score(heuristic_results)
    report["qa_score"] = score
    report["belt"] = belt
    report["glow"] = glow
    report["steps_completed"].append("compute_score")
    print(f"    → Score: {score}/100 | Belt: {belt} | GLOW: {glow}")

    # Step 8: Seal with SHA-256
    print("  Step 8/8: Seal with SHA-256…")
    report = _seal_report(report, outbox=True)
    report_path = OUTBOX_DIR / f"report-{run_id}.json"

    print(f"\n  ✅ Report sealed: {report_path}")
    print(f"  📊 QA Score: {score}/100 ({belt} belt) | GLOW: {glow}")
    print(f"  🔐 Evidence: {report.get('evidence_hash', '—')[:30]}…")
    print(f"  🤖 Next: AI coding agent reads report → adds analysis_response → human approves fixes")

    return report


# ─── Self-diagnostic ────────────────────────────────────────────────────────

def run_self_diagnostic() -> dict:
    """QA all solace-browser pages. Returns summary."""
    print("\n🔍 SELF-DIAGNOSTIC MODE — Solace Browser")
    print("   Scanning all core pages…\n")
    results = []
    for page in SELF_DIAGNOSTIC_PAGES:
        try:
            r = run_qa(
                page["url"],
                page["name"],
                persona="james_bach",
                spec_id="self-diag-" + datetime.datetime.utcnow().strftime("%Y%m%d"),
            )
            results.append(r)
        except Exception as exc:
            print(f"  ❌ Failed: {page['name']} — {exc}")
            results.append({
                "page_name": page["name"],
                "target_url": page["url"],
                "qa_score": 0,
                "belt": "White",
                "error": str(exc),
            })

    scores = [r.get("qa_score", 0) for r in results]
    avg_score = sum(scores) / len(scores) if scores else 0
    summary = {
        "run_type": "self-diagnostic",
        "run_at": datetime.datetime.utcnow().isoformat() + "Z",
        "pages_checked": len(results),
        "average_qa_score": round(avg_score, 1),
        "overall_belt": _score_to_belt(avg_score),
        "page_results": [
            {"name": r.get("page_name"), "score": r.get("qa_score", 0), "belt": r.get("belt")}
            for r in results
        ],
    }

    OUTBOX_DIR.mkdir(parents=True, exist_ok=True)
    summary_path = OUTBOX_DIR / f"self-diag-{datetime.datetime.utcnow().strftime('%Y%m%d')}.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*60}")
    print(f"📊 SELF-DIAGNOSTIC COMPLETE")
    print(f"   Average score: {avg_score:.1f}/100 ({summary['overall_belt']} belt)")
    for r in summary["page_results"]:
        icon = "✅" if r["score"] >= 75 else "⚠️" if r["score"] >= 60 else "❌"
        print(f"   {icon} {r['name']}: {r['score']}/100 ({r['belt']})")
    print(f"   Summary: {summary_path}")
    print(f"{'='*60}")

    return summary


# ─── Inbox processor ────────────────────────────────────────────────────────

def process_inbox() -> list[dict]:
    """Process all test specs in inbox/. Returns list of reports."""
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    specs = sorted(INBOX_DIR.glob("test-spec-*.json"))
    if not specs:
        print("📥 Inbox is empty. Drop test-spec-*.json files to queue QA runs.")
        return []

    reports = []
    for spec_path in specs:
        with open(spec_path) as f:
            spec = json.load(f)
        print(f"\n📥 Processing: {spec_path.name}")

        mode = spec.get("mode", "web")
        persona = spec.get("persona", "james_bach")
        checks = spec.get("checks", {})
        spec_id = spec.get("spec_id")

        if mode == "cli":
            r = run_cli(
                cmd=spec["target_cmd"],
                cwd=spec.get("target_cwd"),
                checks=checks,
                persona=persona,
                spec_id=spec_id,
            )
        elif mode == "web":
            if not _browser_available():
                print(f"  ⚠️  Browser not running — skipping web spec {spec_path.name}")
                print("     Start with: python3 solace_browser_server.py --port 9222 --head")
                continue
            r = run_qa(
                target_url=spec["target_url"],
                page_name=spec.get("page_name"),
                persona=persona,
                baseline_id=checks.get("baseline_id"),
                spec_id=spec_id,
            )
        else:
            print(f"  ⚠️  Unknown mode '{mode}' — skipping {spec_path.name}")
            continue

        reports.append(r)
        # Archive processed spec
        done_dir = INBOX_DIR / "processed"
        done_dir.mkdir(exist_ok=True)
        spec_path.rename(done_dir / spec_path.name)

    return reports


# ─── Entry point ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Solace Inspector (Paper 42, Auth 65537) — Agent-native QA for any target",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 scripts/run_solace_inspector.py --url http://localhost:8791/
  python3 scripts/run_solace_inspector.py --url https://solaceagi.com --persona cem_kaner
  python3 scripts/run_solace_inspector.py --cmd "python3 server.py --help" --cwd /path/to/project
  python3 scripts/run_solace_inspector.py --self-diagnostic
  python3 scripts/run_solace_inspector.py --inbox

Output: data/default/apps/solace-inspector/outbox/report-*.json
Architecture: Agent-native (zero LLM API calls — your AI agent reads reports and analyzes)
        """,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--url", help="[web mode] URL to inspect")
    group.add_argument("--cmd", help="[cli mode] Command to run")
    group.add_argument("--self-diagnostic", action="store_true",
                       help="QA all solace-browser pages (web mode)")
    group.add_argument("--inbox", action="store_true",
                       help="Process all inbox/ test specs (auto-detect mode)")
    parser.add_argument("--persona", default="james_bach",
                        choices=list(PERSONA_PROMPTS.keys()),
                        help="Analysis persona (for agent_analysis_request)")
    parser.add_argument("--name", help="Human-readable target name")
    parser.add_argument("--cwd", help="[cli mode] Working directory for command")
    parser.add_argument("--baseline", help="[web mode] Baseline run_id to diff against")
    args = parser.parse_args()

    if args.cmd:
        # CLI mode — no browser required
        run_cli(args.cmd, cwd=args.cwd, persona=args.persona)
        return

    if not args.inbox and not args.self_diagnostic and not args.url:
        parser.print_help()
        sys.exit(1)

    # For --inbox, skip browser check — CLI specs don't need browser.
    # Browser check happens inside run_qa() if needed.
    if not args.inbox and not _browser_available():
        print("❌ Solace Browser not running. Start with:")
        print("   python3 solace_browser_server.py --port 9222 --head")
        sys.exit(1)

    if args.self_diagnostic:
        run_self_diagnostic()
    elif args.inbox:
        process_inbox()
    elif args.url:
        run_qa(args.url, page_name=args.name, persona=args.persona, baseline_id=args.baseline)


if __name__ == "__main__":
    main()
