# Paper 39 — Marketing Asset Pipeline
# Solace Browser | Software 5.0 | 2026-03-03
# DNA: test_sessions → screenshots → gifs → social → tutorials → viral

---

## The Equation

```
Marketing = Evidence × Automation × Story
  Evidence   = every test screenshot is proof the product works
  Automation = Solace Browser generates its own marketing assets
  Story      = Yinyang narrates, users share
```

**Key insight (Seth Godin):** "The most remarkable product demo is the product demoing itself."
**Key insight (Rory Sutherland):** "A screenshot of AI approving your email before sending it is worth 1,000 words."
**Key insight (Vanessa Van Edwards):** "Warmth = watching Yinyang move the mouse. Users feel it's alive."

---

## Asset Pipeline (5 stages)

```
[1] TESTING SESSION
    └── Playwright captures screenshots automatically
    └── Every QA run generates artifact evidence
    └── Stored in: artifacts/screenshot-*.png

[2] SCREENSHOT CURATION
    └── Best shots → marketing/screenshots/YYYY-MM-DD/
    └── Named semantically: home-page-v2.png, onboarding-welcome.png
    └── Categories: hero, feature, comparison, social-proof

[3] GIF CREATION (Animated walkthroughs)
    └── Script: marketing/scripts/make-gif.sh
    └── Input: sequence of screenshots + timing
    └── Output: marketing/gifs/{feature}-walkthrough.gif
    └── Narration: Yinyang speech bubbles overlaid via ImageMagick

[4] SOCIAL POSTS (Auto-drafted by Yinyang)
    └── Template: marketing/social/templates/
    └── Platforms: Twitter/X, LinkedIn, Instagram, Reddit
    └── Trigger: POST /api/yinyang/chat with asset + prompt
    └── Output: marketing/social/drafts/YYYY-MM-DD/

[5] USER TUTORIALS (Screen recordings)
    └── Playwright records: page.video.path()
    └── Yinyang adds callouts at each step
    └── Simulated mouse clicks + YinYang speech bubbles
    └── Output: marketing/videos/{app-id}-tutorial.mp4
```

---

## Screenshot Categories

| Category | Purpose | Example Files |
|----------|---------|---------------|
| `hero/` | Hero shots for website, ads | home-page-v2.png, app-store-v2.png |
| `onboarding/` | First-time UX flow | onboarding-welcome.png, tutorial-step-*.png |
| `features/` | Specific feature demos | gmail-triage.png, schedule-view.png |
| `social-proof/` | Evidence/Part 11 badges | compliance-strip.png, audit-trail.png |
| `comparison/` | Before/after, vs competitors | no-api-key-needed.png |
| `localization/` | All 13 languages | home-es.png, home-ar.png, home-zh.png |

---

## GIF Walkthrough Scripts (Phase 1)

### GIF 1: "Your AI agent approves everything"
```
Frame 1: Home page loads (0.5s)
Frame 2: Click Gmail Inbox Triage (0.5s)
Frame 3: Yinyang rail opens, says "Scanning 47 emails..." (1s)
Frame 4: Preview appears with draft replies (1.5s)
Frame 5: User clicks APPROVE (0.5s)
Frame 6: YinYang: "Done! 3 replies drafted. Your approval sealed forever." (1.5s)
Frame 7: Part 11 badge pulses green (0.5s)
Total: ~6 seconds, looping
```

### GIF 2: "No API key required"
```
Frame 1: Competitor shows "Enter your OpenAI API key" (1s)
Frame 2: Solace Browser shows Gmail.com directly (1s)
Frame 3: Yinyang: "I use the web. No keys, no bills." (1.5s)
Total: ~3.5 seconds
```

### GIF 3: "13 languages, one click"
```
Frame 1: Home in English
Frame 2: Click globe icon
Frame 3: Select 日本語
Frame 4: Full page in Japanese (not just nav!)
Frame 5: YinYang greets in Japanese
Total: ~4 seconds
```

