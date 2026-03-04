# Styleguide: App Detail Page
# Auth: 65537 | Version: 1.0 | Date: 2026-03-03
# SW5.0 Stage: [Papers ✓] [Diagrams ✓] [**Styleguide ✓**] [Code] [Tests] [Seal]
# Depends on: Paper 08 (Yinyang Universal Interface), solaceagi/style-guide.html (inspiration)

---

## 1. Design Principles (Jon Ive + Rory Sutherland Committee)

**Jon Ive:** "Clarity of purpose over accumulation of features. Every pixel must earn its place."
**Rory Sutherland:** "The Run button should feel inevitable. Users need to feel it's the only logical choice."
**Vanessa Van Edwards:** "Warmth first. Show the YinYang logo before showing the technical details."

### Single Job Rule
The app-detail page has ONE job: help the user RUN the app. Every other element is
subordinate to this goal. Information supports the run decision — it does not compete with it.

---

## 2. Token Reference (Must Use Only These)

```css
/* Backgrounds */
--sb-bg              /* page background */
--sb-surface         /* rail, cards */
--sb-surface-strong  /* inner card elevation */

/* Borders */
--sb-border          /* standard */
--sb-border-strong   /* accent/focus */

/* Text */
--sb-text            /* primary */
--sb-text-muted      /* labels, captions */

/* Actions */
--sb-signal          /* primary CTA (Run App) */
--sb-success         /* approve button */
--sb-danger          /* reject button */
--sb-warning         /* low budget warning */
--sb-accent          /* hover highlights */

/* Typography */
--sb-font-display    /* app name heading */
--sb-font-body       /* labels, descriptions */
--sb-font-mono       /* cost values, SHA hash */
```

---

## 3. Layout Anatomy

```
┌─────────────────────────────────────────────────────────────┐
│ NAV: logo + links + lang + auth                             │
├─────────────────────────────────────────────────────────────┤
│ ← Apps           [TOP RAIL — only during execution]        │
│                                                             │
│  [ICON 80px] APP NAME            [▶ Run App   ]            │
│              description          [🕐 Schedule ]            │
│              ● Available | site | author | version          │
├─────────────────────────────────────────────────────────────┤
│ [RUNNING BANNER — hidden unless app is executing]           │
├─────────────────────────────────────────────────────────────┤
│ [APPROVAL CARD — hidden unless preview ready]               │
│   Step previews                                             │
│   [✓ Approve & Run]  [✗ Reject]                            │
├─────────────────────────────────────────────────────────────┤
│ RECENT RUNS                                                 │
│   [empty state OR run history rows]                         │
├─────────────────────────────────────────────────────────────┤
│ CUSTOMIZE THIS APP                                          │
│  [Prompts] [Templates] [Assets] [Policies]                  │
│  (2-col mobile, 4-col desktop)                              │
├─────────────────────────────────────────────────────────────┤
│ INFO CARDS: cost / replay cost / safety / evidence          │
│  (2-col mobile, 4-col desktop)                              │
├─────────────────────────────────────────────────────────────┤
│ FOOTER                                                      │
├─────────────────────────────────────────────────────────────┤
│ [BOTTOM RAIL 36px] YinYang | $X.XX | Belt ────────── [▲]  │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specs

### 4.1 Run Button (Primary CTA)

```
Visual:   var(--sb-signal) background, var(--sb-bg) text color
Size:     padding 14px 28px, border-radius 12px, font-weight 700
Icon:     ▶ symbol (1.1rem) to the left of label
Hover:    opacity: 0.85, translateY(-1px)
Active:   translateY(0)
Disabled: opacity 0.5, cursor not-allowed (while running)
Loading:  label changes to "Starting…", opacity 0.6
```

### 4.2 Schedule Button (Secondary CTA)

```
Visual:   rgba(255,255,255,0.07) background, var(--sb-text-muted) text
Size:     padding 9px 20px, same border-radius
Icon:     🕐 emoji prefix
Role:     Clearly subordinate to Run button
```

### 4.3 Status Badge

```
● Available: var(--sb-success) dot + green border
● Running:   var(--sb-warning) dot + pulsing animation
● Error:     var(--sb-danger) dot + red border
● Offline:   var(--sb-text-muted) dot
```

### 4.4 Running Banner

```
Hidden by default (display: none)
Shown: when run starts
Content: [YinYang rotating GIF 32px] "Yinyang is running Gmail Inbox Triage…"
Color:   var(--sb-signal) left border, var(--sb-surface) background
Height:  44px
Animation: fade-in 0.2s ease
```

### 4.5 Approval Card

```
Hidden by default (display: none)
Shown: when step preview is ready
Border: var(--sb-border-strong) — orange tint (signals urgency without alarm)
Content:
  - "Review before running" title
  - Numbered step list
  - [✓ Approve & Run] in var(--sb-success)
  - [✗ Reject] in var(--sb-danger)
