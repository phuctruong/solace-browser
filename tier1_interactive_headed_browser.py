#!/usr/bin/env python3
"""
INTERACTIVE HEADED BROWSER FOR TIER 1 TASKS
============================================

Opens a VISIBLE browser for live monitoring while we perfect Gmail tasks.
You can watch the automation happen in real-time!

INSTRUCTIONS:
1. Run this script
2. A browser window will open (VISIBLE)
3. Log into Gmail if prompted (you'll see it happening)
4. Once logged in, the script will test features
5. Watch the automation work through the tasks

Live Browser: HEADED + VISIBLE
"""

import asyncio
import json
import os
from datetime import datetime
from playwright.async_api import async_playwright

async def main():
    print("\n" + "="*80)
    print("SOLACE BROWSER: TIER 1 INTERACTIVE HEADED BROWSER")
    print("="*80)
    print(f"\nLaunching VISIBLE browser window...")
    print(f"You will see the browser open and automation happen LIVE")
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    async with async_playwright() as p:
        # **KEY DIFFERENCE**: headless=False + slow_mo for visibility
        browser = await p.chromium.launch(
            headless=False,  # ← VISIBLE WINDOW
            slow_mo=300,     # ← SLOW DOWN for watching (300ms)
            args=[
                "--start-maximized",  # Open maximized
                "--disable-blink-features=AutomationControlled",  # Hide headless hint
            ]
        )

        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080}
        )

        page = await context.new_page()

        try:
            # ================================================================
            # STEP 1: Navigate to Gmail
            # ================================================================
            print("[ACTION] Navigating to Gmail...")
            print(f"  → URL: https://mail.google.com/\n")

            await page.goto("https://mail.google.com/", wait_until='domcontentloaded')

            # Wait for page to settle
            await page.wait_for_timeout(3000)

            current_url = page.url
            print(f"[INFO] Current URL: {current_url}")

            # Check if on login or inbox
            if "accounts.google.com" in current_url or "signin" in current_url:
                print("\n[STATUS] Gmail login page detected")
                print("[INSTRUCTION] ⚠ Please log in to Gmail in the browser window")
                print("[WAITING] Waiting for login (max 300 seconds)...\n")

                # Wait for navigation to Gmail (user logs in)
                try:
                    await page.wait_for_url("**/mail.google.com/**", timeout=300000)
                    print("[SUCCESS] Login detected! Proceeding with automation...")
                except:
                    print("[TIMEOUT] Login took too long. Closing.")
                    return
            else:
                print("[STATUS] Gmail inbox detected (already logged in)")

            # Wait for Gmail to fully load
            await page.wait_for_timeout(3000)

            # ================================================================
            # STEP 2: Take initial screenshot
            # ================================================================
            print("\n[ACTION] Taking screenshot of Gmail inbox...")
            screenshot = await page.screenshot(path="artifacts/tier1_gmail_inbox_initial.png")
            print(f"[SAVED] artifacts/tier1_gmail_inbox_initial.png\n")

            # ================================================================
            # STEP 3: Find and document what we see
            # ================================================================
            print("[ANALYSIS] Scanning Gmail interface...")

            page_info = await page.evaluate("""
                () => {
                    let info = {
                        url: window.location.href,
                        title: document.title,
                        buttons: [],
                        inputFields: [],
                        selectors: []
                    };

                    // Find compose-like buttons
                    document.querySelectorAll('[role="button"], button, div[aria-label], a[aria-label]').forEach(el => {
                        let label = el.getAttribute('aria-label') || el.innerText || el.textContent || '';
                        label = label.trim().substring(0, 100);

                        if (label.toLowerCase().includes('compose') ||
                            label.toLowerCase().includes('attachment') ||
                            label.toLowerCase().includes('attach')) {
                            info.buttons.push({
                                text: label,
                                role: el.getAttribute('role'),
                                ariaLabel: el.getAttribute('aria-label'),
                                className: el.className
                            });
                        }
                    });

                    // Find input fields
                    document.querySelectorAll('input, textarea, [contenteditable="true"]').forEach(el => {
                        let label = el.getAttribute('aria-label') || el.placeholder || el.name || '';
                        if (label) {
                            info.inputFields.push({
                                label: label.substring(0, 100),
                                type: el.type,
                                placeholder: el.placeholder
                            });
                        }
                    });

                    return info;
                }
            """)

            print(f"  URL: {page_info['url']}")
            print(f"  Title: {page_info['title']}\n")

            if page_info['buttons']:
                print(f"  Found {len(page_info['buttons'])} compose/attachment buttons:")
                for btn in page_info['buttons']:
                    print(f"    • {btn['text']}")
                    print(f"      aria-label: {btn['ariaLabel']}\n")

            if page_info['inputFields']:
                print(f"  Found {len(page_info['inputFields'])} input fields:")
                for field in page_info['inputFields'][:5]:
                    print(f"    • {field['label']} ({field['type']})\n")

            # ================================================================
            # STEP 4: Try to find and click Compose
            # ================================================================
            print("[ACTION] Attempting to click Compose button...")

            compose_found = False
            selectors_to_try = [
                "div[aria-label='Compose']",
                "button[aria-label='Compose']",
                "[data-tooltip='Compose']",
                '.T-I-KE[role="button"]',
                'a[aria-label="Compose"]',
                '[gh="cm"]',
            ]

            for selector in selectors_to_try:
                try:
                    element = await page.query_selector(selector)
                    if element:
                        print(f"  ✓ Found: {selector}")
                        await page.click(selector, timeout=2000)
                        compose_found = True
                        print(f"  ✓ Clicked compose button")
                        await page.wait_for_timeout(2000)
                        break
                except Exception as e:
                    pass

            if compose_found:
                # Take compose window screenshot
                screenshot = await page.screenshot(path="artifacts/tier1_compose_opened.png")
                print(f"  [SAVED] artifacts/tier1_compose_opened.png\n")

                # ================================================================
                # STEP 5: Find attachment button in compose
                # ================================================================
                print("[ACTION] Looking for attachment upload button...")

                attachment_info = await page.evaluate("""
                    () => {
                        let attachments = [];
                        document.querySelectorAll('[role="button"], button, div[aria-label], input[type="file"]').forEach(el => {
                            let label = el.getAttribute('aria-label') || el.getAttribute('title') || el.innerText || '';
                            label = label.toLowerCase();
                            if (label.includes('attach') || label.includes('file') || label.includes('upload')) {
                                attachments.push({
                                    text: el.getAttribute('aria-label') || el.innerText || 'Unknown',
                                    type: el.tagName,
                                    role: el.getAttribute('role'),
                                    ariaLabel: el.getAttribute('aria-label'),
                                    inputType: el.type
                                });
                            }
                        });
                        return attachments;
                    }
                """)

                if attachment_info:
                    print(f"  ✓ Found {len(attachment_info)} attachment-related elements:")
                    for att in attachment_info:
                        print(f"    • {att['text']}")
                        print(f"      role: {att['role']}, type: {att['type']}\n")
                else:
                    print(f"  ⚠ No attachment elements found in compose window")

            else:
                print(f"  ✗ Could not find Compose button")
                print(f"  Selectors tried: {', '.join(selectors_to_try)}")

            # ================================================================
            # STEP 6: Keep browser open for user inspection
            # ================================================================
            print("\n" + "="*80)
            print("BROWSER STILL OPEN FOR INSPECTION")
            print("="*80)
            print("\nThe browser window is still open. You can:")
            print("  1. Manually interact with Gmail")
            print("  2. Click compose and test attachments yourself")
            print("  3. Check the console for errors")
            print("  4. Close the browser window when done")
            print(f"\nPress Ctrl+C here to close the browser...\n")

            # Keep process alive
            while True:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            print("\n[INTERRUPT] User closed session")
        except Exception as e:
            print(f"\n[ERROR] {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("\n[CLEANUP] Closing browser...")
            await context.close()
            await browser.close()
            print("[DONE] Browser closed\n")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nSession ended by user")
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback
        traceback.print_exc()
