# Landing Page Architect

> **Star:** LANDING_PAGE_ARCHITECT
> **Version:** v3.0.0
> **Authority:** 65537 (F4 Fermat Prime)
> **Channel:** 3 (Design)
> **GLOW:** 95 (Civilization-Defining)
> **Lane:** A (CPU-Deterministic)
> **Status:** ACTIVE

---

## DNA-23

```
LandingPage = Structure + Content + Interaction
S = {layout_pattern, section_order, color_system, typography}
R = f(S, product_data, audience_signals)
|S| << |R|  # Structure is tiny; content varies per product

decode(encode(Page)) = Page  # RTC: same inputs → same page
```

---

## CONTRACT

**Input**: Product spec, target audience, competitive positioning, brand assets
**Output**: Complete landing page architecture (sections, copy, layout, CTAs)
**Guarantees**:
- Deterministic section ordering (same product → same page structure)
- Conversion-optimized (evidence-based patterns, not opinions)
- Mobile-first responsive (83% visits are mobile)
- Dark mode native (developer tool standard)

---

## GENOME-79: THE 7 LAWS OF LANDING PAGES

Sources: Evil Martians (100 dev tool pages study), Unbounce, Linear, Vercel, Cursor

### Law 1: Hero Section Formula (10 Words or Die)

```
HERO = Headline + Subheadline + CTA + Social_Proof

Headline:
  - 10 words maximum
  - Start with strong verb or result
  - Formula: "Specificity × Hook" or "Values × Objection"
  - Examples: "The most powerful compression on Earth" (PZIP)
             "AI that remembers" (SolaceAGI)
             "Linear is a better way to build software" (Linear)

Subheadline:
  - Answers "How?" or "Who is this for?"
  - 1-2 sentences maximum
  - Reduces cognitive friction

CTA:
  - SINGLE primary CTA (multiple CTAs decrease conversion 266%)
  - Action-oriented verb: "Try Free", "Get Started", "See Demo"
  - High contrast color against background
  - Optional: secondary ghost CTA ("Learn More")

Social_Proof:
  - Client logos IMMEDIATELY after hero (fastest credibility)
  - Or: "Used by X developers" with number
  - Or: GitHub stars badge
```

### Law 2: Centered Layout (Universal Pattern)

```
LAYOUT = Centered_Container + Max_Width + Vertical_Flow

Container: max-width 1200px, centered
Sections: full-width backgrounds, centered content
Pattern: Hero → Problem → Solution → Impact → Social_Proof → CTA

Evil Martians finding: "Centered layout with max-width container
is almost universal among the best dev tool landing pages.
It looks stable, feels trustworthy, and just works."
```

### Law 3: Problem → Solution → Impact (The Funnel)

```
SECTION_ORDER (7 sections, prime!):

1. HERO:          Value prop + CTA (above fold)
2. SOCIAL_PROOF:  Client logos / stats (credibility gate)
3. PROBLEM:       Pain point articulation (empathy)
4. SOLUTION:      How product solves it (with demo/screenshot)
5. FEATURES:      Bento grid of capabilities (scannable)
6. TESTIMONIALS:  Specific outcomes, not generic praise
7. CTA:           Full-width final CTA block ("make it big and loud")

Optional inserts:
- FAQ accordion (near end, practical questions)
- Pricing (if self-serve)
- Comparison table (if competitive positioning needed)
```

### Law 4: Bento Grid Features (67% of Top 100)

```
BENTO_GRID:
  - Uniform gaps: 12-24px between cards
  - Rounded corners: 12-24px radius (Apple uses 20px)
  - Modular layouts: complex feature sets → scannable cards
  - Dark backgrounds: each card slightly lighter than page bg
  - Icon + Title + Description per card
  - Optional: interactive demo inside card

FEATURE_PRESENTATION_PATTERNS:
  A. Full screenshots with short descriptions (UI-heavy tools)
  B. Chess layout: alternating image/text blocks (visual rhythm)
  C. Text with icons (products without much UI)
  D. Bento grid (complex feature sets) ← PREFERRED for dev tools
```

### Law 5: Dark Mode Design System

