#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROMIUM_OUT="${CHROMIUM_OUT:-${REPO_ROOT}/source/src/out/Solace}"
HUB_DIR="${REPO_ROOT}/solace-hub/src-tauri"
HUB_BINARY="${HUB_BINARY:-${HUB_DIR}/target/release/solace-hub}"
DIST_DIR="${DIST_DIR:-${REPO_ROOT}/dist}"
BUNDLE_DIR="${BUNDLE_DIR:-${DIST_DIR}/solace-browser-release}"
TARBALL="${TARBALL:-${DIST_DIR}/solace-browser-chromium-linux-x86_64.tar.gz}"
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

require_file "${CHROMIUM_OUT}/chrome"
require_file "${CHROMIUM_OUT}/chrome-wrapper"
require_file "${REPO_ROOT}/yinyang_server.py"
require_file "${REPO_ROOT}/yinyang-server.py"

if [ ! -x "${HUB_BINARY}" ]; then
  echo "Building Solace Hub release binary..."
  (cd "${HUB_DIR}" && cargo build --release)
fi

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

copy_runtime_file "${CHROMIUM_OUT}/chrome"
copy_runtime_file "${CHROMIUM_OUT}/chrome-wrapper"
copy_runtime_file "${CHROMIUM_OUT}/chrome_crashpad_handler"

while IFS= read -r runtime_file; do
  case "$(basename "${runtime_file}")" in
    chrome|chrome-wrapper|chrome_crashpad_handler)
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

mkdir -p "${BUNDLE_DIR}/data/default"
copy_tree "${REPO_ROOT}/data/default/apps" "${BUNDLE_DIR}/data/default/"
copy_tree "${REPO_ROOT}/data/default/app-store" "${BUNDLE_DIR}/data/default/"
copy_tree "${REPO_ROOT}/data/fun-packs" "${BUNDLE_DIR}/data/"

install -m 755 "${HUB_BINARY}" "${BUNDLE_DIR}/solace-hub"

for script_name in yinyang_server.py yinyang-server.py yinyang_mcp_server.py hub_tunnel_client.py evidence_bundle.py solace_cli.py; do
  if [ -f "${REPO_ROOT}/${script_name}" ]; then
    install -m 755 "${REPO_ROOT}/${script_name}" "${BUNDLE_DIR}/${script_name}"
  fi
done

install -m 644 "${REPO_ROOT}/VERSION" "${BUNDLE_DIR}/VERSION"
if [ -f "${REPO_ROOT}/requirements.txt" ]; then
  install -m 644 "${REPO_ROOT}/requirements.txt" "${BUNDLE_DIR}/requirements.txt"
fi
if [ -f "${REPO_ROOT}/solace-hub/src-tauri/icons/yinyang-logo.png" ]; then
  install -m 644 "${REPO_ROOT}/solace-hub/src-tauri/icons/yinyang-logo.png" "${BUNDLE_DIR}/yinyang-logo.png"
fi

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
  "browser_binary": "chrome",
  "runtime_port": 8888
}
EOF

rm -f "${TARBALL}" "${TARBALL}.sha256"
(cd "${DIST_DIR}" && tar -czf "$(basename "${TARBALL}")" solace-browser-release)
sha256sum "${TARBALL}" > "${TARBALL}.sha256"

echo "${BUNDLE_DIR}"
echo "${TARBALL}"
echo "${TARBALL}.sha256"
