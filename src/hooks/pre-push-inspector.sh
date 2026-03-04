#!/usr/bin/env bash
# pre-push-inspector.sh — Solace Inspector Pre-Push Certification Gate
# Auth: 65537 | Paper 44 | Committee: Bach · Hendrickson · Bolton · Beck · Vogels
# DNA: gate(deploy) = certify(northstars) * seal(evidence); ship_only_if_green
#
# Install: cp src/hooks/pre-push-inspector.sh .git/hooks/pre-push && chmod +x .git/hooks/pre-push
# Bypass:  INSPECTOR_SKIP=1 git push  (hotfixes only — bypass is logged, never silent)
#
# Gates (both must pass for push to proceed):
#   Gate 1 — CPU Gate:       all CLI specs must report Belt: Green (no White, no Orange)
#   Gate 2 — Northstar Gate: no northstar JSON may have certification_status=BROKEN or =UNCERTIFIED
#
# Optional:
#   Gate 3 — LLM Gate:       ABCD specs run if SOLACE_API_KEY is set; warns if evidence >90 days old
#
# Fail-safe rule: if Inspector cannot run (infra issue), gate blocks.
#   Exception: if Solace Browser is not running, web specs are skipped — CLI specs still run.
#   The gate blocks only on actual quality failures, not infrastructure absences.

set -euo pipefail

# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

GATE_VERSION="1.0"
LOG_FILE="/tmp/inspector-pre-push.log"
BYPASS_LOG_RELATIVE="data/default/apps/solace-inspector/bypass.log"
NORTHSTARS_RELATIVE="data/default/apps/solace-inspector/inbox/northstars"
RUNNER_RELATIVE="scripts/run_solace_inspector.py"
ABCD_STALE_DAYS=90

# Colors (safe — only used when stdout is a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    RED='' GREEN='' YELLOW='' CYAN='' BOLD='' RESET=''
fi

# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

print_header() {
    echo ""
    echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}${CYAN}║   Solace Inspector — Pre-Push Certification Gate    ║${RESET}"
    echo -e "${BOLD}${CYAN}║   Auth: 65537 | Paper 44 | gate v${GATE_VERSION}              ║${RESET}"
    echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${RESET}"
    echo ""
}

print_pass() {
    echo -e "${GREEN}  ✓ $1${RESET}"
}

print_fail() {
    echo -e "${RED}  ✗ $1${RESET}"
}

print_warn() {
    echo -e "${YELLOW}  ⚠ $1${RESET}"
}

print_section() {
    echo ""
    echo -e "${BOLD}── $1 ──${RESET}"
}

# ─────────────────────────────────────────────────────────────────────────────
# Step 0: Detect project root
# ─────────────────────────────────────────────────────────────────────────────

PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    echo "ERROR: Cannot determine git project root. Are you inside a git repository?"
    exit 1
}

BYPASS_LOG="${PROJECT_ROOT}/${BYPASS_LOG_RELATIVE}"
NORTHSTARS_DIR="${PROJECT_ROOT}/${NORTHSTARS_RELATIVE}"
RUNNER="${PROJECT_ROOT}/${RUNNER_RELATIVE}"

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Check INSPECTOR_SKIP — emergency bypass for hotfixes
# ─────────────────────────────────────────────────────────────────────────────

if [ "${INSPECTOR_SKIP:-}" = "1" ]; then
    print_header
    print_warn "INSPECTOR_SKIP=1 detected — emergency bypass activated."
    print_warn "This bypass is LOGGED. Northstar certification was NOT verified."
    echo ""

    # Write bypass record to evidence log
    BYPASS_TIMESTAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    BYPASS_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
    BYPASS_USER="$(git config user.name 2>/dev/null || echo unknown)"
    BYPASS_COMMIT="$(git rev-parse --short HEAD 2>/dev/null || echo unknown)"

    mkdir -p "$(dirname "${BYPASS_LOG}")"
    {
        echo "────────────────────────────────────────"
        echo "${BYPASS_TIMESTAMP} | BYPASS | branch=${BYPASS_BRANCH} | user=${BYPASS_USER} | commit=${BYPASS_COMMIT}"
        echo "  WARNING: CPU gate and northstar gate bypassed."
        echo "  Required: Run full Inspector gate before next sprint end."
        echo "  Command: python3 scripts/run_solace_inspector.py --inbox"
    } >> "${BYPASS_LOG}"

    echo -e "${YELLOW}  Bypass record written to: ${BYPASS_LOG_RELATIVE}${RESET}"
    echo -e "${YELLOW}  Required: run full Inspector gate before next sprint end.${RESET}"
    echo ""
    echo -e "${YELLOW}  Allowing push. Fix the northstars after the hotfix.${RESET}"
    echo ""
    exit 0
