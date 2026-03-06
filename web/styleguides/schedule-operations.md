# Styleguide: Schedule Operations Dashboard
# DNA: `schedule(ops) = cron(apps) x keepalive(sessions) x evidence(part11) x esign(trust) -> dashboard`
# Paper: 25 | Diagram: 38 | GLOW: 124 | Auth: 65537
# Personas: Jony Ive (simplicity), Vanessa Van Edwards (trust), Rory Sutherland (ROI), Seth Godin (permission)

## 1. Design Principles (Jony Ive)

- **One glance = full system state**: Operations panel shows 4 cards at top — always visible
- **Remove until it breaks**: 4 tabs by intent (Upcoming, Approvals, History, eSign) — NOT 4 views of same data
- **Progressive disclosure**: Summary → click → detail drawer → full evidence
- **Fail-closed approval**: 30s countdown → auto-DENY (never auto-approve)

## 2. Layout Hierarchy

```
┌─────────────────────────────────────────────────────┐
│  OPERATIONS HEADER (always visible)                  │
│  [YinYang icon] Operations [This Week] [7d|30d|All] │
├─────────────────────────────────────────────────────┤
│  ROI PANEL (always visible)                          │
│  runs | hours saved | tokens | saved vs GPT-4 |     │
│  agent cost | net savings | streak                   │
│  [Recipe hit rate bar]                               │
├─────────────────────────────────────────────────────┤
│  SIGN-OFF ALERT (conditional — amber pulse)          │
├─────────────────────────────────────────────────────┤
│  TABS: [Upcoming] [Approvals (N)] [History] [eSign]  │
│  FILTERS: [All apps ▾] [All statuses ▾]             │
├─────────────────────────────────────────────────────┤
│  TAB CONTENT (one active at a time)                  │
│    Tab 1: App Schedules + Keep-Alive + Calendar      │
│    Tab 2: Waiting (amber) + Recently Approved        │
│    Tab 3: Activity Table (App|Status|Time|Dur|$|🔗)  │
│    Tab 4: eSign Stats + Attestations + Part 11 Chain │
└─────────────────────────────────────────────────────┘
```

## 3. Color System

| Token | Value | Usage |
|-------|-------|-------|
| `--sched-success` | `#065f46` | Completed runs |
| `--sched-failed` | `#7f1d1d` | Failed runs |
| `--sched-pending` | `#78350f` | Needs approval (amber) |
| `--sched-future` | `#1e3a8a` | Scheduled future runs |
| `--sched-cancel` | `#374151` | Cancelled/expired |
| `--sb-signal` | `#64c4ff` | Ops card numbers |

## 4. Tab 1: Upcoming

### App Schedules Section
- List of activated apps with cron patterns
- Each item: emoji + name + pattern label + "Next: [time]" + Active/Paused status
- Click to edit schedule (opens Schedule Editor drawer)

### Keep-Alive Sessions Section
- Count badge in section header: `(N)`
- Each item: 🔄 + domain + refresh interval
- Enabled/disabled toggle

### Calendar Section
- Month navigation: ‹ Month Year ›
- Mon-Sun grid, 7 columns
- Today highlighted blue
- App pills in cells: colored by status
- Click pill → Run Detail drawer

### Schedule Patterns (cron presets)
| Pattern | Label | Next Run Logic |
|---------|-------|---------------|
| `daily_6am` | Every day 6:00 AM | Tomorrow 06:00 |
| `daily_7am` | Every day 7:00 AM | Tomorrow 07:00 |
| `daily_9am` | Every day 9:00 AM | Tomorrow 09:00 |
| `weekdays_8am` | Mon-Fri 8:00 AM | Next weekday 08:00 |
| `weekdays_10am` | Mon-Fri 10:00 AM | Next weekday 10:00 |
| `weekly_monday_8am` | Monday 8:00 AM | Next Monday 08:00 |
| `every_2h` | Every 2 hours | +2h from now |
| `every_4h` | Every 4 hours | +4h from now |

## 5. Tab 2: Approvals

### Kanban Layout (2 columns)
- **Waiting for Your Approval** (amber border): pending_approval + cooldown items
- **Recently Approved**: last 20 approved items

### Approval Card
```
┌──────────────────────────────────┐
│ 📧 Gmail Inbox Triage            │
│ ⏳ pending approval · Today 7:02 │
│ "Archived 3 emails, drafted 1"   │
│ 🔗 a3f2e1...                     │
│                                   │
│ ⏳ 28s remaining                  │
│ [✅ Approve] [🔏 Approve+eSign]  │
│ [✕ Reject]                        │
└──────────────────────────────────┘
```

### Approval Rules (Paper 25 invariant O4)
- 30s countdown (configurable in settings)
- Auto-DENY on timeout (Fallback Ban — never auto-approve)
- "Approve + eSign" calls solaceagi.com POST /api/v1/esign/sign
- eSign requires auth token (free: 0 eSign/mo, Starter: 100/mo, Pro: unlimited)
- Each approval creates Part 11 evidence entry

## 6. Tab 3: History

### Activity Table Columns
| Column | Content |
|--------|---------|
| App | emoji + name |
| Status | color-coded badge (success/failed/pending/scheduled/cancelled) |
| Time | Today HH:MM or Mon DD HH:MM |
| Duration | Ns or N.Nm |
| Cost | $0.0000 or — |
| Evidence | 🔗 hash (first 12 chars) or — |

