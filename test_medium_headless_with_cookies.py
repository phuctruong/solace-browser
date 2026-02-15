#!/usr/bin/env python3
"""
Test Medium in HEADLESS mode with cf_clearance Cookie
======================================================
Goal: Verify that pre-authenticated cf_clearance cookie allows headless access
Expected: Cloudflare should skip challenge because cf_clearance is valid
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumHeadlessCookieTest:
    def __init__(self, cookies_file):
        self.browser = None
        self.context = None
        self.page = None
        self.cookies_file = cookies_file
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "mode": "headless",
            "cookies_loaded": False,
            "page_loaded": False,
            "challenge_detected": False,
            "content_found": False,
            "success": False,
            "findings": []
        }

    async def start(self):
        """Start headless browser"""
        print("🖥️  Starting HEADLESS browser (NO UI)...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=True)  # HEADLESS
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        print("✅ Headless browser started\n")

    async def stop(self):
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def load_cookies(self):
        """Load cookies from file"""
        print("=" * 70)
        print("STEP 1: Load cf_clearance Cookie")
        print("=" * 70)

        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)

            print(f"\n📋 Loaded {len(cookies)} cookies from file")

            # Add cookies to browser context
            await self.context.add_cookies(cookies)
            print("✅ Cookies added to browser context")

            # Show key cookie
            cf_cookie = [c for c in cookies if c['name'] == 'cf_clearance']
            if cf_cookie:
                c = cf_cookie[0]
                print(f"\n🔑 Key Cookie Found:")
                print(f"   Name: {c['name']}")
                print(f"   Value: {c['value'][:50]}...")
                print(f"   Expires: {c['expires']} (~28 days)")
                self.results["cookies_loaded"] = True

            return True

        except Exception as e:
            print(f"❌ Error loading cookies: {str(e)}")
            self.results["findings"].append(f"Cookie load error: {str(e)}")
            return False

    async def navigate_medium_headless(self):
        """Navigate to Medium in headless mode with cookies"""
        print("\n" + "=" * 70)
        print("STEP 2: Navigate to Medium (Headless + Cookies)")
        print("=" * 70)

        print("\n🌐 Navigating to medium.com with cf_clearance cookie...")

        try:
            # Navigate
            response = await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
            print(f"✅ Page loaded (status: {response.status})")

            self.results["page_loaded"] = True
            await asyncio.sleep(2)

            return True

        except Exception as e:
            print(f"⚠️  Navigation error: {str(e)[:100]}")
            self.results["findings"].append(f"Navigation error: {str(e)[:100]}")
            return False

    async def check_challenge_status(self):
        """Check if Cloudflare challenge is still present"""
        print("\n" + "=" * 70)
        print("STEP 3: Check for Cloudflare Challenge")
        print("=" * 70)

        try:
            html = await self.page.content()

            # Take screenshot (even in headless, we can see what was rendered)
            screenshot_path = "/tmp/medium_headless_with_cookies.png"
            await self.page.screenshot(path=screenshot_path)
            print(f"\n📸 Screenshot: {screenshot_path}")

            # Check for challenge indicators
            challenge_indicators = [
                ("Just a moment", "Just a moment" in html),
                ("challenge", "challenge" in html.lower()),
                ("Turnstile", "turnstile" in html.lower()),
                ("cf-challenge", "cf-challenge" in html.lower()),
            ]

            print("\n🔍 Checking for Cloudflare challenge...")
            challenge_found = False
            for indicator_name, found in challenge_indicators:
                if found:
                    print(f"  ⚠️  {indicator_name}")
                    challenge_found = True
                else:
                    print(f"  ✓ No {indicator_name}")

            if challenge_found:
                print("\n⚠️  CLOUDFLARE CHALLENGE STILL PRESENT")
                self.results["challenge_detected"] = True
                self.results["findings"].append("Cloudflare challenge still blocks access")
                return False
            else:
                print("\n✅ NO CLOUDFLARE CHALLENGE DETECTED!")
                self.results["findings"].append("Cloudflare challenge bypassed!")
                return True

        except Exception as e:
            print(f"❌ Error checking challenge: {str(e)}")
            return False

    async def check_content(self):
        """Check if we can access Medium content"""
        print("\n" + "=" * 70)
        print("STEP 4: Check for Medium Content")
        print("=" * 70)

        try:
            html = await self.page.content()

            print("\n🔍 Looking for Medium content...")

            # Check for various content indicators
            content_indicators = [
                ("Article elements", "<article" in html),
                ("Medium UI", "medium" in html.lower()),
                ("Stories", "stories" in html.lower()),
                ("Navigation", "nav" in html.lower()),
                ("Feed/Homepage", "feed" in html.lower() or "home" in html.lower()),
            ]

            content_found_count = 0
            for indicator_name, found in content_indicators:
                if found:
                    print(f"  ✓ {indicator_name}")
                    content_found_count += 1
                else:
                    print(f"  ✗ {indicator_name}")

            if content_found_count >= 2:
                print(f"\n✅ MEDIUM CONTENT ACCESSIBLE ({content_found_count}/5 indicators)")
                self.results["content_found"] = True
                return True
            else:
                print(f"\n⚠️  Limited content found ({content_found_count}/5 indicators)")
                return False

        except Exception as e:
            print(f"❌ Error checking content: {str(e)}")
            return False

    async def verify_no_cloudflare_scripts(self):
        """Verify that Cloudflare challenge scripts didn't load"""
        print("\n" + "=" * 70)
        print("STEP 5: Verify Cloudflare Didn't Load Challenge Scripts")
        print("=" * 70)

        try:
            # Get all scripts that loaded
            scripts = await self.page.evaluate("""
                () => {
                    const scripts = Array.from(document.querySelectorAll('script'));
                    return scripts.map(s => s.src || s.textContent.substring(0, 50)).filter(s => s);
                }
            """)

            cf_scripts = [s for s in scripts if 'cloudflare' in s.lower() or 'challenge' in s.lower()]

            print(f"\n📊 Total scripts loaded: {len(scripts)}")
            print(f"   Cloudflare challenge scripts: {len(cf_scripts)}")

            if cf_scripts:
                print("\n⚠️  Cloudflare scripts found:")
                for script in cf_scripts[:5]:
                    print(f"   • {script[:60]}...")
                self.results["findings"].append(f"Cloudflare scripts still loaded: {len(cf_scripts)}")
            else:
                print("\n✅ No Cloudflare challenge scripts loaded!")
                self.results["findings"].append("Cloudflare challenge scripts not needed")

            return len(cf_scripts) == 0

        except Exception as e:
            print(f"⚠️  Could not verify scripts: {str(e)[:100]}")
            return None

    async def run_test(self):
        """Run the complete headless test"""
        print("\n" + "█" * 70)
        print("MEDIUM HEADLESS TEST WITH cf_clearance COOKIE")
        print("Testing if pre-authenticated cookie allows headless access")
        print("█" * 70)

        try:
            # Step 1: Load cookies
            if not await self.load_cookies():
                print("\n❌ Failed to load cookies")
                return

            # Step 2: Navigate with cookies
            if not await self.navigate_medium_headless():
                print("\n❌ Failed to navigate")
                return

            # Step 3: Check for challenge
            challenge_bypassed = await self.check_challenge_status()

            # Step 4: Check content
            content_accessible = await self.check_content()

            # Step 5: Verify no challenge scripts
            await self.verify_no_cloudflare_scripts()

            # Determine overall success
            if challenge_bypassed and content_accessible:
                self.results["success"] = True
                print("\n" + "=" * 70)
                print("🎉 SUCCESS!")
                print("=" * 70)
                print("\n✅ Headless access to Medium SUCCESSFUL with cf_clearance cookie!")
                print("✅ Cloudflare challenge was completely bypassed!")
                print("✅ Medium content loaded and accessible!")

        finally:
            # Save results
            with open('/tmp/medium_headless_cookie_results.json', 'w') as f:
                json.dump(self.results, f, indent=2)

            print("\n" + "=" * 70)
            print("TEST COMPLETE")
            print("=" * 70)
            print(f"\n📊 Results: /tmp/medium_headless_cookie_results.json")
            print(f"\n📈 Summary:")
            print(f"   Cookies Loaded: {self.results['cookies_loaded']}")
            print(f"   Page Loaded: {self.results['page_loaded']}")
            print(f"   Challenge Bypassed: {not self.results['challenge_detected']}")
            print(f"   Content Found: {self.results['content_found']}")
            print(f"   OVERALL SUCCESS: {self.results['success']}")

            print(f"\n💡 Key Findings:")
            for finding in self.results["findings"]:
                print(f"   • {finding}")

async def main():
    # Use cookies from the headed test
    cookies_file = '/tmp/medium_cookies_after_captcha.json'

    tester = MediumHeadlessCookieTest(cookies_file)
    await tester.start()

    try:
        await tester.run_test()
    finally:
        await tester.stop()

if __name__ == "__main__":
    asyncio.run(main())
