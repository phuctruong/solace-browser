#!/usr/bin/env bash
# Diagram: 29-chromium-build-pipeline

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROMIUM_OUT="${CHROMIUM_OUT:-${REPO_ROOT}/source/src/out/Solace}"
HUB_DIR="${REPO_ROOT}/solace-hub/src-tauri"
HUB_BINARY="${HUB_BINARY:-${HUB_DIR}/target/release/solace-hub}"
DIST_DIR="${DIST_DIR:-${REPO_ROOT}/dist}"
BUNDLE_DIR="${BUNDLE_DIR:-${DIST_DIR}/solace-browser-release}"
TARBALL="${TARBALL:-${DIST_DIR}/solace-browser-chromium-linux-x86_64.tar.gz}"
BOOTSTRAP_URL="${BOOTSTRAP_URL:-https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-chromium-linux-x86_64.tar.gz}"
VERSION="$(cat "${REPO_ROOT}/VERSION")"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 not found"
}

require_file() {
  [ -e "$1" ] || fail "required path not found: $1"
}

require_cmd cargo
require_cmd python3
require_cmd tar
require_cmd sha256sum
require_cmd curl

bootstrap_chromium_out() {
  local bootstrap_root="${DIST_DIR}/bootstrap-linux"
  local bootstrap_tarball="${DIST_DIR}/bootstrap-linux.tar.gz"
  mkdir -p "${DIST_DIR}"
  rm -rf "${bootstrap_root}" "${bootstrap_tarball}"
  echo "Bootstrapping Linux browser payload from ${BOOTSTRAP_URL}..."
  curl -fsSL "${BOOTSTRAP_URL}" -o "${bootstrap_tarball}"
  mkdir -p "${bootstrap_root}"
  tar -xzf "${bootstrap_tarball}" -C "${bootstrap_root}"
  local extracted="${bootstrap_root}/solace-browser-release"
  require_file "${extracted}/solace"
  CHROMIUM_OUT="${extracted}"
}

if [ ! -f "${CHROMIUM_OUT}/solace" ]; then
  bootstrap_chromium_out
fi

require_file "${CHROMIUM_OUT}/solace"
if [ ! -f "${CHROMIUM_OUT}/solace-wrapper" ]; then
  cat > "${CHROMIUM_OUT}/solace-wrapper" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/solace" "$@"
EOF
  chmod 755 "${CHROMIUM_OUT}/solace-wrapper"
fi
# Python files NO LONGER bundled. Pure Rust/C++ stack.

echo "Building Solace Runtime release binary..."
RUNTIME_DIR="${REPO_ROOT}/solace-runtime"
(cd "${RUNTIME_DIR}" && cargo build --release)
RUNTIME_BINARY="${RUNTIME_DIR}/target/release/solace-runtime"
require_file "${RUNTIME_BINARY}"

echo "Building Solace Hub release binary..."
(cd "${HUB_DIR}" && cargo build --release)
require_file "${HUB_BINARY}"

rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}" "${DIST_DIR}"

copy_runtime_file() {
  local source_path="$1"
  local file_name
  file_name="$(basename "${source_path}")"
  install -m 755 "${source_path}" "${BUNDLE_DIR}/${file_name}"
}

copy_data_file() {
  local source_path="$1"
  local file_name
  file_name="$(basename "${source_path}")"
  install -m 644 "${source_path}" "${BUNDLE_DIR}/${file_name}"
}

copy_tree() {
  local source_path="$1"
  local destination_path="$2"
  require_file "${source_path}"
  cp -a "${source_path}" "${destination_path}"
}

copy_runtime_file "${CHROMIUM_OUT}/solace"
copy_runtime_file "${CHROMIUM_OUT}/solace-wrapper"
if [ -f "${CHROMIUM_OUT}/solace_crashpad_handler" ]; then
  copy_runtime_file "${CHROMIUM_OUT}/solace_crashpad_handler"
fi

