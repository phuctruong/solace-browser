#!/usr/bin/env python3

"""
LINKEDIN - SMART GOOGLE OAUTH LOGIN
Finds and clicks the Google button using intelligent detection
"""

import asyncio
import os
import sys

if not os.environ.get('DISPLAY'):
    os.environ['DISPLAY'] = ':1'

try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: Playwright not installed")
    sys.exit(1)


async def main():
    print("\n" + "=" * 80)
    print("LINKEDIN - GOOGLE OAUTH LOGIN (SMART METHOD)")
    print("=" * 80 + "\n")

    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()
    page = await context.new_page()

    try:
        # Step 1: Open LinkedIn login
        print("STEP 1: Opening LinkedIn login page...")
        await page.goto("https://www.linkedin.com/login", wait_until='domcontentloaded')
        await asyncio.sleep(2)
        print("✓ Page loaded\n")

        # Get all buttons and their content
        print("STEP 2: Analyzing page for Google button...")
        all_buttons = await page.query_selector_all("button, a[role='button'], div[role='button']")

        print(f"Found {len(all_buttons)} interactive elements\n")

        google_element = None

        # Look through all elements
        for i, element in enumerate(all_buttons):
            # Get the full text content and HTML
            text = await element.text_content()
            html = await element.get_attribute('innerHTML')

            if text:
                text_lower = text.lower().strip()
                print(f"{i+1}. {text_lower[:50]}")

                # Check if this element contains Google
                if 'google' in text_lower:
                    print(f"   ↳ FOUND GOOGLE BUTTON!")
                    google_element = element
                    break

            if html and 'google' in html.lower():
                if 'google' in text.lower() if text else True:
                    print(f"{i+1}. [Google element found in HTML]")
                    google_element = element
                    break

        if not google_element:
            print("\n❌ Google button not found in current elements")
            print("\nTrying to find using SVG or image-based buttons...")

            # Try to find by aria-label
            elements = await page.query_selector_all("[aria-label*='google' i], [aria-label*='Google']")
            if elements:
                print(f"✓ Found {len(elements)} element(s) with Google aria-label")
                google_element = elements[0]

        if not google_element:
            # Try JavaScript evaluation
            print("\nUsing JavaScript to find Google button...")
            google_element = await page.evaluate("""
                () => {
                    const elements = Array.from(document.querySelectorAll('button, a, div[role="button"]'));
                    for (let el of elements) {
                        if ((el.textContent || el.innerText || '').toLowerCase().includes('google') ||
                            el.innerHTML.toLowerCase().includes('google')) {
                            return el;
                        }
                    }
                    return null;
                }
            """)

        if google_element:
            print("✓ Google button found!\n")
        else:
            print("❌ Still cannot find Google button\n")

            # Take screenshot and show buttons
            print("Taking screenshot of page...")
            await page.screenshot(path="artifacts/linkedin-debug.png")

            print("Showing all button texts:")
            buttons = await page.query_selector_all("button")
            for btn in buttons[:10]:
                text = await btn.text_content()
                print(f"  - {text.strip() if text else '(empty)'}")

            return False

        # Step 3: Click the Google button
        print("STEP 3: Clicking Google button...\n")

        if isinstance(google_element, dict):
            # JavaScript returned element ref
            await page.evaluate("(el) => el.click()", google_element)
        else:
            # Playwright element
            await google_element.click()

        print("✓ Clicked!\n")

        await asyncio.sleep(3)
        await page.screenshot(path="artifacts/linkedin-google-clicked.png")

        # Step 4: Google OAuth page
        print("STEP 4: Google OAuth page loading...")
        print(f"Current URL: {page.url}\n")

        await page.wait_for_load_state('domcontentloaded')
        await asyncio.sleep(2)

        print("=" * 80)
        print("✅ SUCCESSFULLY CLICKED GOOGLE BUTTON!")
        print("=" * 80)
        print("\nGoogle OAuth page is now displayed in the browser.")
        print("\nYou can now:")
        print("  1. Enter your Gmail email")
        print("  2. Click Next")
        print("  3. Enter your Gmail password")
        print("  4. Allow LinkedIn to access your account")
        print("  5. You will be logged into LinkedIn")
        print("\nBrowser window is ready. Press Ctrl+C when done.\n")

        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass

        await page.screenshot(path="artifacts/linkedin-final-result.png")
        return True

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        await page.screenshot(path="artifacts/linkedin-error.png")
        return False

    finally:
        await browser.close()
        await playwright.stop()


if __name__ == '__main__':
    asyncio.run(main())
