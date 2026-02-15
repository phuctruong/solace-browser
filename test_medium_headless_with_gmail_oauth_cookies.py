#!/usr/bin/env python3
"""
Test Medium Headless with Gmail OAuth Cookies
==============================================
Use the cf_clearance and session cookies from Gmail OAuth login
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumHeadlessGmailOAuthTest:
    def __init__(self, cookies_file):
        self.browser = None
        self.context = None
        self.page = None
        self.cookies_file = cookies_file
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "mode": "headless",
            "method": "gmail_oauth_cookies",
            "page_loaded": False,
            "challenge_detected": False,
            "content_found": False,
            "cf_clearance_verified": False,
            "success": False
        }

    async def start(self):
        """Start headless browser"""
        print("🖥️  Starting HEADLESS browser...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        print("✅ Headless browser started\n")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def run_test(self):
        """Run the test"""
        print("=" * 70)
        print("MEDIUM HEADLESS TEST - Gmail OAuth Cookies")
        print("Testing if cf_clearance from Gmail OAuth works in headless")
        print("=" * 70)

        # Load cookies from Gmail OAuth login
        print("\n📋 Loading cookies from Gmail OAuth login...")
        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)

            print(f"✅ Loaded {len(cookies)} cookies")

            # Add to browser context
            await self.context.add_cookies(cookies)
            print("✅ Cookies added to headless browser context")

            # Verify cf_clearance
            cf_cookie = [c for c in cookies if c['name'] == 'cf_clearance']
            if cf_cookie:
                print("\n🔑 CF_CLEARANCE verified:")
                print(f"   Value: {cf_cookie[0]['value'][:50]}...")
                print(f"   Expires: {cf_cookie[0]['expires']}")
                self.results["cf_clearance_verified"] = True

        except Exception as e:
            print(f"❌ Error loading cookies: {e}")
            return

        # Navigate to Medium
        print("\n🌐 Navigating to Medium in headless mode...")
        try:
            response = await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
            print(f"✅ Page loaded (status: {response.status})")
            self.results["page_loaded"] = True

            # Take screenshot
            await self.page.screenshot(path="/tmp/medium_headless_gmail_oauth_result.png")
            print("📸 Screenshot: /tmp/medium_headless_gmail_oauth_result.png")

        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return

        await asyncio.sleep(2)

        # Check for challenge
        print("\n🔍 Checking for Cloudflare challenge...")
        html = await self.page.content()
        content_size = len(html)
        print(f"   Page size: {content_size} bytes")

        if "Just a moment" in html:
            print("   ⚠️  'Just a moment' (Cloudflare challenge) detected")
            self.results["challenge_detected"] = True
        else:
            print("   ✅ No challenge detected")

        if len(html) > 50000:
            print("   ✅ Substantial content loaded (> 50KB)")
            self.results["content_found"] = True
        else:
            print("   ⚠️  Limited content (< 50KB)")

        # Check for Medium-specific content
        print("\n🔍 Checking for Medium content...")
        indicators = [
            ("Feed", "feed" in html.lower()),
            ("Articles", "<article" in html),
            ("Medium UI", "medium" in html.lower()),
            ("Home page", "home" in html.lower()),
        ]

        found = 0
        for name, result in indicators:
            if result:
                print(f"   ✅ {name}")
                found += 1
            else:
                print(f"   ❌ {name}")

        # Determine success
        if (not self.results["challenge_detected"] and
            self.results["content_found"] and
            found >= 2):
            print("\n🎉 SUCCESS!")
            print("   Gmail OAuth cookies work in headless mode!")
            print("   Cloudflare challenge was bypassed!")
            self.results["success"] = True
        else:
            print("\n⚠️  Partial success or limitations detected")

        # Save results
        with open('/tmp/medium_headless_gmail_oauth_results.json', 'w') as f:
            json.dump(self.results, f, indent=2)

        # Print final summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Method: Gmail OAuth Cookies")
        print(f"Page Loaded: {self.results['page_loaded']}")
        print(f"Challenge Bypassed: {not self.results['challenge_detected']}")
        print(f"Content Found: {self.results['content_found']}")
        print(f"CF_Clearance Verified: {self.results['cf_clearance_verified']}")
        print(f"SUCCESS: {self.results['success']}")

        return self.results["success"]

async def main():
    cookies_file = '/tmp/medium_login_cookies.json'

    tester = MediumHeadlessGmailOAuthTest(cookies_file)
    await tester.start()

    try:
        success = await tester.run_test()
        if success:
            print("\n✨ BREAKTHROUGH! Medium is accessible in headless with Gmail OAuth!")
        else:
            print("\n⚠️  Gmail OAuth cookies alone may not be enough")
    finally:
        await tester.stop()

if __name__ == "__main__":
    asyncio.run(main())