### Row Click → Run Detail Drawer
- Status, Time, Duration, Cost, Tokens, Safety Tier, Scopes
- Evidence Hash (full, monospace, blue)
- Output Summary
- Cross-App Triggers (if any)
- Screenshot preview (if captured)

## 7. Tab 4: eSign

### Stats Row
- **Total Attestations**: all-time count
- **This Month**: current month count
- **Remaining**: based on tier (Free: 0 | Starter: 100/mo | Pro: Unlimited)

### Recent Attestations List
- 🔏 + app emoji + name + time + hash preview (16 chars)
- Click → verify against solaceagi.com POST /api/v1/esign/verify

### Part 11 Evidence Chain
- Chain Active/Disabled indicator
- Entry count + mode (data/screenshot)
- ALCOA+ compliance markers: Attributable, Legible, Contemporaneous, Original, Accurate

## 8. API Integration (solaceagi.com)

### eSign Flow (OAuth3 required)
```
POST /api/v1/esign/sign
  Authorization: Bearer {oauth3_token}
  Body: { document_id, statement_key, evidence_hash, metadata }
  Returns: { signature_id, esign_hash, timestamp, chain_position }
```

### Sync Flow (offline resilience)
```
POST /api/v1/fs/sync/push
  Body: { settings, audit_entries[], evidence_hashes[] }
  Returns: { synced_count, conflicts[] }

POST /api/v1/fs/sync/pull
  Returns: { settings, new_entries[], last_sync }
```

### Evidence Flow (Part 11)
```
POST /api/v1/evidence
  Body: { run_id, app_id, action, hash, prev_hash, timestamp }
  Returns: { evidence_id, chain_position, sealed: true }
```

## 9. Offline Behavior

### Queue-and-Sync Architecture
- **Local-first**: All operations work offline (schedule, approve, reject)
- **Offline queue**: `~/.solace/sync/offline-queue.jsonl` (append-only)
- **Sync on reconnect**: When internet available, flush queue to solaceagi.com
- **Conflict resolution**: Server wins for settings, client wins for evidence (append-only)
- **Visual indicator**: "Offline — changes will sync when back online" banner

### What Works Offline
| Feature | Offline | Needs Cloud |
|---------|---------|-------------|
| View schedules | ✅ | — |
| Edit schedules | ✅ | — |
| View history | ✅ | — |
| Approve runs | ✅ (queued) | Sync later |
| eSign | ❌ | Requires solaceagi.com |
| Part 11 evidence | ✅ (local chain) | Sync later |
| Prime Wiki | ✅ (cached) | Push/pull needs cloud |

### Sync Protocol
1. On boot: check `navigator.onLine`
2. If online: `GET /api/v1/fs/sync/status` → compare timestamps
3. If behind: `POST /api/v1/fs/sync/pull` → merge
4. If ahead: `POST /api/v1/fs/sync/push` → flush offline queue
5. Listen for `online` event → auto-sync

## 10. Remote Access / Audit Logging

### Remote Commands Log
Every remote API call is logged to Part 11 audit trail:
```json
{
  "type": "remote_command",
  "command": "run|approve|reject|config",
  "source_ip": "...",
  "bearer_token_id": "...",
  "timestamp": "ISO8601",
  "evidence_hash": "SHA-256",
  "prev_hash": "...(chain link)"
}
```

### Tunnel Status
- cloudflared quick tunnel (if installed)
- Status: Connected/Disconnected/Not Installed
- Public URL displayed when active

## 11. Forbidden States (Paper 25 invariants)

| ID | Invariant | Rule |
|----|-----------|------|
| O1 | No auto-approve | Timeout = DENY, never approve |
| O2 | Evidence mandatory | Every run produces sealed evidence |
| O3 | LLM once at preview | No LLM during execution |
| O4 | Approval gate | Tier B/C actions MUST pause for human |
| O5 | Hash chain integrity | prev_hash links to prior entry |
| O6 | Offline queue | Never drop actions — queue if offline |

## 12. CSS Custom Properties

```css
/* Schedule-specific */
--sched-past: #374151;
--sched-success: #065f46;
--sched-failed: #7f1d1d;
--sched-pending: #78350f;
--sched-future: #1e3a8a;
--sched-cancel: #374151;
--sched-text: #e2e8f0;
--sched-text-dim: #94a3b8;
--sched-bg: #0f1e33;
--sched-card-bg: #0f1e33;
--sched-border: rgba(255,255,255,0.08);

/* Shared design tokens */
--sb-signal: #64c4ff;
--sb-font-display: "Manrope", sans-serif;
```

## 13. localStorage Keys

| Key | Value | Purpose |
|-----|-------|---------|
| `sb_schedule_view` | `upcoming\|approvals\|history\|esign` | Active tab |
| `sb_schedule_period` | `week\|month\|all` | ROI panel period |
| `sb_offline_queue` | JSON array | Pending sync items |
| `sb_last_sync` | ISO timestamp | Last successful sync |
| `sb_esign_tier` | `free\|starter\|pro` | Cached user tier |

---
*Styleguide v1.0 | Paper 25 | Diagram 38 | Auth: 65537*
*"Remove until it breaks, then add back the one thing that matters." — Jony Ive*