fi

# ─────────────────────────────────────────────────────────────────────────────
# Setup: clear log, print header
# ─────────────────────────────────────────────────────────────────────────────

print_header
: > "${LOG_FILE}"   # truncate/create the log file

GATE_FAILED=0
CPU_SPECS_TOTAL=0
CPU_SPECS_PASS=0
CPU_SPECS_FAIL=0
NORTHSTAR_TOTAL=0
NORTHSTAR_BROKEN=0
NORTHSTAR_UNCERTIFIED=0

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Verify Inspector runner exists
# ─────────────────────────────────────────────────────────────────────────────

print_section "Gate 0: Inspector Runner"

if [ ! -f "${RUNNER}" ]; then
    print_fail "Inspector runner not found: ${RUNNER_RELATIVE}"
    print_fail "Cannot certify northstars without the runner."
    print_fail "Fix: ensure scripts/run_solace_inspector.py exists."
    echo ""
    echo -e "${RED}${BOLD}Inspector gate: FAILED — runner missing.${RESET}"
    echo ""
    exit 1
fi

print_pass "Runner found: ${RUNNER_RELATIVE}"

# Check python3 is available
if ! command -v python3 &> /dev/null; then
    print_fail "python3 not found in PATH."
    print_fail "Fix: install Python 3.9+ and ensure it is in PATH."
    echo ""
    echo -e "${RED}${BOLD}Inspector gate: FAILED — python3 missing.${RESET}"
    echo ""
    exit 1
fi

print_pass "python3 available: $(python3 --version 2>&1)"

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Check if Solace Browser is running (web mode probe — non-blocking)
# ─────────────────────────────────────────────────────────────────────────────

print_section "Gate 0b: Browser Status (web mode probe)"

BROWSER_RUNNING=0
if curl -sf --max-time 2 "http://localhost:9222" &>/dev/null 2>&1; then
    BROWSER_RUNNING=1
    print_pass "Solace Browser detected on localhost:9222 — web specs will run."
elif curl -sf --max-time 2 "http://127.0.0.1:8791/" &>/dev/null 2>&1; then
    BROWSER_RUNNING=1
    print_pass "Solace Browser web UI detected on 127.0.0.1:8791 — web specs will run."
else
    print_warn "Solace Browser not running. Web specs will be skipped."
    print_warn "CLI specs will still run. Gate does not block on infrastructure absence."
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Gate 1 — CPU Gate (run --inbox, check for failing belts)
# ─────────────────────────────────────────────────────────────────────────────

print_section "Gate 1: CPU Specs (--inbox)"
echo "  Running: python3 ${RUNNER_RELATIVE} --inbox"
echo "  Log: ${LOG_FILE}"
echo ""

cd "${PROJECT_ROOT}"

# Run inspector, tee output to log AND terminal
if python3 "${RUNNER}" --inbox 2>&1 | tee "${LOG_FILE}"; then
    INSPECTOR_EXIT=0
else
    INSPECTOR_EXIT=${PIPESTATUS[0]}
fi

echo ""

# Count specs by reading the log
CPU_SPECS_TOTAL=$(grep -c "Belt:" "${LOG_FILE}" 2>/dev/null || echo 0)

# Check for failing belts (White = score<70, Orange = score 70-79)
BELT_WHITE_LINES=$(grep -n "Belt: White" "${LOG_FILE}" 2>/dev/null || true)
BELT_ORANGE_LINES=$(grep -n "Belt: Orange" "${LOG_FILE}" 2>/dev/null || true)

