#!/usr/bin/env python3
"""
Test Medium with Persistent Browser Context
=============================================
Strategy: Keep the same browser context from headed login to headless use
This maintains browser fingerprint and session state across transitions
"""
import asyncio
import json
from playwright.async_api import async_playwright
from datetime import datetime

class MediumPersistentContextTest:
    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "headed_phase": {"success": False, "details": ""},
            "headless_phase": {"success": False, "details": ""},
            "overall_success": False
        }

    async def start_headed(self):
        """Start in headed mode"""
        print("🖥️  Starting HEADED browser...")
        p = await async_playwright().start()
        self.browser = await p.chromium.launch(headless=False)  # VISIBLE
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        print("✅ Headed browser started\n")

    async def headed_phase_login(self):
        """Phase 1: Login in headed mode"""
        print("=" * 70)
        print("PHASE 1: HEADED MODE - Get valid session")
        print("=" * 70)

        try:
            print("\n📱 Navigating to Medium...")
            await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)

            await asyncio.sleep(3)

            # Check what we got
            html = await self.page.content()

            if "Just a moment" not in html:
                print("✅ Medium loaded without challenge!")
                self.results["headed_phase"]["success"] = True
                self.results["headed_phase"]["details"] = "Loaded without challenge"
                return True
            else:
                print("⚠️  Cloudflare challenge present in headed mode")
                print("   (This is unusual - headed mode usually bypasses this)")
                self.results["headed_phase"]["success"] = False
                self.results["headed_phase"]["details"] = "Challenge appeared in headed mode"
                return False

        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            self.results["headed_phase"]["success"] = False
            self.results["headed_phase"]["details"] = str(e)[:100]
            return False

    async def transition_to_headless(self):
        """Phase 2: Transition same context to headless"""
        print("\n" + "=" * 70)
        print("PHASE 2: TRANSITION TO HEADLESS (same context)")
        print("=" * 70)

        try:
            print("\n⏸️  Pausing headed browser...")
            print("   (Keeping context active)")

            # Save current context state
            cookies = await self.context.cookies()
            print(f"\n💾 Current context has {len(cookies)} cookies")

            # Check current content
            html = await self.page.content()
            print(f"   Content size: {len(html)} bytes")

            # Take screenshot of current state
            await self.page.screenshot(path="/tmp/medium_before_transition.png")
            print("   Screenshot saved")

            return True

        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            return False

    async def verify_headless_access(self):
        """Phase 3: Test access while keeping context persistent"""
        print("\n" + "=" * 70)
        print("PHASE 3: VERIFY ACCESS (same context persists)")
        print("=" * 70)

        try:
            print("\n🔄 Testing if context state persists...")

            # Try to navigate to a different Medium URL with same context
            print("\n📄 Navigate to Medium feed (same context)...")

            # Use reload to test if we can still access
            await self.page.reload(wait_until='domcontentloaded', timeout=10000)

            await asyncio.sleep(2)

            # Check if we still have access
            html = await self.page.content()

            if "Just a moment" in html:
                print("⚠️  Challenge re-appeared after reload")
                self.results["headless_phase"]["success"] = False
                self.results["headless_phase"]["details"] = "Challenge re-appeared on reload"
                return False
            else:
                print("✅ Content still accessible after reload!")
                self.results["headless_phase"]["success"] = True
                self.results["headless_phase"]["details"] = "Persistent context maintains access"
                return True

        except Exception as e:
            print(f"❌ Error: {str(e)[:100]}")
            self.results["headless_phase"]["success"] = False
            self.results["headless_phase"]["details"] = str(e)[:100]
            return False

    async def test_new_headless_context(self):
        """Test if a NEW headless browser can use the cookies"""
        print("\n" + "=" * 70)
        print("PHASE 4: TEST NEW HEADLESS BROWSER (different process)")
        print("=" * 70)

        try:
            # Close current browser but save cookies first
            cookies = await self.context.cookies()
            await self.context.close()
            await self.browser.close()

            print("\n💾 Saved cookies from headed session")

            # Start new headless browser
            print("\n🖥️  Starting NEW headless browser (separate process)...")
            p = await async_playwright().start()
            headless_browser = await p.chromium.launch(headless=True)
            headless_context = await headless_browser.new_context()

            # Add saved cookies
            await headless_context.add_cookies(cookies)
            print(f"✅ Added {len(cookies)} cookies to new headless context")

            # Try to access Medium
            headless_page = await headless_context.new_page()
            print("\n🌐 Navigate to Medium with saved cookies...")

            await headless_page.goto("https://medium.com", wait_until='domcontentloaded', timeout=10000)

            await asyncio.sleep(2)

            # Check result
            html = await headless_page.content()
            await headless_page.screenshot(path="/tmp/medium_new_headless_result.png")

            if "Just a moment" in html:
                print("❌ NEW headless browser still blocked by Cloudflare")
                self.results["headless_phase"]["success"] = False
                self.results["headless_phase"]["details"] = "New headless process still blocked"
                result = False
            else:
                print("✅ NEW headless browser can access Medium!")
                self.results["headless_phase"]["success"] = True
                self.results["headless_phase"]["details"] = "New headless process successful with cookies"
                result = True

            # Cleanup
            await headless_context.close()
            await headless_browser.close()

            return result

        except Exception as e:
            print(f"⚠️  Error: {str(e)[:100]}")
            self.results["headless_phase"]["success"] = False
            self.results["headless_phase"]["details"] = f"Error: {str(e)[:100]}"
            return False

    async def run_test(self):
        """Run the complete test"""
        print("\n" + "█" * 70)
        print("MEDIUM PERSISTENT CONTEXT TEST")
        print("Testing different strategies for headless access")
        print("█" * 70)

        try:
            # Phase 1: Headed mode
            await self.start_headed()
            headed_ok = await self.headed_phase_login()

            if headed_ok:
                # Phase 2: Transition
                await self.transition_to_headless()

                # Phase 3: Verify
                await self.verify_headless_access()

            # Phase 4: Test new headless browser
            new_headless_ok = await self.test_new_headless_context()

            # Determine overall success
            if headed_ok or new_headless_ok:
                self.results["overall_success"] = True

        finally:
            # Save results
            with open('/tmp/medium_persistent_context_results.json', 'w') as f:
                json.dump(self.results, f, indent=2)

            print("\n" + "=" * 70)
            print("TEST COMPLETE")
            print("=" * 70)
            print(f"\n📊 Results: /tmp/medium_persistent_context_results.json")
            print(f"\n📈 Summary:")
            print(f"   Phase 1 (Headed): {self.results['headed_phase']['success']}")
            print(f"   Phase 3 (Persistent): {self.results['headless_phase']['success']}")
            print(f"   Overall Success: {self.results['overall_success']}")

async def main():
    tester = MediumPersistentContextTest()

    try:
        await tester.run_test()
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Test failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
