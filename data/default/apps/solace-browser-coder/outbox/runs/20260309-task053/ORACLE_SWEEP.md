1. PASS — Adds domain index rebuild helper and route.
2. PASS — GET /api/v1/apps/by-domain requires Bearer auth.
3. PASS — Domain lookup returns installed_apps, store_apps, can_create_custom, and create_url.
4. PASS — Free-tier lookup hides paid installed apps.
5. PASS — Free-tier lookup still surfaces paid store apps as upgrade-required.
6. PASS — Store matching falls back to local manifests when the catalog omits an app.
7. PASS — Exact domain patterns match correctly.
8. PASS — Wildcard subdomain + path patterns match correctly.
9. PASS — Unknown domains return empty app lists, not errors.
10. PASS — Custom app creation writes to data/custom/apps/<app_id>/.
11. PASS — Custom manifest scaffold includes domains and matching site.
12. PASS — Custom app creation triggers a domain index rebuild.
13. PASS — Marketplace install/uninstall now rebuild the domain index.
14. PASS — domains: ["*"] raises DOMAIN_WILDCARD_ABUSE during rebuild/load.
15. PASS — Kill checks clean (9222=0, companion app=0, except Exception=0).
