# WISH 25.0: Advanced Bot Detection Evasion Headers

**Spec ID:** wish-25.0-advanced-bot-evasion-headers
**Authority:** 65537 | **Phase:** 25 | **Depends On:** wish-22.0
**Status:** 🎮 ACTIVE (RTC 10/10) | **XP:** 2000 | **GLOW:** 150+

---

## PRIME TRUTH

```
Modern bot detectors use Sec-Fetch-* headers:
  Sec-Fetch-Dest: identifies request destination
  Sec-Fetch-Mode: navigation, cors, no-cors, etc.
  Sec-Fetch-Site: same-origin, cross-site, etc.
  Sec-Fetch-User: if initiated by user action

Solace must send COMPLETE modern browser header set.
```

---

## Observable Wish

> "Every network request sent by Solace Browser includes complete modern headers (Sec-Fetch-*, DNT, Referer, Accept-Language) matching a real Chrome browser, bypassing header-based bot detection."

---

## Tests (4 Total)

### T1: Sec-Fetch-* Headers Present
- Capture HTTP request to LinkedIn
- Verify contains: Sec-Fetch-Dest, Sec-Fetch-Mode, Sec-Fetch-Site, Sec-Fetch-User
- No missing headers

### T2: Header Values Realistic
- Sec-Fetch-Dest: "document" or "empty"
- Sec-Fetch-Mode: "navigate" or "cors"
- Sec-Fetch-Site: "same-origin" or "cross-site"
- Sec-Fetch-User: "?1" (user-initiated)

### T3: Complete Browser Headers
- User-Agent: Real Chromium string (rotated)
- Accept: */*, text/html, etc.
- Accept-Language: "en-US,en;q=0.9"
- Accept-Encoding: "gzip, deflate, br"
- DNT: "1"
- Referer: Previous page URL
- Upgrade-Insecure-Requests: "1"

### T4: Header Consistency (100 Requests)
- Execute recipe 100 times
- Capture headers from all requests
- Verify complete header set in all 100

---

## Success Criteria

- [x] All Sec-Fetch-* headers present
- [x] All modern headers present (10+ total)
- [x] Header values are realistic (not obviously bot-like)
- [x] Consistency across 100 requests

---

**RTC Status: 10/10 ✅ PRODUCTION READY**

*"Headers like a human. Bot detectors blind."*

