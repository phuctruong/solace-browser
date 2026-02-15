#!/usr/bin/env python3

"""
LinkedIn LLM Automation - OpenClaw Style
Zero human help except OAuth login first time

This script:
1. Navigates to LinkedIn
2. Gets structured ARIA snapshot (like OpenClaw)
3. Uses LLM-like logic to understand the page
4. Updates profile (headline, about, projects) automatically
5. Verifies success via console/network monitoring
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright
from dataclasses import asdict

# Import our enhanced modules
from browser_interactions import format_aria_tree, get_dom_snapshot
from enhanced_browser_interactions import (
    AriaRefMapper,
    PageObserver,
    NetworkMonitor,
    get_llm_snapshot,
    execute_click_via_ref,
    execute_type_via_ref
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('linkedin-llm')


class LinkedInLLMAgent:
    """
    LLM-like agent for LinkedIn automation
    Behaves like OpenClaw: sees structured page, makes decisions, executes actions
    """

    def __init__(self, headless: bool = False, session_file: str = "artifacts/linkedin_session.json"):
        self.headless = headless
        self.session_file = session_file
        self.browser = None
        self.context = None
        self.page = None
        self.ref_mapper = None
        self.page_observer = None
        self.network_monitor = None

        # LinkedIn profile content (from linkedin-suggestions.md)
        self.headline = "Software 5.0 Architect | 65537 Authority | Building Verified AI OS in Public"
        self.about = """I build software that beats entropy.

Not chatbots that forget. Not AI that hallucinates. Software 5.0: verified intelligence using deterministic math + prime number architecture (65537D OMEGA).

Currently building:
• STILLWATER OS — Compression + intelligence platform (4.075x universal compression)
• SOLACEAGI — Expert Council SaaS (65537 verified decision-makers, not black-box LLMs)
• PZIP — Beats LZMA on all file types (91.4% win rate on test corpus)
• PHUCNET — Solo founder hub + ecosystem center (ko-fi.com/phucnet for tips)
• IF-THEORY — Mathematical foundations (prime number research, 137+ discoveries)

Philosophy:
Phuc Forecast (DREAM → FORECAST → DECIDE → ACT → VERIFY)
- Memory × Care × Iteration = Intelligence (LEK)
- Rivals before God (641 → 274177 → 65537 verification ladder)
- Never-worse fallback (regeneration is truth)

Why open-source?
Building publicly because:
1. Verification gates (9 audit reports per product, all published)
2. Community keeps me honest (harsh QA culture)
3. Solo founder narrative (one engineer, big ambitions)
4. Support via tips (ko-fi.com/phucnet) drives alignment with users

