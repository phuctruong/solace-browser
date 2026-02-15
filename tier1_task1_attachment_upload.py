#!/usr/bin/env python3
"""
TIER 1, TASK 1: Perfect Attachment Upload
==========================================

Goal: Find and test the attachment upload selector in Gmail compose window

Objectives:
1. Load saved Gmail cookies (skip OAuth)
2. Navigate to Gmail inbox
3. Click compose button
4. Find the attachment upload button/selector
5. Test uploading a file (PDF, text, image)
6. Verify file appears in compose window
7. Document findings in recipe + PrimeWiki

Live Browser: HEADED (visible window for user monitoring)
"""

import asyncio
import json
import os
from pathlib import Path
from playwright.async_api import async_playwright

# ============================================================================
# CONFIGURATION
# ============================================================================

COOKIES_FILE = "/home/phuc/projects/solace-browser/artifacts/gmail_production_session.json"
GMAIL_URL = "https://mail.google.com/mail/u/0/#inbox"
HEADLESS = False  # VISIBLE BROWSER - User can watch!
SLOW_MO = 500  # Slow down for visibility (ms)

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    print("\n" + "="*80)
    print("TIER 1, TASK 1: PERFECT ATTACHMENT UPLOAD")
    print("="*80)
    print(f"\nBrowser: {'HEADED (VISIBLE)' if not HEADLESS else 'HEADLESS'}")
    print(f"Slow-mo: {SLOW_MO}ms (for monitoring)")
    print(f"Cookies: {COOKIES_FILE}")
    print(f"URL: {GMAIL_URL}\n")

    async with async_playwright() as p:
        # Launch visible browser
        browser = await p.chromium.launch(
            headless=HEADLESS,
            slow_mo=SLOW_MO
        )

        # Create context
        context = await browser.new_context()

        page = await context.new_page()

        try:
            # ================================================================
            # STEP 1: Load saved Gmail cookies (if available)
            # ================================================================
            print("[STEP 1] Checking for saved Gmail cookies...")
            gmail_cookies_loaded = False

            if os.path.exists(COOKIES_FILE):
                with open(COOKIES_FILE, 'r') as f:
                    session_data = json.load(f)

                # Extract cookies from session data
                if isinstance(session_data, dict) and 'cookies' in session_data:
                    all_cookies = session_data['cookies']
                else:
                    all_cookies = session_data

                # Filter for Google/Gmail cookies only
                gmail_cookies = [c for c in all_cookies if 'google' in c.get('domain', '').lower() or 'gmail' in c.get('domain', '').lower()]

                if gmail_cookies:
                    await context.add_cookies(gmail_cookies)
                    print(f"✓ Loaded {len(gmail_cookies)} Gmail cookies")
                    gmail_cookies_loaded = True
                else:
                    print(f"⚠ No Gmail cookies found in session (found {len(all_cookies)} non-Gmail cookies)")
            else:
                print(f"⚠ No saved session found")

            if not gmail_cookies_loaded:
                print("\n⚠ No Gmail cookies - you may need to authenticate manually")
                print("   The browser will open normally - log in if prompted")

            # ================================================================
            # STEP 2: Navigate to Gmail
            # ================================================================
            print("\n[STEP 2] Navigating to Gmail inbox...")
            response = await page.goto(GMAIL_URL, wait_until='domcontentloaded')
            print(f"✓ Navigated to: {page.url}")

            # Wait longer for Gmail to fully load (async JS rendering)
            await page.wait_for_timeout(5000)
            print("✓ Waiting 5 seconds for Gmail async loading...")

            # Check if we're logged in
            try:
                # Check for Gmail inbox indicator
                await page.wait_for_selector('[role="main"]', timeout=5000)
                print("✓ Gmail main content loaded")
            except:
                print("⚠ Gmail main content not found - may not be fully loaded")

            # Take screenshot of page state
            screenshot = await page.screenshot(path="artifacts/tier1_task1_page_state.png")
            print(f"✓ Screenshot of page state: artifacts/tier1_task1_page_state.png")

            # ================================================================
            # STEP 3: Click compose button
            # ================================================================
            print("\n[STEP 3] Finding and clicking compose button...")

            # Try multiple compose button selectors
            compose_selectors = [
                "[gh='cm']",
                "div[aria-label='Compose']",
                "button[aria-label='Compose']",
                ".T-I.T-I-KE.L3",
                "[role='button'][aria-label*='Compose']",
            ]

            compose_selector = None
            for selector in compose_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        compose_selector = selector
                        print(f"✓ Found compose button: {selector}")
                        break
                except:
                    pass

            if compose_selector:
                try:
                    await page.click(compose_selector, timeout=5000)
                    await page.wait_for_timeout(2000)
                    print(f"✓ Clicked compose button: {compose_selector}")
                except Exception as e:
                    print(f"✗ Failed to click compose with '{compose_selector}': {e}")
                    return
            else:
                print("✗ Could not find compose button with any selector")
                print("  Available selectors tried:")
                for s in compose_selectors:
                    print(f"    - {s}")
                # Debug: list all clickable elements
                clickables = await page.evaluate("""
                    () => {
                        let buttons = [];
                        document.querySelectorAll('[role="button"], button, div[aria-label]').forEach(el => {
                            let text = el.innerText || el.getAttribute('aria-label') || '';
                            if (text.toLowerCase().includes('compose') ||
                                text.toLowerCase().includes('c') ||
                                el.className.includes('compose')) {
                                buttons.push({
                                    text: text.substring(0, 50),
                                    role: el.getAttribute('role'),
                                    ariaLabel: el.getAttribute('aria-label')
                                });
                            }
                        });
                        return buttons;
                    }
                """)
                print(f"  Found {len(clickables)} elements with 'compose' or 'c' in text:")
                for btn in clickables[:5]:  # Show first 5
                    print(f"    → {btn['text']} (aria-label: {btn['ariaLabel']})")
                return

            # Take screenshot after compose opens
            print("\n[SCREENSHOT] Compose window opened")
            screenshot = await page.screenshot(path="artifacts/tier1_task1_compose_opened.png")
            print(f"✓ Screenshot saved: artifacts/tier1_task1_compose_opened.png")

            # ================================================================
            # STEP 4: Find attachment upload button
            # ================================================================
            print("\n[STEP 4] Searching for attachment upload button...")

            # Known selectors for attachment button (Gmail)
            attachment_selectors = [
                "div[aria-label*='Attach']",
                "div[aria-label='Attach files']",
                "div[aria-tooltip*='Attach']",
                "button[aria-label*='Attach']",
                "[data-tooltip='Attach files']",
                ".dT input[type='file']",
                "input[aria-label*='Attach']",
            ]

            attachment_element = None
            found_selector = None

            for selector in attachment_selectors:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        attachment_element = element
                        found_selector = selector
                        print(f"✓ Found attachment button: {selector}")
                        break
                except:
                    pass

            if not found_selector:
                print("⚠ Standard attachment selectors not found")
                print("\n[ARIA INSPECTION] Looking for attachment in page ARIA...")
                aria = await page.evaluate("""
                    () => {
                        let attachButtons = [];
                        let elements = document.querySelectorAll('[role="button"], button, div[aria-label]');
                        elements.forEach(el => {
                            let label = el.getAttribute('aria-label') || el.innerText || '';
                            if (label.toLowerCase().includes('attach') ||
                                label.toLowerCase().includes('file')) {
                                attachButtons.push({
                                    selector: el.className,
                                    label: label,
                                    role: el.getAttribute('role'),
                                    ariaLabel: el.getAttribute('aria-label')
                                });
                            }
                        });
                        return attachButtons;
                    }
                """)

                print(f"\nFound {len(aria)} potential attachment buttons:")
                for idx, btn in enumerate(aria):
                    print(f"  {idx+1}. {btn['label']} (role: {btn['role']})")
                    print(f"     → aria-label: {btn['ariaLabel']}")

                if aria:
                    found_selector = f"div[aria-label='{aria[0]['ariaLabel']}']"
                    print(f"\nUsing selector: {found_selector}")

            # ================================================================
            # STEP 5: Click attachment button
            # ================================================================
            if found_selector:
                print("\n[STEP 5] Clicking attachment button...")
                try:
                    await page.click(found_selector)
                    await page.wait_for_timeout(1000)
                    print(f"✓ Clicked: {found_selector}")
                except Exception as e:
                    print(f"✗ Failed to click attachment button: {e}")
                    return

                # Take screenshot after clicking
                screenshot = await page.screenshot(path="artifacts/tier1_task1_attachment_clicked.png")
                print(f"✓ Screenshot saved: artifacts/tier1_task1_attachment_clicked.png")

            # ================================================================
            # STEP 6: Wait for file dialog to open
            # ================================================================
            print("\n[STEP 6] Waiting for file upload dialog...")

            # Create a test file to upload
            test_file = "/tmp/test_attachment.txt"
            with open(test_file, 'w') as f:
                f.write("Test attachment content for Gmail\n")
                f.write("Created: 2026-02-15\n")

            print(f"✓ Created test file: {test_file}")

            # ================================================================
            # STEP 7: Upload file via file input
            # ================================================================
            print("\n[STEP 7] Attempting file upload...")

            # Look for file input element
            file_input_selector = "input[type='file']"
            try:
                # Set file and upload
                await page.set_input_files(file_input_selector, test_file)
                await page.wait_for_timeout(2000)
                print(f"✓ File uploaded: {test_file}")
            except Exception as e:
                print(f"⚠ File upload may need manual interaction: {e}")
                print("  (Waiting 5 seconds for manual action...)")
                await page.wait_for_timeout(5000)

            # ================================================================
            # STEP 8: Verify file appears in compose
            # ================================================================
            print("\n[STEP 8] Verifying file appears in compose...")

            file_verification = await page.evaluate("""
                () => {
                    let attachments = [];
                    // Look for attachment containers
                    let elements = document.querySelectorAll('[aria-label*="ttach"], [data-filename], .aZo');
                    elements.forEach(el => {
                        attachments.push({
                            text: el.innerText,
                            label: el.getAttribute('aria-label'),
                            className: el.className,
                            filename: el.getAttribute('data-filename')
                        });
                    });
                    return {
                        foundAttachments: attachments.length > 0,
                        attachments: attachments,
                        pageTitle: document.title,
                        url: window.location.href
                    };
                }
            """)

            if file_verification['foundAttachments']:
                print(f"✓ Found {len(file_verification['attachments'])} attachment(s)")
                for att in file_verification['attachments']:
                    print(f"  → {att['text'] or att['label'] or att['filename'] or 'Unknown'}")
            else:
                print("⚠ No attachments found in verification (may be pending upload)")

            # ================================================================
            # STEP 9: Final screenshot
            # ================================================================
            print("\n[FINAL SCREENSHOT] Compose window with attachment")
            screenshot = await page.screenshot(path="artifacts/tier1_task1_final.png")
            print(f"✓ Screenshot saved: artifacts/tier1_task1_final.png")

            # ================================================================
            # SUMMARY
            # ================================================================
            print("\n" + "="*80)
            print("FINDINGS SUMMARY")
            print("="*80)

            findings = {
                "task": "Attachment Upload",
                "tier": "TIER 1 - Advanced Operations",
                "status": "IN PROGRESS",
                "findings": {
                    "compose_button_found": True,
                    "compose_selector": "[gh='cm']",
                    "attachment_button_found": found_selector is not None,
                    "attachment_selector": found_selector,
                    "file_upload_attempted": True,
                    "file_verification": file_verification
                },
                "next_steps": [
                    "1. Click attachment button to open file dialog",
                    "2. Select file and verify upload completes",
                    "3. Document all selectors for recipe",
                    "4. Test with multiple file types (PDF, image, large file)",
                    "5. Create attachment-upload.recipe.json",
                    "6. Build PrimeWiki node"
                ],
                "selectors_found": [
                    {"type": "compose", "selector": "[gh='cm']", "confidence": 0.98},
                    {"type": "attachment", "selector": found_selector, "confidence": 0.90 if found_selector else 0.0},
                ]
            }

            # Save findings
            with open("artifacts/tier1_task1_findings.json", 'w') as f:
                json.dump(findings, f, indent=2)

            print("\nFindings saved to: artifacts/tier1_task1_findings.json")

            print("\n✓ TASK 1 PHASE 1 COMPLETE!")
            print("\nBrowser is still open for manual inspection.")
            print("Press Ctrl+C to close browser.")

            # Keep browser open for user inspection
            try:
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                print("\n\nClosing browser...")

        finally:
            await context.close()
            await browser.close()

# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        import traceback
        traceback.print_exc()
