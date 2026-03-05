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
VERSIONED_CACHE_CONTROL="${VERSIONED_CACHE_CONTROL:-public,max-age=31536000,immutable}"
LATEST_CACHE_CONTROL="${LATEST_CACHE_CONTROL:-no-store,max-age=0,must-revalidate}"
WINDOWS_PACKAGE_MODE="${WINDOWS_PACKAGE_MODE:-auto}"
UPX_ENABLED="${UPX_ENABLED:-auto}"

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
  local source_name
  source_name="$(basename "$source_file")"
  if command -v sha256sum >/dev/null 2>&1; then
    local digest
    digest="$(sha256sum "$source_file" | awk '{print $1}')"
    printf "%s  %s\n" "$digest" "$source_name" >"$output_file"
    return 0
  fi
  if command -v shasum >/dev/null 2>&1; then
    local digest
    digest="$(shasum -a 256 "$source_file" | awk '{print $1}')"
    printf "%s  %s\n" "$digest" "$source_name" >"$output_file"
    return 0
  fi
  SOURCE_FILE="$source_file" OUTPUT_FILE="$output_file" SOURCE_NAME="$source_name" python3 - <<'PY'
from pathlib import Path
import hashlib
import os

source = Path(os.environ["SOURCE_FILE"])
hasher = hashlib.sha256()
with source.open("rb") as handle:
    while True:
        chunk = handle.read(1024 * 1024)
        if not chunk:
            break
        hasher.update(chunk)
digest = hasher.hexdigest()
Path(os.environ["OUTPUT_FILE"]).write_text(
    f"{digest}  {os.environ['SOURCE_NAME']}\n",
    encoding="utf-8",
)
PY
}

