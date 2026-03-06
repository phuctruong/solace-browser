# Styleguide: First-Time App Onboarding
## Grey to Green in Four States

| Field | Value |
|-------|-------|
| **Paper** | 24 (First-Time App Onboarding) |
| **Diagram** | 37 (4-State Lifecycle FSM) |
| **Rung** | 65537 |
| **DNA** | `onboard(app) = detect(installed) x setup(config) x activate(ready) -> run` |
| **Persona** | Jony Ive (design), Dieter Rams (reduction) |

---

## 1. Design Principles

### Remove Until It Breaks (Jony Ive)

The onboarding flow contains exactly what the user needs to see and nothing more. Every element must justify its presence. If removing it does not break comprehension, remove it.

| Principle | Application |
|-----------|-------------|
| **Progressive disclosure** | Grey apps reveal setup on click. Banner reveals agent command on hover. Advanced config fields hidden behind a toggle. |
| **Grey-to-color as reward** | The visual transition IS the feedback. No toasts, no confetti, no modals on activation. The icon turning from grey to full color is the celebration. |
| **YinYang as guide** | YinYang speaks in conversational fragments, not checklists. It observes what the user has done and suggests the next natural step. |
| **Zero-config ideal** | If the OAuth3 vault already has credentials, activation is automatic and silent. The best setup is no setup. |
| **Quiet confidence** | Activated apps do not announce themselves. The absence of grey is the signal that everything is ready. |
| **Material honesty** | Grey means not ready. Full color means ready. There are no in-between visual states. |

### What This Is Not

- Not a wizard. No "Step 1 of 4" progress bars.
- Not a checklist. No checkboxes to tick.
- Not a tutorial. No arrows pointing at UI elements.
- Not dismissable-and-forgotten. The banner returns if the problem is not solved.

---

## 2. Visual States (4 States)

### 2.1 Installed (Grey)

The app exists in the store manifest but has no configuration. It cannot execute recipes.

| Property | Value |
|----------|-------|
| **CSS class** | `.app-card--installed` |
| **Border** | `1px dashed var(--sb-border)` |
| **Background** | `var(--sb-surface)` |
| **Icon filter** | `filter: grayscale(100%) opacity(0.5)` |
| **Icon opacity** | `opacity: 0.5` |
| **Badge text** | `"Set Up"` |
| **Badge background** | `var(--sb-bg-white-alpha-05)` |
| **Badge text color** | `var(--sb-text-muted)` |
| **Card opacity** | `opacity: 0.65` |
| **Cursor** | `cursor: pointer` |
| **Hover** | `opacity: 0.80; border-color: var(--sb-text-muted)` |

```css
.app-card--installed {
  border: 1px dashed var(--sb-border);
  background: var(--sb-surface);
  opacity: 0.65;
  cursor: pointer;
  transition: opacity 0.2s ease, border-color 0.2s ease;
}

.app-card--installed:hover {
  opacity: 0.80;
  border-color: var(--sb-text-muted);
}

.app-card--installed .app-card__icon {
  filter: grayscale(100%) opacity(0.5);
  transition: filter 0.4s ease;
}

.app-card--installed .app-card__badge {
  background: var(--sb-bg-white-alpha-05);
  color: var(--sb-text-muted);
}
```

### 2.2 Setup (Grey, Pulsing Border)

The user or agent is actively providing configuration. The app is in a transient input state.

| Property | Value |
|----------|-------|
| **CSS class** | `.app-card--setup` |
| **Border** | `1px solid var(--sb-signal)` |
| **Border animation** | `pulse-border 2s ease-in-out infinite` |
| **Background** | `var(--sb-surface)` |
| **Icon filter** | `filter: grayscale(100%) opacity(0.7)` |
| **Badge text** | `"Setting Up..."` |
| **Badge background** | `var(--sb-bg-signal-alpha-12)` |
| **Badge text color** | `var(--sb-signal)` |
| **Card opacity** | `1` (active state, no dimming) |

