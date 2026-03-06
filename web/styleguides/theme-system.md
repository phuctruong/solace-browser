# Styleguide: Theme System
## Three Built-In Themes + Custom Theme Engine

| Field | Value |
|-------|-------|
| **Paper** | 53 (Convergent Feedback Loop — MVP Example) |
| **Rung** | 65537 |
| **DNA** | `theme(choice) = css_vars(tokens) x user_pref(stored) x system_pref(fallback) x a11y(contrast)` |
| **Persona** | Dieter Rams (reduction), Don Norman (UX), Jony Ive (visual design) |

---

## 1. Architecture

### CSS Custom Properties

All theme values use `--sb-*` CSS custom properties declared on `:root` (dark default) and overridden via `[data-theme="X"]` selectors. Components NEVER use hardcoded colors.

```
:root                     → dark theme values (default, matches site.css)
[data-theme="dark"]       → explicit dark (re-declares :root for consistency)
[data-theme="light"]      → warm white, high contrast
[data-theme="midnight"]   → true black OLED, electric blue
[data-theme="custom-*"]   → user-defined overrides (injected <style>)
```

### Theme Loading Priority

```
1. Saved preference (localStorage "solace-theme")
2. System preference (prefers-color-scheme)
3. Default: "dark"
```

### FOUC Prevention

`layout.js` applies `data-theme` attribute and injects theme CSS link BEFORE DOMContentLoaded fires. Since dark is the default and `:root` in `site.css` already has dark values, the default case has zero flash.

---

## 2. The Three Themes

### Dark (Default)

DNA: `dark(trust) = deep_navy(foundation) x warm_orange(energy) x cool_blue(clarity)`

| Token | Value | Purpose |
|-------|-------|---------|
| `--sb-bg` | `#081019` | Deep navy background — trust, professionalism |
| `--sb-surface` | `#0f1825` | Card/panel surface — subtle elevation |
| `--sb-accent` | `#ff6b35` | Warm orange — energy, CTA, brand identity |
| `--sb-signal` | `#64c4ff` | Cool blue — information, links, status |
| `--sb-success` | `#46d9a7` | Mint green — positive confirmation |
| `--sb-danger` | `#ff7c7c` | Soft red — errors, destructive actions |
| `--sb-purple` | `#AE67FA` | Purple — premium, special features |
| `--sb-terminal-text` | `#95ffcf` | Bright mint — terminal/code output |

**Character:** Professional but warm. The orange accent on navy creates trust without coldness.

### Light

DNA: `light(clarity) = warm_white(openness) x deep_orange(energy) x slate_text(readability)`

| Token | Value | Purpose |
|-------|-------|---------|
| `--sb-bg` | `#faf8f5` | Warm white — not clinical, approachable |
| `--sb-surface` | `#ffffff` | Pure white cards — clean separation |
| `--sb-accent` | `#e55a2b` | Deep orange — stronger than dark for light bg |
| `--sb-signal` | `#1a7fb8` | Deep blue — readable on light backgrounds |
| `--sb-text` | `#2c2420` | Dark warm slate — easier on eyes than pure black |
| `--sb-text-muted` | `#7a6e62` | Warm gray — secondary text with warmth |

**Character:** Clean, professional, elder-friendly. Designed for daytime use and T8 accessibility. WCAG AAA contrast ratios.

### Midnight

DNA: `midnight(depth) = true_black(OLED) x electric_blue(focus) x minimal_chrome(immersion)`

| Token | Value | Purpose |
|-------|-------|---------|
| `--sb-bg` | `#000000` | True black — OLED power saving |
| `--sb-surface` | `#0a0a0a` | Near-black — minimal elevation |
| `--sb-accent` | `#4da6ff` | Electric blue — cool, focused, tech aesthetic |
| `--sb-signal` | `#64c4ff` | Bright cyan — high visibility on black |
| `--sb-terminal-text` | `#80ffb0` | Matrix green — developer nostalgia |
| `--sb-purple` | `#b880ff` | Bright purple — vivid on pure black |

**Character:** Zero distraction. Maximum contrast. For developers and night owls who want nothing between them and the content. Electric blue replaces warm orange for a cooler, more focused aesthetic.

---

## 3. Token Categories

Every theme MUST define all token categories:

| Category | Tokens | Notes |
|----------|--------|-------|
| **Core backgrounds** | `--sb-bg`, `--sb-surface`, `--sb-surface-strong`, `--sb-surface-soft` | Base layering |
| **Borders** | `--sb-border`, `--sb-border-strong` | Structural separation |
| **Text** | `--sb-text`, `--sb-text-muted` | Primary + secondary |
| **Accent** | `--sb-accent`, `--sb-accent-soft`, `--sb-accent-hover`, `--sb-on-accent` | Brand color + states |
| **Signals** | `--sb-signal`, `--sb-success`, `--sb-warning`, `--sb-danger` | Semantic status |
| **Shadows** | `--sb-shadow`, `--sb-shadow-glow`, `--sb-shadow-glow-lg` | Depth + emphasis |
| **Gradients** | `--sb-grad-header`, `--sb-grad-hero-bg` | Decorative surfaces |
| **Alpha overlays** | `--sb-bg-alpha-*`, `--sb-bg-white-alpha-*` | Transparency layers |
| **Input/Terminal** | `--sb-bg-input`, `--sb-bg-terminal` | Interactive surfaces |

---

## 4. Custom Theme Rules

### Creating Custom Themes

Users can override any `--sb-*` token. The custom CSS is wrapped in `[data-theme="custom-{id}"]` automatically by `theme.js`.

### Minimum Viable Custom Theme

A custom theme needs at minimum:
- `--sb-bg` (background)
- `--sb-accent` (brand color)
- `--sb-text` (text color)

Everything else inherits from the closest built-in theme (dark by default).

### App Store Submission (Paid Users)

Custom themes submitted to the App Store must:
1. Pass WCAG AA contrast ratio (4.5:1 text, 3:1 large text)
2. Define all core token categories (not just 3)
3. Include a preview thumbnail (auto-generated)
4. Have a unique name (no collisions)

---

## 5. Accessibility Requirements

| Requirement | Dark | Light | Midnight |
|-------------|------|-------|----------|
| Text contrast (WCAG AA, 4.5:1) | Pass | Pass | Pass |
| Large text contrast (3:1) | Pass | Pass | Pass |
| Focus indicator visible | Pass | Pass | Pass |
| Respects `prefers-reduced-motion` | Yes | Yes | Yes |
| Respects `prefers-color-scheme` | Auto-switch | Auto-switch | Manual only |

---

## 6. What This Styleguide Is NOT

- **Not a component library** — components use tokens, this defines the tokens
- **Not a brand guide** — this is the implementation layer below the brand
- **Not exhaustive** — new tokens can be added; existing ones must not be removed without migration
