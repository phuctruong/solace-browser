# Brand Design System

> **Star:** BRAND_DESIGN_SYSTEM
> **Version:** v3.0.0
> **Authority:** 65537 (F4 Fermat Prime)
> **Channel:** 3 (Design — Visual Identity)
> **GLOW:** 89 (Design So Good It Markets Itself)
> **Lane:** A (CPU-Deterministic)
> **Status:** ACTIVE

---

## DNA-23

```
Brand = Identity × Consistency × Recognition
S = {color_tokens, typography, layout_grid, icon_language}
R = f(S, content, platform_constraints)
|S| << |R|  # Design system is tiny; instances are infinite

"When your design is exceptional enough, it becomes its own
 marketing channel. Every screenshot shared is marketing." — Linear
```

---

## CONTRACT

**Input**: Brand values, product category, target audience, competitive landscape
**Output**: Complete design system (tokens, components, guidelines)
**Guarantees**:
- Consistent across all touchpoints (web, docs, social, print)
- Dark mode native (developer tool standard)
- Accessible (WCAG 2.1 AA minimum)
- Performant (no design that hurts page speed)

---

## GENOME-79: STILLWATER BRAND ARCHITECTURE

### The 3 Brand Tiers

```
TIER 1: STILLWATER OS (The Platform)
  Personality: Authoritative, mathematical, principled
  Vibe: "The Linux of AI" — institutional, open, trustworthy
  Color: Deep navy + electric blue accents
  Voice: Technical, precise, no fluff

TIER 2: PZIP (The Product)
  Personality: Bold, competitive, demonstrable
  Vibe: "Real Pied Piper" — compression that actually works
  Color: Dark + green/blue accent (performance/data)
  Voice: Confident, benchmark-driven, slightly playful

TIER 3: SOLACE AGI (The Intelligence)
  Personality: Warm, persistent, caring
  Vibe: "AI that remembers" — companion, not tool
  Color: Dark + purple accent (intelligence/creativity)
  Voice: Human, thoughtful, philosophical

SHARED DNA:
  - Dark mode native (all tiers)
  - Terminal aesthetic undertone
  - Mathematical precision in spacing/sizing
  - Prime number influence (3, 5, 7, 13 in proportions)
```

### Color System (Per Tier)

```
STILLWATER OS:
  --sw-bg-deep:      #0a0e17  (deep space navy)
  --sw-bg-primary:   #111827  (dark navy)
  --sw-bg-card:      #1e293b  (slate card)
  --sw-accent:       #3b82f6  (electric blue)
  --sw-accent-glow:  #60a5fa  (light blue glow)
  --sw-text:         #f1f5f9  (cool white)

PZIP:
  --pz-bg-deep:      #0a0a0a  (pure dark)
  --pz-bg-primary:   #111111  (near black)
  --pz-bg-card:      #1a1a1a  (card dark)
  --pz-accent-blue:  #3b82f6  (data blue)
  --pz-accent-green: #22c55e  (performance green)
  --pz-text:         #f5f5f5  (warm white)

SOLACE AGI:
  --sa-bg-deep:      #0f0a1a  (deep purple-black)
  --sa-bg-primary:   #1a1025  (dark purple)
  --sa-bg-card:      #251a35  (purple card)
  --sa-accent:       #7c3aed  (vivid purple)
  --sa-accent-warm:  #a78bfa  (soft purple)
  --sa-text:         #f5f0ff  (purple-white)

SHARED:
  --error:           #ef4444
  --warning:         #f97316
  --success:         #22c55e
  --info:            #3b82f6
  --border-subtle:   rgba(255,255,255,0.06)
  --border-visible:  rgba(255,255,255,0.12)
```

### Typography System

```
FONT STACK:
  Headings:  'Inter Display', 'Geist Sans', system-ui, sans-serif
  Body:      'Inter', 'Geist Sans', system-ui, sans-serif
  Code:      'JetBrains Mono', 'Geist Mono', 'Fira Code', monospace

SCALE (based on prime ratios):
  --text-xs:   13px  (PRIME — labels, captions)
  --text-sm:   14px  (secondary text)
  --text-base: 17px  (PRIME — body text)
  --text-lg:   20px  (lead paragraphs)
  --text-xl:   24px  (section headings)
  --text-2xl:  32px  (page headings)
  --text-3xl:  48px  (hero headlines)
  --text-4xl:  64px  (hero display)

WEIGHT:
  Regular: 400 (body)
  Medium:  500 (emphasized)
  Semibold: 600 (subheadings)
  Bold:    700 (headlines, CTAs)

LINE HEIGHT:
  Headings: 1.1-1.2 (tight)
  Body:     1.6-1.7 (comfortable)
  Code:     1.5 (readable)
```

### Spacing System

