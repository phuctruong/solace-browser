#!/usr/bin/env python3

"""
SOLACE BROWSER - LOGIN AUTOMATION MODULE
Handles authentication for major websites
"""

import asyncio
import configparser
from pathlib import Path
from typing import Dict, Optional
import sys
import os

# Set display
if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':1'

try:
    from playwright.async_api import async_playwright, Page
except ImportError:
    print("ERROR: Playwright not installed")
    sys.exit(1)


class SolaceLoginBot:
    """Automates login to various websites"""

    def __init__(self, credentials_file: str = "credentials.properties"):
        self.credentials_file = credentials_file
        self.credentials = self._load_credentials()
        self.page: Optional[Page] = None
        self.browser = None

    def _load_credentials(self) -> Dict[str, Dict[str, str]]:
        """Load credentials from properties file"""
        config = configparser.ConfigParser()

        if not Path(self.credentials_file).exists():
            print(f"ERROR: {self.credentials_file} not found")
            return {}

        config.read(self.credentials_file)

        credentials = {}
        for section in config.sections():
            credentials[section] = dict(config.items(section))

        return credentials

    async def start_browser(self, headless: bool = False):
        """Start browser instance"""
        print(f"Starting browser (headless={headless})...")
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        context = await self.browser.new_context()
        self.page = await context.new_page()
        print("✓ Browser ready")

    async def stop_browser(self):
        """Stop browser"""
        if self.browser:
            await self.browser.close()
            print("✓ Browser closed")

    async def login_linkedin(self) -> bool:
        """Login to LinkedIn"""
        print("\n" + "=" * 70)
        print("LOGGING IN TO LINKEDIN")
        print("=" * 70)

        creds = self.credentials.get('linkedin', {})
        email = creds.get('email')
        password = creds.get('password')

        if not email or email == 'your-email@example.com':
            print("❌ LinkedIn credentials not configured")
            print("   Edit credentials.properties and set linkedin.email and linkedin.password")
            return False

        try:
            print(f"Navigate to LinkedIn...")
            await self.page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
            await asyncio.sleep(2)

            print(f"Entering email: {email}")
            await self.page.fill("input#username", email)
            await asyncio.sleep(1)

            print(f"Entering password...")
            await self.page.fill("input#password", password)
            await asyncio.sleep(1)

            print(f"Clicking login button...")
            await self.page.click("button[type='submit']")
            await asyncio.sleep(5)

            # Check if login successful
            if "linkedin.com/feed" in self.page.url or "welcome" in self.page.url.lower():
                print("✅ LinkedIn login SUCCESSFUL!")
                await self.page.screenshot(path="artifacts/login-linkedin-success.png")
                return True
            else:
                print(f"⚠️  Login may have issues. Current URL: {self.page.url}")
                await self.page.screenshot(path="artifacts/login-linkedin-attempt.png")
                return False

        except Exception as e:
            print(f"❌ LinkedIn login failed: {e}")
            await self.page.screenshot(path="artifacts/login-linkedin-error.png")
            return False

    async def login_gmail(self) -> bool:
        """Login to Gmail"""
        print("\n" + "=" * 70)
        print("LOGGING IN TO GMAIL")
        print("=" * 70)

        creds = self.credentials.get('gmail', {})
        email = creds.get('email')
        password = creds.get('password')

        if not email or email == 'your-email@gmail.com':
            print("❌ Gmail credentials not configured")
            print("   Edit credentials.properties and set gmail.email and gmail.password")
            return False

        try:
            print(f"Navigate to Gmail...")
            await self.page.goto("https://mail.google.com", wait_until='domcontentloaded')
            await asyncio.sleep(3)

            # Google might redirect to accounts.google.com
            if "accounts.google.com" in self.page.url:
                print(f"Redirected to Google login page")

            print(f"Entering email: {email}")
            email_input = await self.page.query_selector("input[type='email']")
            if email_input:
                await self.page.fill("input[type='email']", email)
                await asyncio.sleep(1)

                print(f"Clicking Next...")
                next_buttons = await self.page.query_selector_all("button")
                for btn in next_buttons:
                    text = await btn.text_content()
                    if "Next" in text:
                        await btn.click()
                        break

                await asyncio.sleep(3)

            print(f"Entering password...")
            password_input = await self.page.query_selector("input[type='password']")
            if password_input:
                await self.page.fill("input[type='password']", password)
                await asyncio.sleep(1)

                print(f"Clicking login...")
                next_buttons = await self.page.query_selector_all("button")
                for btn in next_buttons:
                    text = await btn.text_content()
                    if "Next" in text:
                        await btn.click()
                        break

            await asyncio.sleep(5)

            # Check if login successful
            if "mail.google.com" in self.page.url or "inbox" in self.page.url.lower():
                print("✅ Gmail login SUCCESSFUL!")
                await self.page.screenshot(path="artifacts/login-gmail-success.png")
                return True
            else:
                print(f"⚠️  Login may have issues. Current URL: {self.page.url}")
                await self.page.screenshot(path="artifacts/login-gmail-attempt.png")
                return False

        except Exception as e:
            print(f"❌ Gmail login failed: {e}")
            await self.page.screenshot(path="artifacts/login-gmail-error.png")
            return False

    async def login_github(self) -> bool:
        """Login to GitHub"""
        print("\n" + "=" * 70)
        print("LOGGING IN TO GITHUB")
        print("=" * 70)

        creds = self.credentials.get('github', {})
        username = creds.get('username')
        password = creds.get('password')

        if not username or username == 'your-username':
            print("❌ GitHub credentials not configured")
            print("   Edit credentials.properties and set github.username and github.password")
            return False

        try:
            print(f"Navigate to GitHub...")
            await self.page.goto("https://github.com/login", wait_until='domcontentloaded')
            await asyncio.sleep(2)

            print(f"Entering username: {username}")
            await self.page.fill("input#login_field", username)
            await asyncio.sleep(1)

            print(f"Entering password...")
            await self.page.fill("input#password", password)
            await asyncio.sleep(1)

            print(f"Clicking Sign in...")
            await self.page.click("input[type='submit']")
            await asyncio.sleep(5)

            # Check if login successful
            if "github.com" in self.page.url and "login" not in self.page.url.lower():
                print("✅ GitHub login SUCCESSFUL!")
                await self.page.screenshot(path="artifacts/login-github-success.png")
                return True
            else:
                print(f"⚠️  Login may have issues. Current URL: {self.page.url}")
                await self.page.screenshot(path="artifacts/login-github-attempt.png")
                return False

        except Exception as e:
            print(f"❌ GitHub login failed: {e}")
            await self.page.screenshot(path="artifacts/login-github-error.png")
            return False

    async def login_twitter(self) -> bool:
        """Login to Twitter/X"""
        print("\n" + "=" * 70)
        print("LOGGING IN TO TWITTER/X")
        print("=" * 70)

        creds = self.credentials.get('twitter', {})
        email = creds.get('email')
        password = creds.get('password')

        if not email or email == 'your-email@example.com':
            print("❌ Twitter credentials not configured")
            print("   Edit credentials.properties and set twitter.email and twitter.password")
            return False

        try:
            print(f"Navigate to Twitter...")
            await self.page.goto("https://twitter.com/login", wait_until='domcontentloaded')
            await asyncio.sleep(2)

            print(f"Entering email: {email}")
            email_inputs = await self.page.query_selector_all("input")
            if email_inputs:
                await email_inputs[0].fill(email)
                await asyncio.sleep(1)

            print(f"Clicking Next...")
            next_buttons = await self.page.query_selector_all("button")
            for btn in next_buttons:
                text = await btn.text_content()
                if "Next" in text:
                    await btn.click()
                    break

            await asyncio.sleep(2)

            print(f"Entering password...")
            password_inputs = await self.page.query_selector_all("input[type='password']")
            if password_inputs:
                await password_inputs[0].fill(password)
                await asyncio.sleep(1)

            print(f"Clicking login...")
            login_buttons = await self.page.query_selector_all("button")
            for btn in login_buttons:
                text = await btn.text_content()
                if "Log in" in text:
                    await btn.click()
                    break

            await asyncio.sleep(5)

            # Check if login successful
            if "twitter.com/home" in self.page.url or "x.com/home" in self.page.url:
                print("✅ Twitter login SUCCESSFUL!")
                await self.page.screenshot(path="artifacts/login-twitter-success.png")
                return True
            else:
                print(f"⚠️  Login may have issues. Current URL: {self.page.url}")
                await self.page.screenshot(path="artifacts/login-twitter-attempt.png")
                return False

        except Exception as e:
            print(f"❌ Twitter login failed: {e}")
            await self.page.screenshot(path="artifacts/login-twitter-error.png")
            return False


