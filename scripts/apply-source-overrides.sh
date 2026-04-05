#!/usr/bin/env bash
# Apply source-overrides/ files on top of source/src/ before building
# Each file in source-overrides/ mirrors a path under source/src/
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
OVERRIDES_DIR="$REPO_ROOT/source-overrides"
SOURCE_DIR="$REPO_ROOT/source/src"

if [ ! -d "$OVERRIDES_DIR" ]; then
  echo "[apply-overrides] No source-overrides/ directory found. Nothing to do."
  exit 0
fi

echo "[apply-overrides] Applying source overrides from: $OVERRIDES_DIR"

find "$OVERRIDES_DIR" -type f -name "*.cc" -o -name "*.h" -o -name "*.gn" -o -name "*.gni" | while read override_file; do
  rel_path="${override_file#$OVERRIDES_DIR/}"
  target="$SOURCE_DIR/$rel_path"

  if [ -f "$target" ]; then
    # Backup original if not already backed up
    if [ ! -f "${target}.solace-original" ]; then
      cp "$target" "${target}.solace-original"
    fi
    cp "$override_file" "$target"
    echo "  APPLIED: $rel_path"
  else
    echo "  SKIP (target not found): $rel_path"
  fi
done

echo "[apply-overrides] Done."
