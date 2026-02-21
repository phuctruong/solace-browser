# PrimeWiki: Notion Invariants

**Platform**: Notion
**Version**: 1.0.0
**Authority**: 65537
**Created**: 2026-02-21

These invariants MUST hold for all Notion automation. Violation = data corruption or account suspension.

---

## Hard Invariants (MUST NEVER VIOLATE)

### I-1: Session Required
```
INVARIANT: All recipes MUST load notion_working_session.json as step 1.
Notion is always behind authentication.
VIOLATION: Any recipe that navigates notion.so without loading session first.
```

### I-2: Autosave Wait After Write
```
INVARIANT: Any recipe that performs a write action (type, click that modifies content)
MUST include a wait step of >= 2000ms before navigating away or returning result.
VIOLATION: Navigate immediately after typing — causes content loss.
```

### I-3: No Credential Injection
```
INVARIANT: No recipe step may inject literal passwords, API keys, or tokens.
VIOLATION: Any step with action=type targeting password/token fields.
```

### I-4: Block-Level Consistency
```
INVARIANT: When reading a page, all returned blocks MUST have data-block-id present.
A block without an ID indicates incomplete DOM render — wait and retry.
VIOLATION: Returning blocks with undefined or null block_id.
```

### I-5: Parent-Child Integrity
```
INVARIANT: When creating a page, it MUST be created under an accessible parent.
Creating a page in a workspace section the session cannot access = error.
VIOLATION: Attempting to create pages in shared databases without proper permissions.
```

### I-6: No Simultaneous Edit Conflicts
```
INVARIANT: If the session detects another user actively editing the same block
(avatar indicator on block), the recipe SHOULD defer and retry after 3s.
VIOLATION: Overwriting concurrent edits without conflict detection.
```

---

## Soft Invariants (SHOULD hold)

### S-1: Read Before Write
```
INVARIANT: Update recipes SHOULD read current page content before modifying
to avoid overwriting important data.
Exception: Append-only operations (adding new blocks) do not need pre-read.
```

### S-2: Screenshot Before Destructive Steps
```
INVARIANT: Before title replacement (select-all + type), SHOULD capture screenshot
of original title for audit trail.
Exception: Trivial titles like "Untitled" (default new page state).
```

### S-3: Render Completion Before Extract
```
INVARIANT: Wait for .notion-page-content AND at least one [data-block-id]
before attempting extraction. Partial render = incomplete data.
```

### S-4: Escape Modal After Search
```
INVARIANT: After search extraction, the search modal SHOULD be closed (Escape key)
to restore the workspace to normal state before returning result.
```

---

## Must-Hold Properties Per Recipe

| Recipe | Property | Test |
|--------|----------|------|
| read-page | Returns page_title | page_title.length > 0 |
| read-page | All blocks have block_id | every block.block_id truthy |
| read-page | Total blocks matches array length | blocks.length == total_blocks |
| create-page | page_url in output | output.page_url contains 'notion.so' |
| create-page | created=true in output | output.created == true |
| update-page | updated=true in output | output.updated == true |
| update-page | Wait >= 2s before return | step with wait_duration_ms >= 2000 |
| search | query echoed in output | output.query == input.query |
| search | All results have title | every result.title truthy |
| search | Modal closed after extract | last action before return = Escape or navigate |

---

## Block-Level Consistency Rules

1. **Block completeness**: A block is "complete" when both `data-block-id` and `[contenteditable]` are present
2. **Empty blocks**: Blocks with empty contenteditable text are valid (empty paragraphs) — not errors
3. **Nested blocks**: Extraction SHOULD be limited to top-level blocks unless explicitly requested
4. **Block type detection**: Use CSS class prefix `notion-` + suffix `-block` to identify type
5. **Rich text**: Block text may contain nested `<span>` elements for formatting — extract `.textContent` for plain text

---

## Forbidden Patterns

```
FORBIDDEN: Navigate away from page within 2s of last write action (autosave violation)
FORBIDDEN: Deleting a workspace or database (no recovery path)
FORBIDDEN: Modifying shared pages without checking write permissions first
FORBIDDEN: Extracting content from private pages the session user cannot access
FORBIDDEN: Storing Notion token_v2 cookie value in recipe file (credentials exposure)
FORBIDDEN: Creating infinite loops via page-creates-page (stack overflow in workspace)
FORBIDDEN: Changing workspace membership settings
```

---

## Invariant Verification Checklist

Before marking any Notion recipe as rung 641:

- [ ] Session loaded as step 1 (notion_working_session.json)
- [ ] All navigate targets use https://www.notion.so or valid workspace URL
- [ ] Write recipes include wait >= 2000ms before return_result
- [ ] oauth3_scopes declared and match operation (read vs write)
- [ ] error_handling.session_expired defined
- [ ] error_handling.page_not_found defined (for page-specific recipes)
- [ ] expected_evidence has screenshots=true and agency_token=true
- [ ] metadata.idempotent=false for all write operations
- [ ] metadata.idempotent=true for all read-only operations
- [ ] No hardcoded page IDs in recipe steps (use params.page_url)
