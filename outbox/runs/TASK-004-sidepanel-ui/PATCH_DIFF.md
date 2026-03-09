diff --git a/chrome/browser/ui/BUILD.gn b/chrome/browser/ui/BUILD.gn
index e62e1bb8c4346..53e1321d1a107 100644
--- a/chrome/browser/ui/BUILD.gn
+++ b/chrome/browser/ui/BUILD.gn
@@ -1377,6 +1377,8 @@ static_library("ui") {
       "webui/side_panel/reading_list/reading_list_page_handler.h",
       "webui/side_panel/reading_list/reading_list_ui.cc",
       "webui/side_panel/reading_list/reading_list_ui.h",
+      "webui/solace_panel_ui.cc",
+      "webui/solace_panel_ui.h",
       "webui/suggest_internals/suggest_internals_handler.cc",
       "webui/suggest_internals/suggest_internals_handler.h",
       "webui/suggest_internals/suggest_internals_ui.cc",
diff --git a/chrome/browser/ui/views/side_panel/side_panel_coordinator.cc b/chrome/browser/ui/views/side_panel/side_panel_coordinator.cc
index e81c36f871327..0aede5badd9b7 100644
--- a/chrome/browser/ui/views/side_panel/side_panel_coordinator.cc
+++ b/chrome/browser/ui/views/side_panel/side_panel_coordinator.cc
@@ -34,13 +34,36 @@
 #include "chrome/browser/ui/views/side_panel/side_panel_web_ui_view.h"
 #include "chrome/browser/ui/views/toolbar/pinned_toolbar_actions_container.h"
 #include "chrome/browser/ui/views/toolbar/toolbar_view.h"
+#include "chrome/browser/ui/webui/solace_panel_ui.h"
+#include "chrome/grit/generated_resources.h"
 #include "components/feature_engagement/public/event_constants.h"
 #include "components/feature_engagement/public/feature_constants.h"
+#include "ui/base/metadata/metadata_impl_macros.h"
 #include "ui/base/unowned_user_data/scoped_unowned_user_data.h"
 #include "ui/views/view.h"
 
 DEFINE_USER_DATA(SidePanelCoordinator);
 
+namespace {
+
+constexpr char kSolacePanelUrl[] = "chrome://solace-panel/";
+
+using SidePanelWebUIViewT_SolacePanelUI = SidePanelWebUIViewT<SolacePanelUI>;
+BEGIN_TEMPLATE_METADATA(SidePanelWebUIViewT_SolacePanelUI, SidePanelWebUIViewT)
+END_METADATA
+
+std::unique_ptr<views::View> CreateSolacePanelWebView(
+    Profile* profile,
+    SidePanelEntryScope& scope) {
+  return std::make_unique<SidePanelWebUIViewT<SolacePanelUI>>(
+      scope, base::RepeatingClosure(), base::RepeatingClosure(),
+      std::make_unique<WebUIContentsWrapperT<SolacePanelUI>>(
+          GURL(kSolacePanelUrl), profile, IDS_PRODUCT_NAME,
+          /*esc_closes_ui=*/false));
+}
+
+}  // namespace
+
 SidePanelCoordinator::SidePanelCoordinator(BrowserView* browser_view)
     : SidePanelUIBase(browser_view->browser()),
       browser_view_(browser_view),
@@ -61,6 +84,11 @@ SidePanelCoordinator* SidePanelCoordinator::From(
 void SidePanelCoordinator::Init(Browser* browser) {
   SidePanelUtil::PopulateGlobalEntries(browser,
                                        SidePanelRegistry::From(browser));
+  CHECK(SidePanelRegistry::From(browser)->Register(
+      std::make_unique<SidePanelEntry>(
+          SidePanelEntry::Key(SidePanelEntry::Id::kYinyang),
+          base::BindRepeating(&CreateSolacePanelWebView, browser->profile()),
+          /*default_content_width_callback=*/base::NullCallback())));
 }
 
 void SidePanelCoordinator::TearDownPreBrowserWindowDestruction() {
diff --git a/chrome/browser/ui/webui/chrome_web_ui_configs.cc b/chrome/browser/ui/webui/chrome_web_ui_configs.cc
index 8762b543020a1..a5e31bfee689f 100644
--- a/chrome/browser/ui/webui/chrome_web_ui_configs.cc
+++ b/chrome/browser/ui/webui/chrome_web_ui_configs.cc
@@ -120,6 +120,7 @@
 #include "chrome/browser/ui/webui/side_panel/history_clusters/history_clusters_side_panel_ui.h"
 #include "chrome/browser/ui/webui/side_panel/reading_list/reading_list_ui.h"
 #include "chrome/browser/ui/webui/signin/sync_confirmation_ui.h"
+#include "chrome/browser/ui/webui/solace_panel_ui.h"
 #include "chrome/browser/ui/webui/suggest_internals/suggest_internals_ui.h"
 #include "chrome/browser/ui/webui/support_tool/support_tool_ui.h"
 #include "chrome/browser/ui/webui/system/system_info_ui.h"
@@ -356,6 +357,7 @@ void RegisterChromeWebUIConfigs() {
   map.AddWebUIConfig(std::make_unique<ReadingListUIConfig>());
   map.AddWebUIConfig(std::make_unique<SearchEngineChoiceUIConfig>());
   map.AddWebUIConfig(std::make_unique<settings::SettingsUIConfig>());
+  map.AddWebUIConfig(std::make_unique<SolacePanelUIConfig>());
   map.AddWebUIConfig(std::make_unique<ShoppingInsightsSidePanelUIConfig>());
   map.AddWebUIConfig(std::make_unique<SuggestInternalsUIConfig>());
   map.AddWebUIConfig(std::make_unique<SupportToolUIConfig>());
diff --git a/chrome/browser/ui/webui/chrome_web_ui_controller_factory.cc b/chrome/browser/ui/webui/chrome_web_ui_controller_factory.cc
index 64348336c6b24..723cbad88a660 100644
--- a/chrome/browser/ui/webui/chrome_web_ui_controller_factory.cc
+++ b/chrome/browser/ui/webui/chrome_web_ui_controller_factory.cc
@@ -140,6 +140,8 @@ using ui::WebDialogUI;
 
 namespace {
 
+constexpr char kSolacePanelHost[] = "solace-panel";
+
 // A function for creating a new WebUI. The caller owns the return value, which
 // may be nullptr (for example, if the URL refers to an non-existent extension).
 typedef WebUIController* (*WebUIFactoryFunction)(WebUI* web_ui,
@@ -349,7 +351,8 @@ bool ChromeWebUIControllerFactory::IsWebUIAllowedToMakeNetworkRequests(
       // https://crbug.com/859345
       origin.host() == chrome::kChromeUIDownloadsHost ||
       // https://crbug.com/376417346
-      origin.host() == chrome::kChromeUIExtensionsHost;
+      origin.host() == chrome::kChromeUIExtensionsHost ||
+      origin.host() == kSolacePanelHost;
 }
 
 ChromeWebUIControllerFactory::ChromeWebUIControllerFactory() = default;
diff --git a/chrome/browser/ui/webui/solace_panel_ui.h b/chrome/browser/ui/webui/solace_panel_ui.h
new file mode 100644
index 0000000000000..ce29ebea5476a
--- /dev/null
+++ b/chrome/browser/ui/webui/solace_panel_ui.h
@@ -0,0 +1,33 @@
+// Copyright 2024 The Chromium Authors
+// Use of this source code is governed by a BSD-style license that can be
+// found in the LICENSE file.
+
+#ifndef CHROME_BROWSER_UI_WEBUI_SOLACE_PANEL_UI_H_
+#define CHROME_BROWSER_UI_WEBUI_SOLACE_PANEL_UI_H_
+
+#include <string_view>
+
+#include "chrome/browser/ui/webui/top_chrome/top_chrome_web_ui_controller.h"
+#include "chrome/browser/ui/webui/top_chrome/top_chrome_webui_config.h"
+
+class SolacePanelUI;
+
+class SolacePanelUIConfig : public DefaultTopChromeWebUIConfig<SolacePanelUI> {
+ public:
+  SolacePanelUIConfig();
+};
+
+class SolacePanelUI : public TopChromeWebUIController {
+ public:
+  explicit SolacePanelUI(content::WebUI* web_ui);
+  SolacePanelUI(const SolacePanelUI&) = delete;
+  SolacePanelUI& operator=(const SolacePanelUI&) = delete;
+  ~SolacePanelUI() override;
+
+  static constexpr std::string_view GetWebUIName() { return "SolacePanel"; }
+
+ private:
+  WEB_UI_CONTROLLER_TYPE_DECL();
+};
+
+#endif  // CHROME_BROWSER_UI_WEBUI_SOLACE_PANEL_UI_H_
diff --git a/chrome/browser/ui/webui/solace_panel_ui.cc b/chrome/browser/ui/webui/solace_panel_ui.cc
new file mode 100644
index 0000000000000..a682fd09a7426
--- /dev/null
+++ b/chrome/browser/ui/webui/solace_panel_ui.cc
@@ -0,0 +1,38 @@
+// Copyright 2024 The Chromium Authors
+// Use of this source code is governed by a BSD-style license that can be
+// found in the LICENSE file.
+
+#include "chrome/browser/ui/webui/solace_panel_ui.h"
+
+#include "chrome/browser/profiles/profile.h"
+#include "chrome/grit/solace_resources.h"
+#include "chrome/grit/solace_resources_map.h"
+#include "content/public/browser/web_ui.h"
+#include "content/public/browser/web_ui_data_source.h"
+#include "services/network/public/mojom/content_security_policy.mojom.h"
+
+namespace {
+
+constexpr char kSolacePanelHost[] = "solace-panel";
+constexpr char kSolacePanelConnectSrc[] =
+    "connect-src ws://localhost:8888 'self';";
+
+}  // namespace
+
+SolacePanelUIConfig::SolacePanelUIConfig()
+    : DefaultTopChromeWebUIConfig(content::kChromeUIScheme, kSolacePanelHost) {}
+
+SolacePanelUI::SolacePanelUI(content::WebUI* web_ui)
+    : TopChromeWebUIController(web_ui) {
+  Profile* profile = Profile::FromWebUI(web_ui);
+  content::WebUIDataSource* source =
+      content::WebUIDataSource::CreateAndAdd(profile, kSolacePanelHost);
+  source->OverrideContentSecurityPolicy(
+      network::mojom::CSPDirectiveName::ConnectSrc, kSolacePanelConnectSrc);
+  source->SetDefaultResource(IDR_SOLACE_SIDEPANEL_HTML);
+  source->AddResourcePaths(kSolaceResources);
+}
+
+SolacePanelUI::~SolacePanelUI() = default;
+
+WEB_UI_CONTROLLER_TYPE_IMPL(SolacePanelUI)
