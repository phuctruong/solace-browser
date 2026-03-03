#!/usr/bin/env bash
# Compile -> upload -> download -> smoke loop for Solace Browser release.
# Outputs metrics and logs into scratch/release-cycle/<timestamp>/.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

VERSION="${VERSION:-$(cat VERSION 2>/dev/null || echo 1.0.0)}"
BUCKET="${BUCKET:-solace-downloads}"
OBJECT_PREFIX="${OBJECT_PREFIX:-solace-browser}"
OBJECT_NAME="${OBJECT_NAME:-solace-browser-linux-x86_64}"
UPLOAD_ENABLED="${UPLOAD_ENABLED:-1}"
RUN_SMOKE="${RUN_SMOKE:-1}"
HEAD_MODE="${HEAD_MODE:---head}"
SMOKE_PORT="${SMOKE_PORT:-9232}"
COMPILE_TIMEOUT="${COMPILE_TIMEOUT:-1800}"

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$PROJECT_ROOT/scratch/release-cycle/$STAMP"
mkdir -p "$OUT_DIR"

log() { printf "[release-cycle] %s\n" "$*"; }

t_ms() { python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

BUILD_START="$(t_ms)"
log "Step 1/6: compile browser binary with PyInstaller (head-on runtime target)."
set +e
timeout "$COMPILE_TIMEOUT" pyinstaller --noconfirm solace-browser.spec >"$OUT_DIR/pyinstaller.log" 2>&1
BUILD_RC=$?
set -e
BUILD_END="$(t_ms)"

if [[ "$BUILD_RC" -ne 0 ]]; then
  log "ERROR: compile step failed (rc=$BUILD_RC). See $OUT_DIR/pyinstaller.log"
  exit 1
fi

BIN_PATH="$PROJECT_ROOT/dist/solace-browser"
if [[ ! -f "$BIN_PATH" ]]; then
  log "ERROR: expected binary not found at $BIN_PATH"
  exit 1
fi

cp "$BIN_PATH" "$PROJECT_ROOT/dist/$OBJECT_NAME"
sha256sum "$PROJECT_ROOT/dist/$OBJECT_NAME" > "$PROJECT_ROOT/dist/$OBJECT_NAME.sha256"
cp "$PROJECT_ROOT/dist/$OBJECT_NAME" "$OUT_DIR/$OBJECT_NAME"
cp "$PROJECT_ROOT/dist/$OBJECT_NAME.sha256" "$OUT_DIR/$OBJECT_NAME.sha256"

UPLOAD_V_PATH="gs://$BUCKET/$OBJECT_PREFIX/v$VERSION/$OBJECT_NAME"
UPLOAD_LATEST_PATH="gs://$BUCKET/$OBJECT_PREFIX/latest/$OBJECT_NAME"

UPLOAD_START=0
UPLOAD_END=0
if [[ "$UPLOAD_ENABLED" == "1" ]]; then
  UPLOAD_START="$(t_ms)"
  log "Step 2/6: upload versioned artifact -> $UPLOAD_V_PATH"
  set +e
  gcloud storage cp "$PROJECT_ROOT/dist/$OBJECT_NAME" "$UPLOAD_V_PATH" >"$OUT_DIR/upload-versioned.log" 2>&1
  UPLOAD_V_RC=$?
  set -e
  if [[ "$UPLOAD_V_RC" -ne 0 ]]; then
    log "ERROR: upload versioned failed (rc=$UPLOAD_V_RC). See $OUT_DIR/upload-versioned.log"
    exit 1
  fi
  log "Step 3/6: upload latest artifact -> $UPLOAD_LATEST_PATH"
  set +e
  gcloud storage cp "$PROJECT_ROOT/dist/$OBJECT_NAME" "$UPLOAD_LATEST_PATH" >"$OUT_DIR/upload-latest.log" 2>&1
  UPLOAD_L_RC=$?
  set -e
  if [[ "$UPLOAD_L_RC" -ne 0 ]]; then
    log "ERROR: upload latest failed (rc=$UPLOAD_L_RC). See $OUT_DIR/upload-latest.log"
    exit 1
  fi
  UPLOAD_END="$(t_ms)"
else
  log "Upload disabled (UPLOAD_ENABLED=0)."
fi

DL_START="$(t_ms)"
log "Step 4/6: download latest artifact from production bucket."
curl -fsSL "https://storage.googleapis.com/$BUCKET/$OBJECT_PREFIX/latest/$OBJECT_NAME" -o "$OUT_DIR/downloaded-$OBJECT_NAME"
chmod +x "$OUT_DIR/downloaded-$OBJECT_NAME"
DL_END="$(t_ms)"

SMOKE_STATUS="skipped"
SMOKE_START=0
SMOKE_END=0
if [[ "$RUN_SMOKE" == "1" ]]; then
  SMOKE_START="$(t_ms)"
  log "Step 5/6: run smoke server with head mode ($HEAD_MODE) on port $SMOKE_PORT."
  set +e
  timeout 35s "$OUT_DIR/downloaded-$OBJECT_NAME" $HEAD_MODE --port "$SMOKE_PORT" >"$OUT_DIR/smoke.log" 2>&1 &
  BIN_PID=$!
  READY=0
  for _ in $(seq 1 50); do
    if curl -fsS "http://127.0.0.1:$SMOKE_PORT/api/status" >"$OUT_DIR/smoke-status.json" 2>/dev/null; then
      READY=1
      break
    fi
    sleep 0.4
  done
  if [[ "$READY" == "1" ]]; then
    SMOKE_STATUS="passed"
    curl -fsS "http://127.0.0.1:$SMOKE_PORT/api/health" >"$OUT_DIR/smoke-health.json" 2>/dev/null || true
  else
    SMOKE_STATUS="failed"
  fi
  kill "$BIN_PID" >/dev/null 2>&1 || true
  wait "$BIN_PID" >/dev/null 2>&1 || true
  set -e
  SMOKE_END="$(t_ms)"
fi

log "Step 6/6: write benchmark and release report."
python3 - <<PY
import json
from pathlib import Path

out_dir = Path("$OUT_DIR")
binary = out_dir / "$OBJECT_NAME"
size_bytes = binary.stat().st_size

build_ms = $BUILD_END - $BUILD_START
upload_ms = ($UPLOAD_END - $UPLOAD_START) if $UPLOAD_END else 0
download_ms = $DL_END - $DL_START
smoke_ms = ($SMOKE_END - $SMOKE_START) if $SMOKE_END else 0

report = {
    "version": "$VERSION",
    "artifact": "$OBJECT_NAME",
    "size_bytes": size_bytes,
    "gcs_paths": {
        "versioned": "$UPLOAD_V_PATH",
        "latest": "$UPLOAD_LATEST_PATH",
    },
    "timings_ms": {
        "build": build_ms,
        "upload": upload_ms,
        "download": download_ms,
        "smoke": smoke_ms,
    },
    "flags": {
        "upload_enabled": "$UPLOAD_ENABLED" == "1",
        "run_smoke": "$RUN_SMOKE" == "1",
        "head_mode": "$HEAD_MODE",
    },
    "smoke_status": "$SMOKE_STATUS",
}

(out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
md = [
    "# Browser Release Cycle",
    "",
    f"- Version: `{report['version']}`",
    f"- Artifact: `{report['artifact']}`",
    f"- Size: `{report['size_bytes']}` bytes",
    f"- Smoke status: `{report['smoke_status']}`",
    "",
    "## Timings (ms)",
    "",
    f"- Build: `{build_ms}`",
    f"- Upload: `{upload_ms}`",
    f"- Download: `{download_ms}`",
    f"- Smoke: `{smoke_ms}`",
    "",
    "## GCS Targets",
    "",
    f"- Versioned: `{report['gcs_paths']['versioned']}`",
    f"- Latest: `{report['gcs_paths']['latest']}`",
]
(out_dir / "report.md").write_text("\\n".join(md) + "\\n", encoding="utf-8")
PY

log "Release cycle complete. Artifacts: $OUT_DIR"
