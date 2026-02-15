#!/usr/bin/env python3

import asyncio
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from solace_browser_server import SolaceBrowser


async def debug_google_oauth():
    """Debug LinkedIn's Google OAuth configuration"""

    print("\n" + "=" * 80)
    print("DEBUGGING: LinkedIn Google OAuth Configuration")
    print("=" * 80 + "\n")

    browser = SolaceBrowser(headless=False, debug_ui=False)
    await browser.start()

    print("📌 Navigating to LinkedIn login page...")
    await browser.current_page.goto("https://www.linkedin.com/login", wait_until='networkidle')
    await asyncio.sleep(3)

    print("✓ Page loaded\n")

    # Check the Google SDK configuration
    print("📌 Checking Google SDK configuration...")
    config = await browser.current_page.evaluate("""
        () => {
            const result = {
                googleLibraryLoaded: typeof gapi !== 'undefined',
                googleAccountsLoaded: typeof google !== 'undefined' && typeof google.accounts !== 'undefined',
                googleSignInLoaded: typeof google !== 'undefined' && typeof google.accounts !== 'undefined' && typeof google.accounts.id !== 'undefined'
            };

            // Try to get OAuth client ID
            const scripts = document.querySelectorAll('script');
            for (let script of scripts) {
                if (script.src && script.src.includes('gsi')) {
                    result.gsiScript = script.src;
                }
            }

            // Check for any stored credentials or tokens
            result.localStorage = {};
            for (let key in localStorage) {
                if (key.includes('google') || key.includes('auth') || key.includes('oauth')) {
                    result.localStorage[key] = localStorage.getItem(key).substring(0, 50);
                }
            }

            return result;
        }
    """)

    print(f"Google SDK Info: {config}\n")

    # Try to find the OAuth redirect URL
    print("📌 Searching for OAuth redirect URLs...")
    links = await browser.current_page.evaluate("""
        () => {
            const oauthLinks = [];

            // Check all links
            const allLinks = document.querySelectorAll('a, button, div[role="button"]');
            for (let el of allLinks) {
                const href = el.getAttribute('href') || '';
                const onclick = el.getAttribute('onclick') || '';
                const text = el.textContent.toLowerCase();

                if (href.includes('google') || href.includes('oauth') ||
                    onclick.includes('google') || onclick.includes('oauth') ||
                    text.includes('google')) {
                    oauthLinks.push({
                        tag: el.tagName,
                        text: el.textContent.substring(0, 30),
                        href: href.substring(0, 100),
                        onclick: onclick.substring(0, 100)
                    });
                }
            }

            return oauthLinks.slice(0, 10);
        }
    """)

    print(f"OAuth-related elements found:")
    for link in links:
        print(f"  - {link}")

    # Try to trigger the Google Sign-In manually
    print("\n📌 Attempting manual OAuth flow...")
    try:
        # Try to call the Google SDK function directly
        result = await browser.current_page.evaluate("""
            async () => {
                // Check if Google Sign-In SDK is loaded
                if (typeof google !== 'undefined' && google.accounts && google.accounts.id) {
                    // Try to trigger the One Tap UI or sign-in flow
                    if (google.accounts.id.prompt) {
                        console.log('Google One Tap available');
                        google.accounts.id.prompt((notification) => {
                            console.log('One Tap notification:', notification);
                        });
                        return 'one_tap_triggered';
                    }

                    if (google.accounts.id.renderButton) {
                        console.log('renderButton available');
                        // Try to render the button again to trigger it
                        return 'render_button_available';
                    }
                }

                return 'google_sdk_not_available';
            }
        """)

        print(f"Manual trigger result: {result}\n")

    except Exception as e:
        print(f"Error triggering manual flow: {e}\n")

    # Check if there's a way to navigate directly to Google OAuth
    print("📌 Checking for direct OAuth URLs...")
    direct_oauth = await browser.current_page.evaluate("""
        () => {
            // LinkedIn usually has the OAuth client ID in the page source or data attributes
            const clientId = document.querySelector('[data-client-id]')?.getAttribute('data-client-id');
            const stateToken = document.querySelector('[data-state]')?.getAttribute('data-state');

            // Check all data attributes
            let iframeContainer = document.querySelector('div.alternate-signin__btn--google');
            let attributes = {};
            if (iframeContainer) {
                for (let attr of iframeContainer.attributes) {
                    attributes[attr.name] = attr.value;
                }
            }

            return {
                clientId,
                stateToken,
                iframeAttributes: attributes
            };
        }
    """)

    print(f"OAuth configuration: {direct_oauth}\n")

    print("📌 Checking network requests (from localStorage/sessionStorage)...")
    storage = await browser.current_page.evaluate("""
        () => {
            const result = {};

            // Check sessionStorage for any OAuth tokens or state
            for (let i = 0; i < sessionStorage.length; i++) {
                const key = sessionStorage.key(i);
                if (key.includes('oauth') || key.includes('google') || key.includes('state')) {
                    result[key] = sessionStorage.getItem(key).substring(0, 100);
                }
            }

            return result;
        }
    """)

    if Object(storage):
        print(f"Session storage: {storage}")
    else:
        print("No OAuth-related data in sessionStorage")

    await browser.stop()
    print("\n✓ Debug complete\n")


if __name__ == "__main__":
    asyncio.run(debug_google_oauth())
