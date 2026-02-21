# PrimeWiki: Notion Process Model

**Platform**: Notion
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21
**C-Score**: 0.88 (Coherence — Notion SPA, selectors moderately stable)
**G-Score**: 0.85 (Gravity — key landmarks verified)

---

## Architecture Overview

Notion is a React SPA with:
- Real-time collaborative editing (all writes auto-save)
- Block-based content model (every element is a block with UUID)
- Two content types: **Pages** (free-form) and **Databases** (structured)
- Authentication via `token_v2` httpOnly cookie (long-lived session)

---

## Navigation State Machine

```
UNAUTHENTICATED
    ↓ navigate notion.so
AUTH_GATE
    ↓ token_v2 cookie valid
WORKSPACE
    ↓ navigate page URL
PAGE_VIEW (read-only display)
    ↓ click anywhere in content
PAGE_EDIT (live editing, autosave)
    ↓ Ctrl+K
SEARCH_MODAL
    ↓ type query + results appear
SEARCH_RESULTS
    ↓ click result
PAGE_VIEW (new page)
    ↓ Ctrl+N
NEW_PAGE_EDIT (blank page, cursor in title)
    ↓ type title + Enter
PAGE_BODY_EDIT
    ↓ wait 2s
AUTOSAVED
```

---

## Block Content Model

Every piece of content in Notion is a block:

```
Block
├── id: UUID (data-block-id attribute)
├── type: "text" | "heading_1" | "heading_2" | "heading_3" |
│         "bulleted_list_item" | "numbered_list_item" | "toggle" |
│         "to_do" | "quote" | "code" | "callout" | "divider" |
│         "image" | "video" | "file" | "embed" | "database" |
│         "child_page" | "child_database" | "table"
├── content: rich text array (text + formatting annotations)
└── children: [Block, ...]  (nested blocks)
```

CSS class naming: `.notion-{type}-block`
Examples:
- Paragraph: `.notion-text-block`
- H1: `.notion-header-block`
- H2: `.notion-sub_header-block`
- H3: `.notion-sub_sub_header-block`
- Bullet: `.notion-bulleted_list-block`
- Numbered: `.notion-numbered_list-block`
- Toggle: `.notion-toggle-block`

---

## Page Structure (DOM)

```html
<div class="notion-app">
  <div class="notion-sidebar">
    <!-- workspace navigation -->
  </div>
  <div class="notion-frame">
    <div class="notion-page-content">
      <div class="notion-page-block">
        <!-- Page icon + title -->
        <div class="notion-title-block">
          <div contenteditable="true" spellcheck="true">
            <span>Page Title Here</span>
          </div>
        </div>
      </div>
      <!-- Content blocks -->
      <div class="notion-text-block" data-block-id="uuid-here">
        <div contenteditable="true">
          <span>Paragraph text</span>
        </div>
      </div>
      <div class="notion-header-block" data-block-id="uuid-here">
        <div contenteditable="true">
          <span>Heading 1</span>
        </div>
      </div>
    </div>
  </div>
</div>
```

---

## Database Structure (DOM)

```html
<!-- Table view -->
<div class="notion-collection-view">
  <div class="notion-collection-view-body">
    <div class="notion-collection-item" data-block-id="row-uuid">
      <div class="notion-collection-item-title">Row Title</div>
      <!-- Property cells -->
      <div class="notion-collection-property" data-property="status">
        <span class="notion-select-value">In Progress</span>
      </div>
    </div>
  </div>
</div>
```

---

## Key Selectors Table

| Element | Selector | Confidence |
|---------|----------|-----------|
| Page content container | `.notion-page-content` | 0.97 |
| Page title block | `.notion-title-block` | 0.95 |
| Title contenteditable | `.notion-title-block [contenteditable]` | 0.94 |
| Content block | `[data-block-id]` | 0.99 |
| Text block | `.notion-text-block` | 0.96 |
| H1 block | `.notion-header-block` | 0.95 |
| H2 block | `.notion-sub_header-block` | 0.95 |
| Bullet block | `.notion-bulleted_list-block` | 0.94 |
| Block contenteditable | `[data-block-id] [contenteditable]` | 0.93 |
| Sidebar | `.notion-sidebar` | 0.95 |
| Search modal | `input[placeholder*='Search']` | 0.90 |
| Search results | `[aria-label*='Search result']` | 0.85 |
| Database view | `.notion-collection-view` | 0.93 |
| Database row | `.notion-collection-item` | 0.92 |
| New page button | `[aria-label*='New page']` | 0.88 |

---

## Auth State Detection

| Condition | Indicator | Action |
|-----------|-----------|--------|
| Authenticated | `.notion-sidebar` present | Proceed |
| Session expired | Redirect to notion.so/login | Reload session cookies |
| No workspace access | "Join or create workspace" shown | BLOCKED |
| Guest access | Limited toolbar (no edit) | Read-only mode |

---

## Autosave Behavior

Notion auto-saves:
- After 2s of no typing (debounce)
- On page navigation
- On window blur
- On keyboard shortcut Ctrl+S (explicit save — same as autosave)

**Do NOT** reload the page within 3s of a write operation — content may not be persisted yet.

---

## OAuth3 Scope Map

| Action | OAuth3 Scope | Risk |
|--------|-------------|------|
| Read page content | `notion.read.page` | low |
| Search workspace | `notion.read.search` | low |
| Read database | `notion.read.database` | low |
| Create page | `notion.write.create` | medium |
| Update page | `notion.write.update` | medium |
| Delete page | `notion.write.delete` | high |
| Share page | `notion.write.share` | medium |