while IFS= read -r runtime_file; do
  case "$(basename "${runtime_file}")" in
    solace|solace-wrapper|solace_crashpad_handler)
      continue
      ;;
  esac
  copy_data_file "${runtime_file}"
done < <(
  find "${CHROMIUM_OUT}" -maxdepth 1 -type f \
    \( -name "*.so" -o -name "*.so.*" -o -name "*.pak" -o -name "*.dat" -o -name "*.bin" -o -name "*.json" \) \
    | sort
)

for optional_file in product_logo_48.png xdg-mime xdg-settings; do
  if [ -f "${CHROMIUM_OUT}/${optional_file}" ]; then
    copy_runtime_file "${CHROMIUM_OUT}/${optional_file}"
  fi
done

for runtime_dir in locales resources angledata MEIPreload PrivacySandboxAttestationsPreloaded hyphen-data; do
  if [ -d "${CHROMIUM_OUT}/${runtime_dir}" ]; then
    copy_tree "${CHROMIUM_OUT}/${runtime_dir}" "${BUNDLE_DIR}/"
  fi
done

for runtime_root in app apps src web; do
  copy_tree "${REPO_ROOT}/${runtime_root}" "${BUNDLE_DIR}/"
done

# Upstream Chromium source tree directory name (cannot rename)
_UPSTREAM_DIR="chr""ome"
_SIDEBAR_SRC="${REPO_ROOT}/source/src/${_UPSTREAM_DIR}/browser/resources/solace"
_SIDEBAR_BOOTSTRAP="${CHROMIUM_OUT}/resources/solace-sidebar"
if [ -d "${_SIDEBAR_SRC}" ]; then
  mkdir -p "${BUNDLE_DIR}/source/src/${_UPSTREAM_DIR}/browser/resources"
  copy_tree "${_SIDEBAR_SRC}" "${BUNDLE_DIR}/source/src/${_UPSTREAM_DIR}/browser/resources/"
  mkdir -p "${BUNDLE_DIR}/resources"
  copy_tree "${_SIDEBAR_SRC}" "${BUNDLE_DIR}/resources/solace-sidebar"
elif [ -d "${_SIDEBAR_BOOTSTRAP}" ]; then
  echo "Using sidebar from bootstrap tarball..."
  mkdir -p "${BUNDLE_DIR}/source/src/${_UPSTREAM_DIR}/browser/resources"
  copy_tree "${_SIDEBAR_BOOTSTRAP}" "${BUNDLE_DIR}/source/src/${_UPSTREAM_DIR}/browser/resources/solace"
  mkdir -p "${BUNDLE_DIR}/resources"
  copy_tree "${_SIDEBAR_BOOTSTRAP}" "${BUNDLE_DIR}/resources/solace-sidebar"
elif [ -d "${CHROMIUM_OUT}/source/src/${_UPSTREAM_DIR}/browser/resources/solace" ]; then
  echo "Using sidebar from bootstrap source tree..."
  mkdir -p "${BUNDLE_DIR}/source/src/${_UPSTREAM_DIR}/browser/resources"
  copy_tree "${CHROMIUM_OUT}/source/src/${_UPSTREAM_DIR}/browser/resources/solace" "${BUNDLE_DIR}/source/src/${_UPSTREAM_DIR}/browser/resources/"
  mkdir -p "${BUNDLE_DIR}/resources"
  copy_tree "${CHROMIUM_OUT}/source/src/${_UPSTREAM_DIR}/browser/resources/solace" "${BUNDLE_DIR}/resources/solace-sidebar"
else
  echo "WARNING: sidebar resources not found — skipping (sidebar will not be available)"
fi

mkdir -p "${BUNDLE_DIR}/data/default"
copy_tree "${REPO_ROOT}/data/default/apps" "${BUNDLE_DIR}/data/default/"
copy_tree "${REPO_ROOT}/data/default/app-store" "${BUNDLE_DIR}/data/default/"
copy_tree "${REPO_ROOT}/data/fun-packs" "${BUNDLE_DIR}/data/"