if [ -n "${BELT_WHITE_LINES}" ]; then
    CPU_SPECS_FAIL=$(echo "${BELT_WHITE_LINES}" | wc -l | tr -d ' ')
    GATE_FAILED=1
    print_fail "Belt: White detected in ${CPU_SPECS_FAIL} spec(s) — these are regressions:"
    while IFS= read -r line; do
        echo -e "    ${RED}${line}${RESET}"
    done <<< "${BELT_WHITE_LINES}"
fi

if [ -n "${BELT_ORANGE_LINES}" ]; then
    ORANGE_COUNT=$(echo "${BELT_ORANGE_LINES}" | wc -l | tr -d ' ')
    CPU_SPECS_FAIL=$((CPU_SPECS_FAIL + ORANGE_COUNT))
    GATE_FAILED=1
    print_fail "Belt: Orange detected in ${ORANGE_COUNT} spec(s) — below deploy threshold:"
    while IFS= read -r line; do
        echo -e "    ${RED}${line}${RESET}"
    done <<< "${BELT_ORANGE_LINES}"
fi

if [ "${INSPECTOR_EXIT}" -ne 0 ] && [ -z "${BELT_WHITE_LINES}" ] && [ -z "${BELT_ORANGE_LINES}" ]; then
    GATE_FAILED=1
    print_fail "Inspector runner exited with code ${INSPECTOR_EXIT} — inspect log for errors."
    print_fail "Log: ${LOG_FILE}"
fi

CPU_SPECS_PASS=$((CPU_SPECS_TOTAL - CPU_SPECS_FAIL))

if [ "${GATE_FAILED}" -eq 0 ]; then
    print_pass "CPU Gate: all ${CPU_SPECS_TOTAL} spec(s) Green — no regressions found."
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Gate 2 — Northstar Gate (check JSON files for BROKEN/UNCERTIFIED)
# ─────────────────────────────────────────────────────────────────────────────

print_section "Gate 2: Northstar Contracts (inbox/northstars/)"

NORTHSTAR_GATE_FAILED=0

if [ ! -d "${NORTHSTARS_DIR}" ]; then
    print_warn "No northstars directory found at ${NORTHSTARS_RELATIVE}"
    print_warn "Skipping northstar gate — no contracts to check."
else
    # Find all northstar JSON files
    NORTHSTAR_FILES=$(find "${NORTHSTARS_DIR}" -name "*.json" -type f 2>/dev/null || true)
    NORTHSTAR_TOTAL=$(echo "${NORTHSTAR_FILES}" | grep -c "." 2>/dev/null || echo 0)

    if [ -z "${NORTHSTAR_FILES}" ]; then
        print_warn "No northstar JSON files found in ${NORTHSTARS_RELATIVE}"
        print_warn "Skipping northstar gate."
    else
        echo "  Checking ${NORTHSTAR_TOTAL} northstar contract(s)..."
        echo ""

        while IFS= read -r ns_file; do
            [ -z "${ns_file}" ] && continue

            NS_NAME="$(basename "${ns_file}" .json)"
            CERT_STATUS="$(python3 -c "
import json, sys
try:
    with open('${ns_file}') as f:
        d = json.load(f)
    print(d.get('certification_status', 'UNKNOWN'))
except Exception as e:
    print('READ_ERROR: ' + str(e))