verify_binary_format() {
  local target_os="$1"
  local binary_path="$2"
  local windows_package_mode="${3:-binary}"
  TARGET_OS="$target_os" BINARY_PATH="$binary_path" WINDOWS_PACKAGE_MODE="$windows_package_mode" python3 - <<'PY'
from pathlib import Path
import os
import struct
import sys

target_os = os.environ["TARGET_OS"]
binary_path = Path(os.environ["BINARY_PATH"])
data = binary_path.read_bytes()[:64]
windows_package_mode = os.environ.get("WINDOWS_PACKAGE_MODE", "binary")

def fail(msg: str) -> None:
    print(f"[release-cycle] ERROR: {msg}", file=sys.stderr)
    sys.exit(1)

if len(data) < 4:
    fail(f"artifact too small to classify: {binary_path}")

def is_elf(blob: bytes) -> bool:
    return blob.startswith(b"\x7fELF")

def is_pe(blob: bytes, full_path: Path) -> bool:
    if not blob.startswith(b"MZ"):
        return False
    full = full_path.read_bytes()
    if len(full) < 0x40:
        return False
    pe_offset = struct.unpack("<I", full[0x3C:0x40])[0]
    if pe_offset + 4 > len(full):
        return False
    return full[pe_offset:pe_offset + 4] == b"PE\x00\x00"

def is_macho(blob: bytes) -> bool:
    magic = blob[:4]
    return magic in {
        b"\xfe\xed\xfa\xce",  # MH_MAGIC
        b"\xce\xfa\xed\xfe",  # MH_CIGAM
        b"\xfe\xed\xfa\xcf",  # MH_MAGIC_64
        b"\xcf\xfa\xed\xfe",  # MH_CIGAM_64
        b"\xca\xfe\xba\xbe",  # FAT_MAGIC
        b"\xbe\xba\xfe\xca",  # FAT_CIGAM
        b"\xca\xfe\xba\xbf",  # FAT_MAGIC_64
        b"\xbf\xba\xfe\xca",  # FAT_CIGAM_64
    }

if target_os == "linux":
    if not is_elf(data):
        fail(f"expected Linux ELF artifact but got non-ELF file: {binary_path}")
elif target_os == "windows":
    if not is_pe(data, binary_path):
        fail(f"expected Windows PE artifact but got non-PE file: {binary_path}")
    if windows_package_mode == "msi":
        full = binary_path.read_bytes()
        ole2_header = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        if not full.startswith(ole2_header):
            fail(
                "expected Windows MSI artifact with OLE2 header "
                f"but header missing: {binary_path}"
            )
    elif windows_package_mode == "installer":
        full = binary_path.read_bytes()
        if b"Inno Setup Setup Data" not in full:
            fail(
                "expected Windows installer artifact with Inno Setup marker "
                f"but marker missing: {binary_path}"
            )
elif target_os == "macos":
    if not is_macho(data):
        fail(f"expected macOS Mach-O artifact but got non-Mach-O file: {binary_path}")
else:
    fail(f"unsupported TARGET_OS for binary verification: {target_os}")

print(f"[release-cycle] Binary format verified for {target_os}: {binary_path}")
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

if [[ "$TARGET_OS" == "windows" && "$WINDOWS_PACKAGE_MODE" == "auto" ]]; then
  WINDOWS_PACKAGE_MODE="msi"
elif [[ "$WINDOWS_PACKAGE_MODE" == "auto" ]]; then
  WINDOWS_PACKAGE_MODE="binary"
fi

if [[ "$UPX_ENABLED" == "auto" ]]; then
  if command -v upx >/dev/null 2>&1; then
    UPX_ENABLED="1"
  else
    UPX_ENABLED="0"
  fi
fi

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
    if [[ "$WINDOWS_PACKAGE_MODE" == "msi" ]]; then
      DEFAULT_OBJECT_NAME="solace-browser-windows-$TARGET_ARCH.msi"
    else
      DEFAULT_OBJECT_NAME="solace-browser-windows-$TARGET_ARCH.exe"
    fi
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
    if [[ -f "$OUT_DIR/pyinstaller.log" ]]; then
      log "Last 80 lines from pyinstaller.log:"
      tail -n 80 "$OUT_DIR/pyinstaller.log" >&2 || true
    fi
    exit 1
  fi
else
  log "Step 1/6: compile skipped (BUILD_ENABLED=0)."
fi
BUILD_END="$(t_ms)"

if [[ ! -f "$BUILD_BIN_PATH" ]]; then
  log "ERROR: expected build output not found at $BUILD_BIN_PATH"
  exit 1
fi

FINAL_BUILD_PATH="$BUILD_BIN_PATH"

# ── UPX compression for Linux/macOS ──────────────────────────────────────────
if [[ "$UPX_ENABLED" == "1" && "$BUILD_ENABLED" == "1" && "$TARGET_OS" != "windows" ]]; then
  ORIGINAL_SIZE="$(stat --printf='%s' "$BUILD_BIN_PATH" 2>/dev/null || stat -f '%z' "$BUILD_BIN_PATH" 2>/dev/null || echo 0)"
  log "Step 1.1/6: compress binary with UPX (original: ${ORIGINAL_SIZE} bytes)."
  set +e
  upx --best --lzma "$BUILD_BIN_PATH" >"$OUT_DIR/upx.log" 2>&1
  UPX_RC=$?
  set -e
  if [[ "$UPX_RC" -ne 0 ]]; then
    log "WARNING: UPX compression failed (rc=$UPX_RC). Continuing with uncompressed binary."
    cat "$OUT_DIR/upx.log" >&2 || true
  else
    COMPRESSED_SIZE="$(stat --printf='%s' "$BUILD_BIN_PATH" 2>/dev/null || stat -f '%z' "$BUILD_BIN_PATH" 2>/dev/null || echo 0)"
    log "UPX: ${ORIGINAL_SIZE} → ${COMPRESSED_SIZE} bytes ($(( 100 - COMPRESSED_SIZE * 100 / ORIGINAL_SIZE ))% reduction)"
  fi
fi

# ── Windows MSI packaging ────────────────────────────────────────────────────
if [[ "$TARGET_OS" == "windows" && "$BUILD_ENABLED" == "1" && "$WINDOWS_PACKAGE_MODE" == "msi" ]]; then
  log "Step 1.1/6: package Windows MSI with WiX toolset."
  WINDOWS_MSI_PATH="$PROJECT_ROOT/dist/solace-browser-windows-${TARGET_ARCH}.msi"
  POWERSHELL_BIN=""
  if command -v pwsh >/dev/null 2>&1; then
    POWERSHELL_BIN="pwsh"
  elif command -v powershell.exe >/dev/null 2>&1; then
    POWERSHELL_BIN="powershell.exe"
  elif command -v powershell >/dev/null 2>&1; then
    POWERSHELL_BIN="powershell"
  else
    log "ERROR: no PowerShell runtime available to build Windows MSI."
    exit 1
  fi
  set +e
  "$POWERSHELL_BIN" -NoProfile -ExecutionPolicy Bypass \
    -File "$PROJECT_ROOT/scripts/package-windows-msi.ps1" \
    -InputBinary "$BUILD_BIN_PATH" \
    -OutputMsi "$WINDOWS_MSI_PATH" \
    -AppVersion "$VERSION" >"$OUT_DIR/windows-msi.log" 2>&1
  MSI_RC=$?
  set -e
  if [[ "$MSI_RC" -ne 0 ]]; then
    log "ERROR: Windows MSI packaging failed (rc=$MSI_RC). See $OUT_DIR/windows-msi.log"
    tail -n 120 "$OUT_DIR/windows-msi.log" >&2 || true
    exit 1
  fi
  FINAL_BUILD_PATH="$WINDOWS_MSI_PATH"
elif [[ "$TARGET_OS" == "windows" && "$BUILD_ENABLED" == "1" && "$WINDOWS_PACKAGE_MODE" == "installer" ]]; then
  log "Step 1.1/6: package Windows installer with Inno Setup (legacy)."
  WINDOWS_INSTALLER_PATH="$PROJECT_ROOT/dist/solace-browser-windows-installer.exe"
  POWERSHELL_BIN=""
  if command -v pwsh >/dev/null 2>&1; then
    POWERSHELL_BIN="pwsh"
  elif command -v powershell.exe >/dev/null 2>&1; then
    POWERSHELL_BIN="powershell.exe"
  elif command -v powershell >/dev/null 2>&1; then
    POWERSHELL_BIN="powershell"
  else
    log "ERROR: no PowerShell runtime available to build Windows installer."
    exit 1
  fi
  set +e
  "$POWERSHELL_BIN" -NoProfile -ExecutionPolicy Bypass \
    -File "$PROJECT_ROOT/scripts/package-windows-installer.ps1" \
    -InputBinary "$BUILD_BIN_PATH" \
    -OutputInstaller "$WINDOWS_INSTALLER_PATH" \
    -AppVersion "$VERSION" >"$OUT_DIR/windows-installer.log" 2>&1
  INSTALLER_RC=$?
  set -e
  if [[ "$INSTALLER_RC" -ne 0 ]]; then
    log "ERROR: Windows installer packaging failed (rc=$INSTALLER_RC). See $OUT_DIR/windows-installer.log"
    tail -n 120 "$OUT_DIR/windows-installer.log" >&2 || true
    exit 1
  fi
  FINAL_BUILD_PATH="$WINDOWS_INSTALLER_PATH"
fi

if [[ ! -f "$FINAL_BUILD_PATH" ]]; then
  log "ERROR: final packaged artifact not found at $FINAL_BUILD_PATH"
  exit 1
fi

DIST_OBJECT_PATH="$PROJECT_ROOT/dist/$OBJECT_NAME"
DIST_SHA_PATH="$PROJECT_ROOT/dist/$OBJECT_NAME.sha256"
SAME_PATH="$(python3 - <<PY
from pathlib import Path
src = Path(r"$FINAL_BUILD_PATH").resolve()
dst = Path(r"$DIST_OBJECT_PATH").resolve()
print("1" if src == dst else "0")
PY
)"
if [[ "$SAME_PATH" != "1" ]]; then
  cp "$FINAL_BUILD_PATH" "$DIST_OBJECT_PATH"
fi
verify_binary_format "$TARGET_OS" "$DIST_OBJECT_PATH" "$WINDOWS_PACKAGE_MODE"
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
  gcloud storage cp --cache-control="$VERSIONED_CACHE_CONTROL" "$DIST_OBJECT_PATH" "$UPLOAD_V_PATH" >"$OUT_DIR/upload-versioned.log" 2>&1
  UPLOAD_V_RC=$?
  set -e
  if [[ "$UPLOAD_V_RC" -ne 0 ]]; then
    log "ERROR: upload versioned failed (rc=$UPLOAD_V_RC). See $OUT_DIR/upload-versioned.log"
    exit 1
  fi
  log "Step 3/6: upload latest artifact -> $UPLOAD_LATEST_PATH"
  set +e
  gcloud storage cp --cache-control="$LATEST_CACHE_CONTROL" "$DIST_OBJECT_PATH" "$UPLOAD_LATEST_PATH" >"$OUT_DIR/upload-latest.log" 2>&1
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
WINDOWS_PACKAGE_MODE="$WINDOWS_PACKAGE_MODE" \
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
        "windows_package_mode": os.environ["WINDOWS_PACKAGE_MODE"],
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
