#!/usr/bin/env bash
# Compile -> upload -> download -> smoke loop for Solace Browser release.
# Cross-platform: TARGET_OS=linux|macos|windows.
# Outputs metrics and logs into scratch/release-cycle/<timestamp>/.

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$PROJECT_ROOT"

VERSION="${VERSION:-$(cat VERSION 2>/dev/null || echo 1.0.0)}"
BUCKET="${BUCKET:-solace-downloads}"
OBJECT_PREFIX="${OBJECT_PREFIX:-solace-browser}"
TARGET_OS="${TARGET_OS:-}"
TARGET_ARCH="${TARGET_ARCH:-}"
UPLOAD_ENABLED="${UPLOAD_ENABLED:-1}"
DOWNLOAD_ENABLED="${DOWNLOAD_ENABLED:-auto}"
RUN_SMOKE="${RUN_SMOKE:-auto}"
BUILD_ENABLED="${BUILD_ENABLED:-1}"
ALLOW_NON_NATIVE_TARGET="${ALLOW_NON_NATIVE_TARGET:-0}"
HEAD_MODE="${HEAD_MODE:---head}"
SMOKE_PORT="${SMOKE_PORT:-9232}"
COMPILE_TIMEOUT="${COMPILE_TIMEOUT:-1800}"

log() { printf "[release-cycle] %s\n" "$*"; }

t_ms() { python3 - <<'PY'
import time
print(int(time.time() * 1000))
PY
}

run_with_timeout() {
  local timeout_value="$1"
  shift
  if command -v timeout >/dev/null 2>&1; then
    timeout "$timeout_value" "$@"
    return $?
  fi
  if command -v gtimeout >/dev/null 2>&1; then
    gtimeout "$timeout_value" "$@"
    return $?
  fi
  "$@"
}

write_sha256() {
  local source_file="$1"
  local output_file="$2"
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$source_file" >"$output_file"
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$source_file" >"$output_file"
    return 0
  fi
  python3 - <<PY
from pathlib import Path
import hashlib
source = Path(r"$source_file")
digest = hashlib.sha256(source.read_bytes()).hexdigest()
Path(r"$output_file").write_text(f"{digest}  {source.name}\n", encoding="utf-8")
PY
}

detect_os() {
  local uname_s
  uname_s="$(uname -s 2>/dev/null || echo unknown)"
  case "$uname_s" in
    Linux*) echo "linux" ;;
    Darwin*) echo "macos" ;;
    MINGW*|MSYS*|CYGWIN*|Windows_NT) echo "windows" ;;
    *) echo "linux" ;;
  esac
}

detect_arch() {
  local uname_m
  uname_m="$(uname -m 2>/dev/null || echo x86_64)"
  case "$uname_m" in
    x86_64|amd64) echo "x86_64" ;;
    aarch64|arm64) echo "arm64" ;;
    *) echo "$uname_m" ;;
  esac
}

TARGET_OS="${TARGET_OS:-$(detect_os)}"
TARGET_ARCH="${TARGET_ARCH:-$(detect_arch)}"
HOST_OS="$(detect_os)"

case "$TARGET_OS" in
  linux)
    DEFAULT_SPEC_FILE="solace-browser.spec"
    DEFAULT_BUILD_BIN_PATH="$PROJECT_ROOT/dist/solace-browser"
    DEFAULT_OBJECT_NAME="solace-browser-linux-$TARGET_ARCH"
    ;;
  macos)
    DEFAULT_SPEC_FILE="solace-browser-macos.spec"
    DEFAULT_BUILD_BIN_PATH="$PROJECT_ROOT/dist/solace-browser"
    DEFAULT_OBJECT_NAME="solace-browser-macos-universal"
    ;;
  windows)
    DEFAULT_SPEC_FILE="solace-browser.spec"
    DEFAULT_BUILD_BIN_PATH="$PROJECT_ROOT/dist/solace-browser.exe"
    DEFAULT_OBJECT_NAME="solace-browser-windows-$TARGET_ARCH.exe"
    ;;
  *)
    log "ERROR: unsupported TARGET_OS=$TARGET_OS (expected linux|macos|windows)"
    exit 1
    ;;
esac

OBJECT_NAME="${OBJECT_NAME:-$DEFAULT_OBJECT_NAME}"
SPEC_FILE="${SPEC_FILE:-$DEFAULT_SPEC_FILE}"
BUILD_BIN_PATH="${BUILD_BIN_PATH:-$DEFAULT_BUILD_BIN_PATH}"

if [[ "$BUILD_ENABLED" == "1" && "$ALLOW_NON_NATIVE_TARGET" != "1" && "$TARGET_OS" != "$HOST_OS" ]]; then
  log "ERROR: native build required for TARGET_OS=$TARGET_OS but host is $HOST_OS."
  log "Use a native CI runner (macos-latest/windows-latest) or set ALLOW_NON_NATIVE_TARGET=1 only for non-release diagnostics."
  exit 1
