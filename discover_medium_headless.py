#!/usr/bin/env python3
"""
Headless-Only Discovery: Medium
Discover Medium's structure, features, and selectors using ONLY headless Playwright
No UI inspection - pure code-based discovery
"""
import asyncio
import json
import re
from playwright.async_api import async_playwright
from datetime import datetime

class MediumHeadlessExplorer:
    """Discover Medium using headless browser only"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.discoveries = {
            "timestamp": datetime.now().isoformat(),
            "platform": "medium.com",
            "discovery_method": "headless-only",
            "pages_explored": [],
            "features_identified": [],
            "selectors_found": {},
            "challenges": []
        }

    async def start(self):
        """Start headless browser"""
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def stop(self):
        """Stop browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def log(self, message: str, indent: int = 0):
        """Pretty print discovery logs"""
        prefix = "  " * indent
        print(f"{prefix}{message}")

    async def explore_page(self, url: str, name: str):
        """Navigate and explore a page"""
        self.log(f"\n{'='*70}", 0)
        self.log(f"EXPLORING: {name}", 0)
        self.log(f"URL: {url}", 1)
        self.log(f"{'='*70}", 0)

        try:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)  # Let JS render

            page_data = {
                "url": url,
                "name": name,
                "title": await self.page.title(),
                "html_size": len(await self.page.content()),
                "selectors_found": {},
                "text_content": None
            }

            # Get page text
            try:
                text = await self.page.inner_text('body')
                page_data["text_content"] = text[:500] if text else None
            except:
                pass

            self.discoveries["pages_explored"].append(page_data)
            return page_data

        except Exception as e:
            self.log(f"❌ Error exploring {name}: {e}", 1)
            return None

    async def find_selectors(self, pattern_name: str, selectors: dict):
        """Try to find elements using various selector patterns"""
        self.log(f"\n🔍 Searching for: {pattern_name}", 1)

        found = {}
        for selector_name, selector in selectors.items():
            try:
                count = len(await self.page.query_selector_all(selector))
                if count > 0:
                    found[selector_name] = {
                        "selector": selector,
                        "count": count,
                        "status": "✅ FOUND"
                    }
                    self.log(f"  ✅ {selector_name}: {count} elements", 2)

                    # Get sample HTML
                    try:
                        elem = await self.page.query_selector(selector)
                        if elem:
                            html = await elem.outer_html()
                            found[selector_name]["sample"] = html[:200]
                    except:
                        pass
                else:
                    found[selector_name] = {
                        "selector": selector,
                        "count": 0,
                        "status": "❌ NOT FOUND"
                    }
            except Exception as e:
                found[selector_name] = {
                    "selector": selector,
                    "status": f"⚠️  ERROR: {str(e)[:50]}"
                }

        return found

    async def discover_homepage(self):
        """Discover Medium homepage structure"""
        self.log("\n📰 PHASE 1: HOMEPAGE DISCOVERY", 0)

        page_data = await self.explore_page("https://medium.com", "Medium Homepage")

        # Look for article cards
        article_selectors = {
            "article_by_data": "article",
            "article_by_role": "[role='article']",
            "article_by_class": "[class*='article']",
            "post_card": "[class*='post']",
            "story_card": "[class*='story']",
        }
        article_finds = await self.find_selectors("Article Cards", article_selectors)

        # Look for navigation
        nav_selectors = {
            "nav_tag": "nav",
            "nav_by_role": "[role='navigation']",
            "header_tag": "header",
        }
        nav_finds = await self.find_selectors("Navigation Elements", nav_selectors)

        # Look for buttons
        button_selectors = {
            "button_all": "button",
            "a_tags": "a",
            "write_button": "button:has-text('Write')",
            "sign_in": "button:has-text('Sign in')",
        }
        button_finds = await self.find_selectors("Buttons & Links", button_selectors)

        return {
            "articles": article_finds,
            "navigation": nav_finds,
            "buttons": button_finds
        }

    async def discover_article_page(self):
        """Discover article page structure"""
        self.log("\n📄 PHASE 2: ARTICLE PAGE DISCOVERY", 0)

        # Get a real article URL from homepage
        self.log("Finding article URL...", 1)
        article_links = await self.page.query_selector_all("a[href*='/']")

        article_url = None
        for link in article_links:
            try:
                href = await link.get_attribute('href')
                if href and 'medium.com' in href and '/p/' in href:
                    article_url = href
                    break
            except:
                pass

        if not article_url:
            self.log("❌ Could not find article link, trying generic path", 1)
            article_url = "https://medium.com/@medium"

        self.log(f"Exploring article at: {article_url}", 1)
        page_data = await self.explore_page(article_url, "Article Page")

        if not page_data:
            return None

        # Look for article content
        content_selectors = {
            "article_tag": "article",
            "main_tag": "main",
            "title": "[role='heading']",
            "author": "[class*='author']",
            "clap_button": "button[aria-label*='clap' i]",
            "response_button": "button[aria-label*='response' i]",
            "bookmark": "button[aria-label*='bookmark' i]",
            "share": "button[aria-label*='share' i]",
        }
        content_finds = await self.find_selectors("Article Elements", content_selectors)

        return {
            "url": article_url,
            "content": content_finds
        }

    async def discover_interactions(self):
        """Discover interactive elements"""
        self.log("\n⚡ PHASE 3: INTERACTIVE ELEMENTS", 0)

        interaction_selectors = {
            "clap_button": "button[aria-label*='clap' i]",
            "clap_svg": "svg[aria-label*='clap' i]",
            "like_button": "button[aria-label*='like' i]",
            "heart_button": "button[aria-label*='heart' i]",
            "share_button": "button[aria-label*='share' i]",
            "bookmark_button": "button[aria-label*='save' i]",
            "more_button": "button[aria-label*='more' i]",
            "dropdown": "[role='menu']",
            "modal": "[role='dialog']",
        }
        interaction_finds = await self.find_selectors("Interactive Elements", interaction_selectors)

        return interaction_finds

    async def discover_forms(self):
        """Discover form elements"""
        self.log("\n📝 PHASE 4: FORMS & INPUT", 0)

        form_selectors = {
            "search_input": "input[type='search']",
            "text_input": "input[type='text']",
            "textarea": "textarea",
            "sign_in_form": "[class*='sign' i]",
            "email_input": "input[type='email']",
            "password_input": "input[type='password']",
        }
        form_finds = await self.find_selectors("Form Elements", form_selectors)

        return form_finds

    async def analyze_structure(self):
        """Analyze page structure"""
        self.log("\n🏗️  PHASE 5: STRUCTURE ANALYSIS", 0)

        html = await self.page.content()

        # Check for React
        if 'react' in html.lower():
            self.log("✅ React detected", 1)
            self.discoveries["challenges"].append("React-based rendering - may need waits")

        # Check for data attributes
        if 'data-testid' in html:
            self.log("✅ data-testid attributes found (good for selectors)", 1)

        if 'aria-label' in html:
            self.log("✅ aria-label attributes found (good for accessibility selectors)", 1)

        # Check for common frameworks
        if 'nextjs' in html.lower() or '_next' in html:
            self.log("⚠️  Next.js detected", 1)
            self.discoveries["challenges"].append("Next.js framework - SSR/SPA hybrid")

        # Estimate complexity
        if '<button' in html:
            button_count = len(re.findall(r'<button', html))
            self.log(f"Found {button_count} button elements", 1)

        if '<form' in html:
            form_count = len(re.findall(r'<form', html))
            self.log(f"Found {form_count} form elements", 1)

    async def create_discovery_report(self):
        """Create comprehensive discovery report"""
        self.log("\n" + "="*70, 0)
        self.log("📊 DISCOVERY REPORT", 0)
        self.log("="*70, 0)

        print(json.dumps(self.discoveries, indent=2))

        return self.discoveries

async def main():
    """Discover Medium in headless-only mode"""
    explorer = MediumHeadlessExplorer()
    await explorer.start()

    try:
        print("\n" + "█"*70)
        print("HEADLESS-ONLY DISCOVERY: MEDIUM")
        print("Testing self-learning loop on new platform")
        print("Browser Mode: HEADLESS (no UI)")
        print("LLM Usage: 0% (pure code-based discovery)")
        print("█"*70)

        # Phase 1: Homepage
        homepage_data = await explorer.discover_homepage()

        # Phase 2: Article page
        article_data = await explorer.discover_article_page()

        # Phase 3: Interactions
        interactions = await explorer.discover_interactions()

        # Phase 4: Forms
        forms = await explorer.discover_forms()

        # Phase 5: Structure analysis
        await explorer.analyze_structure()

        # Create report
        report = await explorer.create_discovery_report()

        # Save discovery to file
        with open('/tmp/medium_discovery_headless.json', 'w') as f:
            json.dump(report, f, indent=2)

        print("\n✅ Discovery report saved to: /tmp/medium_discovery_headless.json")
        print("\n🎯 Next: Analyze findings and create recipes")

    finally:
        await explorer.stop()

if __name__ == "__main__":
    asyncio.run(main())
