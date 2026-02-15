#!/usr/bin/env python3
"""
Headless Discovery with Stealth Mode: Medium
Handle Cloudflare protection by mimicking real browser behavior
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumStealthExplorer:
    """Discover Medium using stealth techniques"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.discoveries = {
            "timestamp": datetime.now().isoformat(),
            "platform": "medium.com",
            "discovery_method": "headless-stealth",
            "stealth_measures": [
                "Chrome user agent",
                "Real viewport size",
                "Timezone/language headers",
                "Accept headers",
                "Referer header"
            ],
            "pages_explored": [],
            "features_identified": [],
            "selectors_found": {},
            "challenges": []
        }

    async def start(self):
        """Start headless browser with stealth measures"""
        p = await async_playwright().start()

        # Use Chrome user agent instead of Playwright
        self.browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        # Create context with realistic headers
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
        )

        self.page = await self.context.new_page()

        # Override navigator.webdriver
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5],
            });
        """)

    async def stop(self):
        """Stop browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def log(self, message: str, indent: int = 0):
        """Pretty print logs"""
        prefix = "  " * indent
        print(f"{prefix}{message}")

    async def explore_page(self, url: str, name: str, wait_time: int = 3):
        """Navigate and explore a page"""
        self.log(f"\n{'='*70}", 0)
        self.log(f"EXPLORING: {name}", 0)
        self.log(f"URL: {url}", 1)
        self.log(f"{'='*70}", 0)

        try:
            response = await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)
            self.log(f"Response: {response.status if response else 'N/A'}", 1)

            # Wait for JS to render
            await asyncio.sleep(wait_time)

            html = await self.page.content()
            title = await self.page.title()

            page_data = {
                "url": url,
                "name": name,
                "title": title,
                "html_size": len(html),
                "status": response.status if response else None,
                "cloudflare_blocked": "Just a moment" in html or "Cloudflare" in html,
            }

            # Get text content
            try:
                text = await self.page.inner_text('body')
                page_data["text_preview"] = text[:200] if text else None
            except:
                pass

            # Check what content we got
            if "Just a moment" in html:
                self.log("⚠️  Cloudflare verification page detected", 1)
                page_data["status_note"] = "Blocked by Cloudflare"
            elif "bot" in html.lower():
                self.log("⚠️  Bot detection page", 1)
                page_data["status_note"] = "Bot detection active"
            else:
                self.log("✅ Real content loaded", 1)
                page_data["status_note"] = "Content accessible"

            self.discoveries["pages_explored"].append(page_data)
            return page_data

        except Exception as e:
            self.log(f"❌ Error: {e}", 1)
            return None

    async def try_different_approaches(self):
        """Try multiple approaches to access Medium"""
        self.log("\n🔄 TRYING DIFFERENT APPROACHES", 0)

        approaches = [
            ("https://medium.com/", "Medium Homepage (direct)", 2),
            ("https://medium.com/browse", "Medium Browse (direct)", 2),
            ("https://medium.com/trending", "Medium Trending", 2),
            ("https://medium.com/@medium/lists", "Medium Lists", 2),
        ]

        for url, name, wait in approaches:
            await self.explore_page(url, name, wait)
            html = await self.page.content()

            if "Just a moment" not in html and len(html) > 50000:
                self.log("✅ Found working approach!", 1)
                return True

        return False

    async def check_cloudflare_challenge(self):
        """Check if Cloudflare challenge can be bypassed"""
        self.log("\n🔐 CHECKING CLOUDFLARE DETECTION", 0)

        # Try waiting longer for Cloudflare to pass
        self.log("Attempting: Extended wait (10 seconds)...", 1)
        await asyncio.sleep(10)

        html = await self.page.content()
        if "Just a moment" not in html:
            self.log("✅ Cloudflare challenge passed!", 1)
            return True
        else:
            self.log("❌ Still blocked after 10 second wait", 1)
            return False

    async def analyze_if_accessible(self):
        """Analyze what content is accessible"""
        html = await self.page.content()

        if "Just a moment" in html:
            self.log("\n⚠️  MEDIUM IS CLOUDFLARE-PROTECTED", 0)
            self.log("Status: Cannot access real content in headless mode", 1)
            self.discoveries["challenges"].append({
                "type": "Cloudflare Protection",
                "severity": "BLOCKING",
                "description": "Medium uses Cloudflare to block automated access",
                "workarounds": [
                    "Use authenticated session (cookies)",
                    "Use browser-based headers with full user-agent",
                    "Try residential IP vs datacenter IP",
                    "Use human-like interaction patterns"
                ]
            })
            return False
        else:
            self.log("\n✅ MEDIUM CONTENT ACCESSIBLE", 0)
            return True

    async def discover_structure(self):
        """If accessible, discover structure"""
        html = await self.page.content()

        if len(html) < 30000:  # Likely just the Cloudflare page
            self.log("\n❌ Page too small - likely still blocked", 1)
            return False

        self.log("\n📊 DISCOVERING STRUCTURE", 0)

        # Look for article elements
        articles = await self.page.query_selector_all("article")
        self.log(f"Found {len(articles)} article elements", 1)

        # Look for buttons
        buttons = await self.page.query_selector_all("button")
        self.log(f"Found {len(buttons)} buttons", 1)

        # Look for links
        links = await self.page.query_selector_all("a[href*='/']")
        self.log(f"Found {len(links)} links", 1)

        self.discoveries["features_identified"].append({
            "articles": len(articles),
            "buttons": len(buttons),
            "links": len(links)
        })

        return len(articles) > 0 or len(buttons) > 0

    async def create_report(self):
        """Create discovery report"""
        self.log("\n" + "="*70, 0)
        self.log("📊 DISCOVERY REPORT", 0)
        self.log("="*70, 0)

        print(json.dumps(self.discoveries, indent=2))

        # Save to file
        with open('/tmp/medium_discovery_stealth.json', 'w') as f:
            json.dump(self.discoveries, f, indent=2)

        print("\n✅ Report saved to: /tmp/medium_discovery_stealth.json")

async def main():
    """Main discovery flow"""
    explorer = MediumStealthExplorer()
    await explorer.start()

    try:
        print("\n" + "█"*70)
        print("STEALTH-MODE DISCOVERY: MEDIUM")
        print("Testing self-learning on Cloudflare-protected site")
        print("Stealth Measures: User agent + Headers + Anti-detection")
        print("█"*70)

        # Try different approaches
        success = await explorer.try_different_approaches()

        # If still blocked, try Cloudflare bypass
        if not success:
            print("\n⚠️  Initial approaches blocked, trying Cloudflare bypass...")
            success = await explorer.check_cloudflare_challenge()

        # Analyze current state
        is_accessible = await explorer.analyze_if_accessible()

        # If accessible, discover structure
        if is_accessible:
            await explorer.discover_structure()

        # Create report
        await explorer.create_report()

        # Summary
        print("\n" + "="*70)
        if is_accessible:
            print("✅ DISCOVERY SUCCESSFUL - Medium structure mapped")
        else:
            print("⚠️  DISCOVERY BLOCKED - Medium protected by Cloudflare")
            print("\nSolution: Use authenticated session or work with another platform")
        print("="*70)

    finally:
        await explorer.stop()

if __name__ == "__main__":
    asyncio.run(main())
