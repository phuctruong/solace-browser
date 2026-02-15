#!/usr/bin/env python3

"""
LinkedIn Complete Workflow - With Proper Login Handling
Behaves like OpenClaw: structured ARIA analysis + human-like interactions
"""

import asyncio
import json
import logging
import configparser
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from dataclasses import asdict

from browser_interactions import format_aria_tree, get_dom_snapshot
from enhanced_browser_interactions import (
    AriaRefMapper,
    PageObserver,
    NetworkMonitor,
    get_llm_snapshot
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('linkedin-complete')


class LinkedInAutomation:
    """Complete LinkedIn automation with login handling"""

    def __init__(self):
        self.browser = None
        self.context = None
        self.page = None
        self.ref_mapper = None
        self.observer = None
        self.network = None
        self.session_file = "artifacts/linkedin_session.json"

        # Load credentials
        self.credentials = self.load_credentials()

    def load_credentials(self):
        """Load credentials from credentials.properties"""
        config = configparser.ConfigParser()
        config.read('credentials.properties')
        return {
            'email': config.get('linkedin', 'email', fallback=''),
            'password': config.get('linkedin', 'password', fallback='')
        }

    async def start(self):
        """Start browser"""
        logger.info("🚀 Starting browser...")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=['--disable-blink-features=AutomationControlled']
        )

        # Try to load session
        context_options = {}
        if Path(self.session_file).exists():
            logger.info(f"📂 Loading saved session: {self.session_file}")
            context_options['storage_state'] = self.session_file

        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

        # Setup monitoring
        self.observer = PageObserver(self.page)
        self.network = NetworkMonitor(self.page)

        logger.info("✅ Browser started")

    async def save_session(self):
        """Save session"""
        if self.context:
            Path(self.session_file).parent.mkdir(parents=True, exist_ok=True)
            await self.context.storage_state(path=self.session_file)
            logger.info(f"💾 Session saved: {self.session_file}")

    async def goto(self, url: str):
        """Navigate to URL"""
        logger.info(f"🌐 Navigating to: {url}")
        await self.page.goto(url, wait_until='networkidle')
        await asyncio.sleep(2)

    async def get_snapshot(self):
        """Get structured snapshot"""
        aria_tree = await format_aria_tree(self.page, limit=500)
        dom_tree = await get_dom_snapshot(self.page, limit=800)

        self.ref_mapper = AriaRefMapper()
        await self.ref_mapper.build_map(self.page, [asdict(node) for node in aria_tree])

        snapshot = await get_llm_snapshot(
            self.page,
            [asdict(node) for node in aria_tree],
            dom_tree,
            self.observer,
            self.network
        )

        return snapshot

    async def login_if_needed(self):
        """Handle login if on login page"""
        current_url = self.page.url
        logger.info(f"📍 Current URL: {current_url}")

        # Check if on login page
        if '/login' in current_url or '/uas/login' in current_url or 'authwall' in current_url:
            logger.info("🔐 Login page detected - logging in...")

            # Get snapshot to find form fields
            snapshot = await self.get_snapshot()

            # Find email and password fields
            email_ref = None
            password_ref = None
            signin_ref = None

            for node in snapshot['aria']:
                role = (node.get('role') or '').lower()
                name = (node.get('name') or '').lower()
                ref = node.get('ref')

                if 'textbox' in role and 'email' in name:
                    email_ref = ref
                    logger.info(f"  Found email field: {ref}")

                if 'textbox' in role and 'password' in name:
                    password_ref = ref
                    logger.info(f"  Found password field: {ref}")

                if role == 'button' and 'sign in' in name:
                    signin_ref = ref
                    logger.info(f"  Found sign in button: {ref}")

            # Fill credentials using DOM selectors (more reliable for login)
            if email_ref or password_ref:
                try:
                    # Try standard LinkedIn login selectors
                    await self.page.fill('input[name="session_key"]', self.credentials['email'])
                    logger.info("✅ Filled email")
                    await asyncio.sleep(0.5)

                    await self.page.fill('input[name="session_password"]', self.credentials['password'])
                    logger.info("✅ Filled password")
                    await asyncio.sleep(0.5)

                    await self.page.click('button[type="submit"]')
                    logger.info("✅ Clicked sign in")

                    # Wait for navigation
                    await asyncio.sleep(5)

                    # Save session
                    await self.save_session()

                    logger.info("✅ Login complete!")
                    return True

                except Exception as e:
                    logger.error(f"❌ Login failed: {e}")
                    logger.warning("👉 Please log in manually")
                    await asyncio.sleep(30)  # Give time for manual login
                    await self.save_session()
                    return True

        return False

    async def find_elements(self, snapshot):
        """Find key elements using LLM-like analysis"""
        findings = {
            'edit_button': None,
            'add_profile_section': None,
            'more_button': None
        }

        for node in snapshot['aria']:
            role = (node.get('role') or '').lower()
            name = (node.get('name') or '').lower()
            ref = node.get('ref')

            # Look for edit/pencil icons (LinkedIn uses these)
            if role == 'button':
                if 'edit' in name or 'pencil' in name or 'add profile section' in name:
                    logger.info(f"  Found: {ref} | {role} | {name}")
                    if 'edit' in name or 'pencil' in name:
                        findings['edit_button'] = ref
                    if 'add profile section' in name:
                        findings['add_profile_section'] = ref

            # Look for More button
            if role == 'button' and 'more' in name:
                findings['more_button'] = ref
                logger.info(f"  Found More button: {ref}")

        return findings

    async def click_element(self, selector: str, description: str = ""):
        """Click element by CSS selector"""
        try:
            logger.info(f"🖱️  Clicking {description or selector}...")
            await self.page.click(selector, timeout=5000)
            await asyncio.sleep(1)
            logger.info(f"  ✅ Click succeeded")
            return True
        except Exception as e:
            logger.error(f"  ❌ Click failed: {e}")
            return False

    async def type_text(self, selector: str, text: str, description: str = ""):
        """Type text into field"""
        try:
            logger.info(f"⌨️  Typing into {description or selector}...")
            logger.info(f"  Text: {text[:100]}...")

            await self.page.fill(selector, text)
            await asyncio.sleep(0.5)

            logger.info(f"  ✅ Type succeeded")
            return True
        except Exception as e:
            logger.error(f"  ❌ Type failed: {e}")
            return False

    async def update_profile(self):
        """Main workflow"""
        logger.info("=" * 80)
        logger.info("🎯 LINKEDIN PROFILE UPDATE - OPENCLAW STYLE")
        logger.info("=" * 80)

        # Step 1: Navigate to profile
        await self.goto("https://www.linkedin.com/in/phuctruong/")

        # Step 2: Handle login if needed
        await self.login_if_needed()

        # Step 3: Navigate to profile again (after login)
        await self.goto("https://www.linkedin.com/in/phuctruong/")

        # Step 4: Get snapshot
        logger.info("\n📊 PHASE 1: Analyze profile page")
        snapshot = await self.get_snapshot()
        logger.info(f"✅ Found {len(snapshot['aria'])} ARIA nodes")

        # Step 5: Find edit button
        findings = await self.find_elements(snapshot)

        # Step 6: Click edit intro section
        # LinkedIn profile has multiple edit sections
        # Try to click the pencil/edit icon in the intro section
        logger.info("\n✏️  PHASE 2: Edit profile intro")

        # Try various edit button selectors
        edit_selectors = [
            'button[aria-label*="Edit intro"]',
            'button[aria-label*="Edit introduction"]',
            'button[data-control-name="edit_topcard"]',
            '.pv-top-card-profile-picture__edit-profile-icon',
            'button.pv-top-card-profile-picture__edit-profile-icon',
        ]

        edit_clicked = False
        for selector in edit_selectors:
            if await self.click_element(selector, f"Edit intro ({selector})"):
                edit_clicked = True
                break

        if not edit_clicked:
            logger.warning("⚠️ Could not find Edit intro button")
            logger.info("📸 Taking screenshot for debugging...")
            await self.page.screenshot(path='artifacts/linkedin_debug.png')
            logger.info("👉 Screenshot saved to artifacts/linkedin_debug.png")

            # Show what buttons we found
            logger.info("\n🔍 Buttons found on page:")
            for node in snapshot['aria'][:100]:
                if node.get('role') == 'button':
                    logger.info(f"  {node['ref']} | {node.get('name')}")

        logger.info("\n✅ Workflow complete!")

        # Keep browser open
        logger.info("\n👉 Browser staying open for inspection...")
        await asyncio.sleep(60)

    async def stop(self):
        """Stop browser"""
        if self.browser:
            await self.browser.close()
            logger.info("🛑 Browser stopped")


async def main():
    automation = LinkedInAutomation()

    try:
        await automation.start()
        await automation.update_profile()
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
    finally:
        await automation.stop()


if __name__ == "__main__":
    asyncio.run(main())
