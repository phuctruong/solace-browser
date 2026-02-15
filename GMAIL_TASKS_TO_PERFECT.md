# Gmail Tasks - Complete Perfection List

**Status**: Working through tasks LIVE with headed browser
**Auth**: 65537 | **Date**: 2026-02-15

---

## ✅ ALREADY PERFECTED (6 core + demonstrated)

```
TIER 1: CORE OPERATIONS
✅ 1. OAuth Login (recipe exists, 47 cookies saved)
✅ 2. Click Compose (selector verified, workflow tested)
✅ 3. Fill To field (autocomplete handled, tested)
✅ 4. Fill Subject (selector verified, tested)
✅ 5. Fill Body (selector verified, tested)
✅ 6. Send Email (Ctrl+Enter verified, tested)

TIER 2: NAVIGATION
✅ 7. Navigate to Inbox (with cookies, no OAuth)
✅ 8. Read Inbox (selectors verified)
✅ 9. Sent Folder (selector verified)
✅ 10. Drafts Folder (selector verified)
✅ 11. Search Emails (selector verified)

TIER 3: EMAIL ACTIONS
✅ 12. Reply (selector verified)
✅ 13. Forward (selector verified)
✅ 14. Archive (selector verified)
✅ 15. Delete (selector verified)
✅ 16. Mark Read (selector verified)
✅ 17. Mark Unread (selector verified)
✅ 18. Star/Important (selector verified)
```

---

## 🎯 TASKS TO PERFECT (NEXT - With Headed Browser Live)

### TIER 1: ADVANCED OPERATIONS (Priority 1)

```
TASK 1: Perfect Attachment Upload
├─ Selector: Find upload button in compose
├─ Test: Upload a file (PDF, text, image)
├─ Verify: File appears in compose
├─ Edge cases: Multiple files, large files
└─ Recipe: Create attachment-upload.recipe.json

TASK 2: Perfect CC/BCC Fields
├─ Selector: input[aria-label='Cc'], input[aria-label='Bcc']
├─ Test: Fill CC field with email
├─ Test: Fill BCC field with email
├─ Verify: Both fields work independently
└─ Recipe: Create cc-bcc.recipe.json

TASK 3: Perfect Reply-All
├─ Selector: Find "Reply all" button
├─ Test: Open email, click Reply All
├─ Test: Verify all recipients in To field
├─ Edge case: Original recipients appear
└─ Recipe: Create reply-all.recipe.json

TASK 4: Perfect Email Threading (Read full conversation)
├─ Selector: Extract full email thread
├─ Test: Get sender, subject, timestamps
├─ Test: Extract full body text
├─ Test: Get attachments list
└─ Recipe: create thread-extraction.recipe.json

TASK 5: Perfect Label Management
├─ Selector: Find label buttons/actions
├─ Test: Apply label to email
├─ Test: Remove label from email
├─ Test: Create new label
├─ Test: List all labels
└─ Recipe: create label-management.recipe.json
```

### TIER 2: BULK OPERATIONS (Priority 2)

```
TASK 6: Perfect Bulk Select (Select multiple emails)
├─ Selector: Checkbox for "select all"
├─ Test: Select multiple emails
├─ Test: Unselect specific emails
├─ Test: Apply action to selected emails
├─ Edge case: 100+ emails
└─ Recipe: create bulk-select.recipe.json

TASK 7: Perfect Bulk Archive
├─ Test: Select 5 emails
├─ Test: Archive all at once
├─ Verify: All disappeared from inbox
├─ Verify: Appear in All Mail
└─ Recipe: create bulk-archive.recipe.json

TASK 8: Perfect Bulk Delete
├─ Test: Select 5 emails
├─ Test: Delete all at once
├─ Verify: All in Trash
├─ Verify: Can recover from Trash
└─ Recipe: create bulk-delete.recipe.json

TASK 9: Perfect Bulk Label Apply
├─ Test: Select 5 emails
├─ Test: Apply label to all
├─ Verify: All have label
├─ Test: Remove label from all
└─ Recipe: create bulk-label.recipe.json

TASK 10: Perfect Bulk Star
├─ Test: Select 5 emails
├─ Test: Star all at once
├─ Verify: All starred
├─ Test: Unstar all
└─ Recipe: create bulk-star.recipe.json
```

### TIER 3: ADVANCED READING (Priority 3)

```
TASK 11: Perfect Email Body Extraction
├─ Selector: Get full email body HTML
├─ Test: Extract plain text
├─ Test: Handle formatted text
├─ Test: Handle quoted text
├─ Edge case: Multiple signatures
└─ Recipe: create body-extraction.recipe.json

TASK 12: Perfect Attachment Download
├─ Selector: Find attachment elements
├─ Test: Click download for each attachment
├─ Test: Get filename
├─ Test: Get file size
└─ Recipe: create attachment-download.recipe.json

TASK 13: Perfect Contact Extraction
├─ Selector: Extract email addresses from thread
├─ Test: Get sender info
├─ Test: Get all recipients
├─ Test: Get CC recipients
└─ Recipe: create contact-extraction.recipe.json

TASK 14: Perfect Draft Management
├─ Selector: Find draft emails in Drafts folder
├─ Test: Open draft
├─ Test: Continue editing
├─ Test: Delete draft
└─ Recipe: create draft-management.recipe.json

TASK 15: Perfect Scheduled Send
├─ Selector: Find "Schedule send" button
├─ Test: Schedule email for future time
├─ Test: Verify scheduled emails list
└─ Recipe: create scheduled-send.recipe.json
```