async def main():
    """Run login automation demo"""
    print("\n")
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  SOLACE BROWSER - LOGIN AUTOMATION DEMO".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "═" * 68 + "╝")
    print("")

    bot = SolaceLoginBot()

    # Check if credentials are configured
    if not bot.credentials:
        print("⚠️  No credentials found!")
        print("")
        print("Setup Instructions:")
        print("1. Edit credentials.properties")
        print("2. Add your email/username and password for each site")
        print("3. Save the file")
        print("4. Run this script again")
        print("")
        return

    # Start browser with visible window
    await bot.start_browser(headless=False)

    try:
        results = {}

        # Try each login
        if 'linkedin' in bot.credentials:
            results['LinkedIn'] = await bot.login_linkedin()

        if 'gmail' in bot.credentials:
            results['Gmail'] = await bot.login_gmail()

        if 'github' in bot.credentials:
            results['GitHub'] = await bot.login_github()

        if 'twitter' in bot.credentials:
            results['Twitter'] = await bot.login_twitter()

        # Summary
        print("\n" + "=" * 70)
        print("LOGIN AUTOMATION RESULTS")
        print("=" * 70)

        for site, success in results.items():
            status = "✅ SUCCESS" if success else "❌ FAILED"
            print(f"{site:15} {status}")

        print("=" * 70)
        print("\nScreenshots saved to artifacts/login-*.png")

    finally:
        await bot.stop_browser()


if __name__ == '__main__':
    asyncio.run(main())
