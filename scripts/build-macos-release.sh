#!/usr/bin/env bash
# Diagram: 29-chromium-build-pipeline

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CHROMIUM_OUT="${CHROMIUM_OUT:-${REPO_ROOT}/source/src/out/Solace}"
HUB_BINARY="${HUB_BINARY:-${REPO_ROOT}/solace-hub/src-tauri/target/release/solace-hub}"
DIST_DIR="${DIST_DIR:-${REPO_ROOT}/dist}"
BUNDLE_DIR="${BUNDLE_DIR:-${DIST_DIR}/solace-browser-release-macos}"
TARBALL="${TARBALL:-${DIST_DIR}/solace-browser-macos-universal.tar.gz}"
BOOTSTRAP_URL="${BOOTSTRAP_URL:-https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-macos-universal}"
VERSION="$(cat "${REPO_ROOT}/VERSION")"

fail() {
  echo "ERROR: $1" >&2
  exit 1
}

require_file() {
  [ -e "$1" ] || fail "required path not found: $1"
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 not found"
}

require_cmd tar
require_cmd shasum
require_cmd cargo
require_cmd curl

bootstrap_chromium_out() {
  local bootstrap_root="${DIST_DIR}/bootstrap-macos"
  mkdir -p "${bootstrap_root}" "${DIST_DIR}"
  rm -rf "${bootstrap_root}"
  mkdir -p "${bootstrap_root}"
  echo "Bootstrapping macOS browser payload from ${BOOTSTRAP_URL}..."
  curl -fsSL "${BOOTSTRAP_URL}" -o "${bootstrap_root}/solace"
  chmod 755 "${bootstrap_root}/solace"
  CHROMIUM_OUT="${bootstrap_root}"
}

if [ ! -f "${CHROMIUM_OUT}/solace" ]; then
  bootstrap_chromium_out
fi

require_file "${CHROMIUM_OUT}"
require_file "${CHROMIUM_OUT}/solace"
require_file "${REPO_ROOT}/yinyang_server.py"
require_file "${REPO_ROOT}/yinyang-server.py"

if [ ! -x "${HUB_BINARY}" ]; then
  (cd "${REPO_ROOT}/solace-hub/src-tauri" && cargo build --release)
fi
require_file "${HUB_BINARY}"

rm -rf "${BUNDLE_DIR}"
mkdir -p "${BUNDLE_DIR}" "${DIST_DIR}"

copy_tree() {
  local source_path="$1"
  local destination_path="$2"
  require_file "${source_path}"
  cp -a "${source_path}" "${destination_path}"
}

copy_tree "${CHROMIUM_OUT}/solace" "${BUNDLE_DIR}/"

while IFS= read -r runtime_file; do
  cp -a "${runtime_file}" "${BUNDLE_DIR}/"
done < <(
  find "${CHROMIUM_OUT}" -maxdepth 1 -type f \
    \( -name "*.dylib" -o -name "*.framework" -o -name "*.pak" -o -name "*.dat" -o -name "*.bin" -o -name "*.json" \) \
    | sort
)

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
  "bundle": "solace-browser-release-macos",
  "macos_portable": true,
  "hub_binary": "solace-hub",
  "browser_binary": "solace",
  "runtime_port": 8888
}
EOF

rm -f "${TARBALL}" "${TARBALL}.sha256"
(cd "${DIST_DIR}" && tar -czf "$(basename "${TARBALL}")" "$(basename "${BUNDLE_DIR}")")
shasum -a 256 "${TARBALL}" > "${TARBALL}.sha256"

echo "${BUNDLE_DIR}"
echo "${TARBALL}"
echo "${TARBALL}.sha256"