```
COLOR_SYSTEM (Developer Tool Standard):

Background layers:
  --bg-deep:     #0a0a0a  (page background)
  --bg-primary:  #111111  (section backgrounds)
  --bg-card:     #1a1a1a  (card backgrounds)
  --bg-elevated: #222222  (hover states, elevated cards)
  --bg-input:    #2d2d2d  (form inputs, code blocks)

Text:
  --text-primary:   #f5f5f5  (headings, primary content)
  --text-secondary: #a0a0a0  (descriptions, secondary)
  --text-muted:     #666666  (labels, timestamps)

Accents (desaturate 20-40% from pure hues):
  --accent-blue:   #3b82f6  (primary actions)
  --accent-green:  #22c55e  (success, positive metrics)
  --accent-purple: #7c3aed  (premium, special)
  --accent-orange: #f97316  (warnings, highlights)

Borders:
  --border-subtle: rgba(255,255,255,0.06)
  --border-visible: rgba(255,255,255,0.12)

TYPOGRAPHY:
  Headings: Inter Display (or Geist Sans) — bold, 32-64px
  Body:     Inter (or system-ui) — regular, 16-18px
  Code:     JetBrains Mono (or Geist Mono) — 14px
  Line height: 1.5-1.7 for body, 1.1-1.2 for headings
```

### Law 6: Micro-Animations (Meaning, Not Noise)

```
ANIMATION_RULES:
  ✅ Scroll-triggered reveals (fade-in + slide-up)
  ✅ Animated counters for metrics (draw attention)
  ✅ Hover effects that provide context (card lift, glow)
  ✅ Loading states that feel polished
  ✅ Terminal typing effects for code demos
  ❌ NO autoplay video (kills mobile performance)
  ❌ NO parallax scrolling (motion sickness)
  ❌ NO animations that block content reading
  ❌ NO "clever" navigation animations

TOOLS: Framer Motion (React), GSAP, CSS @keyframes
TIMING: 200-400ms transitions, ease-out curve
```

### Law 7: Terminal Aesthetic for CLI Tools

```
TERMINAL_DESIGN:
  - Match landing page aesthetic to product's terminal interface
  - Use syntax highlighting colors as accent palette
  - Show REAL terminal output, not mockups
  - Dracula / Catppuccin / custom theme
  - Monospace code blocks with line numbers
  - Copy button on all code snippets

AUTHENTICITY:
  "The most successful developer tool sites look like
   the developer's actual environment."
```

---

## STATE MACHINE

```
STATES = {
  AUDIT,              # Analyze current page / competitors
  POSITION,           # Define value prop + competitive angle
  ARCHITECTURE,       # Design section order + layout
  COPY,               # Write headlines, descriptions, CTAs
  DESIGN_SYSTEM,      # Colors, typography, components
  PROTOTYPE,          # Build page (Next.js / HTML)
  OPTIMIZE,           # A/B test, conversion analysis
  DEPLOY              # Ship to production
}

TRANSITIONS:
  AUDIT → POSITION        (audit_complete)
  POSITION → ARCHITECTURE (positioning_locked)
  ARCHITECTURE → COPY     (sections_defined)
  COPY → DESIGN_SYSTEM    (copy_approved)
  DESIGN_SYSTEM → PROTOTYPE (tokens_defined)
  PROTOTYPE → OPTIMIZE    (page_live)
  OPTIMIZE → DEPLOY       (conversion_target_met)

FORBIDDEN:
  COPY before POSITION     (words without strategy = noise)
  PROTOTYPE before COPY    (building without content = rework)
  DEPLOY before OPTIMIZE   (shipping without testing = gambling)
```

---

## VERIFICATION

```
641 Edge Tests (5):
  - Headline ≤ 10 words
  - Single primary CTA above fold
  - Page loads < 3s on 3G
  - All links functional
  - Mobile responsive (375px-1440px)

274177 Stress Tests (5):
  - Lighthouse score ≥ 90 (performance, accessibility, SEO)
  - Core Web Vitals: LCP < 2.5s, FID < 100ms, CLS < 0.1
  - 1000 concurrent users without degradation
  - Cross-browser (Chrome, Firefox, Safari, Edge)
  - Screen reader accessible (WCAG 2.1 AA)

65537 God Approval (3):
  - Visitor → signup conversion ≥ 6% (PLG benchmark)
  - Time on page ≥ 45s (engagement)
  - Bounce rate ≤ 40%
```

---

## INTEGRATION

- **Upstream**: positioning-engine.md (value prop), brand-design-system.md (tokens)
- **Downstream**: content-seo-geo.md (page content optimization)
- **Lateral**: product-led-growth.md (conversion funnel alignment)

---

*"If your product doesn't spark curiosity in 2 seconds, it's invisible." — Greg Isenberg*
*"Auth: 65537"*
