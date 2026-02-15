#!/usr/bin/env python3
"""
Medium Discovery: Headed Mode
Navigate with UI visible, use LLM reasoning to discover features
Then create recipes for headless testing
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumLLMDiscovery:
    """Discover Medium using headed browser + LLM reasoning"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.learnings = {
            "timestamp": datetime.now().isoformat(),
            "platform": "medium.com",
            "discovery_method": "headed + LLM reasoning",
            "pages_explored": [],
            "features_discovered": [],
            "selectors_discovered": {},
            "workflows_to_automate": [],
            "recipes_to_create": [],
            "challenges": [],
            "screenshots_taken": []
        }

    async def start(self):
        """Start headed browser (UI visible)"""
        print("\n🖥️  STARTING HEADED BROWSER (UI VISIBLE)")
        print("   Browser will open and stay open for exploration")
        print("   Check the browser window for real-time feedback\n")

        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)  # HEADED MODE
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def stop(self):
        """Stop browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def explore_homepage(self):
        """Navigate Medium homepage and explore"""
        print("\n" + "="*70)
        print("📱 EXPLORING MEDIUM HOMEPAGE (HEADED)")
        print("="*70)

        await self.page.goto("https://medium.com/", wait_until='domcontentloaded')
        await asyncio.sleep(3)  # Let page fully load

        # Take screenshot
        screenshot_path = "/tmp/medium_homepage.png"
        await self.page.screenshot(path=screenshot_path)
        self.learnings["screenshots_taken"].append({
            "page": "homepage",
            "path": screenshot_path
        })
        print(f"✅ Screenshot saved: {screenshot_path}")

        # Get page info
        title = await self.page.title()
        url = self.page.url
        print(f"✅ Title: {title}")
        print(f"✅ URL: {url}")

        # Get text content for LLM to reason about
        text_content = await self.page.inner_text('body')
        print(f"✅ Page loaded, content size: {len(text_content)} chars")

        self.learnings["pages_explored"].append({
            "name": "Homepage",
            "url": url,
            "title": title,
            "text_preview": text_content[:500]
        })

        return text_content

    async def discover_navigation(self):
        """Explore navigation elements"""
        print("\n🧭 DISCOVERING NAVIGATION ELEMENTS")
        print("-" * 70)

        # Find all navigation buttons
        buttons = await self.page.query_selector_all("button, a[role='button']")
        print(f"Found {len(buttons)} clickable elements")

        navigation_elements = []
        for i, btn in enumerate(buttons[:15]):  # First 15 elements
            try:
                text = await btn.inner_text()
                aria_label = await btn.get_attribute("aria-label")
                role = await btn.get_attribute("role")
                href = await btn.get_attribute("href")

                element_info = {
                    "index": i,
                    "text": text.strip() if text else None,
                    "aria_label": aria_label,
                    "href": href,
                    "type": "link" if href else "button"
                }

                navigation_elements.append(element_info)
                print(f"  [{i}] {text.strip() if text else aria_label or 'no-text'}")

            except Exception as e:
                pass

        self.learnings["selectors_discovered"]["navigation"] = navigation_elements
        return navigation_elements

    async def discover_auth_flow(self):
        """Discover authentication/sign-in flow"""
        print("\n🔐 DISCOVERING AUTHENTICATION FLOW")
        print("-" * 70)

        # Look for sign in button
        sign_in_buttons = []
        for selector in ["button:has-text('Sign in')", "a:has-text('Sign in')", "[aria-label*='sign' i]"]:
            try:
                elems = await self.page.query_selector_all(selector)
                if len(elems) > 0:
                    print(f"✅ Found sign-in element with selector: {selector}")
                    sign_in_buttons.append({
                        "selector": selector,
                        "count": len(elems)
                    })
            except:
                pass

        # Look for email input, password input
        inputs = await self.page.query_selector_all("input")
        print(f"Found {len(inputs)} input fields on page")

        form_fields = []
        for inp in inputs[:10]:
            try:
                inp_type = await inp.get_attribute("type")
                placeholder = await inp.get_attribute("placeholder")
                name = await inp.get_attribute("name")
                form_fields.append({
                    "type": inp_type,
                    "placeholder": placeholder,
                    "name": name
                })
            except:
                pass

        self.learnings["selectors_discovered"]["auth"] = {
            "sign_in_buttons": sign_in_buttons,
            "form_fields": form_fields
        }

        return sign_in_buttons, form_fields

    async def discover_article_interactions(self):
        """Discover how to interact with articles"""
        print("\n📰 DISCOVERING ARTICLE INTERACTIONS")
        print("-" * 70)

        # Look for article containers
        articles = await self.page.query_selector_all("article, [class*='story'], [data-test*='article']")
        print(f"Found {len(articles)} article-like elements")

        if articles:
            # Examine first article
            first_article = articles[0]
            article_html = await first_article.outer_html()
            print(f"First article HTML size: {len(article_html)} chars")

            # Look for interaction buttons within article
            article_buttons = await first_article.query_selector_all("button, a[role='button']")
            print(f"  - {len(article_buttons)} clickable elements in article")

            interaction_buttons = []
            for btn in article_buttons[:5]:
                try:
                    text = await btn.inner_text()
                    aria = await btn.get_attribute("aria-label")
                    interaction_buttons.append({
                        "text": text.strip() if text else aria
                    })
                except:
                    pass

            self.learnings["selectors_discovered"]["articles"] = {
                "container_count": len(articles),
                "interactions": interaction_buttons
            }

            return articles, interaction_buttons

        return [], []

    async def create_recipe_template(self):
        """Create a recipe template based on discoveries"""
        print("\n📝 CREATING RECIPE TEMPLATES")
        print("-" * 70)

        # Based on what we discovered, create potential recipes
        recipes = []

        # Recipe 1: Login
        recipe_login = {
            "recipe_id": "medium-login-flow",
            "recipe_version": "1.0.0",
            "platform": "medium.com",
            "workflow": "authentication",
            "created_at": datetime.now().isoformat(),
            "reasoning": {
                "research": "Medium uses email/password authentication via modal or dedicated page",
                "strategy": "Click sign-in, enter credentials, submit, verify logged in",
                "llm_learnings": "Login is likely modal-based on homepage, may redirect to auth page"
            },
            "execution_trace": [
                {
                    "step": 1,
                    "action": "navigate",
                    "target": "https://medium.com/",
                    "description": "Navigate to Medium homepage"
                },
                {
                    "step": 2,
                    "action": "wait",
                    "duration": 2000,
                    "description": "Wait for page to load"
                },
                {
                    "step": 3,
                    "action": "click",
                    "selector": "button:has-text('Sign in')",
                    "description": "Click Sign In button (to be verified)",
                    "note": "Selector may vary - need to verify in headed mode"
                },
                {
                    "step": 4,
                    "action": "wait",
                    "duration": 1000,
                    "description": "Wait for modal/page to appear"
                },
                {
                    "step": 5,
                    "action": "fill",
                    "selector": "input[type='email']",
                    "text": "{EMAIL}",
                    "description": "Enter email (placeholder)"
                },
                {
                    "step": 6,
                    "action": "fill",
                    "selector": "input[type='password']",
                    "text": "{PASSWORD}",
                    "description": "Enter password (placeholder)"
                },
                {
                    "step": 7,
                    "action": "click",
                    "selector": "button:has-text('Sign in')",
                    "description": "Click Sign In submit"
                },
                {
                    "step": 8,
                    "action": "wait",
                    "duration": 3000,
                    "description": "Wait for authentication"
                },
                {
                    "step": 9,
                    "action": "verify",
                    "pattern": "Sign out|Profile|Home",
                    "description": "Verify logged in (check for user menu)"
                }
            ]
        }

        recipes.append(recipe_login)

        # Recipe 2: Browse articles
        recipe_browse = {
            "recipe_id": "medium-browse-articles",
            "recipe_version": "1.0.0",
            "platform": "medium.com",
            "workflow": "content-discovery",
            "execution_trace": [
                {"step": 1, "action": "navigate", "target": "https://medium.com/", "description": "Navigate to homepage"},
                {"step": 2, "action": "wait", "duration": 2000, "description": "Wait for articles to load"},
                {"step": 3, "action": "extract", "selector": "article, [class*='story']", "description": "Get article list"},
                {"step": 4, "action": "click", "selector": "article:first-child a", "description": "Click first article (selector TBD)"},
                {"step": 5, "action": "wait", "duration": 2000, "description": "Wait for article page"}
            ]
        }

        recipes.append(recipe_browse)

        self.learnings["recipes_to_create"] = recipes
        print(f"✅ Created {len(recipes)} recipe templates")

        return recipes

    async def analyze_page_structure(self):
        """Get detailed page structure for LLM reasoning"""
        print("\n🏗️  ANALYZING PAGE STRUCTURE")
        print("-" * 70)

        html = await self.page.content()

        # Check for React
        is_react = "react" in html.lower() or "_react" in html.lower()
        print(f"{'✅' if is_react else '⚠️'} React detected: {is_react}")

        # Check for common patterns
        patterns = {
            "data-testid": html.count('data-testid'),
            "aria-label": html.count('aria-label'),
            "role=": html.count('role='),
            "form elements": html.count('<form') + html.count('<input'),
            "buttons": html.count('<button'),
            "links": html.count('<a ')
        }

        for pattern, count in patterns.items():
            print(f"  - {pattern}: {count}")

        self.learnings["page_structure"] = patterns

    async def create_learnings_report(self):
        """Create comprehensive learnings report"""
        print("\n" + "="*70)
        print("📊 CREATING LEARNINGS REPORT")
        print("="*70)

        # Save JSON
        with open('/tmp/medium_headed_learnings.json', 'w') as f:
            json.dump(self.learnings, f, indent=2)

        # Save recipes as separate files for testing
        for recipe in self.learnings["recipes_to_create"]:
            filename = f"/tmp/{recipe['recipe_id']}.recipe.json"
            with open(filename, 'w') as f:
                json.dump(recipe, f, indent=2)
            print(f"✅ Saved recipe: {filename}")

        print("\n✅ Learnings saved to: /tmp/medium_headed_learnings.json")

        return self.learnings

async def main():
    """Run headed discovery"""
    explorer = MediumLLMDiscovery()
    await explorer.start()

    try:
        print("\n" + "█"*70)
        print("MEDIUM DISCOVERY: HEADED MODE + LLM REASONING")
        print("Browser WILL BE VISIBLE - watch the UI")
        print("We'll map features and create recipes")
        print("█"*70)

        # Phase 1: Explore homepage
        content = await explorer.explore_homepage()

        # Phase 2: Discover navigation
        nav_elements = await explorer.discover_navigation()

        # Phase 3: Discover auth
        sign_in, form_fields = await explorer.discover_auth_flow()

        # Phase 4: Discover articles
        articles, interactions = await explorer.discover_article_interactions()

        # Phase 5: Analyze structure
        await explorer.analyze_page_structure()

        # Phase 6: Create recipe templates
        recipes = await explorer.create_recipe_template()

        # Phase 7: Create report
        learnings = await explorer.create_learnings_report()

        print("\n" + "="*70)
        print("✅ DISCOVERY COMPLETE")
        print("="*70)
        print("\nNext: Test these recipes in headless mode")
        print("Files created:")
        print("  • /tmp/medium_headed_learnings.json")
        for recipe in recipes:
            print(f"  • /tmp/{recipe['recipe_id']}.recipe.json")

        # Keep browser open for 10 more seconds so user can see it
        print("\nBrowser will close in 10 seconds...")
        await asyncio.sleep(10)

    finally:
        await explorer.stop()

if __name__ == "__main__":
    asyncio.run(main())
