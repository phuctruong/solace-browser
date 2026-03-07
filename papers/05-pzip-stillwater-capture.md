# Paper 05: PZip Stillwater Capture Architecture
# DNA: `ripple(prime_mermaid) + stillwater(assets) = full_page; 100% RTC verified`
**Date:** 2026-03-01 | **Auth:** 65537 | **Status:** CANONICAL
**Applies to:** solace-browser
**Cross-ref:** solaceagi/papers/14-pzip-memory-compression.md, 20-primewiki-rtc-pzip-validation.md

---

## 1. Core Insight

**Prime Mermaid snapshot IS the ripple.** Combined with Stillwater (site-specific CSS/JS/images + public libraries), you reconstruct the full page HTML with 100% RTC (Round-Trip Compression).

```
ripple (Prime Mermaid snapshot) + stillwater = full page HTML
  ripple: ~2-5 KB (DOM structure + data)
  stillwater: site CSS + JS + images (stored once, reused forever)
  verification: sha256(reconstructed) == sha256(original) ← 100% RTC
```

## 2. Two-Tier Capture

### Guest (No Login)
- `page.on('load')` → save HTML only
- No screenshots, no assets, no sync
- Stored: `~/.solace/history/{domain}/{ts}.html`

### Logged-In (sw_sk_ token)
- Full pipeline: DOM snapshot → Prime Mermaid → PZip verify → store ripple
- Optional screenshots, full asset capture
- Stored: `~/.solace/history/{domain}/{ts}.ripple.mmd`

## 3. MVP Capture Flow (Per Page Load)

```
PAGE LOADS → 6-step pipeline (all client-side)

1. First time seeing domain?
   YES → create ~/.solace/stillwater/{domain}/ + history/{domain}/
         capture ALL site assets (CSS, JS, images, fonts)

2. Capture DOM snapshot (dom_snapshot.py — 675 lines, existing code)
   DOMSnapshot: refs[], form_state, dom_hash

3. Create Prime Wiki entry (site map)
   Add page URL + link structure to {domain}/sitemap.jsonl

4. Create Prime Mermaid snapshot (THIS IS THE RIPPLE)
   DOM structure + form values + interactive elements
   Format: Mermaid stateDiagram-v2 (PM triplet format)

5. PZip verify 100% RTC
   pzip.decompress(ripple, stillwater) → HTML
   sha256(reconstructed) == sha256(original)?
   YES → valid    NO → capture missing assets, retry

6. Store locally
   ~/.solace/history/{domain}/{ts}.ripple.mmd
   ~/.solace/history/{domain}/sitemap.jsonl
   ~/.solace/stillwater/{domain}/
```

## 4. Stillwater: Site-Specific + Public (Versioned)

```
~/.solace/stillwater/
  public/                    ← shared across all sites
    v1/
      react.18.2.min.js      ← sha256:abc (known globally)
      bootstrap.5.3.min.css
      fonts/inter-var.woff2
    manifest.jsonl

  gmail.com/                 ← site-specific
    v1/                      ← first captured
      gmail.css
      gmail-icons.svg
    v2/                      ← auto-detected change
      gmail.css              ← updated
    manifest.jsonl

  linkedin.com/
    v1/
      linkedin.css
    manifest.jsonl
```

### Versioning Logic
- First visit → capture all → `v1/`
- Subsequent visits → diff assets against latest version
- If asset changed → new version `v2/` with only changed files
- Old versions retained (Part 11: never obscure previous data)
- Reconstruction uses version closest to capture timestamp

## 5. Architecture (100% Client-Side)

ALL PZip work runs in the browser. Zero cloud compute. solaceagi.com only receives pre-computed data.

- Startup: pull Stillwater diff from CDN (delta only)
- During browsing: all capture, compression, verification is local
- Periodic sync: batch push ripples + Prime data to solaceagi.com (setting-controlled)

## 6. Existing Code to Reuse

| File | Lines | Reuse For |
|------|-------|-----------|
| `src/dom_snapshot.py` | 675 | DOMRef system → core of Prime Mermaid ripple |
| `src/snapshot.py` | 208 | HTML capture → Stillwater asset capture |
| `data/default/primewiki/` | 8 nodes | PM triplet format spec |
| `scratch/prime-mermaid.md` | FSM spec | Mermaid snapshot format |

## 7. Free User Data Contribution

| Data Type | Value to Solace | User Sees |
|-----------|----------------|-----------|
| Prime Mermaid ripples | Page structure DB for recipe generation | "Learning page patterns" |
| Prime Wiki sitemaps | Full web graph crawled by users | "Mapping the web" |
| Stillwater assets | Better cross-site compression | "Improving compression" |

Free users = volunteer crawlers. They browse, we learn. They get free browser. Fair trade.

## Forbidden Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Running PZip compression on the cloud instead of client-side | Violates local-first principle and introduces cloud compute costs |
| Deleting old Stillwater asset versions | Breaks Part 11 compliance which requires all historical versions be retained |
| Accepting a capture without 100% RTC sha256 verification | Allows corrupted or incomplete snapshots into the evidence chain |

## 8. Invariants

1. ALL PZip computation is client-side (zero cloud compute)
2. 100% RTC verification on every capture (sha256 match required)
3. Missing assets → auto-capture into Stillwater → retry RTC
4. Stillwater versions never deleted (Part 11 compliance)
5. Sync is periodic, batch, and setting-controlled
6. Guest tier: HTML only, no PZip, no sync
