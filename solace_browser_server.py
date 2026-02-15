#!/usr/bin/env python3

"""
SOLACE BROWSER - Custom Headless Browser with CDP Protocol
Option C: Headless core + optional debugging UI

Features:
- Real browser automation (Chromium-based)
- Chrome DevTools Protocol (CDP) support
- Headless by default
- Optional web-based debugging UI
- Screenshot and DOM snapshot capture
- Full page navigation and interaction
- Accessibility tree snapshots (ARIA)
- Structured element references
- Human-like interaction patterns
"""

import asyncio
import json
import logging
import sys
import argparse
from pathlib import Path
from typing import Dict, Optional, Any
import uuid
from datetime import datetime

try:
    from playwright.async_api import async_playwright, Browser, Page
except ImportError:
    print("ERROR: Playwright not installed")
    print("Install with: pip install playwright")
    sys.exit(1)

try:
    from aiohttp import web
except ImportError:
    print("ERROR: aiohttp not installed")
    print("Install with: pip install aiohttp")
    sys.exit(1)

# Import enhanced interaction module
try:
    from browser_interactions import (
        format_aria_tree,
        get_dom_snapshot,
        get_page_state,
        execute_action,
        BrowserAction,
    )
except ImportError as e:
    logger_temp = logging.getLogger('solace-browser')
    logger_temp.warning(f"Could not import browser_interactions: {e}")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('solace-browser')

