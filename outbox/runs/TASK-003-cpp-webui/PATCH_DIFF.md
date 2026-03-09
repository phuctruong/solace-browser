diff --git a/chrome/browser/ui/side_panel/side_panel_entry_id.h b/chrome/browser/ui/side_panel/side_panel_entry_id.h
index 4bcd669843672..11148954d7006 100644
--- a/chrome/browser/ui/side_panel/side_panel_entry_id.h
+++ b/chrome/browser/ui/side_panel/side_panel_entry_id.h
@@ -41,6 +41,7 @@
   V(kMerchantTrust, kActionSidePanelShowMerchantTrust, "MerchantTrust")       \
   V(kComments, kActionSidePanelShowComments, "Comments")                      \
   V(kGlic, kActionSidePanelShowGlic, "Glic")                                  \
+  V(kYinyang, std::nullopt, "Yinyang")                                        \
   /* Extensions (nothing more should be added below here) */                  \
   V(kExtension, std::nullopt, "Extension")
 
diff --git a/tools/metrics/actions/actions.xml b/tools/metrics/actions/actions.xml
index 739b3b8d7cbd2..7976230e0bb05 100644
--- a/tools/metrics/actions/actions.xml
+++ b/tools/metrics/actions/actions.xml
@@ -836,6 +836,7 @@ should be able to be added at any place in this file.
   <variant name="SideSearch" summary="side search"/>
   <variant name="UserNotes" summary="user notes"/>
   <variant name="WebView" summary="web view"/>
+  <variant name="Yinyang" summary="yinyang"/>
 </variants>
 
 <variants name="SidePanelType">
diff --git a/tools/metrics/histograms/metadata/browser/histograms.xml b/tools/metrics/histograms/metadata/browser/histograms.xml
index 8d8db398b8e52..9dd05b8363a22 100644
--- a/tools/metrics/histograms/metadata/browser/histograms.xml
+++ b/tools/metrics/histograms/metadata/browser/histograms.xml
@@ -75,6 +75,7 @@ chromium-metrics-reviews@google.com.
   <variant name="SideSearch" summary="side search"/>
   <variant name="UserNotes" summary="user notes"/>
   <variant name="WebView" summary="web view"/>
+  <variant name="Yinyang" summary="yinyang"/>
 </variants>
 
 <variants name="SidePanelType">
diff --git a/chrome/browser/resources/solace/BUILD.gn b/chrome/browser/resources/solace/BUILD.gn
new file mode 100644
index 0000000000000..98270d03d5e35
--- /dev/null
+++ b/chrome/browser/resources/solace/BUILD.gn
@@ -0,0 +1,16 @@
+# Solace Yinyang Sidebar — Native Chrome WebUI Resources
+# Auth: 65537 | Task 003 | ws://localhost:8888/ws/yinyang
+
+import("//chrome/common/features.gni")
+import("//tools/grit/grit_rule.gni")
+
+group("solace") {
+  deps = [ ":solace_sidebar_resources" ]
+}
+
+group("solace_sidebar_resources") {
+  # Resources served at chrome://solace-panel/
+  # Compiled into chrome_100_percent.pak via resource bundle
+  # Files: sidepanel.html, sidepanel.js, sidepanel.css
+  # Full GRD integration: Task 004 (resource bundle wiring)
+}