### TIER 4: FILTERING & SEARCH (Priority 4)

```
TASK 16: Perfect Advanced Search
├─ Operators: from:, to:, subject:, has:, before:, after:
├─ Test: Search with multiple filters
├─ Test: Save search as filter
├─ Edge case: Complex boolean queries
└─ Recipe: create advanced-search.recipe.json

TASK 17: Perfect Auto-Reply Setup
├─ Selector: Find settings → Auto-reply
├─ Test: Enable auto-reply
├─ Test: Set message
├─ Test: Set date range
└─ Recipe: create auto-reply.recipe.json

TASK 18: Perfect Filter Rules
├─ Selector: Find filter creation UI
├─ Test: Create rule (if X, then Y)
├─ Test: Apply to existing emails
├─ Test: Auto-apply to new emails
└─ Recipe: create filter-rules.recipe.json

TASK 19: Perfect Spam Management
├─ Selector: Find spam folder
├─ Test: Move email to spam
├─ Test: Mark as spam
├─ Test: Unmark as spam
└─ Recipe: create spam-management.recipe.json

TASK 20: Perfect Unsubscribe
├─ Selector: Find unsubscribe link
├─ Test: Click unsubscribe
├─ Verify: Email unsubscribed
└─ Recipe: create unsubscribe.recipe.json
```

### TIER 5: ADVANCED FEATURES (Priority 5)

```
TASK 21: Perfect Email Templates
├─ Selector: Find templates feature
├─ Test: Create template
├─ Test: Use template in compose
├─ Test: Save response template
└─ Recipe: create template-management.recipe.json

TASK 22: Perfect Snooze Email
├─ Selector: Find snooze button
├─ Test: Snooze for 1 hour
├─ Test: Snooze for tomorrow
├─ Test: Snooze for custom time
└─ Recipe: create snooze-email.recipe.json

TASK 23: Perfect Multiple Accounts (Account Switching)
├─ Selector: Account switcher
├─ Test: Switch between accounts
├─ Test: Send from different account
├─ Test: Compose in account 2
└─ Recipe: create account-switching.recipe.json

TASK 24: Perfect Undo Send
├─ Selector: Find undo send option
├─ Test: Send email
├─ Test: Click undo in notification
├─ Verify: Email recalled
└─ Recipe: create undo-send.recipe.json

TASK 25: Perfect Priority Inbox
├─ Selector: Find priority settings
├─ Test: Mark email as important
├─ Test: Mark email as not important
├─ Test: Filter by priority
└─ Recipe: create priority-management.recipe.json
```

---

## 📊 TASK TRACKER

```
PERFECTION CHECKLIST:

TIER 1 (Advanced Operations): 5 tasks
├─ [ ] Task 1: Attachment Upload
├─ [ ] Task 2: CC/BCC Fields
├─ [ ] Task 3: Reply-All
├─ [ ] Task 4: Email Threading
└─ [ ] Task 5: Label Management

TIER 2 (Bulk Operations): 5 tasks
├─ [ ] Task 6: Bulk Select
├─ [ ] Task 7: Bulk Archive
├─ [ ] Task 8: Bulk Delete
├─ [ ] Task 9: Bulk Label
└─ [ ] Task 10: Bulk Star

TIER 3 (Advanced Reading): 5 tasks
├─ [ ] Task 11: Body Extraction
├─ [ ] Task 12: Attachment Download
├─ [ ] Task 13: Contact Extraction
├─ [ ] Task 14: Draft Management
└─ [ ] Task 15: Scheduled Send

TIER 4 (Filtering & Search): 5 tasks
├─ [ ] Task 16: Advanced Search
├─ [ ] Task 17: Auto-Reply
├─ [ ] Task 18: Filter Rules
├─ [ ] Task 19: Spam Management
└─ [ ] Task 20: Unsubscribe

TIER 5 (Advanced Features): 5 tasks
├─ [ ] Task 21: Email Templates
├─ [ ] Task 22: Snooze Email
├─ [ ] Task 23: Account Switching
├─ [ ] Task 24: Undo Send
└─ [ ] Task 25: Priority Inbox

TOTAL: 25 advanced tasks to perfect
ALREADY DONE: 18 core operations ✅
```

---

## 🎯 NEXT STEP: Live Headed Browser Testing

```
I will now:

1. Start persistent_browser_server.py
2. Open a HEADED (not headless) browser
3. Work through tasks TIER 1 (5 tasks)
4. You can WATCH me work in real-time
5. Create recipes + PrimeWiki + Skills as I go
6. Report which selectors work, which need adjusting

Expected: 3-4 hours to perfect TIER 1 + TIER 2 (10 core tasks)

Ready to watch? I'll narrate what's happening! 🚀
```

---

**Auth**: 65537 | **Status**: Ready for live testing with headed browser