fi

if [[ "$DOWNLOAD_ENABLED" == "auto" ]]; then
  if [[ "$TARGET_OS" == "windows" ]]; then
    DOWNLOAD_ENABLED="0"
  else
    DOWNLOAD_ENABLED="1"
  fi
fi

if [[ "$RUN_SMOKE" == "auto" ]]; then
  if [[ "$TARGET_OS" == "linux" ]]; then
    RUN_SMOKE="1"
  else
    RUN_SMOKE="0"
  fi
fi

STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$PROJECT_ROOT/scratch/release-cycle/$STAMP"
mkdir -p "$OUT_DIR"

log "Platform: os=$TARGET_OS arch=$TARGET_ARCH object=$OBJECT_NAME spec=$SPEC_FILE"

BUILD_START="$(t_ms)"
if [[ "$BUILD_ENABLED" == "1" ]]; then
  log "Step 1/6: compile browser binary with PyInstaller."
  set +e
  run_with_timeout "$COMPILE_TIMEOUT" pyinstaller --noconfirm "$SPEC_FILE" >"$OUT_DIR/pyinstaller.log" 2>&1
  BUILD_RC=$?
  set -e
  if [[ "$BUILD_RC" -ne 0 ]]; then
    log "ERROR: compile step failed (rc=$BUILD_RC). See $OUT_DIR/pyinstaller.log"
    exit 1
  fi
else
  log "Step 1/6: compile skipped (BUILD_ENABLED=0)."
fi
BUILD_END="$(t_ms)"

if [[ ! -f "$BUILD_BIN_PATH" && "$TARGET_OS" == "windows" && -f "$PROJECT_ROOT/dist/solace-browser" ]]; then
  BUILD_BIN_PATH="$PROJECT_ROOT/dist/solace-browser"
fi
if [[ ! -f "$BUILD_BIN_PATH" ]]; then
  log "ERROR: expected build output not found at $BUILD_BIN_PATH"
  exit 1
fi

DIST_OBJECT_PATH="$PROJECT_ROOT/dist/$OBJECT_NAME"
DIST_SHA_PATH="$PROJECT_ROOT/dist/$OBJECT_NAME.sha256"
SAME_PATH="$(python3 - <<PY
from pathlib import Path
src = Path(r"$BUILD_BIN_PATH").resolve()
dst = Path(r"$DIST_OBJECT_PATH").resolve()
print("1" if src == dst else "0")
PY
)"
if [[ "$SAME_PATH" != "1" ]]; then
  cp "$BUILD_BIN_PATH" "$DIST_OBJECT_PATH"
fi
write_sha256 "$DIST_OBJECT_PATH" "$DIST_SHA_PATH"
cp "$DIST_OBJECT_PATH" "$OUT_DIR/$OBJECT_NAME"
cp "$DIST_SHA_PATH" "$OUT_DIR/$OBJECT_NAME.sha256"

UPLOAD_V_PATH="gs://$BUCKET/$OBJECT_PREFIX/v$VERSION/$OBJECT_NAME"
UPLOAD_LATEST_PATH="gs://$BUCKET/$OBJECT_PREFIX/latest/$OBJECT_NAME"

UPLOAD_START=0
UPLOAD_END=0
if [[ "$UPLOAD_ENABLED" == "1" ]]; then
  UPLOAD_START="$(t_ms)"
  log "Step 2/6: upload versioned artifact -> $UPLOAD_V_PATH"
  set +e
  gcloud storage cp "$DIST_OBJECT_PATH" "$UPLOAD_V_PATH" >"$OUT_DIR/upload-versioned.log" 2>&1
  UPLOAD_V_RC=$?
  set -e
  if [[ "$UPLOAD_V_RC" -ne 0 ]]; then
    log "ERROR: upload versioned failed (rc=$UPLOAD_V_RC). See $OUT_DIR/upload-versioned.log"
    exit 1
  fi
  log "Step 3/6: upload latest artifact -> $UPLOAD_LATEST_PATH"
  set +e
  gcloud storage cp "$DIST_OBJECT_PATH" "$UPLOAD_LATEST_PATH" >"$OUT_DIR/upload-latest.log" 2>&1
  UPLOAD_L_RC=$?
  set -e
  if [[ "$UPLOAD_L_RC" -ne 0 ]]; then
    log "ERROR: upload latest failed (rc=$UPLOAD_L_RC). See $OUT_DIR/upload-latest.log"
    exit 1
  fi
  UPLOAD_END="$(t_ms)"
else
  log "Step 2/6: upload skipped (UPLOAD_ENABLED=0)."
fi

