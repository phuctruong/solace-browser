#!/usr/bin/env python3

"""
LINKEDIN OAUTH - VERIFICATION TEST
Uses browser DevTools inspection to verify if login actually worked
"""

import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def test_oauth_with_verification():
    """Test OAuth login and verify with network inspection"""

    print("\n" + "=" * 80)
    print("LINKEDIN OAUTH LOGIN - FULL VERIFICATION TEST")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False, debug_ui=False)
    await browser.start()

    # Setup network request/response interception
    network_events = []
    auth_tokens = {}

    def on_response(response):
        """Capture response details"""
        try:
            url = response.url
            status = response.status
            headers = response.headers

            event = {
                "url": url,
                "status": status,
                "method": response.request.method if response.request else "?",
                "headers": dict(headers)
            }

            network_events.append(event)

            # Look for OAuth-related responses
            if "google" in url or "linkedin" in url or "oauth" in url or "auth" in url:
                print(f"🌐 {response.request.method if response.request else 'GET'} {url} -> {status}")

                # Check for auth tokens in response headers
                if "set-cookie" in headers:
                    print(f"   🔐 Set-Cookie: {headers['set-cookie'][:80]}...")
                if "authorization" in headers:
                    print(f"   🔐 Authorization: {headers['authorization'][:80]}...")

        except Exception as e:
            pass

    # Listen for responses
    browser.current_page.on("response", on_response)

    print("=" * 80)
    print("STEP 1: Navigate to LinkedIn Login")
    print("=" * 80 + "\n")

    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)
    print(f"✓ Navigated to LinkedIn login\n")

    # Inspect page state BEFORE clicking
    print("=" * 80)
    print("STEP 2: Inspect Pre-Click State")
    print("=" * 80 + "\n")

    pre_click_state = await browser.current_page.evaluate("""
        () => {
            return {
                title: document.title,
                url: window.location.href,
                cookies: document.cookie,
                localStorage_keys: Object.keys(localStorage),
                sessionStorage_keys: Object.keys(sessionStorage),
                google_sdk: typeof google !== 'undefined',
                buttons_count: document.querySelectorAll('button').length
            };
        }
    """)

    print(f"Page Title: {pre_click_state['title']}")
    print(f"URL: {pre_click_state['url']}")
    print(f"Cookies: {pre_click_state['cookies'][:100] if pre_click_state['cookies'] else '(none)'}")
    print(f"LocalStorage Keys: {pre_click_state['localStorage_keys']}")
    print(f"SessionStorage Keys: {pre_click_state['sessionStorage_keys']}")
    print(f"Google SDK Available: {pre_click_state['google_sdk']}")
    print(f"Buttons on page: {pre_click_state['buttons_count']}\n")

    # Take screenshot before click
    await browser.current_page.screenshot(path="artifacts/oauth-01-before-click.png")
    print("✓ Screenshot: artifacts/oauth-01-before-click.png\n")

    print("=" * 80)
    print("STEP 3: Trigger OAuth Login")
    print("=" * 80 + "\n")

    # Trigger the login
    result = await browser.login_linkedin_google()
    print(f"Login result: {json.dumps(result, indent=2)}\n")

    await asyncio.sleep(2)

    # Take screenshot after click
    await browser.current_page.screenshot(path="artifacts/oauth-02-after-click.png")
    print("✓ Screenshot: artifacts/oauth-02-after-click.png\n")

    # Inspect page state AFTER clicking
    print("=" * 80)
    print("STEP 4: Inspect Post-Click State")
    print("=" * 80 + "\n")

    post_click_state = await browser.current_page.evaluate("""
        () => {
            return {
                title: document.title,
                url: window.location.href,
                cookies: document.cookie,
                localStorage_keys: Object.keys(localStorage),
                sessionStorage_keys: Object.keys(sessionStorage),
                redirected: window.location.href !== 'https://www.linkedin.com/login',
                is_google: 'google.com' in window.location.href,
                is_accounts_google: 'accounts.google.com' in window.location.href
            };
        }
    """)

    print(f"Page Title: {post_click_state['title']}")
    print(f"URL: {post_click_state['url']}")
    print(f"Redirected: {post_click_state['redirected']}")
    print(f"Is Google.com: {post_click_state['is_google']}")
    print(f"Is Accounts.Google.com: {post_click_state['is_accounts_google']}")
    print(f"Cookies Present: {len(post_click_state['cookies']) > 0}")
    print(f"LocalStorage Keys: {post_click_state['localStorage_keys']}")
    print(f"SessionStorage Keys: {post_click_state['sessionStorage_keys']}\n")

    # Check network activity
    print("=" * 80)
    print("STEP 5: Network Traffic Analysis")
    print("=" * 80 + "\n")

    print(f"Total network requests captured: {len(network_events)}\n")

    # Group by domain
    domains = {}
    for event in network_events:
        domain = event["url"].split("/")[2] if "/" in event["url"] else "unknown"
        if domain not in domains:
            domains[domain] = []
        domains[domain].append(event)

    print("Requests by domain:")
    for domain in sorted(domains.keys())[:15]:
        count = len(domains[domain])
        print(f"  {domain}: {count} requests")

    # Look for OAuth-related requests
    print("\nOAuth-related requests:")
    oauth_found = False
    for event in network_events:
        if any(x in event["url"].lower() for x in ["oauth", "authorize", "authenticate", "login", "auth"]):
            print(f"  {event['method']} {event['url']} -> {event['status']}")
            oauth_found = True

    if not oauth_found:
        print("  (none found)")

    # Check for Google auth requests
    print("\nGoogle auth requests:")
    google_found = False
    for event in network_events:
        if "accounts.google.com" in event["url"] or "google.com/signin" in event["url"]:
            print(f"  {event['method']} {event['url']} -> {event['status']}")
            google_found = True

    if not google_found:
        print("  (none found)")

    # Detailed verification
    print("\n" + "=" * 80)
    print("STEP 6: Detailed Verification")
    print("=" * 80 + "\n")

    verification = {
        "page_changed": post_click_state['redirected'],
        "url_changed_to_google": post_click_state['is_google'] or post_click_state['is_accounts_google'],
        "oauth_requests_made": oauth_found,
        "google_auth_requests": google_found,
        "login_result_success": result.get("success", False),
        "expected_oauth_url": post_click_state['is_accounts_google']
    }

    print("Verification Results:")
    for key, value in verification.items():
        status = "✅" if value else "❌"
        print(f"  {status} {key}: {value}")

    # Final verification
    print("\n" + "=" * 80)
    print("STEP 7: Final Verdict")
    print("=" * 80 + "\n")

    if verification["page_changed"] and verification["expected_oauth_url"]:
        print("✅ SUCCESS: OAuth login flow worked!")
        print("   - Page redirected to Google OAuth")
        print("   - Ready for user to enter credentials")
    elif verification["page_changed"] and verification["url_changed_to_google"]:
        print("⚠️  PARTIAL: Page changed but not to expected URL")
        print(f"   - Current URL: {post_click_state['url']}")
    elif verification["oauth_requests_made"] or verification["google_auth_requests"]:
        print("⚠️  PARTIAL: OAuth requests made but page not fully redirected")
        print("   - Network traffic shows OAuth attempts")
        print(f"   - Current URL: {post_click_state['url']}")
    else:
        print("❌ FAILED: OAuth login did not work")
        print("   - No page redirect detected")
        print("   - No OAuth network requests found")
        print(f"   - Current URL: {post_click_state['url']}")
        print("   - Check browser window for any error messages")

    # Save detailed report
    report = {
        "timestamp": "",
        "pre_click_state": pre_click_state,
        "post_click_state": post_click_state,
        "login_result": result,
        "verification": verification,
        "network_summary": {
            "total_requests": len(network_events),
            "domains": list(domains.keys()),
            "oauth_requests_found": oauth_found,
            "google_auth_found": google_found
        }
    }

    with open("artifacts/oauth-verification-report.json", "w") as f:
        json.dump(report, f, indent=2)

    print("\n✓ Detailed report saved to: artifacts/oauth-verification-report.json\n")

    # Keep browser open if login was successful
    if verification["page_changed"]:
        print("=" * 80)
        print("Browser showing OAuth page. Press Ctrl+C to close.")
        print("=" * 80)
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass

    await browser.stop()


if __name__ == "__main__":
    asyncio.run(test_oauth_with_verification())