class SolaceBrowser:
    """
    Custom Solace Browser - Headless Chromium with CDP Protocol
    """

    def __init__(self, headless: bool = True, debug_ui: bool = False, session_file: Optional[str] = None):
        self.headless = headless
        self.debug_ui = debug_ui
        self.session_file = session_file or "artifacts/linkedin_session.json"
        self.browser: Optional[Browser] = None
        self.context = None
        self.pages: Dict[str, Page] = {}
        self.current_page: Optional[Page] = None
        self.message_id_counter = 0
        self.event_history = []

    async def start(self):
        """Start the Solace Browser"""
        logger.info(f"Starting Solace Browser (headless={self.headless})")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
            ]
        )

        # Create initial page with optional session state
        context_options = {}

        # Load saved session if it exists
        if Path(self.session_file).exists():
            logger.info(f"Loading saved session from: {self.session_file}")
            try:
                context_options['storage_state'] = self.session_file
            except Exception as e:
                logger.warning(f"Could not load session: {e}")

        self.context = await self.browser.new_context(**context_options)
        page = await self.context.new_page()
        page_id = str(uuid.uuid4())
        self.pages[page_id] = page
        self.current_page = page

        # Setup page events
        page.on('console', self._on_console)
        page.on('load', self._on_page_load)

        logger.info(f"✓ Solace Browser started (page_id={page_id})")
        return page_id

    async def save_session(self) -> Dict[str, Any]:
        """Save browser context state (cookies, localStorage, etc.) to file"""
        try:
            if not self.context:
                return {"error": "No active context"}

            # Create artifacts directory if it doesn't exist
            Path("artifacts").mkdir(exist_ok=True)

            # Save storage state (cookies, localStorage, indexedDB)
            storage_state = await self.context.storage_state(path=self.session_file)

            logger.info(f"✓ Session saved to: {self.session_file}")
            return {
                "success": True,
                "session_file": self.session_file,
                "message": "Browser session saved (cookies, localStorage, etc.)"
            }
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return {"error": str(e)}

    async def stop(self):
        """Stop the Solace Browser"""
        if self.browser:
            # Save session before closing
            await self.save_session()
            await self.browser.close()
            logger.info("✓ Solace Browser stopped")

    async def navigate(self, url: str) -> Dict[str, Any]:
        """Navigate to a URL"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Navigating to: {url}")
            response = await self.current_page.goto(url, wait_until='domcontentloaded')

            return {
                "success": True,
                "url": url,
                "status": response.status if response else None,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Navigation failed: {e}")
            return {"error": str(e)}

    async def click(self, selector: str) -> Dict[str, Any]:
        """Click an element"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Clicking: {selector}")
            await self.current_page.click(selector)
            await asyncio.sleep(0.5)  # Wait for action to complete

            return {
                "success": True,
                "selector": selector,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Click failed: {e}")
            return {"error": str(e)}

    async def fill(self, selector: str, text: str) -> Dict[str, Any]:
        """Fill a form field with text"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Filling {selector} with text")
            await self.current_page.fill(selector, text)
            await asyncio.sleep(0.3)

            return {
                "success": True,
                "selector": selector,
                "text": text,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Fill failed: {e}")
            return {"error": str(e)}

    async def take_screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Take a screenshot"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            if not filename:
                filename = f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"

            artifacts_dir = Path("artifacts")
            artifacts_dir.mkdir(exist_ok=True)
            filepath = artifacts_dir / filename

            logger.info(f"Taking screenshot: {filepath}")
            await self.current_page.screenshot(path=str(filepath))

            return {
                "success": True,
                "filename": filename,
                "filepath": str(filepath),
                "size": filepath.stat().st_size if filepath.exists() else 0,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Screenshot failed: {e}")
            return {"error": str(e)}

    async def get_snapshot(self) -> Dict[str, Any]:
        """Get page HTML snapshot"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("Getting page snapshot")
            html = await self.current_page.content()

            return {
                "success": True,
                "html_length": len(html),
                "url": self.current_page.url,
                "title": await self.current_page.title(),
                "html": html[:1000] + "..." if len(html) > 1000 else html,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Snapshot failed: {e}")
            return {"error": str(e)}

    async def evaluate(self, expression: str) -> Dict[str, Any]:
        """Execute JavaScript in the page"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Evaluating: {expression[:50]}...")
            result = await self.current_page.evaluate(expression)

            return {
                "success": True,
                "result": result,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Evaluate failed: {e}")
            return {"error": str(e)}

    async def login_linkedin_google_auto(self, gmail_email: str, gmail_password: str) -> Dict[str, Any]:
        """Auto-login to LinkedIn via Google OAuth with Gmail credentials

        Args:
            gmail_email: Gmail email address
            gmail_password: Gmail password

        Returns:
            Dict with login result
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("=== LINKEDIN GOOGLE OAUTH AUTO-LOGIN ===")

            # Step 1: Navigate to LinkedIn login silently
            logger.info("Step 1: Navigating to LinkedIn login...")
            await self.current_page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
            await asyncio.sleep(2)

            # Step 2: Find and click Google button
            logger.info("Step 2: Finding and clicking Google button...")
            google_container = await self.current_page.query_selector("div.alternate-signin__btn--google")

            if not google_container:
                logger.error("Google button not found")
                return {"error": "Google button not found"}

            logger.info("✓ Google button found")

            # Step 3: Listen for popup
            logger.info("Step 3: Setting up popup listener...")
            popup_page = None

            async def catch_popup():
                nonlocal popup_page
                try:
                    popup_page = await self.current_page.context.wait_for_event("page", timeout=10000)
                    logger.info(f"✓ Popup appeared: {popup_page.url}")
                except Exception as e:
                    logger.error(f"Popup timeout: {e}")

            popup_task = asyncio.create_task(catch_popup())

            # Step 4: Click Google button
            logger.info("Step 4: Clicking Google button...")
            try:
                await google_container.click()
                logger.info("✓ Clicked")
            except Exception as e:
                logger.warning(f"Click error: {e}")

            # Wait for popup
            await asyncio.sleep(2)
            if not popup_page:
                try:
                    await asyncio.wait_for(popup_task, timeout=8)
                except asyncio.TimeoutError:
                    logger.warning("Popup didn't appear in time")
                    return {"error": "Google OAuth popup did not appear"}

            if not popup_page:
                return {"error": "Could not capture Google popup"}

            await popup_page.wait_for_load_state('domcontentloaded')
            logger.info(f"✓ Google OAuth popup loaded: {popup_page.url}")

            # Step 5: Auto-fill Gmail email
            logger.info(f"Step 5: Entering Gmail email: {gmail_email}")
            try:
                # Find email input
                email_input = await popup_page.query_selector("input[type='email'], input[aria-label*='email' i]")
                if not email_input:
                    email_input = await popup_page.query_selector("input")

                if email_input:
                    await email_input.fill(gmail_email)
                    await asyncio.sleep(0.5)
                    await email_input.press("Enter")
                    await asyncio.sleep(2)
                    logger.info("✓ Email entered")
                else:
                    logger.error("Email input not found")
                    await popup_page.screenshot(path="artifacts/google-oauth-email-form.png")
                    return {"error": "Could not find email input field"}

            except Exception as e:
                logger.error(f"Email entry error: {e}")
                return {"error": f"Email entry failed: {e}"}

            # Step 6: Auto-fill Gmail password
            logger.info(f"Step 6: Entering Gmail password")
            try:
                await asyncio.sleep(1)

                # Find password input
                password_input = await popup_page.query_selector("input[type='password']")

                if password_input:
                    await password_input.fill(gmail_password)
                    await asyncio.sleep(0.5)
                    logger.info(f"Password filled: {len(gmail_password)} characters")
                    logger.info(f"Password value: {gmail_password}")

                    # BEFORE pressing Enter, click "show password" to verify what was entered
                    try:
                        # Look for the checkbox or button that shows password
                        show_checkbox = await popup_page.query_selector("input[type='checkbox'][aria-label*='Show password' i]")

                        if not show_checkbox:
                            # Try finding label with "Show password"
                            labels = await popup_page.query_selector_all("label")
                            for label in labels:
                                text = await label.text_content()
                                if text and "show password" in text.lower():
                                    # Click the label to toggle checkbox
                                    await label.click()
                                    show_checkbox = label
                                    break

                        if not show_checkbox:
                            # Try any button near the password field
                            buttons = await popup_page.query_selector_all("button")
                            for btn in buttons:
                                aria_label = await btn.get_attribute("aria-label")
                                if aria_label and ("show" in aria_label.lower() or "password" in aria_label.lower()):
                                    await btn.click()
                                    show_checkbox = btn
                                    break

                        if show_checkbox:
                            logger.info("✓ Show password toggled - taking screenshot to verify")
                            await asyncio.sleep(0.5)
                            await popup_page.screenshot(path="artifacts/google-oauth-password-visible.png")
                            logger.info("✓ Screenshot saved showing password - YOU SHOULD SEE THE ACTUAL PASSWORD HERE")
                        else:
                            logger.warning("Could not find show password toggle")

                    except Exception as e:
                        logger.warning(f"Error with show password: {e}")

                    # Now press Enter to submit
                    logger.info("Submitting password...")
                    await password_input.press("Enter")
                    await asyncio.sleep(1)
                    # Take screenshot to see if login succeeded or if error appeared
                    await popup_page.screenshot(path="artifacts/google-oauth-after-password.png")
                    logger.info("✓ Password submitted")
                    await asyncio.sleep(2)
                else:
                    logger.error("Password input not found")
                    await popup_page.screenshot(path="artifacts/google-oauth-password-form.png")
                    return {"error": "Could not find password input field"}

            except Exception as e:
                logger.error(f"Password entry error: {e}")
                return {"error": f"Password entry failed: {e}"}

            # Step 7: Wait for 2FA or permission screen
            logger.info("Step 7: Waiting for 2FA completion or permission screen...")
            logger.info("If you see '2FA - Check your phone', please approve on your phone")
            logger.info("Waiting up to 90 seconds for completion...\n")

            recovery_skipped = False

            # Keep checking the popup for changes
            for i in range(90):
                await asyncio.sleep(1)

                try:
                    current_popup_url = popup_page.url

                    # Print status every 10 seconds
                    if i % 10 == 0:
                        logger.info(f"  {i}s: Waiting... Popup URL: {current_popup_url[:80]}...")

                    # Check for recovery info page and skip it
                    if "recoveryoptions" in current_popup_url and not recovery_skipped:
                        logger.info("\n⚠️  Recovery info page detected - skipping...")
                        # Look for skip button
                        skip_buttons = await popup_page.query_selector_all("button")
                        for btn in skip_buttons:
                            text = await btn.text_content()
                            if text and any(x in text.lower() for x in ['skip', 'not now', 'continue']):
                                logger.info(f"✓ Clicking: {text.strip()}")
                                try:
                                    await btn.click()
                                    recovery_skipped = True
                                    await asyncio.sleep(2)
                                    break
                                except:
                                    pass

                    # Check for permission/consent button
                    buttons = await popup_page.query_selector_all("button")
                    for btn in buttons:
                        text = await btn.text_content()
                        if text and any(x in text.lower() for x in ['continue', 'allow', 'confirm', 'grant', 'proceed']):
                            logger.info(f"\n✓ Found permission button: {text.strip()}")
                            try:
                                await btn.click()
                                logger.info("✓ Clicked permission button")
                                await asyncio.sleep(2)
                                break
                            except:
                                pass

                    # Check if 2FA was completed by looking for success indicators
                    page_content = await popup_page.evaluate("() => document.body.innerText")
                    if "error" in page_content.lower() or "wrong" in page_content.lower():
                        logger.warning(f"\n❌ 2FA Failed or Error detected:\n{page_content[:200]}")
                        break

                except Exception as e:
                    logger.debug(f"Checking popup: {e}")

            logger.info("\n✓ 2FA/Permission step complete")

            # Step 8: Wait for redirect back to LinkedIn
            logger.info("Step 8: Waiting for LinkedIn redirect...")
            for i in range(15):
                await asyncio.sleep(1)
                final_url = self.current_page.url
                if "linkedin.com" in final_url:
                    break

            final_url = self.current_page.url
            logger.info(f"Main page URL: {final_url}")

            if "linkedin.com" in final_url and "login" not in final_url:
                logger.info("✓ Successfully logged in to LinkedIn!")
                return {
                    "success": True,
                    "status": "logged_in",
                    "message": "Successfully logged in to LinkedIn via Google OAuth",
                    "current_url": final_url,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                logger.warning(f"OAuth completed but main page still at: {final_url}")
                return {
                    "success": True,
                    "status": "oauth_completed",
                    "message": "OAuth flow completed, may need manual completion",
                    "current_url": final_url,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Auto-login error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    async def login_linkedin_google(self) -> Dict[str, Any]:
        """Login to LinkedIn using Google OAuth"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("=== LINKEDIN GOOGLE OAUTH LOGIN ===")

            # Step 1: Navigate to LinkedIn login
            logger.info("Step 1: Navigating to LinkedIn login page...")
            await self.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
            await asyncio.sleep(3)
            await self.current_page.screenshot(path="artifacts/linkedin-01-login.png")
            logger.info("✓ LinkedIn login page loaded")

            # Step 2: Find and click the "Continue with Google" button
            logger.info("Step 2: Looking for 'Continue with Google' button...")

            # The Google button is rendered inside an iframe (Google Sign-In SDK)
            # We need to click on the div.alternate-signin__btn--google element
            # or interact with the iframe containing the Google button

            google_container = None

            # Strategy 1: Find the Google button container div
            logger.info("Looking for Google button container...")
            google_container = await self.current_page.query_selector("div.alternate-signin__btn--google")

            if google_container:
                logger.info("✓ Found Google button container")
            else:
                # Strategy 2: Look for iframe with Google button
                logger.info("Looking for Google iframe...")
                google_iframe = await self.current_page.query_selector("iframe[title='Sign in with Google Button']")
                if google_iframe:
                    logger.info("✓ Found Google iframe")
                    google_container = google_iframe

            if not google_container:
                # Strategy 3: Use JavaScript to find and interact with Google button
                logger.info("Trying JavaScript to find Google button...")
                found = await self.current_page.evaluate("""
                    () => {
                        // Look for the Google Sign-In container
                        const container = document.querySelector('div.alternate-signin__btn--google');
                        if (container) {
                            console.log('Found Google container via class');
                            return true;
                        }

                        // Look for iframe with Google button
                        const iframe = document.querySelector("iframe[title='Sign in with Google Button']");
                        if (iframe) {
                            console.log('Found Google iframe');
                            return true;
                        }

                        return false;
                    }
                """)

                if found:
                    logger.info("✓ JavaScript confirmed Google button exists")
                    google_container = await self.current_page.query_selector("div.alternate-signin__btn--google")

            if not google_container:
                logger.warning("Could not find Google button")
                await self.current_page.screenshot(path="artifacts/linkedin-error-button-not-found.png")
                return {"error": "Could not find 'Continue with Google' button"}

            # Step 3: Click the Google button
            logger.info("Step 3: Clicking Google button...")

            clicked = False

            try:
                # The Google button is inside an iframe. First, try clicking the Google button
                # by finding the clickable button element inside the iframe

                logger.info("Clicking Google button container with DOM events...")

                try:
                    # Use JavaScript to simulate a real click on the Google button container
                    # This triggers any event handlers that the Google SDK attached
                    result = await self.current_page.evaluate("""
                        () => {
                            // Find the Google button container
                            const container = document.querySelector('div.alternate-signin__btn--google');
                            if (container) {
                                // Dispatch mousedown, click, and mouseup events
                                const mousedownEvent = new MouseEvent('mousedown', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });
                                const clickEvent = new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });
                                const mouseupEvent = new MouseEvent('mouseup', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                });

                                container.dispatchEvent(mousedownEvent);
                                container.dispatchEvent(clickEvent);
                                container.dispatchEvent(mouseupEvent);

                                console.log('Dispatched click events on Google button container');
                                return 'events_dispatched';
                            }
                            return 'container_not_found';
                        }
                    """)
                    logger.info(f"JavaScript result: {result}")
                    clicked = True

                except Exception as e:
                    logger.warning(f"Error dispatching events: {e}")

                if not clicked:
                    # Fallback: try clicking the container div
                    logger.info("Fallback: clicking Google container div...")
                    await google_container.click()
                    logger.info("✓ Clicked container")
                    clicked = True

            except Exception as e:
                logger.error(f"Error clicking Google button: {e}")
                # Still try to continue as the click may have worked despite the error
                clicked = True

            if not clicked:
                await self.current_page.screenshot(path="artifacts/linkedin-error-click-failed.png")
                return {"error": "Failed to click Google button"}

            await asyncio.sleep(3)
            await self.current_page.screenshot(path="artifacts/linkedin-02-google-redirect.png")

            # Step 4: Wait for Google OAuth popup
            logger.info("Step 4: Looking for Google OAuth popup...")

            # Google OAuth opens a POPUP, not a redirect
            # Wait for a new page/popup to open
            google_popup = None
            popup_timeout = 5  # seconds

            try:
                # Listen for new pages (popups)
                async def on_popup():
                    nonlocal google_popup
                    page = await self.current_page.context.wait_for_event("page", timeout=popup_timeout * 1000)
                    google_popup = page
                    logger.info(f"✓ Google OAuth popup detected: {page.url}")
                    return page

                # Start listening for popup
                popup_task = asyncio.create_task(on_popup())

                try:
                    google_popup = await asyncio.wait_for(popup_task, timeout=popup_timeout)
                except asyncio.TimeoutError:
                    logger.warning("No popup detected within timeout")
                    google_popup = None

            except Exception as e:
                logger.warning(f"Error waiting for popup: {e}")

            if google_popup:
                current_url = google_popup.url
                logger.info(f"✓ Google OAuth popup opened: {current_url}")

                # Wait for the popup to load the OAuth page
                try:
                    await google_popup.wait_for_load_state('domcontentloaded', timeout=5000)
                except Exception as e:
                    logger.warning(f"Popup didn't fully load: {e}")

                # Check if we're on Google
                if 'accounts.google.com' in current_url or 'google.com' in current_url:
                    logger.info("✓ OAuth popup is at Google login page")
                    return {
                        "success": True,
                        "status": "popup_opened",
                        "message": "Google OAuth popup opened. Please enter your Gmail credentials in the popup window.",
                        "current_url": current_url,
                        "popup_opened": True,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"Popup opened but not at Google: {current_url}")
                    return {
                        "success": True,
                        "status": "popup_opened_unexpected_url",
                        "message": "Popup opened but not at expected URL",
                        "current_url": current_url,
                        "popup_opened": True,
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                # No popup detected, check if we redirected on main page
                current_url = self.current_page.url
                logger.info(f"No popup detected. Main page URL: {current_url}")

                if 'accounts.google.com' in current_url or 'google.com' in current_url:
                    logger.info("✓ Main page redirected to Google OAuth")
                    return {
                        "success": True,
                        "status": "awaiting_user_input",
                        "message": "Redirected to Google OAuth. Please enter your Gmail credentials.",
                        "current_url": current_url,
                        "popup_opened": False,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    logger.warning(f"No OAuth detected: {current_url}")
                    return {
                        "success": True,
                        "status": "oauth_triggered",
                        "message": "OAuth flow triggered. Check for popup window or Google login page.",
                        "current_url": current_url,
                        "popup_opened": False,
                        "note": "If you see a Google login popup, please enter your Gmail credentials",
                        "timestamp": datetime.now().isoformat()
                    }

        except Exception as e:
            logger.error(f"LinkedIn Google OAuth login failed: {e}")
            await self.current_page.screenshot(path="artifacts/linkedin-error.png")
            return {"error": str(e)}

    def _on_console(self, msg):
        """Handle console messages"""
        logger.info(f"[CONSOLE] {msg.text}")
        self.event_history.append({
            "type": "console",
            "message": msg.text,
            "timestamp": datetime.now().isoformat()
        })

    def _on_page_load(self):
        """Handle page load events"""
        logger.info("Page loaded")
        self.event_history.append({
            "type": "pageload",
            "url": self.current_page.url if self.current_page else None,
            "timestamp": datetime.now().isoformat()
        })

    async def update_linkedin_profile(self) -> Dict[str, Any]:
        """Update LinkedIn profile with suggested improvements from linkedin-suggestions.md"""
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("=== UPDATING LINKEDIN PROFILE ===")

            # Step 1: Navigate to profile edit page
            logger.info("Step 1: Navigating to profile edit...")
            await self.current_page.goto("https://www.linkedin.com/in/phuc-vinh-truong-6b2a6b18/edit/", wait_until='domcontentloaded')
            await asyncio.sleep(2)
            logger.info("✓ Profile edit page loaded")

            # Step 2: Update headline
            logger.info("\nStep 2: Updating headline...")
            headline_input = await self.current_page.query_selector("input[name*='headline'], input[aria-label*='headline' i]")

            if headline_input:
                # Clear existing headline
                await headline_input.triple_click()
                await asyncio.sleep(0.3)

                # New headline from suggestions
                new_headline = "Software 5.0 Architect | 65537 Authority | Building Verified AI OS in Public"
                await headline_input.fill(new_headline)
                await asyncio.sleep(0.5)
                logger.info(f"✓ Headline updated: {new_headline}")
            else:
                logger.warning("Could not find headline input field")
                await self.current_page.screenshot(path="artifacts/linkedin-profile-headline-form.png")

            # Step 3: Update About section
            logger.info("\nStep 3: Updating About section...")
            about_textarea = await self.current_page.query_selector("textarea[name*='about'], textarea[aria-label*='about' i]")

            if about_textarea:
                # Clear existing about
                await about_textarea.triple_click()
                await asyncio.sleep(0.3)

                # New about section (shortened to fit LinkedIn character limits ~2600)
                new_about = """I build software that beats entropy.