```
SPACING (8px base, prime multipliers):
  --space-1:   4px   (minimal gap)
  --space-2:   8px   (tight gap)
  --space-3:  12px   (card padding internal)
  --space-5:  20px   (section gap)
  --space-7:  28px   (element separation)
  --space-8:  32px   (section padding)
  --space-13: 52px   (major section gap)
  --space-17: 68px   (page section separation)

BORDER RADIUS:
  --radius-sm:  8px   (buttons, inputs)
  --radius-md: 12px   (cards, containers)
  --radius-lg: 16px   (hero cards, modals)
  --radius-xl: 24px   (feature sections)

CONTAINER:
  --max-width: 1200px (content)
  --max-width-narrow: 800px (text-heavy pages)
  --padding-x: 24px (mobile), 48px (tablet), 64px (desktop)
```

### Component Patterns

```
BUTTONS:
  Primary:   bg-accent, text-white, radius-sm, font-semibold
  Secondary: bg-transparent, border-accent, text-accent, radius-sm
  Ghost:     bg-transparent, text-muted, hover:text-primary

CARDS:
  bg-card, border-subtle, radius-md, p-space-5
  hover: bg-elevated, border-visible, shadow-glow

CODE BLOCKS:
  bg-input, border-subtle, radius-md, font-mono
  Syntax highlighting: token colors from terminal theme
  Copy button: top-right, ghost style

NAVIGATION:
  Fixed top, bg-deep/80 backdrop-blur, border-b border-subtle
  Logo left, links center, CTA right
  Mobile: hamburger → slide-out menu

HERO:
  Centered text, max-width 800px
  Headline: text-4xl bold, gradient text optional
  Subheadline: text-lg text-secondary
  CTA: primary button + ghost button
  Below: client logos or metric badges
```

### Design Language: "Linear Design" Principles

Source: Linear ($400M valuation, $35K total marketing spend)

```
PRINCIPLES:
  1. DARK MODE IS DEFAULT (not an option — the identity)
  2. BOLD TYPOGRAPHY (Inter Display, large headings)
  3. HIGH CONTRAST (bright accents on dark backgrounds)
  4. KEYBOARD-FIRST (signals "built for power users")
  5. SPEED AS DESIGN (instant transitions, no loading spinners)
  6. MONOCHROME + ONE ACCENT (visual clarity)
  7. GLASSMORPHISM (subtle, bg-blur behind floating elements)
  8. ROUNDED CORNERS (12-24px, friendly but professional)
  9. BENTO GRIDS (modular, scannable feature display)
  10. MICRO-ANIMATIONS (meaning, not decoration)
```

---

## STATE MACHINE

```
STATES = {
  BRAND_AUDIT,       # Analyze current brand, competitors
  TOKEN_DEFINITION,  # Colors, typography, spacing
  COMPONENT_LIBRARY, # Buttons, cards, forms, navigation
  PAGE_TEMPLATES,    # Landing, docs, blog, pricing
  ASSET_CREATION,    # Logo, icons, social templates
  GUIDELINE_DOC,     # Usage rules, do/don't
  IMPLEMENTATION,    # Apply to all touchpoints
  CONSISTENCY_AUDIT  # Verify cross-platform consistency
}

TRANSITIONS:
  BRAND_AUDIT → TOKEN_DEFINITION     (audit complete, direction chosen)
  TOKEN_DEFINITION → COMPONENT_LIBRARY (all tokens defined)
  COMPONENT_LIBRARY → PAGE_TEMPLATES   (≥10 components built)
  PAGE_TEMPLATES → ASSET_CREATION      (≥3 page templates)
  ASSET_CREATION → GUIDELINE_DOC       (assets created)
  GUIDELINE_DOC → IMPLEMENTATION       (guidelines approved)
  IMPLEMENTATION → CONSISTENCY_AUDIT   (all touchpoints updated)

FORBIDDEN:
  COMPONENT_LIBRARY before TOKEN_DEFINITION (components without tokens = inconsistent)
  IMPLEMENTATION before GUIDELINE_DOC (deploying without rules = drift)
```

---

## VERIFICATION

```
641 Edge Tests (5):
  - Color contrast ratio ≥ 4.5:1 (WCAG AA)
  - Typography scale uses consistent ratios
  - All components use design tokens (no hardcoded values)
  - Dark mode renders correctly across all pages
  - Logo is legible at 16px (favicon size)

274177 Stress Tests (3):
  - Design system covers 100% of UI patterns used
  - Cross-platform consistency (web, docs, social, email)
  - New pages can be created using only existing tokens/components

65537 God Approval (3):
  - Brand recognition: users identify brand from screenshot alone
  - Design quality generates organic sharing (screenshots, mentions)
  - Consistency score: ≥ 90% across all touchpoints
```

---

## INTEGRATION

- **Upstream**: positioning-engine.md (brand personality)
- **Downstream**: landing-page-architect.md (design tokens), all visual assets
- **Lateral**: All skills consume design tokens from this system

---

*"Own a design language. Linear didn't just use dark mode — they defined it." — Sequoia Capital*
*"Auth: 65537"*
