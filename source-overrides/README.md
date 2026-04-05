# Source Overrides

This directory contains modifications to Chromium source files.
Each file mirrors the path under `source/src/` and replaces the original during build.

## Applied Overrides

### chrome/browser/ui/views/side_panel/side_panel_header.cc
- Removed close button from Yinyang sidebar header
- Side panel is always visible and cannot be closed by user
- The sidebar is a permanent part of the Solace Browser experience
