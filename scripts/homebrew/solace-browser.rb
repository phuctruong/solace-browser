# Homebrew formula — Solace Browser + Solace Hub (macOS)
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
  desc "Hub-first Solace Browser bundle for macOS"
  homepage "https://solaceagi.com"
  version "1.0.0"

  # Universal bundle (arm64 + x86_64) — ships the Browser and Solace Hub together
  url "https://storage.googleapis.com/solace-downloads/solace-browser/v1.0.0/solace-browser-macos-universal.tar.gz"
  # TODO: replace after first GH Actions build + GCS promotion
  # Get sha256 from: curl -sL https://...latest/solace-browser-macos-universal.tar.gz.sha256
  sha256 "PLACEHOLDER_SHA256_REPLACE_AFTER_FIRST_MACOS_BUILD"

  bottle :unneeded

  def install
    libexec.install Dir["*"]
    bin.install_symlink libexec/"solace-browser-release-macos/solace-browser" => "solace-browser"
    bin.install_symlink libexec/"solace-browser-release-macos/solace-hub" => "solace-hub"
  end

  def post_install
    (Pathname.new(Dir.home) / ".solace").mkpath
  end

  service do
    run [opt_bin / "solace-hub"]
    keep_alive true
    log_path var / "log/solace-browser.log"
    error_log_path var / "log/solace-browser.log"
    working_dir var
  end

  test do
    assert_match "solace", shell_output("#{bin}/solace-browser --help 2>&1")
  end
end
