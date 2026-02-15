#!/usr/bin/env python3
"""
Gmail Master Automation - Headless Mode
Ultimate test: OAuth flow + session persistence + self-learning

Flow:
1. Read credentials.properties
2. Navigate to Gmail (headless)
3. Fill username/password
4. Detect OAuth/2FA prompt
5. Ask user for code
6. Complete login
7. Save cookies
8. Explore Gmail interface
9. Benchmark operations
10. Create recipes/skills
"""

import requests
import time
import json
import configparser
from pathlib import Path

API = "http://localhost:9222"
SESSION_FILE = "artifacts/gmail_session.json"

def read_credentials():
    """Read Gmail credentials from properties file"""
    config = configparser.ConfigParser()
    config.read('credentials.properties')

    return {
        'email': config.get('gmail', 'email'),
        'password': config.get('gmail', 'password')
    }

def timed_step(name, func):
    """Time and log each step"""
    print(f"\n{'='*70}")
    print(f"📍 {name}")
    print('='*70)
    start = time.time()
    result = func()
    duration = time.time() - start
    print(f"✅ Completed in {duration:.2f}s")
    return result, duration

def main():
    print("\n" + "="*70)
    print("🚀 GMAIL MASTER AUTOMATION - HEADLESS MODE")
    print("="*70)
    print("Ultimate Test: OAuth + Session + Self-Learning")
    print()

    # Check browser
    health = requests.get(f"{API}/health", timeout=10).json()
    if health.get('status') != 'ok':
        print("❌ Browser server not running")
        print("Start with: python3 persistent_browser_server.py --headless")
        return

    print("✅ Headless browser ready\n")

    # Read credentials
    creds = read_credentials()
    print(f"📧 Email: {creds['email']}")
    print(f"🔑 Password: {'*' * len(creds['password'])}\n")

    timings = {}

    # Step 1: Navigate to Gmail
    def navigate():
        result = requests.post(f"{API}/navigate",
                              json={"url": "https://mail.google.com"},
                              timeout=30)
        return result.json()

    result, duration = timed_step("Navigate to Gmail", navigate)
    timings['navigate'] = duration

    time.sleep(2)  # Wait for page load

    # Take screenshot to see what we got
    print("\n📸 Taking screenshot of current page...")
    screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
    print(f"   Saved: {screenshot.get('path')}")

    # Step 2: Get ARIA snapshot to understand the page
    def get_snapshot():
        snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
        aria = snapshot.get('aria', [])

        # Look for login-related elements
        login_elements = [n for n in aria if n.get('name') and
                         any(keyword in n['name'].lower()
                             for keyword in ['email', 'username', 'sign in', 'next'])]

        print(f"\n   Found {len(aria)} ARIA nodes")
        print(f"   Login-related elements: {len(login_elements)}")

        if login_elements:
            print("\n   Login elements found:")
            for elem in login_elements[:5]:
                print(f"   - {elem.get('ref')}: {elem.get('role')} - {elem.get('name')}")

        return snapshot

    snapshot, duration = timed_step("Get ARIA Snapshot", get_snapshot)
    timings['aria_snapshot'] = duration

    # Step 3: Find and fill email field
    print("\n" + "="*70)
    print("📧 STEP 3: Fill Email")
    print("="*70)

    # Try multiple strategies to find email field
    email_selectors = [
        'role=textbox[name="Email"]',
        'role=textbox[name="Email or phone"]',
        'input[type="email"]',
        'input[name="identifier"]',
        '#identifierId'
    ]

    email_filled = False
    for selector in email_selectors:
        print(f"\n   Trying selector: {selector}")
        result = requests.post(f"{API}/fill",
                              json={"selector": selector, "text": creds['email']},
                              timeout=30)

        if result.json().get('success'):
            print(f"   ✅ Email filled with: {selector}")
            email_filled = True
            break
        else:
            print(f"   ❌ Failed: {result.json().get('error', 'unknown')[:50]}")

    if not email_filled:
        print("\n⚠️  Could not fill email - check screenshot")
        print("Continuing anyway to see what we can learn...")

    time.sleep(1)

    # Step 4: Click Next button
    print("\n" + "="*70)
    print("▶️  STEP 4: Click Next")
    print("="*70)

    next_selectors = [
        'role=button[name="Next"]',
        'role=button[name=/next/i]',
        'button:has-text("Next")',
        '#identifierNext'
    ]

    next_clicked = False
    for selector in next_selectors:
        print(f"\n   Trying selector: {selector}")
        result = requests.post(f"{API}/click",
                              json={"selector": selector},
                              timeout=30)

        if result.json().get('success'):
            print(f"   ✅ Next clicked with: {selector}")
            next_clicked = True
            break

    if not next_clicked:
        print("\n⚠️  Could not click Next")

    time.sleep(2)  # Wait for password page

    # Take screenshot
    screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
    print(f"\n📸 Screenshot: {screenshot.get('path')}")

    # Step 5: Fill password
    print("\n" + "="*70)
    print("🔑 STEP 5: Fill Password")
    print("="*70)

    password_selectors = [
        'role=textbox[name="Enter your password"]',
        'role=textbox[name="Password"]',
        'input[type="password"]',
        'input[name="password"]',
        '#password input'
    ]

    password_filled = False
    for selector in password_selectors:
        print(f"\n   Trying selector: {selector}")
        result = requests.post(f"{API}/fill",
                              json={"selector": selector, "text": creds['password']},
                              timeout=30)

        if result.json().get('success'):
            print(f"   ✅ Password filled")
            password_filled = True
            break

    time.sleep(1)

    # Step 6: Click Next/Login
    print("\n" + "="*70)
    print("🔓 STEP 6: Click Login")
    print("="*70)

    login_selectors = [
        'role=button[name="Next"]',
        'role=button[name="Sign in"]',
        'button:has-text("Next")',
        '#passwordNext'
    ]

    for selector in login_selectors:
        print(f"\n   Trying selector: {selector}")
        result = requests.post(f"{API}/click",
                              json={"selector": selector},
                              timeout=30)

        if result.json().get('success'):
            print(f"   ✅ Login clicked")
            break

    time.sleep(3)  # Wait for OAuth/2FA or success

    # Step 7: Check what we got
    print("\n" + "="*70)
    print("🔍 STEP 7: Check Current State")
    print("="*70)

    # Take screenshot
    screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
    print(f"\n📸 Screenshot: {screenshot.get('path')}")

    # Get current URL
    # Get snapshot to see what's on page
    snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
    aria = snapshot.get('aria', [])

    # Check for OAuth/2FA indicators
    oauth_indicators = [n for n in aria if n.get('name') and
                       any(keyword in n['name'].lower()
                           for keyword in ['verify', 'code', '2-step', 'authentication',
                                         'phone', 'backup', 'security'])]

    if oauth_indicators:
        print("\n🔐 OAuth/2FA DETECTED!")
        print("\n   OAuth-related elements:")
        for elem in oauth_indicators[:10]:
            print(f"   - {elem.get('name')}")

        print("\n" + "="*70)
        print("⏸️  PAUSED: USER ACTION REQUIRED")
        print("="*70)
        print("\nI've detected an OAuth/2FA prompt.")
        print("Please check your phone/email for the verification code.")
        print("\nOnce you have the code, I'll:")
        print("1. Fill the code")
        print("2. Complete login")
        print("3. Save session cookies")
        print("4. Continue with Gmail exploration")
        print("\nScreenshot saved to see what prompt you got!")

    else:
        # Check if we're logged in (look for Gmail interface)
        gmail_indicators = [n for n in aria if n.get('name') and
                           any(keyword in n['name'].lower()
                               for keyword in ['inbox', 'compose', 'search mail',
                                             'primary', 'starred'])]

        if gmail_indicators:
            print("\n✅ LOGGED IN SUCCESSFULLY!")
            print("\n   Gmail interface detected:")
            for elem in gmail_indicators[:10]:
                print(f"   - {elem.get('name')}")

            # Save session
            print("\n💾 Saving session cookies...")
            save_result = requests.post(f"{API}/save-session", timeout=30).json()
            if save_result.get('success'):
                print(f"   ✅ Session saved to: {SESSION_FILE}")

        else:
            print("\n⚠️  Unknown state - check screenshot")
            print(f"   Found {len(aria)} ARIA nodes")

    # Summary
    print("\n" + "="*70)
    print("📊 TIMING SUMMARY")
    print("="*70)
    for step, duration in timings.items():
        print(f"   {step}: {duration:.2f}s")

    print("\n" + "="*70)
    print("✅ Gmail Login Attempt Complete")
    print("="*70)
    print("\nNext steps:")
    print("1. Check screenshot to see current state")
    print("2. If OAuth prompt: provide code when ready")
    print("3. If logged in: start Gmail exploration")
    print("4. Benchmark operations")
    print("5. Create recipes + skills")

if __name__ == "__main__":
    main()
