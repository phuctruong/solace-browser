#!/usr/bin/env python3
"""
Test Medium OAuth with CLEAN BROWSER (No extensions, no session persistence)
This will help us see the actual Cloudflare challenge without interference
"""
import asyncio
import configparser
from playwright.async_api import async_playwright
from datetime import datetime

class CleanMediumTest:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.credentials = {}

    def _log(self, msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {msg}")

    def load_credentials(self):
        config = configparser.ConfigParser()
        config.read('credentials.properties')
        if 'gmail' in config:
            self.credentials = dict(config['gmail'])
            self._log(f"✅ Loaded: {self.credentials.get('email')}")
            return True
        return False

    async def run(self):
        """Run the test"""
        self._log("\n" + "="*70)
        self._log("MEDIUM OAUTH - CLEAN BROWSER TEST")
        self._log("="*70)

        if not self.load_credentials():
            return

        p = await async_playwright().start()

        try:
            # Start completely clean browser - NO extensions, NO stealth mode, NO saved session
            self.browser = await p.chromium.launch(headless=False)
            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            self._log("\n✅ Clean browser started (no extensions, no stealth)")

            # Step 1: Navigate to Medium
            self._log("\n📍 Navigate to medium.com")
            await self.page.goto("https://medium.com", wait_until='domcontentloaded')
            self._log("   ✓ Homepage loaded")

            # Step 2: Click Sign in
            self._log("\n📍 Click 'Sign in'")
            await self.page.click("a:has-text('Sign in')")
            await self.page.wait_for_timeout(2000)

            # Step 3: Click Google sign-in
            self._log("\n📍 Click 'Sign in with Google'")
            await self.page.click("a:has-text('Sign in with Google')")
            await self.page.wait_for_timeout(5000)

            # Check current state
            url = self.page.url
            title = await self.page.title()

            self._log(f"\n📊 Current State:")
            self._log(f"   URL: {url}")
            self._log(f"   Title: {title}")

            # Take screenshot
            await self.page.screenshot(path="/tmp/clean_browser_current.png")
            self._log(f"   Screenshot: /tmp/clean_browser_current.png")

            # Check for "Just a moment" (Cloudflare challenge)
            html = await self.page.content()
            if "just a moment" in html.lower():
                self._log("\n🔴 CLOUDFLARE CHALLENGE DETECTED")
                page_text = await self.page.inner_text('body')
                self._log(f"\n📄 Page text preview:")
                for line in page_text.split('\n')[:10]:
                    if line.strip():
                        self._log(f"   {line[:70]}")

            # Wait for user to interact or for challenge to pass
            self._log("\n⏳ Waiting 30 seconds... (you can interact with browser)")
            for i in range(30):
                await self.page.wait_for_timeout(1000)
                url = self.page.url
                title = await self.page.title()

                if "accounts.google" in url:
                    self._log(f"   ✓ Redirected to Google ({i}s)")
                    break
                elif "medium" in url and "just" not in title.lower():
                    self._log(f"   ✓ Past challenge ({i}s)")
                    break

                if i % 5 == 0 and i > 0:
                    self._log(f"   {i}s...")

            # Final screenshot
            await self.page.screenshot(path="/tmp/clean_browser_final.png")
            self._log(f"\n📸 Final screenshot: /tmp/clean_browser_final.png")

            final_url = self.page.url
            final_title = await self.page.title()
            self._log(f"\n📊 Final State:")
            self._log(f"   URL: {final_url}")
            self._log(f"   Title: {final_title}")

        except Exception as e:
            self._log(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()

async def main():
    test = CleanMediumTest()
    await test.run()

if __name__ == "__main__":
    asyncio.run(main())