```css
.app-card--setup {
  border: 1px solid var(--sb-signal);
  background: var(--sb-surface);
  opacity: 1;
  animation: pulse-border 2s ease-in-out infinite;
}

@keyframes pulse-border {
  0%, 100% { border-color: var(--sb-signal); }
  50% { border-color: transparent; }
}

.app-card--setup .app-card__icon {
  filter: grayscale(100%) opacity(0.7);
}

.app-card--setup .app-card__badge {
  background: var(--sb-bg-signal-alpha-12);
  color: var(--sb-signal);
}
```

### 2.3 Activated (Full Color)

Configuration complete and validated. The app is ready to execute recipes.

| Property | Value |
|----------|-------|
| **CSS class** | `.app-card--activated` |
| **Border** | `1px solid var(--sb-border)` |
| **Background** | `var(--sb-surface)` |
| **Icon filter** | `filter: none` (full color) |
| **Icon opacity** | `opacity: 1` |
| **Badge text** | `"Ready"` |
| **Badge background** | `var(--sb-bg-success-alpha-14)` |
| **Badge text color** | `var(--sb-success)` |
| **Card opacity** | `1` |

```css
.app-card--activated {
  border: 1px solid var(--sb-border);
  background: var(--sb-surface);
  opacity: 1;
}

.app-card--activated .app-card__icon {
  filter: none;
  opacity: 1;
}

.app-card--activated .app-card__badge {
  background: var(--sb-bg-success-alpha-14);
  color: var(--sb-success);
}
```

### 2.4 Running (Full Color + Green Ring)

A recipe is currently executing. This is a transient state lasting seconds to minutes.

| Property | Value |
|----------|-------|
| **CSS class** | `.app-card--running` |
| **Border** | `2px solid var(--sb-success)` |
| **Border animation** | `running-glow 1.5s ease-in-out infinite` |
| **Background** | `var(--sb-surface)` |
| **Icon filter** | `filter: none` |
| **Badge text** | `"Running"` |
| **Badge background** | `var(--sb-bg-success-alpha-14)` |
| **Badge text color** | `var(--sb-success)` |
| **Box shadow** | `0 0 12px var(--sb-border-success-alpha-18)` |

```css
.app-card--running {
  border: 2px solid var(--sb-success);
  background: var(--sb-surface);
  opacity: 1;
  animation: running-glow 1.5s ease-in-out infinite;
  box-shadow: 0 0 12px rgba(70, 217, 167, 0.18);
}

@keyframes running-glow {
  0%, 100% { box-shadow: 0 0 12px rgba(70, 217, 167, 0.18); }
  50% { box-shadow: 0 0 24px rgba(70, 217, 167, 0.32); }
}

.app-card--running .app-card__icon {
  filter: none;
  opacity: 1;
}

.app-card--running .app-card__badge {
  background: var(--sb-bg-success-alpha-14);
  color: var(--sb-success);
}
```

### 2.5 Grey-to-Color Transition Animation

When an app moves from Setup to Activated, the icon and card transition smoothly. This is the core reward moment.

```css
.app-card--activate-transition .app-card__icon {
  transition: filter 0.4s ease;
  filter: none;
}

.app-card--activate-transition {
  transition: opacity 0.4s ease, border-color 0.4s ease;
  opacity: 1;
  border-color: var(--sb-border);
}
```

The transition is applied by JavaScript when `setAppState(id, "activated")` is called. The class `app-card--installed` is replaced with `app-card--activated`. The CSS `transition: filter 0.4s ease` on the icon handles the visual interpolation from `grayscale(100%)` to `grayscale(0%)`.

**Duration:** 0.4s ease. Not faster (invisible). Not slower (feels sluggish). 0.4s is perceptible as a reward without demanding attention.

---

## 3. Onboarding Banner

The banner appears at the top of the home page when at least one app is in the "installed" state.

### 3.1 Structure

```
+------------------------------------------------------------------+
|  [YinYang avatar]  "3 of 6 apps need setup to start working."    |
|                    [Set up Gmail]  [Set up Slack]  [Set up GitHub]|
|                    Or: let your AI agent handle it                |
+------------------------------------------------------------------+
```

### 3.2 Specifications

| Property | Value |
|----------|-------|
| **CSS class** | `.onboarding-banner` |
| **Background** | `var(--sb-surface-strong)` |
| **Border** | `1px solid var(--sb-border)` |
| **Border radius** | `var(--sb-radius-md)` (16px) |
| **Padding** | `20px 24px` |
| **Margin** | `0 0 24px 0` (bottom spacing before app grid) |
| **Display** | `flex` with `align-items: center` and `gap: 16px` |