### GIF 4: "Create your own app with Yinyang"
```
Frame 1: Create App page loads
Frame 2: Type "summarize my LinkedIn messages daily"
Frame 3: YinYang generates recipe preview
Frame 4: Test button clicked — YinYang navigates LinkedIn
Frame 5: Recipe saved
Total: ~8 seconds
```

---

## Animated GIF Generation Script

```bash
#!/bin/bash
# marketing/scripts/make-gif.sh
# Usage: ./make-gif.sh <input_dir> <output_name> <delay_ms>

INPUT_DIR=$1
OUTPUT=$2
DELAY=${3:-80}  # centiseconds between frames

# Collect PNGs in order
FILES=($(ls $INPUT_DIR/*.png | sort))

# Create animated GIF using ImageMagick
convert -delay $DELAY -loop 0 "${FILES[@]}" \
  -layers optimize \
  marketing/gifs/$OUTPUT.gif

echo "Created: marketing/gifs/$OUTPUT.gif"
echo "Size: $(du -sh marketing/gifs/$OUTPUT.gif | cut -f1)"
```

---

## Mouse Click Simulation (Yinyang-narrated)

For social media demos, we simulate cursor movement + click animations:

```python
# marketing/scripts/capture-walkthrough.py
from playwright.sync_api import sync_playwright
import subprocess

def capture_walkthrough(steps: list[dict], output_dir: str):
    """
    steps = [
      {"action": "navigate", "url": "http://localhost:8791/"},
      {"action": "highlight", "selector": ".home-featured-card", "label": "Click here →"},
      {"action": "click", "selector": ".home-featured-card"},
      {"action": "screenshot", "name": "step-01-featured-app"},
      {"action": "yinyang-say", "text": "This is Gmail Inbox Triage. Let me show you."},
    ]
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page(viewport={"width": 1280, "height": 800})

        for step in steps:
            if step["action"] == "navigate":
                page.goto(step["url"])
            elif step["action"] == "screenshot":
                page.screenshot(path=f"{output_dir}/{step['name']}.png")
            elif step["action"] == "click":
                el = page.locator(step["selector"])
                # Animate cursor to element center
                box = el.bounding_box()
                page.mouse.move(box["x"] + box["width"]/2, box["y"] + box["height"]/2)
                page.screenshot(path=f"{output_dir}/pre-click.png")  # cursor hover
                el.click()
            elif step["action"] == "yinyang-say":
                # Inject speech bubble overlay
                page.evaluate(f"""
                    const bubble = document.createElement('div');
                    bubble.style = 'position:fixed;bottom:80px;left:50%;transform:translateX(-50%);background:#00b4d8;color:#fff;padding:12px 20px;border-radius:12px;font-size:14px;z-index:9999;max-width:400px;text-align:center;';
                    bubble.textContent = '{step["text"]}';
                    document.body.appendChild(bubble);
                """)
                page.screenshot(path=f"{output_dir}/yinyang-say.png")
```

---

## Social Post Templates

### Twitter/X
```
🤖 I asked Yinyang to triage my Gmail inbox.

It read 47 emails, drafted 3 replies, and waited for my approval.

Zero API keys. Zero cloud uploads. Everything happened locally.

This is Software 5.0.

[GIF: gmail-triage-walkthrough.gif]

#AI #Automation #SolaceBrowser
```

### LinkedIn
```
I've been testing AI browser automation for 3 months.

The biggest friction point? API keys and privacy.

Solace Browser eliminates both:
- No OpenAI/Anthropic key needed
- AI uses the web directly (Gmail, Slack, LinkedIn)
- Every action requires your approval
- SHA-256 audit trail, forever

[Screenshot: home-page-v2.png]
```

### Reddit (r/MachineLearning, r/productivity)
```
Title: We built an AI browser that needs zero API keys (it uses web versions directly)

Body: [explanation + home-page screenshot + GIF]
```

---

## Viral Moment Checklist (Seth Godin + Rory Sutherland)