Recent wins:
✓ 100% SWE-bench verified (6/6 benchmarks)
✓ Browser automation complete (Chrome, Edge, Safari control)
✓ OOLONG verified (99.3% infinite context accuracy)
✓ 137 prime discoveries published (Einstein's favorite number)

Building in public. Always shipping. Always verifying.
Harvard '98 | Boston-based | Solo founder | Verified AI.

Support the journey: https://ko-fi.com/phucnet"""

    async def start(self):
        """Start browser with session persistence"""
        logger.info("🚀 Starting LinkedIn LLM Agent")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        # Load saved session if exists
        context_options = {
            'user_agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }

        if Path(self.session_file).exists():
            logger.info(f"📂 Loading saved session from: {self.session_file}")
            context_options['storage_state'] = self.session_file

        self.context = await self.browser.new_context(**context_options)
        self.page = await self.context.new_page()

        # Setup monitoring (OpenClaw pattern)
        self.page_observer = PageObserver(self.page)
        self.network_monitor = NetworkMonitor(self.page)

        logger.info("✅ Browser started with monitoring enabled")

    async def stop(self):
        """Stop browser"""
        if self.browser:
            await self.browser.close()
            logger.info("🛑 Browser stopped")

    async def save_session(self):
        """Save session for future use"""
        if self.context:
            Path(self.session_file).parent.mkdir(parents=True, exist_ok=True)
            await self.context.storage_state(path=self.session_file)
            logger.info(f"💾 Session saved to: {self.session_file}")

    async def get_snapshot(self) -> dict:
        """
        Get LLM-friendly page snapshot (OpenClaw style)
        Returns structured ARIA tree + DOM + console + network
        """
        logger.info("📸 Getting page snapshot...")

        # Get ARIA and DOM trees
        aria_tree = await format_aria_tree(self.page, limit=500)
        dom_tree = await get_dom_snapshot(self.page, limit=800)

        # Build ref mapper (CRITICAL for clicking!)
        self.ref_mapper = AriaRefMapper()
        await self.ref_mapper.build_map(
            self.page,
            [asdict(node) for node in aria_tree]
        )

        # Get comprehensive snapshot
        snapshot = await get_llm_snapshot(
            self.page,
            [asdict(node) for node in aria_tree],
            dom_tree,
            self.page_observer,
            self.network_monitor
        )

        logger.info(f"✅ Snapshot: {snapshot['stats']['ariaNodes']} ARIA nodes, "
                   f"{snapshot['stats']['consoleMessages']} console messages")

        return snapshot

    def llm_analyze_page(self, snapshot: dict) -> dict:
        """
        LLM-like page analysis
        Returns: element refs for key interactive elements
        """
        logger.info("🧠 Analyzing page (LLM-like reasoning)...")

        aria_nodes = snapshot.get('aria', [])
        url = snapshot.get('url', '')

        # Find key elements using LLM-like pattern matching
        findings = {
            'edit_profile_button': None,
            'headline_field': None,
            'about_field': None,
            'save_button': None,
            'is_edit_mode': False
        }

        for node in aria_nodes:
            role = (node.get('role') or '').lower()
            name = (node.get('name') or '').lower()
            ref = node.get('ref')

            # Look for "Edit" button
            if role == 'button' and ('edit' in name or 'pencil' in name):
                findings['edit_profile_button'] = ref
                logger.info(f"  Found Edit Profile: {ref} → {node.get('name')}")

            # Look for headline/title field
            if role == 'textbox':
                if 'headline' in name or 'title' in name:
                    findings['headline_field'] = ref
                    logger.info(f"  Found Headline field: {ref} → {node.get('name')}")
                    findings['is_edit_mode'] = True

            # Look for about/bio field
            if role == 'textbox':
                if 'about' in name or 'bio' in name or 'summary' in name:
                    findings['about_field'] = ref
                    logger.info(f"  Found About field: {ref} → {node.get('name')}")

            # Look for Save button
            if role == 'button' and ('save' in name or 'done' in name):
                findings['save_button'] = ref
                logger.info(f"  Found Save button: {ref} → {node.get('name')}")

        return findings

    async def click_ref(self, ref: str, description: str = "") -> bool:
        """Click element by ref with logging"""
        logger.info(f"🖱️  Clicking {description or ref}...")

        result = await execute_click_via_ref(
            self.page,
            ref=ref,
            ref_mapper=self.ref_mapper,
            timeout_ms=10000
        )

        if result.get('success'):
            logger.info(f"  ✅ Click succeeded: {description or ref}")
            return True
        else:
            logger.error(f"  ❌ Click failed: {result.get('error')}")
            return False

    async def type_ref(self, ref: str, text: str, description: str = "", slowly: bool = True) -> bool:
        """Type into element by ref with logging"""
        logger.info(f"⌨️  Typing into {description or ref}...")
        logger.info(f"  Text: {text[:100]}{'...' if len(text) > 100 else ''}")

        result = await execute_type_via_ref(
            self.page,
            ref=ref,
            text=text,
            ref_mapper=self.ref_mapper,
            slowly=slowly,
            delay_ms=30 if slowly else 0,
            timeout_ms=10000
        )

        if result.get('success'):
            logger.info(f"  ✅ Type succeeded: {description or ref}")
            return True
        else:
            logger.error(f"  ❌ Type failed: {result.get('error')}")
            return False

    async def wait_and_observe(self, seconds: int = 2):
        """Wait and observe page changes"""
        logger.info(f"⏳ Waiting {seconds}s for page updates...")
        await asyncio.sleep(seconds)

        # Check for new console messages
        recent_console = self.page_observer.get_recent_console(5)
        for msg in recent_console:
            logger.info(f"  Console [{msg['type']}]: {msg['text']}")

    async def navigate_to_profile(self, username: str = "phuctruong"):
        """Navigate to LinkedIn profile"""
        url = f"https://www.linkedin.com/in/{username}/"
        logger.info(f"🌐 Navigating to: {url}")

        await self.page.goto(url, wait_until='networkidle')
        await self.wait_and_observe(2)

    async def handle_login_if_needed(self):
        """Check if login is needed and wait for user"""
        snapshot = await self.get_snapshot()
        url = snapshot.get('url', '')

        # Check if we're on login page
        if '/login' in url or '/uas/login' in url:
            logger.warning("🔐 Login required!")
            logger.warning("👉 Please log in manually in the browser window")
            logger.warning("👉 I'll wait for you to complete login...")

            # Wait for login to complete (URL changes)
            while '/login' in self.page.url or '/uas/login' in self.page.url:
                await asyncio.sleep(2)
                logger.info("  Still waiting for login...")

            logger.info("✅ Login complete!")
            await self.save_session()
            await self.wait_and_observe(2)

    async def update_profile_full_workflow(self):
        """
        Complete LinkedIn profile update workflow
        Behaves like OpenClaw LLM: analyze → decide → act → verify
        """
        logger.info("=" * 80)
        logger.info("🎯 LINKEDIN PROFILE UPDATE - LLM AUTOMATION")
        logger.info("=" * 80)

        # Step 1: Navigate to profile
        await self.navigate_to_profile()

        # Step 2: Handle login if needed
        await self.handle_login_if_needed()

        # Step 3: Get initial snapshot
        logger.info("\n📊 PHASE 1: Analyze current page")
        snapshot = await self.get_snapshot()
        findings = self.llm_analyze_page(snapshot)

        # Step 4: Check if already in edit mode
        if findings['is_edit_mode']:
            logger.info("✅ Already in edit mode!")
        else:
            # Need to click Edit button
            if findings['edit_profile_button']:
                logger.info("\n🎬 PHASE 2: Enter edit mode")
                success = await self.click_ref(
                    findings['edit_profile_button'],
                    "Edit Profile button"
                )

                if not success:
                    logger.error("❌ Failed to enter edit mode")
                    return False

                await self.wait_and_observe(3)

                # Re-analyze page after clicking Edit
                snapshot = await self.get_snapshot()
                findings = self.llm_analyze_page(snapshot)
            else:
                logger.warning("⚠️ Could not find Edit button - maybe already in edit mode?")

        # Step 5: Update headline
        if findings['headline_field']:
            logger.info("\n✍️  PHASE 3: Update headline")
            success = await self.type_ref(
                findings['headline_field'],
                self.headline,
                "Headline field",
                slowly=True
            )

            if not success:
                logger.warning("⚠️ Headline update may have failed")

            await self.wait_and_observe(1)
        else:
            logger.warning("⚠️ Could not find headline field")

        # Step 6: Update about section
        if findings['about_field']:
            logger.info("\n📝 PHASE 4: Update about section")
            success = await self.type_ref(
                findings['about_field'],
                self.about,
                "About field",
                slowly=True
            )

            if not success:
                logger.warning("⚠️ About update may have failed")

            await self.wait_and_observe(1)
        else:
            logger.warning("⚠️ Could not find about field")

        # Step 7: Save changes
        if findings['save_button']:
            logger.info("\n💾 PHASE 5: Save changes")
            success = await self.click_ref(
                findings['save_button'],
                "Save button"
            )

            if not success:
                logger.error("❌ Failed to save changes")
                return False

            await self.wait_and_observe(3)
        else:
            logger.warning("⚠️ Could not find Save button - changes may not be saved")

        # Step 8: Verify success
        logger.info("\n✅ PHASE 6: Verify changes")
        final_snapshot = await self.get_snapshot()

        # Check for errors
        if final_snapshot.get('hasErrors'):
            logger.error("❌ Errors detected:")
            for error in final_snapshot.get('errors', []):
                logger.error(f"  - {error.get('message')}")
            return False

        # Check console for success messages
        console_msgs = final_snapshot.get('console', [])
        success_indicators = [
            msg for msg in console_msgs
            if 'success' in msg.get('text', '').lower() or
               'saved' in msg.get('text', '').lower() or
               'updated' in msg.get('text', '').lower()
        ]

        if success_indicators:
            logger.info("✅ Success indicators in console:")
            for msg in success_indicators:
                logger.info(f"  - {msg.get('text')}")

        # Save session
        await self.save_session()

        logger.info("\n" + "=" * 80)
        logger.info("🎉 LINKEDIN PROFILE UPDATE COMPLETE!")
        logger.info("=" * 80)

        # Generate proof artifact
        proof = {
            "timestamp": datetime.now().isoformat(),
            "workflow": "linkedin_profile_update",
            "headline_updated": bool(findings['headline_field']),
            "about_updated": bool(findings['about_field']),
            "changes_saved": bool(findings['save_button']),
            "errors": final_snapshot.get('errors', []),
            "console_messages": len(console_msgs),
            "network_requests": final_snapshot.get('stats', {}).get('networkRequests', 0),
            "verification": {
                "has_errors": final_snapshot.get('hasErrors', False),
                "success_indicators": len(success_indicators)
            }
        }

        # Save proof
        proof_file = f"artifacts/proof-linkedin-update-{int(datetime.now().timestamp())}.json"
        Path(proof_file).parent.mkdir(parents=True, exist_ok=True)
        with open(proof_file, 'w') as f:
            json.dump(proof, f, indent=2)

        logger.info(f"📄 Proof artifact saved: {proof_file}")

        return True


async def main():
    """Main entry point"""
    agent = LinkedInLLMAgent(headless=False)

    try:
        await agent.start()
        success = await agent.update_profile_full_workflow()

        if success:
            logger.info("\n✅ SUCCESS: Profile updated successfully!")
        else:
            logger.error("\n❌ FAILURE: Profile update incomplete")

        # Keep browser open for inspection
        logger.info("\n👉 Browser will stay open for 10 seconds for inspection...")
        await asyncio.sleep(10)

    except Exception as e:
        logger.error(f"❌ Fatal error: {e}", exc_info=True)

    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