" 2>/dev/null || echo "READ_ERROR")"

            case "${CERT_STATUS}" in
                *BROKEN*)
                    NORTHSTAR_BROKEN=$((NORTHSTAR_BROKEN + 1))
                    NORTHSTAR_GATE_FAILED=1
                    print_fail "${NS_NAME}: certification_status=BROKEN"
                    print_fail "  Endpoint regressed. Re-certify before pushing to main."
                    ;;
                UNCERTIFIED)
                    NORTHSTAR_UNCERTIFIED=$((NORTHSTAR_UNCERTIFIED + 1))
                    NORTHSTAR_GATE_FAILED=1
                    print_fail "${NS_NAME}: certification_status=UNCERTIFIED"
                    print_fail "  Add cpu_tests[], run Inspector, certify before pushing."
                    ;;
                *CERTIFIED*)
                    print_pass "${NS_NAME}: ${CERT_STATUS}"
                    ;;
                READ_ERROR*)
                    print_warn "${NS_NAME}: could not parse JSON — ${CERT_STATUS}"
                    ;;
                *)
                    print_warn "${NS_NAME}: unknown status '${CERT_STATUS}'"
                    ;;
            esac

        done <<< "${NORTHSTAR_FILES}"

        if [ "${NORTHSTAR_GATE_FAILED}" -eq 1 ]; then
            GATE_FAILED=1
            echo ""
            print_fail "Northstar Gate: ${NORTHSTAR_BROKEN} BROKEN + ${NORTHSTAR_UNCERTIFIED} UNCERTIFIED — fix before pushing."
        else
            echo ""
            print_pass "Northstar Gate: all ${NORTHSTAR_TOTAL} northstar(s) certified."
        fi
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Gate 3 — LLM Gate (optional, only when SOLACE_API_KEY is set)
# ─────────────────────────────────────────────────────────────────────────────

print_section "Gate 3: LLM Gate (ABCD specs — optional)"

if [ -z "${SOLACE_API_KEY:-}" ]; then
    print_warn "SOLACE_API_KEY not set — LLM/ABCD specs skipped."
    print_warn "To run ABCD gate: SOLACE_API_KEY=<key> git push"
    print_warn "ABCD gate is advisory. CPU + Northstar gates are mandatory."
