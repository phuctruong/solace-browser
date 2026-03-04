# Styleguide: YinYang Palette + Animation System
# Auth: 65537 | Version: 1.0 | Date: 2026-03-03
# SW5.0 Stage: [Papers ✓] [Diagrams ✓] [**Styleguide ✓**] [Code] [Tests] [Seal]
# Depends on: Paper 04 (Dual Rail), Paper 08 (Delight Engine), Paper 09 (Tutorial)

---

## 1. Token Inventory (MANDATORY FIRST STEP — skill: styleguide-first)

All visual elements MUST reference these `--sb-*` tokens only. No hardcoded colors.

### Core Palette Tokens
| Token | Value | Use |
|-------|-------|-----|
| `--sb-signal` | `#64c4ff` | YinYang default color, primary CTA, rail border |
| `--sb-accent` | `#ff6b35` | Hover states, highlights |
| `--sb-success` | `#46d9a7` | Approve, done states |
| `--sb-warning` | `#ffc75a` | Low credits, caution |
| `--sb-danger` | `#ff7c7c` | Error, reject states |
| `--sb-purple` | `#AE67FA` | Aurora palette hint |

### Surface Tokens
| Token | Use |
|-------|-----|
| `--sb-bg` | Page background `#081019` |
| `--sb-surface` | Rail background `#0f1825` |
| `--sb-surface-strong` | Cards `#172335` |
| `--sb-border` | Subtle borders |
| `--sb-text` | Primary text `#f4f7fb` |
| `--sb-text-muted` | Secondary text `#9cb1ca` |

### Font Tokens
| Token | Use |
|-------|-----|
| `--sb-font-display` | Manrope — headings, large text |
| `--sb-font-body` | IBM Plex Sans — body, UI labels |
| `--sb-font-mono` | IBM Plex Mono — code, amounts |

---

## 2. YinYang Palette Collection — Spec

### 2.1 Design Principle

The YinYang logo is a single PNG (`yinyang-logo-32.png`). All 6 color variants are
created purely via CSS `filter` — zero additional image assets needed.

The `transition: filter 0.6s ease` ensures a smooth "mood shift" effect when the palette changes.

### 2.2 Palette Definitions

Palettes map to **warm_token delight states** from Paper 08 §4.2:

| Palette Index | Name | CSS Filter | Delight State | Mood |
|--------------|------|-----------|---------------|------|
| 0 | **Cyan** (default) | `none` | `neutral` | Calm, ready |
| 1 | **Ocean** | `hue-rotate(180deg) saturate(1.5)` | `professional` | Focused, reliable |
| 2 | **Sunset** | `hue-rotate(30deg) saturate(2) brightness(1.08)` | `celebrate` | Warm, energetic |
| 3 | **Aurora** | `hue-rotate(270deg) saturate(1.6) brightness(1.05)` | `encourage` | Magical, creative |
| 4 | **Fire** | `hue-rotate(0deg) saturate(2.5) brightness(1.1)` | `birthday` | Vibrant, festive |
| 5 | **Lunar** | `grayscale(0.8) brightness(1.3) contrast(1.1)` | `suppress_humor` | Minimal, professional |

### 2.3 Palette CSS Classes

```css
/* Applied via data-palette attribute — matched to index above */
.yy-logo-img[data-palette="0"], .yy-input-logo[data-palette="0"] { filter: none; }
.yy-logo-img[data-palette="1"], .yy-input-logo[data-palette="1"] { filter: hue-rotate(180deg) saturate(1.5); }
.yy-logo-img[data-palette="2"], .yy-input-logo[data-palette="2"] { filter: hue-rotate(30deg) saturate(2) brightness(1.08); }
.yy-logo-img[data-palette="3"], .yy-input-logo[data-palette="3"] { filter: hue-rotate(270deg) saturate(1.6) brightness(1.05); }
.yy-logo-img[data-palette="4"], .yy-input-logo[data-palette="4"] { filter: hue-rotate(0deg) saturate(2.5) brightness(1.1); }
.yy-logo-img[data-palette="5"], .yy-input-logo[data-palette="5"] { filter: grayscale(0.8) brightness(1.3) contrast(1.1); }
```

### 2.4 Palette Cycling Logic

- Palette advances by 1 each time the bottom rail is **opened** (not closed)
- Current palette persisted in `localStorage['yy_palette']`
- Wraps at index 6 → back to 0
- On page load, saved palette is restored (no flicker)
- Constant: `YY_PALETTE_COUNT = 6`

---

## 3. Animation Spec — Logo Twist on Open

### 3.1 Purpose

When the YinYang bottom rail expands, the logo performs a "twist" animation — a
360° spin with slight scale bounce — giving the UI personality and signaling state change.
This is tied to Anti-Clippy law: it only triggers on explicit user action (click to open),
never on page load or automatically.

### 3.2 Animation Parameters

```
Name:       yy-logo-twist
Duration:   500ms
Easing:     cubic-bezier(0.34, 1.56, 0.64, 1)  — back-easing "springy"
Direction:  forwards (lands cleanly at 360°)
Triggers:   ONLY on rail open (expanded = true), NOT on close
Repeat:     One-shot per open event (classList.remove + force-reflow + classList.add)
```

### 3.3 Keyframe Spec

```
  0% → rotate(0°)   scale(1)      — start position
 35% → rotate(220°) scale(1.18)   — overshoot with scale-up
 70% → rotate(340°) scale(0.92)   — bounce back, slight scale-down
100% → rotate(360°) scale(1)      — rest at full circle, normal size
```

### 3.4 Accessibility: prefers-reduced-motion

