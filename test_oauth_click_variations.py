#!/usr/bin/env python3

"""
Test different ways to click the Google button
to find which one reliably opens the popup
"""

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_click_method(method_name, click_func):
    """Test a specific click method"""

    print(f"\n{'=' * 80}")
    print(f"Testing: {method_name}")
    print(f"{'=' * 80}\n")

    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("Navigate to LinkedIn login...")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)
    print("✓ Loaded\n")

    print(f"Executing click method: {method_name}...")
    try:
        success = await click_func(browser.current_page)
        print(f"✓ Click executed: {success}\n")
    except Exception as e:
        print(f"✗ Error: {e}\n")
        await browser.stop()
        return False

    print("Waiting 3 seconds for popup to appear...\n")
    await asyncio.sleep(3)

    # Check if popup opened
    current_url = browser.current_page.url
    print(f"Main page URL: {current_url}")

    if "google" in current_url.lower():
        print("✅ POPUP WORKED - Page redirected to Google!")
        result = True
    else:
        print("⚠️  No visible redirect (popup might still be behind)")
        result = None

    await browser.current_page.screenshot(path=f"artifacts/click-test-{method_name.replace(' ', '-').lower()}.png")
    await browser.stop()

    return result


async def main():
    """Test all click variations"""

    print("\n" + "=" * 80)
    print("GOOGLE OAUTH CLICK METHOD VARIATIONS")
    print("=" * 80)

    methods = [
        {
            "name": "Method 1: Click Google container div",
            "func": lambda page: page.query_selector("div.alternate-signin__btn--google").then(
                lambda btn: btn.click() if btn else None
            )
        },
        {
            "name": "Method 2: Click Google iframe",
            "func": lambda page: page.query_selector("iframe[title='Sign in with Google Button']").then(
                lambda iframe: iframe.click() if iframe else None
            )
        },
        {
            "name": "Method 3: Force click container",
            "func": lambda page: page.query_selector("div.alternate-signin__btn--google").then(
                lambda btn: btn.click(force=True) if btn else None
            )
        },
        {
            "name": "Method 4: Force click with delay",
            "func": lambda page: page.query_selector("div.alternate-signin__btn--google").then(
                lambda btn: btn.click(force=True, delay=100) if btn else None
            )
        },
        {
            "name": "Method 5: Double click container",
            "func": lambda page: page.query_selector("div.alternate-signin__btn--google").then(
                lambda btn: btn.dblclick() if btn else None
            )
        },
        {
            "name": "Method 6: JavaScript .click()",
            "func": lambda page: page.evaluate(
                "() => { const btn = document.querySelector('div.alternate-signin__btn--google'); if(btn) btn.click(); }"
            )
        },
        {
            "name": "Method 7: JavaScript on iframe",
            "func": lambda page: page.evaluate(
                "() => { const iframe = document.querySelector('iframe[title=\"Sign in with Google Button\"]'); if(iframe) iframe.click(); }"
            )
        },
        {
            "name": "Method 8: Find and click first button",
            "func": lambda page: page.query_selector("button").then(
                lambda btn: btn.click() if btn else None
            )
        },
    ]

    results = {}

    # Test each method
    for method in methods:
        try:
            # Convert promise-like syntax to async
            async def click_method(page):
                if "div.alternate-signin__btn--google" in method["name"]:
                    btn = await page.query_selector("div.alternate-signin__btn--google")
                    if btn:
                        if "force" in method["name"]:
                            if "delay" in method["name"]:
                                await btn.click(force=True, delay=100)
                            else:
                                await btn.click(force=True)
                        elif "double" in method["name"].lower():
                            await btn.dblclick()
                        else:
                            await btn.click()
                elif "iframe" in method["name"] and "javascript" not in method["name"].lower():
                    iframe = await page.query_selector("iframe[title='Sign in with Google Button']")
                    if iframe:
                        await iframe.click()
                elif "JavaScript" in method["name"] and "iframe" in method["name"]:
                    await page.evaluate(
                        "() => { const iframe = document.querySelector('iframe[title=\"Sign in with Google Button\"]'); if(iframe) iframe.click(); }"
                    )
                elif "JavaScript" in method["name"]:
                    await page.evaluate(
                        "() => { const btn = document.querySelector('div.alternate-signin__btn--google'); if(btn) btn.click(); }"
                    )
                elif "first button" in method["name"]:
                    btn = await page.query_selector("button")
                    if btn:
                        await btn.click()
                return True

            result = await test_click_method(method["name"], click_method)
            results[method["name"]] = "✅ WORKED" if result else "⚠️  UNCERTAIN" if result is None else "❌ FAILED"

        except Exception as e:
            results[method["name"]] = f"❌ ERROR: {str(e)[:50]}"

    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80 + "\n")

    for method, result in results.items():
        print(f"{result} - {method}")

    print(f"\n{'=' * 80}")
    print("RECOMMENDATION")
    print(f"{'=' * 80}\n")

    successful = [m for m, r in results.items() if "✅" in r]
    if successful:
        print(f"✅ These methods worked:")
        for m in successful:
            print(f"   - {m}")
    else:
        print("⚠️  No clearly successful methods detected")
        print("   The popup may be opening but not visible in main page URL")
        print("   Try running with 'headless=False' and watch for popup windows")


if __name__ == "__main__":
    asyncio.run(main())
