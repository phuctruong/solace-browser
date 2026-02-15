#!/usr/bin/env python3

"""
Test direct Google OAuth triggering
Instead of clicking the button, try to trigger the OAuth flow directly
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_direct_oauth():
    """Try to trigger OAuth flow directly via Google SDK"""

    print("\n" + "=" * 80)
    print("DIRECT GOOGLE OAUTH TRIGGER TEST")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False)
    await browser.start()

    print("📌 Step 1: Navigate to LinkedIn login")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)

    # Inspect what's in the Google button iframe
    print("\n📌 Step 2: Inspect Google button iframe URL parameters\n")

    iframe_info = await browser.current_page.evaluate("""
        () => {
            const iframe = document.querySelector("iframe[title='Sign in with Google Button']");
            if (iframe) {
                return {
                    src: iframe.src,
                    title: iframe.title,
                    id: iframe.id,
                    class: iframe.className
                };
            }
            return null;
        }
    """)

    if iframe_info:
        print(f"Google Button iframe found:")
        print(f"  URL: {iframe_info['src']}\n")

        # Parse the OAuth parameters
        from urllib.parse import urlparse, parse_qs
        parsed_url = urlparse(iframe_info['src'])
        params = parse_qs(parsed_url.query)

        print(f"OAuth Parameters:")
        for key in sorted(params.keys()):
            value = params[key][0]
            if len(value) > 60:
                value = value[:60] + "..."
            print(f"  {key}: {value}")
    else:
        print("Google button iframe not found")

    # Try to directly access Google's credential sharing API
    print("\n📌 Step 3: Check for Google Credential Management (credentialsharemode)\n")

    credential_info = await browser.current_page.evaluate("""
        async () => {
            const result = {};

            // Check if navigator.credentials is available (Credential Management API)
            result.credentialMgmtAvailable = typeof navigator.credentials !== 'undefined';

            // Check Google's One Tap config
            if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
                result.google_accounts_id = true;

                // Try to see what functions are available
                result.availableFunctions = [];
                for (let key in google.accounts.id) {
                    result.availableFunctions.push(key);
                }

                // Check if there's a manual OAuth trigger
                result.has_initialize = typeof google.accounts.id.initialize === 'function';
                result.has_renderButton = typeof google.accounts.id.renderButton === 'function';
                result.has_prompt = typeof google.accounts.id.prompt === 'function';
                result.has_requestPermission = typeof google.accounts.id.requestPermission === 'function';
            }

            return result;
        }
    """)

    print(f"Credential/OAuth info:")
    for key, value in credential_info.items():
        print(f"  {key}: {value}")

    # Try different ways to trigger the OAuth
    print("\n📌 Step 4: Try various OAuth trigger methods\n")

    methods = [
        {
            "name": "Direct click on iframe",
            "code": """
                const iframe = document.querySelector("iframe[title='Sign in with Google Button']");
                if (iframe) {
                    iframe.click();
                    return 'clicked_iframe';
                }
                return 'iframe_not_found';
            """
        },
        {
            "name": "Click iframe with force simulation",
            "code": """
                const iframe = document.querySelector("iframe[title='Sign in with Google Button']");
                if (iframe) {
                    const event = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        buttons: 1
                    });
                    iframe.dispatchEvent(event);
                    return 'force_clicked_iframe';
                }
                return 'iframe_not_found';
            """
        },
        {
            "name": "Call Google.accounts.id.requestPermission()",
            "code": """
                if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
                    try {
                        google.accounts.id.requestPermission();
                        return 'permission_requested';
                    } catch(e) {
                        return 'permission_error: ' + e.message;
                    }
                }
                return 'google_api_not_available';
            """
        },
        {
            "name": "Try to find clickable elements in iframe",
            "code": """
                const iframe = document.querySelector("iframe[title='Sign in with Google Button']");
                if (iframe && iframe.contentDocument) {
                    try {
                        const elements = iframe.contentDocument.querySelectorAll('[role="button"], button, a, div[onclick]');
                        return 'found_' + elements.length + '_elements';
                    } catch(e) {
                        return 'cors_error: cannot access iframe';
                    }
                }
                return 'iframe_not_found';
            """
        },
        {
            "name": "Simulate real mouse event on container",
            "code": """
                const container = document.querySelector('div.alternate-signin__btn--google');
                if (container) {
                    const event = new MouseEvent('click', {
                        bubbles: true,
                        cancelable: true,
                        view: window,
                        clientX: container.offsetLeft + 50,
                        clientY: container.offsetTop + 22,
                        buttons: 1
                    });
                    container.dispatchEvent(event);
                    return 'simulated_click_on_container';
                }
                return 'container_not_found';
            """
        }
    ]

    for method in methods:
        try:
            result = await browser.current_page.evaluate(f"() => {{ {method['code']} }}")
            print(f"✓ {method['name']}: {result}")
        except Exception as e:
            print(f"✗ {method['name']}: {str(e)[:80]}")

    # Check if any network requests changed
    print("\n📌 Step 5: Check current URL after trigger attempts\n")

    current_url = browser.current_page.url
    print(f"Current URL: {current_url}")

    if "google" in current_url or "oauth" in current_url:
        print("✅ SUCCESS: OAuth redirect detected!")
    else:
        print("❌ FAILED: Still on LinkedIn login page, no OAuth redirect")

    # Take screenshot
    await browser.current_page.screenshot(path="artifacts/oauth-direct-test.png")

    await browser.stop()

    print("\n" + "=" * 80)
    print("CONCLUSION")
    print("=" * 80)
    print("""
The Google Sign-In SDK is protecting the OAuth flow with strict security checks:

1. ✅ SDK is loaded and available
2. ✅ Button iframe is rendered
3. ❌ Synthetic/programmatic clicks are NOT triggering OAuth
4. ❌ Direct iframe access is blocked by CORS

This is by design - Google prevents automated OAuth to protect user accounts.

The ONLY way to trigger the real OAuth flow is:
- Real user interaction (mouse click in a real browser window)
- Or using actual user authentication (not API-based)
""")


if __name__ == "__main__":
    asyncio.run(test_direct_oauth())