**MANDATORY**: The animation must be disabled when user has system-level reduced motion preference.

```css
@media (prefers-reduced-motion: reduce) {
  .yy-logo-img.is-spinning,
  .yy-input-logo.is-spinning {
    animation: none;
  }
}
```

### 3.5 JavaScript Pattern

```javascript
function _spinLogos() {
  _rail.querySelectorAll('.yy-logo-img, .yy-input-logo').forEach(img => {
    img.classList.remove('is-spinning');
    void img.offsetWidth;  // force reflow so animation restarts
    img.classList.add('is-spinning');
    img.addEventListener('animationend', () => img.classList.remove('is-spinning'), { once: true });
  });
}
```

The `animationend` cleanup ensures the class is removed, allowing future re-triggers.

---

## 4. App-Detail Page — Design Spec

### 4.1 Purpose

The app-detail page is a focused single-app launcher. Jon Ive principle: "Simplicity is not the
absence of clutter. It's clarity of purpose." The page has ONE job: let the user run the app.

### 4.2 Visual Hierarchy

```
LEVEL 1 (Primary):   ▶ Run App button — largest, most prominent, --sb-signal background
LEVEL 2 (Secondary): Schedule button — smaller, muted, --sb-bg-white-alpha-05 background
LEVEL 3 (Meta):      Safety badge, site, author — small text, --sb-text-muted
LEVEL 4 (Context):   Recent runs, customize folders, info cards — supporting info
```

### 4.3 Component Patterns

#### Run Button
```css
/* Uses --sb-signal (primary action) */
background: var(--sb-signal);
color: var(--sb-bg);          /* dark text on light button */
padding: 14px 28px;
border-radius: 12px;          /* --sb-radius-sm equiv */
font-weight: 700;
```

#### Folder Grid (Customize section)
```
2-column grid on mobile, 4-column on desktop
Cards: --sb-surface-strong background, 1px --sb-border border
Drop zone: dashed border, --sb-text-muted text
```

#### Info Cards
```
Horizontal flex row, each card: 50% width on mobile (2x2 grid)
Label: --sb-text-muted, small
Value: --sb-text, medium weight
Special: SHA-256 and safety values use --sb-font-mono
```

### 4.4 States

| State | Visual |
|-------|--------|
| Loading | App name shows "Loading…", icon area placeholder |
| Available | Green dot badge, Run button enabled |
| Running | Running banner visible, Run button disabled (--opacity 0.5) |
| Awaiting approval | Approval card shown, Approve/Reject buttons |
| Done | Recent runs updates, success toast |

### 4.5 Mobile Breakpoints

```
320px:  Single column, buttons stack vertically
768px:  Hero flex row (icon + info + CTAs)
1024px: Max content width --sb-max (1200px)
```

---

## 5. Bottom Rail — Complete Component Spec

### 5.1 Sizes

| State | Height | Content |
|-------|--------|---------|
| Collapsed | 36px | Logo + Name + Credits + Belt + Actions + Toggle icon |
| Expanded | 300px | + Chat history body + Input row |

### 5.2 Keyboard Navigation

| Key | Action |
|-----|--------|
| `Ctrl+Y` | Toggle expand/collapse |
| `Ctrl+Shift+Y` | Toggle + focus input |
| `Escape` | Collapse (if expanded) |
| `Enter` in input | Send message |

### 5.3 ARIA Attributes

```html
<div role="complementary" aria-label="Yinyang Assistant">
  <div role="button" tabindex="0" aria-expanded="true|false" aria-controls="yyRailBody">
  <div aria-live="polite"> <!-- chat history -->
  <input aria-label="Message Yinyang">
  <button aria-label="Send message">
```

---

## 6. Component Gallery Reference

The following components are formally defined in this styleguide and should be
documented in a future `web/component-gallery.html`:

| Component | File | Status |
|-----------|------|--------|
| YinYang Bottom Rail | `web/js/yinyang-rail.js` | Implemented |
| YinYang Top Rail | `web/js/yinyang-rail.js` | Implemented |
| YinYang Palette System | `web/css/site.css` + `yinyang-rail.js` | **NEW — this spec** |
| YinYang Logo Twist | `web/css/site.css` + `yinyang-rail.js` | **NEW — this spec** |
| App-Detail Hero | `web/app-detail.html` | Implemented |
| App-Detail Folder Grid | `web/app-detail.html` | Implemented |
| App-Detail Approval Card | `web/app-detail.html` | Implemented |

**Next:** Create `web/component-gallery.html` as the live reference page.

---

## 7. Verification Checklist (Styleguide-First Skill)

Before marking DONE:
- [x] All rail colors reference `--sb-*` tokens
- [x] Logo color via CSS filter only (no new image assets)
- [x] Animation: 500ms, cubic-bezier spring, one-shot per open
- [ ] `prefers-reduced-motion` support in CSS ← **ADD TO site.css**
- [x] ARIA: `role="button"`, `aria-expanded`, `aria-live`, `aria-label` on all elements
- [x] Keyboard nav: Ctrl+Y, Ctrl+Shift+Y, Escape, Enter
- [x] Palette persisted in localStorage, restored on page load
- [x] Palette cycles only on OPEN, not on close
- [ ] `data-palette` animation transition: `filter 0.6s ease` ← **VERIFY in site.css**
- [x] Mobile: 320px / 768px / 1024px breakpoints handled

---

## DNA
`yinyang.palette = 6_states × delight_tokens × css_filter_only`
`yinyang.twist = open_event × springy_easing × prefers_reduced_motion`
`app_detail = run_first × clarity × evidence_sealed`
