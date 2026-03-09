#!/usr/bin/env bash

set -eu

SOURCE_DIR=$(dirname "$(readlink -f "$0")")
version=$(cat "$SOURCE_DIR/VERSION")
glow="368"
echo "${version}-${glow}"