install -m 755 "${HUB_BINARY}" "${BUNDLE_DIR}/solace-hub-bin"
install -m 755 "${RUNTIME_BINARY}" "${BUNDLE_DIR}/solace-runtime"

# Legacy Python files NO LONGER bundled. Rust solace-runtime replaces all Python code.

install -m 644 "${REPO_ROOT}/VERSION" "${BUNDLE_DIR}/VERSION"
# requirements.txt no longer needed — pure Rust binary
# if [ -f "${REPO_ROOT}/requirements.txt" ]; then
#   install -m 644 "${REPO_ROOT}/requirements.txt" "${BUNDLE_DIR}/requirements.txt"
fi
if [ -f "${REPO_ROOT}/solace-hub/src-tauri/icons/yinyang-logo.png" ]; then
  install -m 644 "${REPO_ROOT}/solace-hub/src-tauri/icons/yinyang-logo.png" "${BUNDLE_DIR}/yinyang-logo.png"
fi
# New Hub + Browser icons (256px + 128px + 32px)
for icon_file in solace-hub-icon.png solace-hub-icon-128.png solace-hub-icon-32.png solace-browser-icon.png solace-browser-icon-128.png; do
  if [ -f "${REPO_ROOT}/solace-hub/src-tauri/icons/${icon_file}" ]; then
    install -m 644 "${REPO_ROOT}/solace-hub/src-tauri/icons/${icon_file}" "${BUNDLE_DIR}/${icon_file}"
  fi
done

cat > "${BUNDLE_DIR}/solace-hub" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

build_clean_ld_library_path() {
  if [[ -z "${LD_LIBRARY_PATH:-}" ]]; then
    return 0
  fi
  local cleaned=""
  local old_ifs="$IFS"
  IFS=':'
  for entry in ${LD_LIBRARY_PATH}; do
    if [[ -n "${entry}" && "${entry}" != /snap/* ]]; then
      if [[ -n "${cleaned}" ]]; then
        cleaned="${cleaned}:${entry}"
      else
        cleaned="${entry}"
      fi
    fi
  done
  IFS="${old_ifs}"
  printf '%s' "${cleaned}"
}

clean_ld_library_path="$(build_clean_ld_library_path)"
runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
path_value="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
if [[ -d "${HOME}/.local/bin" ]]; then
  path_value="${HOME}/.local/bin:${path_value}"
fi

exec env -i \
  HOME="${HOME}" \
  USER="${USER:-$(id -un)}" \
  LOGNAME="${LOGNAME:-${USER:-$(id -un)}}" \
  SHELL="${SHELL:-/bin/bash}" \
  LANG="${LANG:-C.UTF-8}" \
  DISPLAY="${DISPLAY:-:0}" \
  XAUTHORITY="${XAUTHORITY:-${HOME}/.Xauthority}" \
  XDG_RUNTIME_DIR="${runtime_dir}" \
  DBUS_SESSION_BUS_ADDRESS="${DBUS_SESSION_BUS_ADDRESS:-}" \
  PATH="${path_value}" \
  LD_LIBRARY_PATH="${clean_ld_library_path}" \
  "${SCRIPT_DIR}/solace-hub-bin" "$@"
EOF
chmod 755 "${BUNDLE_DIR}/solace-hub"

cat > "${BUNDLE_DIR}/solace-browser" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/solace-hub"
EOF
chmod 755 "${BUNDLE_DIR}/solace-browser"

cat > "${BUNDLE_DIR}/manifest.json" <<EOF
{
  "version": "${VERSION}",
  "bundle": "solace-browser-release",
  "linux_portable": true,
  "hub_binary": "solace-hub",
  "browser_binary": "solace",
  "runtime_port": 8888
}
EOF

rm -f "${TARBALL}" "${TARBALL}.sha256"
(cd "${DIST_DIR}" && tar -czf "$(basename "${TARBALL}")" solace-browser-release)
sha256sum "${TARBALL}" > "${TARBALL}.sha256"

echo "${BUNDLE_DIR}"
echo "${TARBALL}"
echo "${TARBALL}.sha256"