### 3.3 YinYang Avatar

| Property | Value |
|----------|-------|
| **CSS class** | `.onboarding-banner__avatar` |
| **Size** | `40px x 40px` |
| **Border radius** | `50%` |
| **Flex shrink** | `0` |
| **Source** | YinYang SVG from existing assets |

### 3.4 Text Content

| Property | Value |
|----------|-------|
| **CSS class** | `.onboarding-banner__text` |
| **Font** | `var(--sb-font-body)` |
| **Primary line** | `font-size: 14px; color: var(--sb-text)` |
| **Secondary line** | `font-size: 13px; color: var(--sb-text-muted); margin-top: 4px` |

The primary line reads: **"X of Y apps need setup to start working."** where X is the count of apps in "installed" state and Y is the total app count.

The secondary line reads: **"Or: let your AI agent handle it"** with `solace apps setup --all` shown in `var(--sb-font-mono)` on hover or as a tooltip.

### 3.5 Setup Buttons (Inline)

| Property | Value |
|----------|-------|
| **CSS class** | `.onboarding-banner__action` |
| **Background** | `var(--sb-bg-white-alpha-05)` |
| **Border** | `1px solid var(--sb-border)` |
| **Border radius** | `var(--sb-radius-sm)` (10px) |
| **Padding** | `6px 12px` |
| **Font size** | `13px` |
| **Color** | `var(--sb-text)` |
| **Hover background** | `var(--sb-bg-accent-alpha-16)` |
| **Hover border** | `var(--sb-border-accent-alpha-12)` |
| **Hover color** | `var(--sb-accent)` |
| **Max shown** | 3 buttons. If more than 3 apps need setup, show "and X more" as text. |

### 3.6 Visibility Rules

| Condition | Banner State |
|-----------|-------------|
| At least 1 app in "installed" state | **Visible** |
| All apps "activated" or "running" | **Hidden** (removed from DOM, not `display: none`) |
| User dismisses banner | **Hidden until page reload** (banner returns if apps still need setup) |
| All apps activated after dismiss | **Hidden permanently** (until a new app is installed) |

**Invariant (Paper 24, O6):** The banner does NOT have a "dismiss forever" option. Dismissing hides it for the current session only. If apps still need setup, the banner returns on next page load. Only activation solves the problem.

---

## 4. Home Page Layout for First-Time Users

### 4.1 When 0 Apps Are Activated

The home page adapts for users who have installed apps but activated none.

| Section | Behavior |
|---------|----------|
| **Quick Actions** | Hidden (`display: none`). Quick actions require activated apps to function. Showing them with 0 activated apps creates dead buttons. |
| **Onboarding Banner** | Visible, prominent, top of content area. |
| **App Grid** | All cards use `.app-card--installed` (greyed out, dashed borders). Each card shows a "Set Up" badge. |
| **Money Saved Widget** | Visible. Shows `$0.00`. This is intentional -- it establishes the metric from day one. As apps activate and run recipes, the number grows. Starting at zero is motivational, not discouraging. |
| **Recent Activity** | Hidden or shows "No activity yet. Set up an app to get started." in `var(--sb-text-muted)`. |

### 4.2 Progressive Reveal

As apps activate, the home page progressively reveals features:

| Apps Activated | Sections Visible |
|----------------|-----------------|
| 0 | Onboarding banner + greyed app grid + Money Saved ($0.00) |
| 1+ | Onboarding banner (if unactivated apps remain) + app grid (mix of grey and color) + Money Saved + Quick Actions for activated apps |
| All | App grid (full color) + Money Saved + Quick Actions + Recent Activity. Banner gone. |

### 4.3 App Card Base Structure

```html
<div class="app-card app-card--installed" data-app-id="gmail" data-app-state="installed">
  <div class="app-card__icon">
    <img src="/icons/gmail.svg" alt="Gmail" />
  </div>
  <div class="app-card__name">Gmail</div>
  <div class="app-card__badge">Set Up</div>
</div>
```

