diff --git a/solace-hub/src/index.html b/solace-hub/src/index.html
index c6733945..e41e349f 100644
--- a/solace-hub/src/index.html
+++ b/solace-hub/src/index.html
@@ -821,6 +821,9 @@
         <button class="btn-secondary" onclick="refreshStatus()">
           Refresh
         </button>
+        <button class="btn-secondary" onclick="openFunPacks()">
+          Fun Packs
+        </button>
         <button class="btn-secondary" id="btn-setup" onclick="openSetup()" style="display:none;">
           Setup / Onboarding
         </button>
@@ -1427,6 +1430,12 @@
       window.open("http://localhost:8888/onboarding", "_blank");
     }
 
+    function openFunPacks() {
+      const onboardingLink = document.getElementById("onboarding-link");
+      const hubOrigin = new URL(onboardingLink.href).origin;
+      window.open(hubOrigin + "/web/fun-packs.html", "_blank");
+    }
+
     // ── Open Browser ──────────────────────────────────────────────────────────
     async function openBrowser() {
       const btn = document.getElementById("btn-open-browser");