Anti-Clippy: Never auto-approve. Never advance without explicit click.
```

### 4.6 Folder Grid (Customize)

```
4 cards: Prompts, Templates, Assets, Policies
Grid:    2-col at 320px, 4-col at 768px
Card:    var(--sb-surface-strong) bg, 1px var(--sb-border) border, border-radius 12px
Icon:    Large emoji (📝 📋 📦 🛡️) centered
Label:   var(--sb-text), font-weight 600
Sub:     "Drop files here" in var(--sb-text-muted)
Hover:   border-color: var(--sb-signal)
```

### 4.7 Info Cards (4-grid)

```
4 cards: Agent cost / Recipe cost / Safety rating / Evidence
Grid:    2-col at 320px, 4-col at 768px
Label:   var(--sb-text-muted), 0.78rem
Value:   var(--sb-text), 1.1rem, font-weight 700
Cost:    var(--sb-font-mono) — monospace alignment
Evidence: var(--sb-font-mono), var(--sb-success) color
```

---

## 5. Internationalization

All visible text elements must have `data-i18n` attributes.

### Required i18n Keys

| Element | Key | English |
|---------|-----|---------|
| Back link | `ad_back_apps` | ← Apps |
| Run button | `ad_run_btn` | Run App |
| Schedule button | `ad_schedule_btn` | Schedule |
| Status badge | `ad_available` | Available |
| Running banner | `ad_running_label` | Running… |
| Recent Runs heading | `ad_recent_runs` | Recent Runs |
| Empty runs | `ad_empty_runs` | No runs yet — hit Run App to start. |
| Customize heading | `ad_customize_label` | Customize this app |
| Folder: Prompts | `ad_folder_prompts` | Prompts |
| Folder: Templates | `ad_folder_templates` | Templates |
| Folder: Assets | `ad_folder_assets` | Assets |
| Folder: Policies | `ad_folder_policies` | Policies |
| Folder drop zone | `ad_folder_drop` | Drop files here |
| Info: Agent cost | `ad_info_agent_cost` | Agent cost per run |
| Info: Recipe cost | `ad_info_recipe_cost` | Recipe replay cost |
| Info: Safety | `ad_info_safety` | Safety rating |
| Info: Evidence | `ad_info_evidence` | Evidence |
| Evidence value | `ad_info_evidence_val` | SHA-256 sealed forever |
| Safety value | `ad_info_safety_val` | B — needs your approval |
| Approval title | `ad_approval_title` | Review before running |
| Approve button | `ad_approval_approve` | ✓ Approve & Run |
| Reject button | `ad_approval_reject` | ✗ Reject |

All 22 keys above are added to `app/locales/yinyang/en.json` and translated to 12 locales.

---

## 6. Accessibility Checklist

- [x] Back link: `<a>` element with keyboard focus
- [x] Run button: `<button>` with ARIA role
- [x] Running banner: `role="status"` + `aria-live="polite"`
- [x] Approval card: `role="alertdialog"` semantics on container
- [x] Folder grid: `role="listitem"`, keyboard focus on each card
- [x] Info cards: appropriate ARIA labels on complex values
- [x] Images: `alt=""` for decorative, descriptive alt for informational

---

## 7. States and Transitions

```
IDLE → [click Run] → RUNNING → [preview ready] → AWAITING APPROVAL
AWAITING APPROVAL → [click Approve] → EXECUTING → DONE
AWAITING APPROVAL → [click Reject] → IDLE
RUNNING → [error] → ERROR
```

Transitions: 0.2s ease for most state changes. Never instant. Never jarring.

---

## DNA
`app_detail = run_first × warmth × evidence × anti_clippy`
`hierarchy = run(1) > schedule(2) > info(3) > customize(4)`