The `data-app-state` attribute mirrors localStorage and drives the CSS class. JavaScript reads `app:{id}:state` from localStorage on page load and applies the corresponding class.

---

## 5. App Detail -- Activation Flow

### 5.1 Button States

When the user clicks an installed app card, the app detail view opens. The primary action button changes based on state:

| App State | Button Text | Button Class | Behavior |
|-----------|-------------|-------------|----------|
| **Installed** | "Set Up" | `.btn--setup` | Opens the setup form |
| **Setup** (form visible) | "Save & Activate" | `.btn--activate` | Validates config, transitions to Activated if valid |
| **Activated** | "Run Now" | `.btn--run` | Begins recipe execution |
| **Running** | "Running..." | `.btn--running` (disabled) | Non-interactive during execution |

### 5.2 Button Styles

```css
.btn--setup {
  background: var(--sb-bg-signal-alpha-12);
  color: var(--sb-signal);
  border: 1px solid var(--sb-border-signal-alpha-14);
  border-radius: var(--sb-radius-sm);
  padding: 10px 20px;
  font-size: 14px;
  font-family: var(--sb-font-body);
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn--setup:hover {
  background: var(--sb-bg-signal-alpha-22);
}

.btn--activate {
  background: var(--sb-accent);
  color: var(--sb-on-accent);
  border: none;
  border-radius: var(--sb-radius-sm);
  padding: 10px 20px;
  font-size: 14px;
  font-weight: 600;
  font-family: var(--sb-font-body);
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn--activate:hover {
  background: var(--sb-accent-hover);
}

.btn--run {
  background: var(--sb-bg-success-alpha-14);
  color: var(--sb-success);
  border: 1px solid var(--sb-border-success-alpha-18);
  border-radius: var(--sb-radius-sm);
  padding: 10px 20px;
  font-size: 14px;
  font-family: var(--sb-font-body);
  cursor: pointer;
}

.btn--running {
  background: var(--sb-bg-success-alpha-14);
  color: var(--sb-success);
  border: 1px solid var(--sb-border-success-alpha-18);
  border-radius: var(--sb-radius-sm);
  padding: 10px 20px;
  font-size: 14px;
  font-family: var(--sb-font-body);
  cursor: not-allowed;
  opacity: 0.7;
}
```

### 5.3 Activation Sequence

When the user clicks "Save & Activate":

1. **Validate** -- Run `validate_app_config()` on all required fields. If invalid, show inline field errors (red text below the field, using `var(--sb-danger)`). Do NOT transition state.
2. **Save config** -- `setAppConfig(appId, config)` to localStorage.
3. **Set state** -- `setAppState(appId, "activated")` to localStorage.
4. **Schedule cron** -- If the app has a default schedule, register it.
5. **Transition visual** -- Replace `.app-card--setup` with `.app-card--activated`. The CSS `transition: filter 0.4s ease` on the icon handles the grey-to-color animation.
6. **Update banner** -- Re-read all app states, update the banner count. If all activated, remove the banner.

### 5.4 Setup Form

| Property | Value |
|----------|-------|
| **CSS class** | `.setup-form` |
| **Background** | `var(--sb-surface-soft)` |
| **Border** | `1px solid var(--sb-border)` |
| **Border radius** | `var(--sb-radius-md)` |
| **Padding** | `24px` |
| **Field labels** | `font-size: 13px; color: var(--sb-text-muted); margin-bottom: 6px` |
| **Field inputs** | `background: var(--sb-bg-input); border: 1px solid var(--sb-border); border-radius: var(--sb-radius-sm); padding: 10px 12px; color: var(--sb-text); font-family: var(--sb-font-body); font-size: 14px` |
| **Field error** | `font-size: 12px; color: var(--sb-danger); margin-top: 4px` |

Only required fields are shown by default. Optional fields are behind an "Advanced" toggle using `var(--sb-text-muted)` link style.

### 5.5 Cancel Behavior

Clicking "Cancel" during setup:
- Discards all partial config (NOT saved to localStorage).
- Returns app to "installed" state: `setAppState(appId, "installed")`.
- Visual returns to grey (`.app-card--installed`).

**Invariant (Paper 24, O5):** Partial config is NEVER saved. Cancel equals clean slate.

---

