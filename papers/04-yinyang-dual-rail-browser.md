# Paper 04: Yinyang Dual Rail — Browser Integration [SUPERSEDED]
# DNA: `top_rail(status) + bottom_rail(chat+approve) = anti-clippy compliant UI`
# SUPERSEDED BY: Paper 47 (yinyang-sidebar-architecture) — MV3 Side Panel replaces DOM injection
**Date:** 2026-03-01 | **Auth:** 65537 | **Status:** SUPERSEDED
**Applies to:** solace-browser
**Cross-ref:** solaceagi/papers/22-yinyang-chat-rail-proposal.md, 25-yinyang-chat-rail-spec.md

---

## 1. Placement Decision: Dual Rail

Yinyang uses two separate surfaces, each with one job:

| Surface | Height | Purpose | Content |
|---------|--------|---------|---------|
| **Top rail** | 32px fixed | "What is happening right now?" | State dot + text + current step + [Pause] |
| **Bottom rail** | 36px collapsed / 300px expanded | "What should we do next?" | Chat + approve/reject + credits |

### Why Dual Rail (Not Popup, Not Single Bar)

| Anti-Clippy Law | Dual Rail Score | Why |
|----------------|----------------|-----|
| Summon don't ambush | Top is passive status (non-intrusive); bottom is user-summoned | Best |
| Boundary moments | Top auto-shows only during app execution; bottom at approval points | Best |
| Ghost presence | Top = ghost (32px subtle); bottom = ghost when collapsed (36px) | Best |
| One-click collapse | Bottom collapses/expands with one click | Good |
| Expertise detection | Belt level adjusts verbosity in both rails | Good |

## 2. Top Rail Specification

```
┌─ ☯ | PROCESSING | Step 2/5: Scanning inbox | $0.003 | [⏸] ─┐
└─────────────────────────────────────────────────────────────┘
```

- 32px height, fixed position top of viewport
- Injected via `page.add_init_script()` (Playwright)
- Content: FSM state color dot + state text + step progress + cost + [Pause]
- State colors from 12-state FSM (Paper 25)

### Visibility Rules

| Browser State | Top Rail |
|--------------|----------|
| Idle browsing (no apps) | HIDDEN |
| App running | VISIBLE (32px) |
| Preview ready | VISIBLE (amber glow) |
| Error/blocked | VISIBLE (red) |
| Settings page | HIDDEN |

## 3. Bottom Rail Specification

```
Collapsed (36px):
┌─ ☯ Yinyang | $3.47 | Yellow Belt | 847 actions ──── [▲] ─┐
└─────────────────────────────────────────────────────────────┘

Expanded (300px):
┌────────────────────────────────────────────────────────────┐
│ ☯ Yinyang | $3.47 | Yellow Belt                    [▼]    │
│────────────────────────────────────────────────────────────│
│ User: Triage my Gmail inbox                                │
│ Yinyang: Found 42 new emails. Here's what I'd do:        │
│   ✓ Archive 28 (newsletters, promotions)                   │
│   ⭐ Star 5 (from priority contacts)                       │
│   📝 Draft 3 replies (shown in outbox/previews/)           │
│                                                            │
│ [✓ Approve All]  [✏️ Edit]  [✗ Reject]                     │
│                                                            │
│ [📁 VS Code]  [Type a message...                  ] [Send] │
└────────────────────────────────────────────────────────────┘
```

### Behavior

- Default: COLLAPSED (36px) — always visible
- User click [▲] → expands to 300px
- Remembers preference across sessions
- Auto-expands on: PREVIEW_READY, BLOCKED, ERROR
- Auto-collapses: 30s after DONE state

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+Y / Cmd+Y | Toggle expand/collapse |
| Ctrl+Shift+Y | Focus input field |
| Escape | Collapse |
| Enter (in preview) | Approve |
| Ctrl+. | Pause execution |

## 4. Integration with Apps

```
USER: "Triage my Gmail"
  → Bottom rail: chat shows "Running Gmail Inbox Triage..."
  → Top rail: ☯ PROCESSING | Scanning inbox...

APP GENERATES PREVIEW
  → Top rail: ☯ PREVIEW_READY | 42 emails
  → Bottom rail: AUTO-EXPANDS with preview + [Approve] [Edit] [Reject]

USER APPROVES
  → Top rail: ☯ EXECUTING | Step 1/3: Archiving...
  → Cooldown: 5s (medium risk)

DONE
  → Top rail: ☯ DONE (fades → hidden after 5s)
  → Bottom rail: summary + link to report, auto-collapse after 30s
```

## 5. Yinyang + Settings Integration

On settings page, "Ask Yinyang" button opens bottom rail with context pre-filled:
```
User clicks [💬 Ask Yinyang] on History section
  → Bottom rail expands
  → Input pre-filled: "I want to change history settings..."
  → Yinyang: "Sure! What would you like to change? Current settings: enabled=true, dir=~/.solace/history, max=10GB"
```

## 6. The 10 Anti-Clippy Laws (Applied to Dual Rail)

| # | Law | Implementation |
|---|-----|---------------|
| 1 | Summon don't ambush | Bottom rail = user-initiated. Top rail = passive status |
| 2 | Boundary moments | Auto-expand only at PREVIEW_READY, BLOCKED, ERROR |
| 3 | Learn from rejections | Track accept/dismiss per suggestion type across sessions |
| 4 | Expertise detection | Belt level adjusts: White=verbose, Black=terse |
| 5 | Match the user | Power users see data; beginners see guidance |
| 6 | One-click collapse | [▼] collapses, persists across sessions |
| 7 | Every observation justifies itself | Top rail shows real status (not decoration) |
| 8 | Ship brain first | 12-state FSM drives everything; animations last |
| 9 | Honest about what we are | "I pattern-matched this" not "I understand your needs" |
| 10 | Ghost presence | 36px collapsed = visible but zero-effort to ignore |

## Forbidden Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Auto-expanding bottom rail for non-approval events | Violates Anti-Clippy "summon don't ambush" law and trains users to ignore the rail |
| Putting chat or forms in the top rail | Top rail is status-only; mixing concerns destroys the dual-rail separation |
| Auto-approving any action without user click | Breaks PREVIEW_READY → APPROVED gate and violates Part 11 consent |

## 7. Invariants

1. Top rail shows ONLY FSM state — never chat, never forms
2. Bottom rail is ALWAYS user-summoned for chat (never auto-opens for chat)
3. Bottom rail auto-expands ONLY for approval-requiring events
4. PREVIEW_READY → APPROVED requires explicit user click (never auto-approve)
5. Collapse preference persists across sessions
6. Zero forms, toggles, or inputs in either rail (except chat input)