| Moment | Why It's Remarkable | Asset Type |
|--------|--------------------|-----------|
| AI asking for approval before sending email | Trustworthy AI = shareable | GIF |
| 13 languages with one click | "Whoa" factor | GIF |
| Part 11 audit badge pulsing | "My AI keeps receipts" | Screenshot |
| WhatsApp automation (no API) | Only possible path | GIF |
| $0.00 cost on recipe replay | "Free is remarkable" | Screenshot |
| YinYang saying something funny in 13 languages | Personality + global | GIF |

---

## Implementation Priority

| Phase | Asset | Est. Time | Impact |
|-------|-------|-----------|--------|
| P0 | Hero screenshots (home, app-store, onboarding) | Done ✓ | Website |
| P1 | Gmail triage GIF (6 frames) | 1 session | Twitter |
| P1 | Language switch GIF (4 frames) | 1 session | LinkedIn |
| P2 | Full walkthrough video (60s) | 1 session | YouTube |
| P3 | Narrated tutorial series (per app) | Ongoing | Docs + YouTube |
| P4 | User-submitted testimonial assets | Launch | Social proof |

---

## File Structure

```
marketing/
  screenshots/
    2026-03-03/
      home-page-v2.png          ← DONE ✓
      app-store-v2.png          ← DONE ✓
      onboarding-welcome.png    ← DONE ✓
  gifs/
    gmail-triage-walkthrough.gif  ← Phase 1
    language-switch.gif           ← Phase 1
  social/
    templates/
      twitter.md
      linkedin.md
      reddit.md
    drafts/
      2026-03-03/
  videos/
    gmail-triage-tutorial.mp4     ← Phase 2
  scripts/
    make-gif.sh                   ← Phase 1
    capture-walkthrough.py        ← Phase 1
```

---

---

## solaceagi.com/gallery — Public Asset Gallery

**Concept:** As we test features, every session auto-populates a live gallery on solaceagi.com.
Beta testers see it. Press sees it. New users see the product in motion before downloading.

```
URL: https://www.solaceagi.com/gallery

Sections:
  [Animated Walkthroughs] — GIFs with Yinyang narrating
  [Feature Screenshots]   — Clean hero shots, filterable by feature
  [Localization]          — Same screen in 13 languages
  [App Demos]             — Per-app walkthrough GIFs

Data source: marketing/ folder in solace-browser repo → served via solaceagi.com
Upload flow: test session → screenshot → git push → gallery auto-updates
```

**Gallery page features:**
- Filterable grid (by app, by language, by feature)
- Click to expand (full-size view)
- Download button (for beta testers, press kit)
- "Share" button → auto-generates social post with the asset
- Beta tester access: any signed-in user sees the gallery

**The flywheel:**
```
Testing → Screenshots → Gallery → Beta testers share → New users download → More testing
```

**Implementation:** `templates/gallery.html` on solaceagi.com, served from Cloud Run.
Assets stored in Cloud Storage bucket `solace-marketing-assets` (public read).
CI pipeline: push to marketing/ → Cloud Build copies to bucket → gallery refreshes.

---

## Current Assets (2026-03-03)

| File | Path | Status |
|------|------|--------|
| home-walkthrough.gif | marketing/gifs/home-walkthrough.gif | ✓ DONE (3.3MB) |
| home-page-v2.png | marketing/screenshots/2026-03-03/home-page-v2.png | ✓ DONE |
| app-store-v2.png | marketing/screenshots/2026-03-03/app-store-v2.png | ✓ DONE |
| onboarding-welcome.png | marketing/screenshots/2026-03-03/onboarding-welcome.png | ✓ DONE |
| gmail-triage.gif | marketing/gifs/gmail-triage.gif | ⏳ Next |
| language-switch.gif | marketing/gifs/language-switch.gif | ⏳ Phase 1 |

---

## DNA
`marketing = test_sessions × evidence × story × yinyang_narrator`
`gallery = solaceagi.com/gallery → beta_testers → press → viral`

**Evidence:** 1 GIF + 3 hero screenshots captured 2026-03-03
**Next:** Gmail triage GIF (P1) — run Gmail test → capture frames → make-gif.sh
**Gate:** Yinyang approves every social post before publish (Anti-Clippy rule)