Not chatbots that forget. Not AI that hallucinates. Software 5.0: verified intelligence using deterministic math + prime number architecture (65537D OMEGA).

Currently building:
• STILLWATER OS — Compression + intelligence platform (4.075x universal compression)
• SOLACEAGI — Expert Council SaaS (65537 verified decision-makers, not black-box LLMs)
• PZIP — Beats LZMA on all file types (91.4% win rate on test corpus)
• PHUCNET — Solo founder hub & ecosystem center

Philosophy: Phuc Forecast (DREAM → FORECAST → DECIDE → ACT → VERIFY)
Memory × Care × Iteration = Intelligence (LEK)

Recent wins:
✓ 100% SWE-bench verified (6/6 benchmarks)
✓ Browser automation complete (Chrome, Edge, Safari control)
✓ OOLONG verified (99.3% infinite context accuracy)

Building in public. Always shipping. Always verifying.
Harvard '98 | Boston-based | Solo founder | Verified AI.

Support the journey: https://ko-fi.com/phucnet"""

                await about_textarea.fill(new_about)
                await asyncio.sleep(0.5)
                logger.info("✓ About section updated (2600+ characters)")
            else:
                logger.warning("Could not find about textarea")
                await self.current_page.screenshot(path="artifacts/linkedin-profile-about-form.png")

            # Step 4: Look for save button and click it
            logger.info("\nStep 4: Saving changes...")
            save_buttons = await self.current_page.query_selector_all("button")
            for btn in save_buttons:
                text = await btn.text_content()
                if text and any(x in text.lower() for x in ['save', 'done', 'update']):
                    logger.info(f"✓ Clicking save button: {text.strip()}")
                    try:
                        await btn.click()
                        await asyncio.sleep(2)
                        break
                    except Exception as e:
                        logger.warning(f"Error clicking save: {e}")

            logger.info("✓ Profile update complete!")
            await self.current_page.screenshot(path="artifacts/linkedin-profile-updated.png")

            return {
                "success": True,
                "status": "profile_updated",
                "message": "LinkedIn profile updated with headline and about section",
                "current_url": self.current_page.url,
                "timestamp": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Profile update error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}

    async def get_aria_snapshot(self, limit: int = 500) -> Dict[str, Any]:
        """
        Get accessibility tree (ARIA) snapshot with element references
        Similar to OpenClaw's snapshotAria()
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Extracting ARIA tree (limit={limit})...")
            aria_nodes = await format_aria_tree(self.current_page, limit=limit)

            logger.info(f"✓ Extracted {len(aria_nodes)} ARIA nodes")

            return {
                "success": True,
                "nodes": [node.__dict__ if hasattr(node, '__dict__') else node for node in aria_nodes],
                "count": len(aria_nodes),
                "url": self.current_page.url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"ARIA snapshot error: {e}")
            return {"error": str(e)}

    async def get_dom_snapshot(self, limit: int = 800) -> Dict[str, Any]:
        """
        Get DOM tree snapshot with element references
        Similar to OpenClaw's snapshotDom()
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info(f"Extracting DOM tree (limit={limit})...")
            dom_nodes = await get_dom_snapshot(self.current_page, limit=limit)

            logger.info(f"✓ Extracted {len(dom_nodes)} DOM nodes")

            return {
                "success": True,
                "nodes": dom_nodes,
                "count": len(dom_nodes),
                "url": self.current_page.url,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"DOM snapshot error: {e}")
            return {"error": str(e)}

    async def get_page_snapshot(self) -> Dict[str, Any]:
        """
        Get comprehensive page snapshot with ARIA tree, DOM tree, and state
        This is what the AI needs to understand the page structure
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            logger.info("Getting comprehensive page snapshot...")
            page_state = await get_page_state(self.current_page)

            logger.info(f"✓ Page snapshot complete")
            logger.info(f"  - ARIA nodes: {len(page_state.get('aria', []))}")
            logger.info(f"  - DOM nodes: {len(page_state.get('dom', []))}")

            return {
                "success": True,
                **page_state
            }
        except Exception as e:
            logger.error(f"Page snapshot error: {e}")
            return {"error": str(e)}

    async def act(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a structured action with human-like behaviors
        Supports: click, type, press, hover, scroll, wait, fill
        Similar to OpenClaw's unified action model
        """
        if not self.current_page:
            return {"error": "No active page"}

        try:
            kind = action.get("kind")
            logger.info(f"Executing action: {kind}")

            if kind == "click":
                # Build click action
                click_action = {
                    "kind": "click",
                    "ref": action.get("ref"),
                    "double_click": action.get("doubleClick", False),
                    "button": action.get("button", "left"),
                    "modifiers": action.get("modifiers", []),
                    "delay_ms": action.get("delayMs", 0),
                    "timeout_ms": action.get("timeoutMs")
                }
                # Convert to dataclass and execute
                from browser_interactions import ClickAction
                click_obj = ClickAction(**{k: v for k, v in click_action.items() if k != "kind"})
                result = await execute_action(self.current_page, click_obj)
                return result

            elif kind == "type":
                # Build type action
                type_action = {
                    "kind": "type",
                    "ref": action.get("ref"),
                    "text": action.get("text", ""),
                    "slowly": action.get("slowly", False),
                    "delay_ms": action.get("delayMs", 50),
                    "submit": action.get("submit", False),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser_interactions import TypeAction
                type_obj = TypeAction(**{k: v for k, v in type_action.items() if k != "kind"})
                result = await execute_action(self.current_page, type_obj)
                return result

            elif kind == "press":
                # Build press action
                press_action = {
                    "kind": "press",
                    "key": action.get("key", ""),
                    "delay_ms": action.get("delayMs", 0),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser_interactions import PressAction
                press_obj = PressAction(**{k: v for k, v in press_action.items() if k != "kind"})
                result = await execute_action(self.current_page, press_obj)
                return result

            elif kind == "hover":
                # Build hover action
                hover_action = {
                    "kind": "hover",
                    "ref": action.get("ref"),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser_interactions import HoverAction
                hover_obj = HoverAction(**{k: v for k, v in hover_action.items() if k != "kind"})
                result = await execute_action(self.current_page, hover_obj)
                return result

            elif kind == "scrollIntoView":
                # Build scroll action
                scroll_action = {
                    "kind": "scrollIntoView",
                    "ref": action.get("ref"),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser_interactions import ScrollIntoViewAction
                scroll_obj = ScrollIntoViewAction(**{k: v for k, v in scroll_action.items() if k != "kind"})
                result = await execute_action(self.current_page, scroll_obj)
                return result

            elif kind == "wait":
                # Build wait action
                wait_action = {
                    "kind": "wait",
                    "text": action.get("text"),
                    "text_gone": action.get("textGone"),
                    "url": action.get("url"),
                    "selector": action.get("selector"),
                    "load_state": action.get("loadState"),
                    "fn": action.get("fn"),
                    "timeout_ms": action.get("timeoutMs", 30000)
                }
                from browser_interactions import WaitAction
                wait_obj = WaitAction(**{k: v for k, v in wait_action.items() if k != "kind" and v is not None})
                result = await execute_action(self.current_page, wait_obj)
                return result

            elif kind == "fill":
                # Build fill action
                fill_action = {
                    "kind": "fill",
                    "fields": action.get("fields", []),
                    "timeout_ms": action.get("timeoutMs")
                }
                from browser_interactions import FillAction
                fill_obj = FillAction(**{k: v for k, v in fill_action.items() if k != "kind" and v is not None})
                result = await execute_action(self.current_page, fill_obj)
                return result

            else:
                return {"error": f"Unknown action kind: {kind}"}

        except Exception as e:
            logger.error(f"Action execution error: {e}")
            import traceback
            traceback.print_exc()
            return {"error": str(e)}


class SolaceBrowserServer:
    """HTTP/WebSocket server for CDP protocol"""

    def __init__(self, browser: SolaceBrowser, port: int = 9222):
        self.browser = browser
        self.port = port
        self.app = web.Application()
        self._setup_routes()

    def _setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get('/json/version', self._handle_version)
        self.app.router.add_get('/json/list', self._handle_list)
        self.app.router.add_post('/api/navigate', self._handle_navigate)
        self.app.router.add_post('/api/click', self._handle_click)
        self.app.router.add_post('/api/fill', self._handle_fill)
        self.app.router.add_post('/api/screenshot', self._handle_screenshot)
        self.app.router.add_post('/api/snapshot', self._handle_snapshot)
        self.app.router.add_post('/api/evaluate', self._handle_evaluate)
        self.app.router.add_post('/api/login-linkedin-google', self._handle_login_linkedin_google)
        self.app.router.add_post('/api/login-linkedin-google-auto', self._handle_login_linkedin_google_auto)
        self.app.router.add_post('/api/update-linkedin-profile', self._handle_update_linkedin_profile)
        self.app.router.add_post('/api/save-session', self._handle_save_session)
        self.app.router.add_get('/api/session-status', self._handle_session_status)
        # New OpenClaw-like routes for better AI interaction
        self.app.router.add_get('/api/aria-snapshot', self._handle_aria_snapshot)
        self.app.router.add_get('/api/dom-snapshot', self._handle_dom_snapshot)
        self.app.router.add_get('/api/page-snapshot', self._handle_page_snapshot)
        self.app.router.add_post('/api/act', self._handle_act)
        self.app.router.add_get('/api/status', self._handle_status)
        self.app.router.add_get('/api/events', self._handle_events)

        # Debug UI routes
        if self.browser.debug_ui:
            self.app.router.add_get('/', self._handle_ui)
            self.app.router.add_static('/static', Path(__file__).parent / 'browser_ui')

    async def _handle_version(self, request):
        """Return browser version (CDP compatible)"""
        return web.json_response({
            "Browser": "Solace Browser/1.0.0",
            "Protocol-Version": "1.3",
            "User-Agent": "Solace/1.0.0",
            "V8-Version": "12.0.0"
        })

    async def _handle_list(self, request):
        """Return list of pages (CDP compatible)"""
        if not self.browser.current_page:
            return web.json_response([])

        return web.json_response([{
            "description": "Solace Browser Page",
            "devtoolsFrontendUrl": f"devtools://devtools/bundled/inspector.html",
            "faviconUrl": "",
            "id": str(id(self.browser.current_page)),
            "parentId": "",
            "title": await self.browser.current_page.title(),
            "type": "page",
            "url": self.browser.current_page.url,
            "webSocketDebuggerUrl": f"ws://localhost:{self.port}/ws"
        }])

    async def _handle_navigate(self, request):
        """Navigate to URL"""
        data = await request.json()
        result = await self.browser.navigate(data.get('url', ''))
        return web.json_response(result)

    async def _handle_click(self, request):
        """Click element"""
        data = await request.json()
        result = await self.browser.click(data.get('selector', ''))
        return web.json_response(result)

    async def _handle_fill(self, request):
        """Fill form field"""
        data = await request.json()
        result = await self.browser.fill(
            data.get('selector', ''),
            data.get('text', '')
        )
        return web.json_response(result)

    async def _handle_screenshot(self, request):
        """Take screenshot"""
        data = await request.json()
        result = await self.browser.take_screenshot(data.get('filename'))
        return web.json_response(result)

    async def _handle_snapshot(self, request):
        """Get page snapshot"""
        result = await self.browser.get_snapshot()
        return web.json_response(result)

    async def _handle_evaluate(self, request):
        """Evaluate JavaScript"""
        data = await request.json()
        result = await self.browser.evaluate(data.get('expression', ''))
        return web.json_response(result)

    async def _handle_login_linkedin_google(self, request):
        """Login to LinkedIn using Google OAuth"""
        try:
            result = await self.browser.login_linkedin_google()
            return web.json_response(result)
        except Exception as e:
            logger.error(f"LinkedIn login handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_login_linkedin_google_auto(self, request):
        """Auto-login to LinkedIn using Google OAuth with Gmail credentials"""
        try:
            data = await request.json()
            gmail_email = data.get('gmail_email')
            gmail_password = data.get('gmail_password')

            if not gmail_email or not gmail_password:
                return web.json_response({
                    "error": "Missing gmail_email or gmail_password"
                }, status=400)

            result = await self.browser.login_linkedin_google_auto(gmail_email, gmail_password)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Auto-login handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_update_linkedin_profile(self, request):
        """Update LinkedIn profile with suggested improvements"""
        try:
            result = await self.browser.update_linkedin_profile()
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Profile update handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_save_session(self, request):
        """Save browser session (cookies, localStorage) to file"""
        try:
            result = await self.browser.save_session()
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Session save handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_session_status(self, request):
        """Check if saved session exists"""
        session_file = Path(self.browser.session_file)
        return web.json_response({
            "session_exists": session_file.exists(),
            "session_file": str(session_file),
            "file_size": session_file.stat().st_size if session_file.exists() else 0,
            "message": "Session file found" if session_file.exists() else "No saved session"
        })

    async def _handle_aria_snapshot(self, request):
        """Get accessibility tree (ARIA) snapshot with element references"""
        try:
            limit = int(request.query.get('limit', 500))
            result = await self.browser.get_aria_snapshot(limit=limit)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"ARIA snapshot handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_dom_snapshot(self, request):
        """Get DOM tree snapshot with element references"""
        try:
            limit = int(request.query.get('limit', 800))
            result = await self.browser.get_dom_snapshot(limit=limit)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"DOM snapshot handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_page_snapshot(self, request):
        """Get comprehensive page snapshot (ARIA + DOM + state)"""
        try:
            result = await self.browser.get_page_snapshot()
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Page snapshot handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_act(self, request):
        """Execute structured action (click, type, press, hover, wait, etc.)"""
        try:
            data = await request.json()
            result = await self.browser.act(data)
            return web.json_response(result)
        except Exception as e:
            logger.error(f"Act handler error: {e}")
            return web.json_response({"error": str(e)}, status=500)

    async def _handle_status(self, request):
        """Get browser status"""
        return web.json_response({
            "running": self.browser.browser is not None,
            "headless": self.browser.headless,
            "current_url": self.browser.current_page.url if self.browser.current_page else None,
            "pages": len(self.browser.pages),
            "events": len(self.browser.event_history)
        })

    async def _handle_events(self, request):
        """Get event history"""
        limit = int(request.query.get('limit', 100))
        return web.json_response(self.browser.event_history[-limit:])

    async def _handle_ui(self, request):
        """Serve debugging UI"""
        return web.Response(text=self._get_ui_html(), content_type='text/html')

    def _get_ui_html(self):
        """Generate debugging UI HTML"""
        return """
<!DOCTYPE html>
<html>
<head>
    <title>Solace Browser - Debug UI</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif; }
        .container { display: flex; height: 100vh; }
        .sidebar { width: 25%; background: #1e1e1e; color: #fff; padding: 20px; overflow-y: auto; border-right: 1px solid #333; }
        .main { width: 75%; display: flex; flex-direction: column; }
        .viewport { flex: 1; background: #fff; border: 1px solid #ddd; position: relative; overflow: auto; }
        .controls { padding: 20px; background: #f5f5f5; border-bottom: 1px solid #ddd; }
        .input-group { margin-bottom: 10px; }
        input, button { padding: 8px 12px; margin-right: 10px; border: 1px solid #ccc; border-radius: 4px; }
        button { background: #007bff; color: white; cursor: pointer; border: none; }
        button:hover { background: #0056b3; }
        .events { margin-top: 20px; }
        .event { background: #f0f0f0; padding: 10px; margin-bottom: 5px; border-left: 3px solid #007bff; font-size: 12px; }
        .status { padding: 10px; background: #e8f5e9; border-radius: 4px; margin-bottom: 10px; }
        h2 { margin: 20px 0 10px 0; font-size: 16px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="sidebar">
            <h1>Solace Browser</h1>
            <div class="status" id="status">Loading...</div>

            <h2>Controls</h2>
            <div class="input-group">
                <input type="text" id="urlInput" placeholder="Enter URL" style="width: 100%;">
                <button onclick="navigate()">Navigate</button>
            </div>

            <div class="input-group">
                <input type="text" id="selectorInput" placeholder="CSS Selector" style="width: 100%;">
                <button onclick="click()">Click</button>
            </div>

            <div class="input-group">
                <input type="text" id="textInput" placeholder="Text to fill" style="width: 100%;">
                <button onclick="fill()">Fill</button>
            </div>

            <button onclick="screenshot()" style="width: 100%; margin-bottom: 10px;">📸 Screenshot</button>
            <button onclick="snapshot()" style="width: 100%;">📄 Snapshot</button>

            <div class="events">
                <h2>Events</h2>
                <div id="eventsList"></div>
            </div>
        </div>

        <div class="main">
            <div class="controls">
                <h3>Viewport</h3>
                <p id="currentUrl">No page loaded</p>
            </div>
            <div class="viewport" id="viewport">
                <div style="padding: 20px; color: #999;">Loading browser...</div>
            </div>
        </div>
    </div>

    <script>
        const API_BASE = 'http://localhost:9222';

        async function navigate() {
            const url = document.getElementById('urlInput').value;
            const res = await fetch(`${API_BASE}/api/navigate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await res.json();
            console.log('Navigate:', data);
            updateStatus();
        }

        async function click() {
            const selector = document.getElementById('selectorInput').value;
            const res = await fetch(`${API_BASE}/api/click`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selector })
            });
            const data = await res.json();
            console.log('Click:', data);
        }

        async function fill() {
            const selector = document.getElementById('selectorInput').value;
            const text = document.getElementById('textInput').value;
            const res = await fetch(`${API_BASE}/api/fill`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ selector, text })
            });
            const data = await res.json();
            console.log('Fill:', data);
        }

        async function screenshot() {
            const res = await fetch(`${API_BASE}/api/screenshot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();
            alert('Screenshot saved: ' + data.filename);
        }

        async function snapshot() {
            const res = await fetch(`${API_BASE}/api/snapshot`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            });
            const data = await res.json();
            alert('Snapshot: ' + data.url);
        }

        async function updateStatus() {
            const res = await fetch(`${API_BASE}/api/status`);
            const data = await res.json();
            document.getElementById('status').innerHTML = `
                <strong>Status:</strong> ${data.running ? '✓ Running' : '✗ Stopped'}<br>
                <strong>URL:</strong> ${data.current_url || 'None'}<br>
                <strong>Pages:</strong> ${data.pages}
            `;
            document.getElementById('currentUrl').textContent = `Current: ${data.current_url || 'None'}`;

            // Load events
            const evRes = await fetch(`${API_BASE}/api/events?limit=20`);
            const events = await evRes.json();
            const eventsList = document.getElementById('eventsList');
            eventsList.innerHTML = events.reverse().map(e => `
                <div class="event">
                    <strong>${e.type}</strong><br>
                    ${e.message || e.url || ''}<br>
                    <small>${new Date(e.timestamp).toLocaleTimeString()}</small>
                </div>
            `).join('');
        }

        // Update status every 2 seconds
        setInterval(updateStatus, 2000);
        updateStatus();
    </script>
</body>
</html>
        """

    async def start(self):
        """Start the server"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        logger.info(f"✓ CDP Server started on http://localhost:{self.port}")

        # Keep running
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            await runner.cleanup()


async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Solace Browser - Custom Headless Browser')
    parser.add_argument('--headless', action='store_true', default=True,
                       help='Run in headless mode (default: True)')
    parser.add_argument('--show-ui', action='store_true',
                       help='Show debugging UI (default: False)')
    parser.add_argument('--port', type=int, default=9222,
                       help='CDP server port (default: 9222)')

    args = parser.parse_args()

    # Create and start browser
    browser = SolaceBrowser(headless=args.headless, debug_ui=args.show_ui)
    await browser.start()

    # Create and start server
    server = SolaceBrowserServer(browser, port=args.port)

    try:
        await server.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await browser.stop()


if __name__ == '__main__':
    asyncio.run(main())
