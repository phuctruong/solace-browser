**Done**
- Added a pinnable Yinyang browser action that toggles the side panel on click at `source/src/chrome/browser/ui/browser_actions.cc:252`.
- Bound `kYinyang` to its toolbar action id at `source/src/chrome/browser/ui/side_panel/side_panel_entry_id.h:44` and `source/src/chrome/browser/ui/actions/chrome_action_id.h:574`.
- Registered the toolbar action name for the new button at `source/src/chrome/browser/ui/views/toolbar/toolbar_controller.cc:366`.
- Added a focused toolbar browsertest for Yinyang popout behavior at `source/src/chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container_browsertest.cc:227`.

**Verification**
- `gn gen` passed for `source/src/out/Solace`.
- Wrote the requested artifacts to `outbox/runs/TASK-006-toolbar-button/PATCH_DIFF.md:1`, `outbox/runs/TASK-006-toolbar-button/GREEN_GATE.md:1`, and `outbox/runs/TASK-006-toolbar-button/EVIDENCE.json:1`.

If you want, I can do the next pass to make the Yinyang button pinned by default instead of only being available/popped out through the toolbar action system.