## 6. YinYang Walkthrough Messages

YinYang speaks in short, warm, conversational fragments. It appears in a bottom rail (fixed to viewport bottom, above the footer).

### 6.1 Bottom Rail Specifications

| Property | Value |
|----------|-------|
| **CSS class** | `.yinyang-rail` |
| **Position** | `fixed; bottom: 16px; left: 50%; transform: translateX(-50%)` |
| **Background** | `var(--sb-surface-strong)` |
| **Border** | `1px solid var(--sb-border)` |
| **Border radius** | `var(--sb-radius-md)` |
| **Padding** | `12px 20px` |
| **Box shadow** | `var(--sb-shadow)` |
| **Max width** | `480px` |
| **Display** | `flex; align-items: center; gap: 12px` |
| **Z-index** | `100` |
| **Entry animation** | `slide-up 0.3s ease` |
| **Exit animation** | `fade-out 0.2s ease` |

```css
.yinyang-rail {
  position: fixed;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--sb-surface-strong);
  border: 1px solid var(--sb-border);
  border-radius: var(--sb-radius-md);
  padding: 12px 20px;
  box-shadow: var(--sb-shadow);
  max-width: 480px;
  display: flex;
  align-items: center;
  gap: 12px;
  z-index: 100;
  animation: slide-up 0.3s ease;
}

@keyframes slide-up {
  from { transform: translateX(-50%) translateY(20px); opacity: 0; }
  to { transform: translateX(-50%) translateY(0); opacity: 1; }
}

.yinyang-rail__avatar {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
}

.yinyang-rail__text {
  font-size: 13px;
  color: var(--sb-text);
  font-family: var(--sb-font-body);
  line-height: 1.4;
}
```

### 6.2 Message Triggers

| Trigger | Message | Auto-dismiss |
|---------|---------|-------------|
| First arrival on home page with 0 activated apps | "Pick any app to set up first!" | No (stays until user acts) |
| After first app is activated | "Nice! X more to go. Want me to set up the rest?" | After 8 seconds |
| After all apps are activated | "All set! Your apps run on schedule now." | After 6 seconds |
| User returns with all apps activated | No message. YinYang stays silent. | N/A |
| New app installed (not yet activated) | "New app added. Tap it to set up." | After 8 seconds |

### 6.3 Conversational Rules

- Maximum 12 words per message. YinYang is concise.
- No exclamation marks in sequence. One is the maximum.
- No technical jargon. "Set up" not "configure". "Ready" not "activated".
- No questions that require decisions. "Want me to set up the rest?" is the one exception -- it offers delegation to the AI agent.
- Messages never repeat in the same session. Each trigger fires once.

---

## 7. CSS Custom Properties Reference

All values below are sourced from `web/css/site.css` and are the only tokens permitted in onboarding components.

### Inactive / Installed State

| Token | Usage |
|-------|-------|
| `var(--sb-surface)` | Card background (installed, setup) |
| `var(--sb-border)` | Card border (installed -- dashed, activated -- solid) |
| `var(--sb-text-muted)` | Badge text, secondary text, labels |
| `var(--sb-bg-white-alpha-05)` | Badge background (installed state) |

### Setup-In-Progress State

| Token | Usage |
|-------|-------|
| `var(--sb-signal)` | Pulsing border color, badge text |
| `var(--sb-bg-signal-alpha-12)` | Badge background, setup button background |
| `var(--sb-border-signal-alpha-14)` | Setup button border |
| `var(--sb-bg-signal-alpha-22)` | Setup button hover background |

### Activated State

| Token | Usage |
|-------|-------|
| `var(--sb-success)` | Badge text, "Ready" label, run button text |
| `var(--sb-bg-success-alpha-14)` | Badge background, run button background |
| `var(--sb-border-success-alpha-18)` | Run button border, running glow ring |

### Action Buttons

| Token | Usage |
|-------|-------|
| `var(--sb-accent)` | "Save & Activate" button background |
| `var(--sb-accent-hover)` | "Save & Activate" button hover |
| `var(--sb-on-accent)` | "Save & Activate" button text |

### Error / Validation

| Token | Usage |
|-------|-------|
| `var(--sb-danger)` | Inline field error text |
| `var(--sb-bg-danger-alpha-14)` | Error field background highlight |

