# TASK-006 Toolbar Button Patch

```diff
diff --git a/chrome/browser/ui/actions/chrome_action_id.h b/chrome/browser/ui/actions/chrome_action_id.h
index e7028788b77e6..440b244f9e9f1 100644
--- a/chrome/browser/ui/actions/chrome_action_id.h
+++ b/chrome/browser/ui/actions/chrome_action_id.h
@@ -571,6 +571,7 @@
   E(kActionSidePanelShowReadAnything) \
   E(kActionSidePanelShowReadingList, IDC_READING_LIST_MENU_SHOW_UI) \
   E(kActionSidePanelShowSearchCompanion, IDC_SHOW_SEARCH_COMPANION) \
+  E(kActionSidePanelShowYinyang) \
   E(kActionSidePanelShowShoppingInsights) \
   E(kActionSidePanelShowSideSearch) \
   E(kActionSidePanelShowUserNote) \
diff --git a/chrome/browser/ui/browser_actions.cc b/chrome/browser/ui/browser_actions.cc
index 045b8f110a9a8..12b10b948549b 100644
--- a/chrome/browser/ui/browser_actions.cc
+++ b/chrome/browser/ui/browser_actions.cc
@@ -245,6 +245,19 @@ void BrowserActions::InitializeBrowserActions() {
                               IDS_READ_LATER_TITLE, IDS_READ_LATER_TITLE,
                               kReadingListIcon, kActionSidePanelShowReadingList,
                               bwi, true),
+              actions::ActionItem::Builder(CreateToggleSidePanelActionCallback(
+                                               SidePanelEntryKey(
+                                                   SidePanelEntryId::kYinyang),
+                                               bwi))
+                  .SetActionId(kActionSidePanelShowYinyang)
+                  .SetText(u"Yinyang")
+                  .SetTooltipText(u"Yinyang")
+                  .SetImage(ui::ImageModel::FromVectorIcon(
+                      vector_icons::kProductIcon, ui::kColorIcon))
+                  .SetProperty(
+                      actions::kActionItemPinnableKey,
+                      std::underlying_type_t<actions::ActionPinnableState>(
+                          actions::ActionPinnableState::kPinnable)),
               SidePanelAction(SidePanelEntryId::kAboutThisSite,
                               IDS_PAGE_INFO_ABOUT_THIS_PAGE_TITLE,
                               IDS_PAGE_INFO_ABOUT_THIS_PAGE_TITLE,
diff --git a/chrome/browser/ui/side_panel/side_panel_entry_id.h b/chrome/browser/ui/side_panel/side_panel_entry_id.h
index 4bcd669843672..bd9729566c502 100644
--- a/chrome/browser/ui/side_panel/side_panel_entry_id.h
+++ b/chrome/browser/ui/side_panel/side_panel_entry_id.h
@@ -41,6 +41,7 @@
   V(kMerchantTrust, kActionSidePanelShowMerchantTrust, "MerchantTrust")       \
   V(kComments, kActionSidePanelShowComments, "Comments")                      \
   V(kGlic, kActionSidePanelShowGlic, "Glic")                                  \
+  V(kYinyang, kActionSidePanelShowYinyang, "Yinyang")                         \
   /* Extensions (nothing more should be added below here) */                  \
   V(kExtension, std::nullopt, "Extension")
 
diff --git a/chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container_browsertest.cc b/chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container_browsertest.cc
index 54448d9187322..cfa55d6d33e2c 100644
--- a/chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container_browsertest.cc
+++ b/chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container_browsertest.cc
@@ -223,6 +223,22 @@ IN_PROC_BROWSER_TEST_F(PinnedToolbarActionsContainerBrowserTest,
   EXPECT_TRUE(container()->IsActionPoppedOut(kActionSidePanelShowBookmarks));
 }
 
+IN_PROC_BROWSER_TEST_F(PinnedToolbarActionsContainerBrowserTest,
+                       YinyangShowsToolbarButtonWhenOpened) {
+  SidePanelUI* const side_panel_ui = browser()->GetFeatures().side_panel_ui();
+  side_panel_ui->SetNoDelaysForTesting(true);
+
+  SidePanelEntry* const entry = SidePanelRegistry::From(browser())->GetEntryForKey(
+      SidePanelEntry::Key(SidePanelEntryId::kYinyang));
+  ASSERT_NE(entry, nullptr);
+
+  side_panel_ui->Show(SidePanelEntry::Key(SidePanelEntryId::kYinyang));
+  views::test::WaitForAnimatingLayoutManager(container());
+
+  EXPECT_FALSE(container()->IsActionPinned(kActionSidePanelShowYinyang));
+  EXPECT_TRUE(container()->IsActionPoppedOut(kActionSidePanelShowYinyang));
+}
+
 #if !BUILDFLAG(IS_CHROMEOS)
 IN_PROC_BROWSER_TEST_F(PinnedToolbarActionsContainerBrowserTest,
                        QRCodeUpdatesWithSharingHubPrefChanges) {
diff --git a/chrome/browser/ui/views/toolbar/toolbar_controller.cc b/chrome/browser/ui/views/toolbar/toolbar_controller.cc
index 0bf46fe75139a..974674f736cda 100644
--- a/chrome/browser/ui/views/toolbar/toolbar_controller.cc
+++ b/chrome/browser/ui/views/toolbar/toolbar_controller.cc
@@ -363,6 +363,7 @@ std::string ToolbarController::GetActionNameFromElementIdentifier(
            "PinnedShowReadingListSidePanelButton"},
           {kActionSidePanelShowSearchCompanion,
            "PinnedShowSearchCompanionSidePanelButton"},
+          {kActionSidePanelShowYinyang, "PinnedShowYinyangSidePanelButton"},
           {kActionTaskManager, "PinnedTaskManagerButton"},
           {kActionSidePanelShowLensOverlayResults,
            "PinnedShowLensOverlayResultsSidePanelButton"},
```
