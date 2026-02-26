# PrimeWiki: Notion Domain Knowledge

**Platform**: Notion
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21

---

## Core Concepts

### Workspace
The top-level container. Users belong to one or more workspaces. Each workspace has its own pages, databases, and members.

### Pages vs Databases
- **Page**: Free-form content. A nested tree of blocks. Like a document.
- **Database**: Structured data. Each row is a page with properties. Views: Table, Board (Kanban), Gallery, Calendar, Timeline, List.

### Block System
Everything in Notion is a block. Blocks have:
- Unique UUID (data-block-id)
- Type (text, heading_1, todo, etc.)
- Rich text content (text + inline formatting)
- Parent block reference
- Optional children (sub-blocks)

Blocks can be nested arbitrarily deep. Toggle blocks, columns, synced blocks are all just block types.

### Relations & Rollups
Databases can have **relation properties** that link rows across databases. **Rollup properties** aggregate data from related rows. These are the most complex Notion features — automation should read them as text values.

---

## Property Types (Database)

| Type | Displayed As | Extract Method |
|------|-------------|----------------|
| Title | Text | `.notion-collection-item-title` |
| Text | Inline text | contenteditable value |
| Number | Number string | textContent |
| Select | Colored badge | `.notion-select-value` |
| Multi-select | Multiple badges | `.notion-select-value` (multiple) |
| Date | Date string | `.notion-date-mention` |
| Checkbox | Checked/unchecked | `input[type=checkbox]` |
| URL | Hyperlink | `a[href]` |
| Email | Email text | textContent |
| Phone | Phone text | textContent |
| Formula | Computed value | textContent |
| Relation | Page links | `.notion-page-mention` |
| Rollup | Computed aggregate | textContent |
| Person | User avatars | `.notion-user-mention` |
| Files | File links | `.notion-file-mention` |
| Status | Status badge | `.notion-select-value` |
| Created time | Auto date | textContent |
| Last edited | Auto date | textContent |

---

## Notion URL Structure

| Resource | URL Pattern |
|----------|------------|
| Workspace root | `https://www.notion.so` |
| Page (human-readable) | `https://www.notion.so/{Title}-{32-hex-chars}` |
| Page (direct UUID) | `https://www.notion.so/{32-hex-chars}` |
| Database page | `https://www.notion.so/{workspace}/{page-title}-{uuid}` |
| Public share | `https://www.notion.so/{username}/{page-title}-{uuid}` |

### Page ID Extraction
From URL `https://www.notion.so/My-Page-Title-abc123def456789012345678901234567`:
- Page ID = last 32 hex chars: `abc123def456789012345678901234567`
- Formatted UUID: `abc123de-f456-7890-1234-5678901234567`

---

## Editing Behavior

### Click-to-Edit
Notion pages have no explicit "edit mode" button. Simply clicking anywhere in the content area activates inline editing. The cursor appears in the clicked block.

### Keyboard Shortcuts (Most Useful for Automation)
| Shortcut | Action |
|----------|--------|
| Ctrl+K | Open quick search |
| Ctrl+N | New page |
| Ctrl+S | Force save (usually redundant) |
| Ctrl+Z | Undo |
| Ctrl+Shift+M | Add comment |
| / (forward slash) | Block type menu |
| Enter | New block (same type) |
| Tab | Indent block (nest under previous) |
| Shift+Tab | Outdent block |
| Ctrl+Enter | Check/uncheck to-do |

### Autosave Timing
- Notion saves on: typing stop (2s), focus loss, navigation, Ctrl+S
- Autosave indicator: "Saving..." briefly appears in header
- If offline: changes are queued and saved on reconnect
- **Automation rule**: Always wait 2-3s after writing before navigating away

---

## Notion API vs Browser Automation

Notion has an official Public API (api.notion.com):
- Requires integration token
- Works on server-side
- Better for bulk operations
- Does NOT require browser

SolaceBrowser uses browser automation when:
- User does not have API access configured
- Working with content not exposed via API (comments, mentions, attachments)
- Need to capture visual screenshots as evidence
- Performing actions that require UI interaction (formatting, drag-and-drop)

---

## Collaboration Features

### Mentions
`@Name` in text creates a user mention. `@Page Name` creates a page link. In DOM: `.notion-user-mention`, `.notion-page-mention`.

### Comments
Comments appear as discussion threads on blocks. Visible in `.notion-comment-container`. Not accessible via standard block selectors.

### Sharing
- **Private**: Only workspace members
- **Share with web**: Public read access, URL-based
- **Share with email**: Specific people via email invite

---

## Known Limitations for Automation

1. **Block selection menu**: The `/` menu requires waiting for overlay — tricky to target via automation
2. **Drag and drop**: Block reordering cannot be done via click — requires mouse drag events
3. **Image upload**: Requires file input interaction — not covered by text-based recipes
4. **Real-time collaboration**: If another user is editing the same page, concurrent edits may conflict
5. **Load time**: Complex pages with many embedded databases may take 8-12s to fully render
6. **Selector instability**: Notion's CSS class names include hashed suffixes that change with deployments — prefer data attributes and ARIA attributes over class names