### Layout

| Token | Usage |
|-------|-------|
| `var(--sb-radius-lg)` | Not used in onboarding (too large) |
| `var(--sb-radius-md)` | Banner, setup form, YinYang rail (16px) |
| `var(--sb-radius-sm)` | Buttons, badges, input fields (10px) |
| `var(--sb-shadow)` | YinYang rail drop shadow |
| `var(--sb-font-body)` | All body text |
| `var(--sb-font-mono)` | CLI command hints (`solace apps setup --all`) |

---

## 8. Forbidden States

These visual states are forbidden per Paper 24 invariants and Prime Styles rules (G7).

| Forbidden State | Why |
|-----------------|-----|
| Color icon on an installed (not-activated) app | Visual lie. User thinks app is ready when it requires setup. |
| Grey icon on an activated app | Visual lie. User thinks setup is needed when it is already done. |
| Hardcoded hex values in any onboarding CSS | G7: all CSS values must reference custom properties. |
| "Dismiss forever" button on onboarding banner | O6: only activation dismisses the banner permanently. |
| Toast or modal on activation | Design principle: the grey-to-color transition IS the reward. No secondary celebration. |
| Checklist UI with checkboxes | Design principle: YinYang is conversational, not a task manager. |
| More than 3 setup buttons in the banner | Visual clutter. Show 3 buttons + "and X more" text. |
| Setup form showing optional fields by default | Progressive disclosure: required fields only. "Advanced" toggle for the rest. |
| "Run Now" button on an app that is not activated | O1: no app transitions to Running without passing through Activated. |
| `filter: grayscale(50%)` or any partial greyscale | Material honesty: fully grey or fully color. No in-between. |
| Animation duration below 0.2s or above 0.6s | Below 0.2s is imperceptible. Above 0.6s is sluggish. 0.4s is the sweet spot. |
| `except Exception: setAppState(id, "activated")` | Fallback Ban: swallowing validation errors and activating anyway. |

---

## 9. localStorage Keys

| Key Pattern | Value | State |
|-------------|-------|-------|
| `app:{id}:state` | `"installed"` | Default. No config. Grey icon. |
| `app:{id}:state` | `"setup"` | Transient. Config form open. |
| `app:{id}:state` | `"activated"` | Config validated. Full color. |
| `app:{id}:state` | `"running"` | Transient. Recipe executing. |
| `app:{id}:config` | JSON string | Config data (only written on activation, never on partial) |
| `onboarding:dismissed` | `"session"` | Banner dismissed for current session (returns on reload if apps still need setup) |

---

## 10. Implementation Checklist

| # | Task | File(s) | Depends On |
|---|------|---------|-----------|
| 1 | Add CSS classes for 4 app card states | `web/css/onboarding.css` | site.css tokens |
| 2 | Add `pulse-border` and `running-glow` keyframes | `web/css/onboarding.css` | Task 1 |
| 3 | Add onboarding banner HTML + CSS | `web/css/onboarding.css`, home page template | Task 1 |
| 4 | Add YinYang rail HTML + CSS + slide-up animation | `web/css/onboarding.css` | Task 1 |
| 5 | Implement `getAppState()` / `setAppState()` in JS | `web/js/app-state.js` | Prime JS rules (G8) |
| 6 | Implement banner render logic (count, buttons, visibility) | `web/js/onboarding-banner.js` | Task 5 |
| 7 | Implement YinYang message triggers | `web/js/yinyang-walkthrough.js` | Task 5 |
| 8 | Implement setup form + validation | `web/js/setup-form.js` | Task 5 |
| 9 | Implement grey-to-color transition on activation | `web/js/app-state.js` | Tasks 1, 5, 8 |
| 10 | Hide Quick Actions when 0 apps activated | Home page template | Task 5 |
| 11 | Wire "Save & Activate" button to activation sequence | `web/js/setup-form.js` | Tasks 5, 8 |
| 12 | Tests: state transitions, banner visibility, forbidden paths | `tests/onboarding/` | All above |

---

*Styleguide: First-Time App Onboarding | Paper 24 | Diagram 37 | Auth: 65537*
*"Grey means not ready. Color means ready. The transition is the experience."*
