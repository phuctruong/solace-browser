# Paper 41 — Central Apps Architecture
# DNA: `global_apps = YAML(git, $0, offline); user_apps = Firestore; sync = one API`
# Global Apps in Code. User/Team Apps in Firestore.
# 2026-03-03

---

## The Rule (Updated 2026-03-03)

```
Firestore     → OFFICIAL SOURCE OF TRUTH for ALL apps (global + user + team)
                One collection. One admin UI. Easy to update without deployments.

Sync script   → Firestore → YAML in solace-browser repo (auto-sync on change)
              → Firestore → solaceagi.com site_content.py (auto-sync)

Runtime       → solace-browser reads from local YAML (fast, offline, $0)
              → solaceagi.com reads from local Python dict (fast, $0)

Result        → Best of both worlds: Firestore for editing, code for serving
```

### Why Firestore as Source of Truth
- Team can update apps without a code deploy (just edit in Firebase Console)
- User apps and team apps already live in Firestore — one consistent admin experience
- Sync script runs on CI or on-demand: `python scripts/sync-apps-from-firestore.py`
- Code still serves fast (no Firestore reads at runtime = $0 cost)

---

## Why "Global Apps in Code" Wins

| Approach | Cost | Latency | Versioning | Offline |
|----------|------|---------|-----------|---------|
| YAML in repo (current) | $0 | 0ms (local) | Git | ✓ |
| Firestore for globals | $money | ~200ms | Firestore docs | ✗ |
| S3/Cloud Storage | $money | ~100ms | Bucket | ✗ |

**Verdict:** YAML files in the repo are the best option for global apps. Free, fast, versioned, offline-capable.

---

## App Catalog Structure

```
solace-browser/
  data/
    apps/
      gmail-inbox-triage/
        manifest.yaml     ← Global app definition (in code)
        recipe.json       ← Deterministic recipe steps
        inbox/            ← Default prompts/templates
      slack-triage/
        manifest.yaml
        recipe.json
      ...

  web/server.py → GET /api/apps reads all manifest.yaml files → returns JSON
```

### manifest.yaml format (canonical)
```yaml
id: gmail-inbox-triage
name: Gmail Inbox Triage
category: communications
status: installed
safety: B
site: mail.google.com
description: Scan Gmail, prioritize messages, and draft safe replies.
type: standard
source: official_git
icon: gmail
version: 1.0.0
author: Solace AGI
```

---

## Firestore: Only for User + Team Apps

```python
# Firestore collections (only for dynamic, user-created content)

users/{uid}/apps/{app_id}:
  {
    "id": "my-custom-notion-brief",
    "name": "My Notion Daily Brief",
    "type": "user",
    "created_at": "...",
    "recipe": {...},    # Full recipe JSON
    "scope": "private"  # only this user sees it
  }

teams/{team_id}/apps/{app_id}:
  {
    "id": "team-crm-triage",
    "name": "Team CRM Triage",
    "type": "team",
    "created_at": "...",
    "recipe": {...},
    "scope": "team"  # all team members see it
  }

pending_apps/{submission_id}:
  {
    "name": "...",
    "description": "...",
    "submitted_by": "...",
    "status": "pending|approved|rejected"
    # If approved → merged into repo as manifest.yaml → becomes a global app
  }
```

---

## The Sync Flow

```
[Global Apps] ─── YAML in repo ──► /api/apps ──► Browser UI
                                        │
                                        └──► solaceagi.com API (mirrors same YAML)

[User Apps] ─── Firestore ──► login sync ──► /api/apps?scope=user ──► Browser UI

[Team Apps] ─── Firestore ──► team join ──► /api/apps?scope=team ──► Browser UI

[Submit New] ─► Firestore pending_apps ─► Team review ─► YAML PR ─► merge ─► Global
```

---

## API Design

```
GET /api/apps
  Returns: global apps (from YAML) + user apps (from Firestore, if logged in) + team apps

GET /api/apps?category=communications
  Returns: filtered subset

GET /api/apps?scope=user
  Returns: only user's custom apps

POST /api/apps/submit
  Body: {name, description, site, category, recipe_draft}
  Stores in: Firestore pending_apps (for team review)
  Returns: {submission_id, status: "pending"}
```

---

## No Duplication Between solace-browser + solaceagi.com

```
Option A (current): Both read from same YAML files
  → solace-browser: reads local YAML files
  → solaceagi.com: could serve the same YAML as an API (proxy)

Option B (future): solaceagi.com fetches from solace-browser API
  → solaceagi.com /api/apps → fetch from https://api.solaceagi.com/apps
  → Cached 1hr (Redis or in-process)
  → Source of truth: solace-browser repo

Best for launch: Option A (each reads own YAML, same format = easy sync)
Best for scale: Option B (one API, both use it, Firestore adds user/team layer)
```

---

## Migration Path (Zero Cost)

1. ✓ Today: YAML files in solace-browser repo (18 apps)
2. Launch: solaceagi.com mirrors same YAML as static data
3. Post-launch: User-submitted apps → Firestore pending_apps → review → YAML merge
4. Scale: Add team Firestore collections as team features launch
5. Never: Don't put global app catalog in Firestore (costs money, adds latency, no offline)

---

## Forbidden Patterns

| Pattern | Why It Fails |
|---------|-------------|
| Reading global apps from Firestore at runtime | Adds cost, latency, and cloud dependency when YAML files serve at $0 with zero latency |
| Allowing user apps to overwrite official catalog entries | User/team scope must overlay, never mutate, the git-backed global catalog |
| Deploying app catalog changes without git commit | Loses version history, audit trail, and the ability to rollback |

## DNA
`apps = global(yaml) + user(firestore) + team(firestore); cost = $0 for global; git = source_of_truth`

**Status:** YAML approach is current. Firestore only for user/team apps (pending implementation).
**Next:** Wire user app submission to Firestore pending_apps collection.
