#!/usr/bin/env python3
"""
Debug Test: Medium Login with CAPTCHA Handler Extension (WITH CONSOLE LOGGING)
===============================================================================
Improved version that captures browser console messages and errors
"""
import asyncio
import json
import os
import sys
import configparser
from playwright.async_api import async_playwright
from datetime import datetime
import tempfile

class MediumCaptchaHandlerDebugTest:
    def __init__(self, extension_path):
        self.browser = None
        self.context = None
        self.page = None
        self.extension_path = extension_path
        self.credentials = {}
        self.console_logs = []
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "extension_loaded": False,
            "handler_active": False,
            "captcha_detected": False,
            "captcha_auto_clicked": False,
            "login_successful": False,
            "medium_accessible": False,
            "console_logs": [],
            "handler_summary": None,
            "log": []
        }

    def _log(self, msg):
        """Log message"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        self.results["log"].append(log_msg)

    def load_credentials(self):
        """Load credentials from properties file"""
        self._log("Loading credentials from credentials.properties...")
        config = configparser.ConfigParser()
        config.read('credentials.properties')

        if 'gmail' in config:
            self.credentials = dict(config['gmail'])
            self._log(f"✅ Credentials loaded: {self.credentials.get('email')}")
            return True
        else:
            self._log("❌ Gmail credentials not found in credentials.properties")
            return False

    async def start_browser_with_extension(self):
        """Start Playwright with extension loaded"""
        self._log("Starting browser with CAPTCHA handler extension...")

        p = await async_playwright().start()

        try:
            # Launch with extension
            self.browser = await p.chromium.launch(
                headless=False,  # Must be visible
                args=[
                    f'--load-extension={self.extension_path}',
                    f'--disable-extensions-except={self.extension_path}',
                    '--no-sandbox',
                ]
            )

            self.context = await self.browser.new_context()
            self.page = await self.context.new_page()

            # CAPTURE CONSOLE MESSAGES (CRITICAL FOR DEBUGGING)
            def on_console(msg):
                console_entry = {
                    "type": msg.type,
                    "text": msg.text,
                    "location": msg.location,
                    "timestamp": datetime.now().isoformat()
                }
                self.console_logs.append(console_entry)
                self.results["console_logs"].append(console_entry)

                # Log all messages, especially errors
                if msg.type in ['error', 'warning', 'log']:
                    self._log(f"🔹 [CONSOLE {msg.type.upper()}] {msg.text}")

            self.page.on("console", on_console)

            self._log("✅ Browser started with extension")
            self.results["extension_loaded"] = True

            return True
        except Exception as e:
            self._log(f"❌ Error starting browser: {str(e)[:100]}")
            return False

    async def check_handler_status(self):
        """Check if CAPTCHA handler is active"""
        try:
            status = await self.page.evaluate("""
                () => {
                    // Debug: Log what we're checking
                    if (!window.solace_captcha) {
                        console.log('[DEBUG] window.solace_captcha is NOT available');
                        console.log('[DEBUG] window keys:', Object.keys(window).filter(k => k.includes('solace') || k.includes('captcha') || k.includes('CAPTCHA')));
                        return { available: false, debug: 'window.solace_captcha not found' };
                    }

                    console.log('[DEBUG] window.solace_captcha IS available');

                    return {
                        available: true,
                        monitoring: window.solace_captcha.isMonitoring(),
                        summary: window.solace_captcha.getSummary(),
                        logs: window.solace_captcha.getLogs().slice(-5)
                    };
                }
            """)

            if status.get("available"):
                self._log("✅ CAPTCHA handler is active and monitoring")
                self.results["handler_active"] = True

                summary = status.get("summary", {})
                self._log(f"   Detected CAPTCHAs: {summary.get('detected_count', 0)}")
                self._log(f"   Auto-clicked: {summary.get('auto_clicked_count', 0)}")

                logs = status.get("logs", [])
                if logs:
                    self._log("   Recent handler logs:")
                    for log in logs:
                        self._log(f"     {log}")

                return True
            else:
                debug_info = status.get("debug", "Unknown")
                self._log(f"⚠️  CAPTCHA handler not detected: {debug_info}")
                return False

        except Exception as e:
            self._log(f"⚠️  Error checking handler: {str(e)[:200]}")
            import traceback
            self._log(f"   Traceback: {traceback.format_exc()[:200]}")
            return False

    async def take_screenshot(self, name):
        """Take and save screenshot"""
        path = f"/tmp/medium_test_{name}_{datetime.now().strftime('%H%M%S')}.png"
        await self.page.screenshot(path=path)
        self._log(f"📸 Screenshot: {path}")
        return path

    async def run_test(self):
        """Run the complete test"""
        self._log("\n" + "=" * 70)
        self._log("MEDIUM LOGIN WITH CAPTCHA HANDLER - DEBUG MODE")
        self._log("=" * 70)

        # Load credentials
        if not self.load_credentials():
            return False

        # Start browser
        if not await self.start_browser_with_extension():
            return False

        # Wait for extension to load
        self._log("⏳ Waiting for extension to fully load...")
        await asyncio.sleep(3)

        # Check handler status
        self._log("\n🔍 Checking CAPTCHA handler status (before navigation)...")
        await self.check_handler_status()

        # Navigate to Medium
        self._log("\n🌐 Navigate to Medium...")
        try:
            await self.page.goto("https://medium.com", wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(2)
            await self.take_screenshot("01_homepage")
            self._log("✅ Medium homepage loaded")
        except Exception as e:
            self._log(f"❌ Error navigating to Medium: {str(e)[:100]}")
            return False

        # Check handler after page load
        self._log("\n📊 Handler status after page load:")
        await self.check_handler_status()

        # Click Sign in
        self._log("\n🔍 Looking for 'Sign in' link...")
        try:
            sign_in = await self.page.query_selector("a:has-text('Sign in')")
            if sign_in:
                await sign_in.click()
                await asyncio.sleep(2)
                await self.take_screenshot("02_signin_modal")
                self._log("✅ Clicked Sign in")
            else:
                self._log("⚠️  Sign in link not found")
        except Exception as e:
            self._log(f"⚠️  Error clicking Sign in: {str(e)[:50]}")

        # Click Google OAuth
        self._log("\n🔍 Looking for 'Sign in with Google' button...")
        try:
            google_btn = await self.page.query_selector("a:has-text('Google')")
            if google_btn:
                await google_btn.click()
                await asyncio.sleep(3)
                await self.take_screenshot("03_google_oauth")
                self._log("✅ Clicked Google OAuth")
            else:
                self._log("⚠️  Google button not found")
        except Exception as e:
            self._log(f"⚠️  Error clicking Google: {str(e)[:50]}")

        # Handler should be monitoring for CAPTCHA during OAuth flow
        self._log("\n📊 Handler status during OAuth...")
        await self.check_handler_status()

        # Wait and fill credentials
        self._log("\n⏳ Waiting for OAuth page...")
        for i in range(15):
            await asyncio.sleep(1)

            # Check handler
            await self.check_handler_status()

            # Check if we're still on OAuth page or past it
            html = await self.page.content()

            if "accounts.google.com" in self.page.url:
                if i % 5 == 0:
                    self._log(f"   Still on Google OAuth page ({i}s)...")

                # Try to fill email if present
                try:
                    email_input = await self.page.query_selector("input[type='email']")
                    if email_input and await email_input.input_value() == "":
                        email = self.credentials.get('email', '')
                        await email_input.fill(email)
                        self._log(f"   Filled email: {email}")

                        next_btn = await self.page.query_selector("button:has-text('Next')")
                        if next_btn:
                            await next_btn.click()
                            self._log("   Clicked Next on email page")
                except:
                    pass

            elif len(html) > 50000:
                self._log(f"   ✅ Significant content loaded ({len(html)} bytes)")
                break

        await self.take_screenshot("04_final_state")

        # Final handler check
        self._log("\n📊 Final CAPTCHA handler status:")
        await self.check_handler_status()

        # Check final state
        html = await self.page.content()
        if "Just a moment" not in html and len(html) > 50000:
            if "medium" in html.lower() or "feed" in html.lower():
                self._log("✅ Medium content accessible!")
                self.results["medium_accessible"] = True
                self.results["login_successful"] = True
            else:
                self._log("⚠️  Large content but unclear if Medium")
        else:
            self._log(f"⚠️  Challenge still present or content small ({len(html)} bytes)")

        return self.results["login_successful"]

    async def close(self):
        """Close browser"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    def print_summary(self):
        """Print test summary"""
        self._log("\n" + "=" * 70)
        self._log("TEST RESULTS")
        self._log("=" * 70)

        results = self.results
        self._log(f"Extension Loaded: {results['extension_loaded']}")
        self._log(f"Handler Active: {results['handler_active']}")
        self._log(f"CAPTCHA Detected: {results['captcha_detected']}")
        self._log(f"CAPTCHA Auto-Clicked: {results['captcha_auto_clicked']}")
        self._log(f"Login Successful: {results['login_successful']}")
        self._log(f"Medium Accessible: {results['medium_accessible']}")

        # Print console logs
        if self.console_logs:
            self._log(f"\n📋 Browser Console Logs ({len(self.console_logs)} messages):")
            for i, log in enumerate(self.console_logs[-20:], 1):  # Last 20
                self._log(f"   {i}. [{log['type']}] {log['text']}")

        if results['handler_summary']:
            self._log(f"\nHandler Summary:")
            for key, value in results['handler_summary'].items():
                self._log(f"  {key}: {value}")

        # Save results
        with open('/tmp/medium_captcha_handler_debug_test.json', 'w') as f:
            json.dump(results, f, indent=2)

        self._log(f"\n💾 Results saved to: /tmp/medium_captcha_handler_debug_test.json")

        if results['login_successful']:
            self._log("\n🎉 SUCCESS! CAPTCHA handler worked!")
        else:
            self._log("\n⚠️  Test inconclusive - check console logs and browser")

async def main():
    extension_path = os.path.abspath(
        'canon/prime-browser/archive/extension'
    )

    if not os.path.exists(extension_path):
        print(f"❌ Extension path not found: {extension_path}")
        sys.exit(1)

    print(f"Extension path: {extension_path}")

    test = MediumCaptchaHandlerDebugTest(extension_path)

    try:
        success = await test.run_test()
        test.print_summary()

        if success:
            sys.exit(0)
        else:
            sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n⏹️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await test.close()

if __name__ == "__main__":
    asyncio.run(main())