else
    echo "  SOLACE_API_KEY detected — checking ABCD evidence age..."

    # Check age of ABCD-related outbox reports
    OUTBOX_DIR="${PROJECT_ROOT}/data/default/apps/solace-inspector/outbox"
    ABCD_STALE_FOUND=0
    ABCD_STALE_NAMES=""

    if [ -d "${OUTBOX_DIR}" ]; then
        # Find any northstar with abcd_tests that have a certified_at date
        if [ -d "${NORTHSTARS_DIR}" ]; then
            while IFS= read -r ns_file; do
                [ -z "${ns_file}" ] && continue

                NS_NAME="$(basename "${ns_file}" .json)"

                # Extract certified_at and check if it has abcd_tests
                ABCD_INFO=$(python3 -c "
import json, sys
from datetime import datetime, timezone
try:
    with open('${ns_file}') as f:
        d = json.load(f)
    abcd = d.get('abcd_tests', [])
    if not abcd:
        sys.exit(0)
    certified_at = d.get('certified_at')
    if not certified_at:
        print('NO_DATE')
        sys.exit(0)
    try:
        cert_date = datetime.fromisoformat(certified_at.replace('Z',''))
        cert_date = cert_date.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        age_days = (now - cert_date).days
        print(str(age_days))
    except Exception:
        print('PARSE_ERROR')
except Exception as e:
    print('ERROR: ' + str(e))
" 2>/dev/null || echo "")

                if [ "${ABCD_INFO}" = "NO_DATE" ]; then
                    print_warn "${NS_NAME}: ABCD tests listed but no certified_at date."
                elif [ -n "${ABCD_INFO}" ] && echo "${ABCD_INFO}" | grep -qE '^[0-9]+$'; then
                    AGE_DAYS="${ABCD_INFO}"
                    if [ "${AGE_DAYS}" -gt "${ABCD_STALE_DAYS}" ]; then
                        ABCD_STALE_FOUND=1
                        ABCD_STALE_NAMES="${ABCD_STALE_NAMES} ${NS_NAME}(${AGE_DAYS}d)"
                        print_warn "${NS_NAME}: ABCD evidence is ${AGE_DAYS} days old (>${ABCD_STALE_DAYS}d threshold)."
                    else
                        print_pass "${NS_NAME}: ABCD evidence is ${AGE_DAYS} days old — fresh."
                    fi
                fi

            done <<< "$(find "${NORTHSTARS_DIR}" -name "*.json" -type f 2>/dev/null)"
        fi
    fi

    if [ "${ABCD_STALE_FOUND}" -eq 1 ]; then
        print_warn "Stale ABCD evidence detected for:${ABCD_STALE_NAMES}"
        print_warn "LLM model prices/quality may have changed."
        print_warn "Refresh: SOLACE_API_KEY=<key> python3 scripts/run_solace_inspector.py --inbox"
        print_warn "LLM Gate is advisory — push is NOT blocked by stale ABCD evidence."
    else
        print_pass "LLM Gate: ABCD evidence is current (all within ${ABCD_STALE_DAYS} days)."
    fi
fi

# ─────────────────────────────────────────────────────────────────────────────
# Step 7: Final verdict
# ─────────────────────────────────────────────────────────────────────────────

echo ""
echo -e "${BOLD}── Certification Gate Verdict ──${RESET}"
echo ""

# Build a spec count summary from the log
GREEN_COUNT=$(grep -c "Belt: Green" "${LOG_FILE}" 2>/dev/null || echo 0)
TOTAL_BELT_COUNT=$(grep -c "Belt:" "${LOG_FILE}" 2>/dev/null || echo 0)

if [ "${GATE_FAILED}" -eq 0 ]; then
    echo -e "${GREEN}${BOLD}"
    echo "  ╔════════════════════════════════════════════╗"
    echo "  ║  Inspector gate: PASSED                    ║"
    printf "  ║  %-43s║\n" "CPU specs: ${GREEN_COUNT}/${TOTAL_BELT_COUNT} Green"
    printf "  ║  %-43s║\n" "Northstars: ${NORTHSTAR_TOTAL} certified"
    echo "  ║  Push allowed. Evidence sealed.            ║"
    echo "  ╚════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo "  Full log: ${LOG_FILE}"
    echo ""
    exit 0
else
    echo -e "${RED}${BOLD}"
    echo "  ╔════════════════════════════════════════════╗"
    echo "  ║  Inspector gate: FAILED                    ║"
    if [ "${CPU_SPECS_FAIL}" -gt 0 ]; then
        printf "  ║  %-43s║\n" "CPU regressions: ${CPU_SPECS_FAIL} spec(s) failing"
    fi
    if [ "${NORTHSTAR_BROKEN}" -gt 0 ]; then
        printf "  ║  %-43s║\n" "Northstars BROKEN: ${NORTHSTAR_BROKEN}"
    fi
    if [ "${NORTHSTAR_UNCERTIFIED}" -gt 0 ]; then
        printf "  ║  %-43s║\n" "Northstars UNCERTIFIED: ${NORTHSTAR_UNCERTIFIED}"
    fi
    echo "  ║  Fix before pushing to main.               ║"
    echo "  ╚════════════════════════════════════════════╝"
    echo -e "${RESET}"
    echo ""
    echo "  Diagnosis:"
    if [ "${CPU_SPECS_FAIL}" -gt 0 ]; then
        echo "    1. Read the failing spec output above."
        echo "    2. Identify what changed in this push that broke the spec."
        echo "    3. Fix the code (not the spec) and re-run: python3 scripts/run_solace_inspector.py --inbox"
    fi
    if [ "${NORTHSTAR_BROKEN}" -gt 0 ]; then
        echo "    1. Check inbox/northstars/ for BROKEN northstar."
        echo "    2. Fix the endpoint to match its contract."
        echo "    3. Update certification_status to CPU_CERTIFIED + re-run Inspector."
    fi
    if [ "${NORTHSTAR_UNCERTIFIED}" -gt 0 ]; then
        echo "    1. Write cpu_tests[] for each UNCERTIFIED northstar in inbox/."
        echo "    2. Run Inspector --inbox to certify them."
        echo "    3. Update certification_status to CPU_CERTIFIED."
    fi
    echo ""
    echo "  Emergency hotfix: INSPECTOR_SKIP=1 git push (bypass is logged)"
    echo "  Full log: ${LOG_FILE}"
    echo ""
    exit 1
fi
