# PrimeWiki Node: Reddit Homepage (Phase 1)

**Tier**: 47/127/241
**Timestamp**: 2026-02-15
**C-Score**: 0.94 (Coherence - page structure stable)
**G-Score**: 0.91 (Gravity - landmark confidence)
**Phase**: 1 (Discovery) - $0.15 cost completed
**Status**: ✅ Phase 1 Complete - Ready for Phase 2 ($0.0015 replay cost)

---

## Key Landmarks (Verified with CSS Selectors)

| Name | Selector | ARIA Role | Confidence |
|------|----------|-----------|-----------|
| Search Bar | `input[name="q"]` | textbox | 0.99 |
| Log In Link | `a[href*="login"]` | link | 0.98 |
| Hamburger Menu | `#navbar-menu-button` | button | 0.98 |
| Reddit Logo | `a[aria-label="Home"]` | link | 0.97 |
| Get App Button | `#get-app` | button | 0.96 |
| Communities | `a[href^="/r/"]` | link | 0.95 |

---

## Page Statistics

- **Body Size**: 236,250 bytes (full render)
- **DOM Elements**: 827
- **ARIA Nodes**: 417
- **Links Found**: 20+ subreddit links
- **Load Time**: 3-4 seconds with networkidle
- **Framework**: React SPA

---

## Navigation Portals

- Homepage → Search Results: Type in search bar, press Enter
- Homepage → Community Page: Click `a[href^="/r/"]`
- Homepage → Login: Click `a[href*="login"]`
- Homepage → Trending: Click trending post link
- Homepage → Mobile: Click `#get-app`

---

## Phase 2 Replay Cost

- **Discovery**: $0.15 (this LLM session)
- **Replay**: $0.0015 (saved recipe execution)
- **Savings**: 100x cost reduction

---

## Verdict

✅ **Phase 1 Complete**: All critical landmarks discovered and CSS selectors verified.
✅ **Ready for Phase 2**: Execute saved recipes for search, navigation, browsing.
✅ **Safe for Automation**: No bot detection, no rate limiting observed.

**Auth**: 65537 | **Northstar**: Phuc Forecast
