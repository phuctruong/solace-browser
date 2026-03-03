# GCS Download Distribution Contract
**Date:** 2026-03-03  
**Scope:** Solace Browser binaries served by `solaceagi.com` website surfaces.

## Goal
`solaceagi.com` should act as the canonical download entrypoint while binaries are served directly from Google Cloud Storage.

## Bucket Layout
- Bucket: `gs://solace-downloads`
- Prefix: `solace-browser/`
- Channels:
  - Immutable: `v{VERSION}/`
  - Mutable: `latest/`

Artifacts in `latest/`:
1. `solace-browser-linux-x86_64`
2. `solace-browser-linux-x86_64.sha256`
3. `solace-browser-macos-universal`
4. `solace-browser-macos-universal.sha256`
5. `solace-browser-windows-x86_64.exe`
6. `solace-browser-windows-x86_64.exe.sha256`

## Public URLs (Website Must Use)
1. Linux:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-linux-x86_64`
2. macOS:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-macos-universal`
3. Windows:
   - `https://storage.googleapis.com/solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe`

## Upload Commands
Linux:
```bash
gcloud storage cp dist/solace-browser-linux-x86_64 gs://solace-downloads/solace-browser/latest/solace-browser-linux-x86_64
gcloud storage cp dist/solace-browser-linux-x86_64.sha256 gs://solace-downloads/solace-browser/latest/solace-browser-linux-x86_64.sha256
```

macOS:
```bash
gcloud storage cp dist/solace-browser-macos-universal gs://solace-downloads/solace-browser/latest/solace-browser-macos-universal
gcloud storage cp dist/solace-browser-macos-universal.sha256 gs://solace-downloads/solace-browser/latest/solace-browser-macos-universal.sha256
```

Windows:
```bash
gcloud storage cp dist/solace-browser-windows-x86_64.exe gs://solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe
gcloud storage cp dist/solace-browser-windows-x86_64.exe.sha256 gs://solace-downloads/solace-browser/latest/solace-browser-windows-x86_64.exe.sha256
```

## Release Gate
Before merging website download-link changes:
1. All 3 platform URLs return `HTTP 200`.
2. All 3 checksum URLs return `HTTP 200`.
3. Website download buttons point to the exact URLs above (no `github.com/releases` fallback).
4. Binary header checks pass:
   - Linux download starts with `ELF`
   - macOS download starts with Mach-O magic
   - Windows download starts with PE (`MZ` + `PE\0\0`)
