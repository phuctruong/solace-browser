#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

pages=(web/home.html web/download.html web/machine-dashboard.html web/tunnel-connect.html)

for page in "${pages[@]}"; do
  if grep -Eq '<style|style=' "$page"; then
    echo "inline style contract violated: $page"
    exit 1
  fi

  script_lines="$(grep -n '<script' "$page" || true)"
  if [ -n "$script_lines" ]; then
    non_shared_scripts="$(printf '%s\n' "$script_lines" | grep -Fv '<script src="/js/solace.js" defer></script>' || true)"
    if [ -n "$non_shared_scripts" ]; then
      echo "inline or non-shared script contract violated: $page"
      printf '%s\n' "$non_shared_scripts"
      exit 1
    fi
  fi

  grep -Fq '<link rel="stylesheet" href="/css/site.css">' "$page" || { echo "missing shared stylesheet: $page"; exit 1; }
  grep -Fq '<script src="/js/solace.js" defer></script>' "$page" || { echo "missing shared runtime: $page"; exit 1; }
done

sha256sum web/css/site.css | awk '{print $1}' > /tmp/solace-browser-site-css.sha
sha256sum web/js/solace.js | awk '{print $1}' > /tmp/solace-browser-solace-js.sha
cmp -s /tmp/solace-browser-site-css.sha web/css/site.css.sha256 || { echo "site.css hash mismatch"; exit 1; }
cmp -s /tmp/solace-browser-solace-js.sha web/js/solace.js.sha256 || { echo "solace.js hash mismatch"; exit 1; }

echo "All checks passed."
