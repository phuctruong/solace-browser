# Homebrew formula — Solace Browser (Yinyang Server)
# Tap: brew tap solaceai/browser
# Install: brew install solaceai/browser/solace-browser
#
# To publish:
#   1. Create repo: github.com/phuctruong/homebrew-browser
#   2. Copy this file to Formula/solace-browser.rb in that repo
#   3. After a macOS GH Actions build completes, update sha256 below:
#        curl -sL https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-macos-universal.sha256
#   4. Bump version + url + sha256 for each release
#
# BLOCKED ON: macOS GH Actions build (first tag push triggers build-binaries.yml)

class SolaceBrowser < Formula
  desc "AI automation backend for Solace Browser (Yinyang Server)"
  homepage "https://solaceagi.com"
  version "1.0.0"

  # Universal binary (arm64 + x86_64) — runs natively on both Apple Silicon and Intel
  url "https://storage.googleapis.com/solace-downloads/solace-browser/v1.0.0/solace-browser-macos-universal"
  # TODO: replace after first GH Actions build + GCS promotion
  # Get sha256 from: curl -sL https://...latest/solace-browser-macos-universal.sha256
  sha256 "PLACEHOLDER_SHA256_REPLACE_AFTER_FIRST_MACOS_BUILD"

  # No dependencies — PyInstaller bundles Python runtime
  bottle :unneeded

  def install
    bin.install "solace-browser-macos-universal" => "solace-browser"
  end

  def post_install
    # Create ~/.solace directory for port.lock and evidence vault
    (Pathname.new(Dir.home) / ".solace").mkpath
  end

  service do
    run [opt_bin / "solace-browser"]
    keep_alive true
    log_path var / "log/solace-browser.log"
    error_log_path var / "log/solace-browser.log"
    working_dir var
  end

  test do
    # Verify binary runs and returns a version
    system bin / "solace-browser", "--version"
  end
end
