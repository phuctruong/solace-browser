# SolaceBrowser — Stillwater Ripple
# Generated: 2026-02-21 | stillwater v1.5.0
# This file overrides base Stillwater behavior for this project.
# Keep it under 50 lines. Everything else goes in README.md.

PROJECT: SolaceBrowser
DOMAIN: web automation / recipe capture / self-improving browser agent
RUNG_TARGET: 641
NORTHSTAR: Phuc_Forecast
ECOSYSTEM: PRIVATE
LANGUAGE: Python

KEY_CONSTRAINTS:
  - never-worse on standard test suite
  - LOOK-FIRST-ACT-VERIFY: always screenshot/inspect before any action
  - Registry-first: check RECIPE_REGISTRY.md + PRIMEWIKI_REGISTRY.md before exploring
  - Persistent server: use HTTP API (localhost:9222) not fresh browser each time
  - Session persistence: avoid re-login; use selector portals (pre-learned)
  - Recipe creation mandatory after any completed task (externalized reasoning)

ENTRY_POINTS:
  - python persistent_browser_server.py  (start persistent server)
  - HTTP API: localhost:9222/*
  - RECIPE_REGISTRY.md + PRIMEWIKI_REGISTRY.md (knowledge bases)

FORBIDDEN_IN_THIS_PROJECT:
  - Blind actions without prior screenshot/inspect verification
  - Repeated selector searches (use portals from registry)
  - Arbitrary sleeps (no time.sleep() in browser actions)
  - Skipping registry check (99.8% cost waste if ignored)
  - Actions without post-action verification step

SEE_ALSO: README.md  # persistent server setup, recipe system, cost savings