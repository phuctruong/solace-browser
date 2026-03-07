# Styleguide: Sidebar Extension (Yinyang Side Panel)
## MV3 Chrome Extension Design Tokens + Layout

| Field | Value |
|-------|-------|
| **Paper** | 47 (yinyang-sidebar-architecture) |
| **Rung** | 65537 |
| **DNA** | `sidebar(tokens) = yy_prefix(isolated) x dark_first(default) x 4_tabs(minimal) x a11y(wcag_aa)` |
| **Persona** | Dieter Rams (reduction), Addy Osmani (performance), Don Norman (UX) |

---

## 1. Design Token Namespace

The sidebar uses `--yy-*` prefix (Yinyang) to isolate from the main webapp's `--sb-*` tokens. Both derive from the same Solace palette but are independent.

### Core Tokens (sidepanel.css)

```css
:root {
  /* Backgrounds */
  --yy-bg: #0f0f23;              /* Deep space background */
  --yy-surface: #1a1a2e;         /* Card/panel surface */
  --yy-surface-hover: #252540;   /* Hover state */
  --yy-border: #2a2a4a;          /* Borders and dividers */

  /* Text */
  --yy-text: #e0e0e0;            /* Primary text */
  --yy-text-dim: #8888aa;        /* Secondary/muted text */

  /* Brand */
  --yy-accent: #6C5CE7;          /* Primary action (Solace purple) */
  --yy-accent-hover: #7c6cf7;    /* Accent hover */

  /* Status */
  --yy-success: #2ecc71;         /* Connected, completed */
  --yy-warning: #f1c40f;         /* Connecting, caution */
  --yy-danger: #e74c3c;          /* Disconnected, error */

  /* Geometry */
  --yy-radius: 8px;              /* Card radius */
  --yy-radius-sm: 4px;           /* Button/input radius */

  /* Typography */
  --yy-font: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  --yy-font-mono: 'SF Mono', 'Fira Code', monospace;

  /* Motion */
  --yy-transition: 150ms ease;
}
```

### Rules
1. NO hardcoded hex colors outside `:root` — always use `var(--yy-*)`
2. NO `!important` — specificity wins, not force
3. NO inline styles — all styling via CSS classes
4. NO `outline: none` without replacement focus indicator

## 2. Layout Structure

### Panel Dimensions
- Width: ~360px (Chromium side panel default, not controllable by extension)
- Height: 100vh minus header (88px) and tabs
- Scrollable content area: `overflow-y: auto`

### Component Hierarchy
```
body
  header.yy-header          # Logo + connection status dot
  nav.yy-tabs [role=tablist]  # 4 tab buttons
  main.yy-content           # Scrollable content area
    section.yy-panel#panel-now [role=tabpanel]
    section.yy-panel#panel-runs [role=tabpanel]
    section.yy-panel#panel-chat [role=tabpanel]
    section.yy-panel#panel-more [role=tabpanel]
  script[src=sidepanel.js]
```

### Tab Navigation
- Tabs use `role="tablist"` / `role="tab"` / `role="tabpanel"`
- Active tab: `aria-selected="true"` + `.active` class
- Tab content: only `.active` panel is `display: block`
- Keyboard: Tab key moves between tab buttons, Enter/Space activates

## 3. Component Catalog

### Connection Status Dot
```css
.yy-dot                    /* 8px circle, default: danger (red) */
.yy-dot.connected          /* success (green) */
.yy-dot.connecting         /* warning (yellow) + pulse animation */
```

### App Card
```css
.yy-app-card               /* Surface bg, border, radius, hover border */
.yy-app-name               /* 14px, font-weight 600 */
.yy-app-desc               /* 12px, dim text */
.yy-app-actions             /* Flex row with gap 8px */
```

### Buttons
```css
.yy-btn                    /* Base: 6px 12px padding, radius-sm */
.yy-btn-primary            /* Accent bg, white text */
.yy-btn-secondary          /* Surface-hover bg, border */
.yy-btn-sm                 /* Smaller variant for inline actions */
```

### Chat Bubble
```css
.yy-chat-bubble            /* Max-width 85%, rounded corners */
.yy-chat-bubble.yy-assistant  /* Surface bg, left-aligned */
.yy-chat-bubble.yy-user       /* Accent bg, right-aligned */
```

### List Item
```css
.yy-list-item              /* Flex row: icon + content + optional actions */
.yy-list-item-icon         /* 16px flex-shrink-0 */
.yy-list-item-title        /* 13px, font-weight 500 */
.yy-list-item-sub          /* 11px, dim text */
```

### Empty State
```css
.yy-empty-state            /* Centered, padded, dim text */
.yy-hint                   /* 11px, 0.7 opacity */
```

## 4. Typography Scale

| Token | Size | Use |
|-------|------|-----|
| (base) | 13px | Body text, list items |
| .yy-title | 15px | Header brand name |
| .yy-app-name | 14px | Card titles |
| .yy-btn | 12px | Button labels |
| .yy-tab | 12px | Tab labels (uppercase, letter-spacing) |
| .yy-hint | 11px | Subtle hints |
| .yy-stat-label | 10px | Status labels (uppercase) |
| .yy-page-url | 12px | Monospace URL display |

## 5. Scrollbar Styling

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: var(--yy-border); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: var(--yy-text-dim); }
```

## 6. Accessibility Requirements (WCAG 2.1 AA)

- All interactive elements: `role`, `aria-label`, `aria-selected` attributes
- Focus indicators: visible outline on Tab navigation
- Color contrast: all text meets 4.5:1 against background
- No `onclick` handlers in HTML — all via addEventListener in JS
- No `<script>` inline — all from external file
- Screen reader: status changes announced via aria-live regions

## 7. Security (CSP)

Extension CSP in manifest.json:
```
script-src 'self'; object-src 'none'; base-uri 'none';
```

- NO inline scripts
- NO eval()
- NO innerHTML with unescaped user data (always use `escapeHtml()`)
- NO `document.write`

## 8. Icons

Real yinyang logos from `web/images/yinyang/`:
- `icon-16.png` — favicon, small contexts
- `icon-48.png` — extension management page
- `icon-128.png` — Chrome Web Store, large display

All sizes are the actual Solace yinyang logo, not generated placeholders.

---

*Styleguide: Sidebar Extension | Auth: 65537 | Paper 47*
