#!/usr/bin/env python3
"""
Headless Discovery: ProductHunt
A new platform to test the self-learning loop without Cloudflare
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class ProductHuntHeadlessDiscovery:
    """Discover ProductHunt using headless browser only"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.learnings = {
            "timestamp": datetime.now().isoformat(),
            "platform": "producthunt.com",
            "discovery_method": "headless-only",
            "status": "In Progress",
            "features_discovered": [],
            "selectors_found": {},
            "workflows_identified": [],
            "challenges": [],
            "production_readiness": 0
        }

    async def start(self):
        """Start headless browser"""
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080}
        )
        self.page = await self.context.new_page()

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def log(self, msg: str, indent: int = 0):
        print("  " * indent + msg)

    async def discover_homepage(self):
        """Discover ProductHunt homepage"""
        self.log("\n" + "="*70, 0)
        self.log("📱 DISCOVERING PRODUCTHUNT HOMEPAGE", 0)
        self.log("="*70, 0)

        try:
            response = await self.page.goto("https://www.producthunt.com/", wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)

            self.log(f"✅ Status: {response.status if response else 'OK'}", 1)

            title = await self.page.title()
            html = await self.page.content()

            self.log(f"✅ Title: {title}", 1)
            self.log(f"✅ Page Size: {len(html)} bytes", 1)

            # Check what we can see
            text = await self.page.inner_text('body')
            if 'ProductHunt' in text or 'Product Hunt' in text or 'Discover' in text:
                self.log("✅ Real ProductHunt content loaded", 1)
                self.learnings["status"] = "Accessible"
            else:
                self.log("⚠️  Unknown content", 1)
                self.learnings["status"] = "Uncertain"

            return True

        except Exception as e:
            self.log(f"❌ Error: {e}", 1)
            self.learnings["challenges"].append(f"Failed to load homepage: {e}")
            return False

    async def discover_products(self):
        """Discover product listings"""
        self.log("\n🏆 DISCOVERING PRODUCTS", 1)

        try:
            # Look for product elements
            products = await self.page.query_selector_all("[data-test*='product' i], [class*='product' i], article")
            self.log(f"Found {len(products)} product/article elements", 2)

            if products:
                self.learnings["features_discovered"].append("Product Listings")

                # Look for product interactions
                for i, product in enumerate(products[:3]):
                    try:
                        # Get product card HTML structure
                        html = await product.outer_html()
                        self.learnings["selectors_found"]["product_card"] = "article or [class*='product']"

                        # Look for buttons in product
                        buttons = await product.query_selector_all("button")
                        self.log(f"  Product {i}: {len(buttons)} buttons", 2)

                        for btn in buttons[:2]:
                            try:
                                aria = await btn.get_attribute('aria-label')
                                text = await btn.inner_text()
                                if aria or text.strip():
                                    self.log(f"    Button: {aria or text.strip()}", 3)
                            except:
                                pass

                    except:
                        pass

        except Exception as e:
            self.learnings["challenges"].append(f"Error discovering products: {e}")

    async def discover_interactions(self):
        """Discover vote/like/comment interactions"""
        self.log("\n⚡ DISCOVERING INTERACTIONS", 1)

        interaction_selectors = {
            "upvote_button": "[aria-label*='Upvote' i], [aria-label*='vote' i], button[class*='vote' i]",
            "comment_button": "[aria-label*='comment' i], button[class*='comment' i]",
            "share_button": "[aria-label*='share' i], button[class*='share' i]",
            "save_button": "[aria-label*='save' i], [aria-label*='bookmark' i], button[class*='save' i]",
            "like_button": "[aria-label*='like' i], button[class*='like' i]",
        }

        for name, selector in interaction_selectors.items():
            try:
                elements = await self.page.query_selector_all(selector)
                if len(elements) > 0:
                    self.log(f"✅ {name}: {len(elements)} found", 2)
                    self.learnings["selectors_found"][name] = selector
                    self.learnings["features_discovered"].append(name.title())
            except:
                pass

    async def discover_navigation(self):
        """Discover navigation elements"""
        self.log("\n🧭 DISCOVERING NAVIGATION", 1)

        nav_selectors = {
            "header": "header, nav, [role='navigation']",
            "menu": "button[aria-label*='menu' i], [role='menubutton']",
            "search": "input[type='search'], input[placeholder*='search' i]",
            "auth": "button:has-text('Sign'), a:has-text('Sign'), button:has-text('Log')",
        }

        for name, selector in nav_selectors.items():
            try:
                elements = await self.page.query_selector_all(selector)
                if len(elements) > 0:
                    self.log(f"✅ {name}: {len(elements)} found", 2)
                    self.learnings["selectors_found"][name] = selector
            except:
                pass

    async def create_learnings_document(self):
        """Create comprehensive learnings"""
        self.log("\n" + "="*70, 1)
        self.log("📊 CREATING LEARNINGS DOCUMENT", 1)
        self.log("="*70, 1)

        # Estimate production readiness
        features_count = len(self.learnings["features_discovered"])
        selectors_count = len(self.learnings["selectors_found"])
        challenges_count = len(self.learnings["challenges"])

        # Simple scoring
        if self.learnings["status"] == "Accessible":
            base_score = 70
            if features_count >= 5:
                base_score += 15
            if selectors_count >= 5:
                base_score += 10
            if challenges_count == 0:
                base_score += 5

            self.learnings["production_readiness"] = min(base_score, 100)
        else:
            self.learnings["production_readiness"] = 20

        # Save JSON
        with open('/tmp/producthunt_learnings.json', 'w') as f:
            json.dump(self.learnings, f, indent=2)

        self.log(f"✅ Production Readiness: {self.learnings['production_readiness']}/100", 2)
        self.log(f"✅ Features Discovered: {len(self.learnings['features_discovered'])}", 2)
        self.log(f"✅ Selectors Found: {len(self.learnings['selectors_found'])}", 2)

        # Print summary
        md = f"""# ProductHunt: Headless Discovery Report

**Date**: {datetime.now().isoformat()}
**Platform**: producthunt.com
**Status**: {self.learnings['status']}
**Production Readiness**: {self.learnings['production_readiness']}/100

---

## ✅ Features Discovered

{json.dumps(self.learnings['features_discovered'], indent=2)}

## 🎯 Selectors Found

{json.dumps(self.learnings['selectors_found'], indent=2)}

## ⚠️ Challenges

{json.dumps(self.learnings['challenges'], indent=2) if self.learnings['challenges'] else '✅ No blockers found'}

---

## 🎓 Conclusion

ProductHunt **{self.learnings['status'].upper()}** for headless automation.
Production readiness: {self.learnings['production_readiness']}/100

Recommendation: {'✅ READY for recipe creation' if self.learnings['production_readiness'] >= 70 else '⏳ PARTIAL - More investigation needed'}
"""

        print(md)

        with open('/tmp/producthunt_learnings.md', 'w') as f:
            f.write(md)

        return self.learnings

async def main():
    """Run discovery"""
    explorer = ProductHuntHeadlessDiscovery()
    await explorer.start()

    try:
        print("\n" + "█"*70)
        print("HEADLESS DISCOVERY: PRODUCTHUNT")
        print("Testing self-learning loop on automation-friendly platform")
        print("Browser Mode: HEADLESS (no UI)")
        print("LLM Usage: 0%")
        print("█"*70)

        # Phase 1: Homepage
        success = await explorer.discover_homepage()

        if success:
            # Phase 2: Products
            await explorer.discover_products()

            # Phase 3: Interactions
            await explorer.discover_interactions()

            # Phase 4: Navigation
            await explorer.discover_navigation()

        # Phase 5: Create learnings
        learnings = await explorer.create_learnings_document()

        print("\n✅ Discovery complete")
        print(f"  • Saved: /tmp/producthunt_learnings.json")
        print(f"  • Saved: /tmp/producthunt_learnings.md")

    finally:
        await explorer.stop()

if __name__ == "__main__":
    asyncio.run(main())