DL_START=0
DL_END=0
SMOKE_BIN_PATH="$DIST_OBJECT_PATH"
if [[ "$DOWNLOAD_ENABLED" == "1" ]]; then
  DL_START="$(t_ms)"
  log "Step 4/6: download latest artifact from production bucket."
  SMOKE_BIN_PATH="$OUT_DIR/downloaded-$OBJECT_NAME"
  curl -fsSL "https://storage.googleapis.com/$BUCKET/$OBJECT_PREFIX/latest/$OBJECT_NAME" -o "$SMOKE_BIN_PATH"
  if [[ "$TARGET_OS" != "windows" ]]; then
    chmod +x "$SMOKE_BIN_PATH"
  fi
  DL_END="$(t_ms)"
else
  log "Step 4/6: download skipped (DOWNLOAD_ENABLED=0)."
fi

SMOKE_STATUS="skipped"
SMOKE_START=0
SMOKE_END=0
if [[ "$RUN_SMOKE" == "1" ]]; then
  SMOKE_START="$(t_ms)"
  log "Step 5/6: run smoke server with head mode ($HEAD_MODE) on port $SMOKE_PORT."
  set +e
  IFS=' ' read -r -a HEAD_ARGS <<<"$HEAD_MODE"
  run_with_timeout 35s "$SMOKE_BIN_PATH" "${HEAD_ARGS[@]}" --port "$SMOKE_PORT" >"$OUT_DIR/smoke.log" 2>&1 &
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
else
  log "Step 5/6: smoke skipped (RUN_SMOKE=0)."
fi

log "Step 6/6: write benchmark and release report."
OUT_DIR="$OUT_DIR" \
VERSION="$VERSION" \
TARGET_OS="$TARGET_OS" \
TARGET_ARCH="$TARGET_ARCH" \
OBJECT_NAME="$OBJECT_NAME" \
SPEC_FILE="$SPEC_FILE" \
UPLOAD_V_PATH="$UPLOAD_V_PATH" \
UPLOAD_LATEST_PATH="$UPLOAD_LATEST_PATH" \
BUILD_END="$BUILD_END" \
BUILD_START="$BUILD_START" \
UPLOAD_END="$UPLOAD_END" \
UPLOAD_START="$UPLOAD_START" \
DL_END="$DL_END" \
DL_START="$DL_START" \
SMOKE_END="$SMOKE_END" \
SMOKE_START="$SMOKE_START" \
BUILD_ENABLED="$BUILD_ENABLED" \
UPLOAD_ENABLED="$UPLOAD_ENABLED" \
DOWNLOAD_ENABLED="$DOWNLOAD_ENABLED" \
RUN_SMOKE="$RUN_SMOKE" \
HEAD_MODE="$HEAD_MODE" \
SMOKE_STATUS="$SMOKE_STATUS" \
python3 - <<'PY'
import json
import os
from pathlib import Path

out_dir = Path(os.environ["OUT_DIR"])
binary = out_dir / os.environ["OBJECT_NAME"]
size_bytes = binary.stat().st_size

build_ms = int(os.environ["BUILD_END"]) - int(os.environ["BUILD_START"])
upload_end = int(os.environ["UPLOAD_END"])
upload_start = int(os.environ["UPLOAD_START"])
download_end = int(os.environ["DL_END"])
download_start = int(os.environ["DL_START"])
smoke_end = int(os.environ["SMOKE_END"])
smoke_start = int(os.environ["SMOKE_START"])

upload_ms = (upload_end - upload_start) if upload_end else 0
download_ms = (download_end - download_start) if download_end else 0
smoke_ms = (smoke_end - smoke_start) if smoke_end else 0

report = {
    "version": os.environ["VERSION"],
    "platform": {
        "target_os": os.environ["TARGET_OS"],
        "target_arch": os.environ["TARGET_ARCH"],
    },
    "artifact": os.environ["OBJECT_NAME"],
    "size_bytes": size_bytes,
    "spec_file": os.environ["SPEC_FILE"],
    "gcs_paths": {
        "versioned": os.environ["UPLOAD_V_PATH"],
        "latest": os.environ["UPLOAD_LATEST_PATH"],
    },
    "timings_ms": {
        "build": build_ms,
        "upload": upload_ms,
        "download": download_ms,
        "smoke": smoke_ms,
    },
    "flags": {
        "build_enabled": os.environ["BUILD_ENABLED"] == "1",
        "upload_enabled": os.environ["UPLOAD_ENABLED"] == "1",
        "download_enabled": os.environ["DOWNLOAD_ENABLED"] == "1",
        "run_smoke": os.environ["RUN_SMOKE"] == "1",
        "head_mode": os.environ["HEAD_MODE"],
    },
    "smoke_status": os.environ["SMOKE_STATUS"],
}

(out_dir / "metrics.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
md = [
    "# Browser Release Cycle",
    "",
    f"- Version: `{report['version']}`",
    f"- Target OS: `{report['platform']['target_os']}`",
    f"- Target Arch: `{report['platform']['target_arch']}`",
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
(out_dir / "report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
PY

log "Release cycle complete. Artifacts: $OUT_DIR"
