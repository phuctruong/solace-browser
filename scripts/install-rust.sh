#!/usr/bin/env bash
# install-rust.sh — Instructions for setting up Rust to build Solace Hub
#
# SAFE: This script only PRINTS instructions.
# It does NOT execute curl | sh or modify your system.
# Follow the steps manually.

set -euo pipefail

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║          Solace Hub — Rust Build Setup               ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Install Rust via rustup ──────────────────────────────────────────
echo "STEP 1 — Install Rust (rustup)"
echo "──────────────────────────────"
echo ""
echo "  Visit https://rustup.rs for the official instructions."
echo ""
echo "  OR run this command manually (inspect it first — never pipe blindly):"
echo ""
echo "    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"
echo ""
echo "  When prompted, select option 1 (default installation)."
echo "  Then restart your shell or run:"
echo ""
echo "    source \"\$HOME/.cargo/env\""
echo ""

# ── Step 2: Verify Rust installation ─────────────────────────────────────────
echo "STEP 2 — Verify Rust"
echo "────────────────────"
echo ""
echo "    rustc --version   # should print: rustc 1.70+ (MSRV for Tauri 1.x)"
echo "    cargo --version"
echo ""

# ── Step 3: Linux system dependencies ────────────────────────────────────────
echo "STEP 3 — Linux system dependencies (skip on macOS/Windows)"
echo "───────────────────────────────────────────────────────────"
echo ""
echo "    sudo apt-get update"
echo "    sudo apt-get install -y \\"
echo "      libwebkit2gtk-4.0-dev \\"
echo "      build-essential \\"
echo "      curl wget \\"
echo "      libssl-dev \\"
echo "      libgtk-3-dev \\"
echo "      libayatana-appindicator3-dev \\"
echo "      librsvg2-dev"
echo ""

# ── Step 4: Install Tauri CLI ─────────────────────────────────────────────────
echo "STEP 4 — Install Tauri CLI"
echo "──────────────────────────"
echo ""
echo "    cargo install tauri-cli"
echo ""
echo "  This takes ~2–5 minutes on first run (compiles from source)."
echo ""

# ── Step 5: Place the yinyang logo icon ──────────────────────────────────────
echo "STEP 5 — Place yinyang-logo.png"
echo "────────────────────────────────"
echo ""
echo "  Tauri requires at least one icon before building."
echo ""
echo "  Option A — copy from project assets (when available):"
echo "    cp /home/phuc/projects/solace-browser/data/default/yinyang-logo.png \\"
echo "       /home/phuc/projects/solace-browser/solace-hub/src-tauri/icons/yinyang-logo.png"
echo ""
echo "  Option B — generate all icon sizes from master PNG:"
echo "    cd /home/phuc/projects/solace-browser/solace-hub"
echo "    cargo tauri icon src-tauri/icons/yinyang-logo.png"
echo ""

# ── Step 6: Build Solace Hub ─────────────────────────────────────────────────
echo "STEP 6 — Build Solace Hub"
echo "─────────────────────────"
echo ""
echo "  Development (hot-reload, loads src/index.html from filesystem):"
echo ""
echo "    cd /home/phuc/projects/solace-browser/solace-hub"
echo "    cargo tauri dev"
echo ""
echo "  Production build (~20 MB binary):"
echo ""
echo "    cargo tauri build"
echo "    # Output: src-tauri/target/release/bundle/"
echo ""

# ── Summary ───────────────────────────────────────────────────────────────────
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Summary of commands (run in order):                 ║"
echo "║                                                      ║"
echo "║  curl --proto '=https' --tlsv1.2 -sSf \\             ║"
echo "║    https://sh.rustup.rs | sh                         ║"
echo "║  source \"\$HOME/.cargo/env\"                          ║"
echo "║  cargo install tauri-cli                             ║"
echo "║  cd solace-hub && cargo tauri build                  ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  Naming law reminders:"
echo "  - App name: Solace Hub (never 'Companion App')"
echo "  - Port: 8888 (never 9222)"
echo ""
