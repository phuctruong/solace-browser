#!/usr/bin/env python3
"""
Gmail Login - Step by Step with ARIA-first approach
Applying LinkedIn learnings: Get ARIA snapshot first, use role selectors
"""

import requests
import time
import configparser

API = "http://localhost:9222"

def read_creds():
    config = configparser.ConfigParser()
    config.read('credentials.properties')
    return config.get('gmail', 'email'), config.get('gmail', 'password')

print("="*70)
print("🔐 GMAIL LOGIN - STEP BY STEP")
print("="*70)

email, password = read_creds()
print(f"\n📧 Email: {email}")
print(f"🔑 Password: {'*' * len(password)}\n")

# Step 1: Navigate
print("Step 1: Navigate to Gmail...")
requests.post(f"{API}/navigate", json={"url": "https://mail.google.com"}, timeout=30)
time.sleep(3)

# Step 2: Screenshot
screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
print(f"  📸 Screenshot: {screenshot.get('path')}")

# Step 3: Get ARIA to find email field
print("\nStep 2: Get ARIA snapshot to find email field...")
snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
aria = snapshot.get('aria', [])

# Find textbox elements
textboxes = [n for n in aria if n.get('role') == 'textbox']
print(f"  Found {len(textboxes)} textbox elements:")
for tb in textboxes[:5]:
    print(f"  - {tb.get('ref')}: {tb.get('name')} (value: {tb.get('value', '')})")

# Find the email textbox
email_field = None
for tb in textboxes:
    name = tb.get('name', '').lower()
    if 'email' in name or 'phone' in name:
        email_field = tb
        break

if email_field:
    print(f"\n✅ Found email field: {email_field.get('name')}")
    email_selector = f"role=textbox[name=\"{email_field.get('name')}\"]"
    print(f"  Selector: {email_selector}")

    # Fill email
    print("\nStep 3: Fill email...")
    result = requests.post(f"{API}/fill",
                          json={"selector": email_selector, "text": email},
                          timeout=60)  # Increased timeout

    if result.json().get('success'):
        print(f"  ✅ Email filled!")
    else:
        print(f"  ❌ Failed: {result.json().get('error')}")
        print("\n  Trying fallback selector...")
        result = requests.post(f"{API}/fill",
                              json={"selector": "input[type='email']", "text": email},
                              timeout=60)
        if result.json().get('success'):
            print(f"  ✅ Email filled with fallback!")

    time.sleep(1)

    # Find and click Next button
    print("\nStep 4: Find and click Next button...")
    buttons = [n for n in aria if n.get('role') == 'button' and
               n.get('name') and 'next' in n.get('name').lower()]

    if buttons:
        next_btn = buttons[0]
        print(f"  Found: {next_btn.get('name')}")
        next_selector = f"role=button[name=\"{next_btn.get('name')}\"]"

        result = requests.post(f"{API}/click",
                              json={"selector": next_selector},
                              timeout=60)
        if result.json().get('success'):
            print(f"  ✅ Next clicked!")
        else:
            print(f"  ❌ Click failed, trying fallback...")
            requests.post(f"{API}/click",
                         json={"selector": "button:has-text('Next')"},
                         timeout=60)

    time.sleep(3)  # Wait for password page

    # Screenshot after Next
    screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
    print(f"\n  📸 Screenshot: {screenshot.get('path')}")

    # Step 5: Get new ARIA snapshot for password page
    print("\nStep 5: Get ARIA for password page...")
    snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
    aria = snapshot.get('aria', [])

    # Find password textbox
    textboxes = [n for n in aria if n.get('role') == 'textbox']
    print(f"  Found {len(textboxes)} textboxes")

    password_field = None
    for tb in textboxes:
        name = tb.get('name', '').lower()
        if 'password' in name:
            password_field = tb
            break

    if password_field:
        print(f"\n✅ Found password field: {password_field.get('name')}")
        password_selector = f"role=textbox[name=\"{password_field.get('name')}\"]"

        print("\nStep 6: Fill password...")
        result = requests.post(f"{API}/fill",
                              json={"selector": password_selector, "text": password},
                              timeout=60)

        if result.json().get('success'):
            print(f"  ✅ Password filled!")
        else:
            print(f"  ❌ Failed, trying fallback...")
            requests.post(f"{API}/fill",
                         json={"selector": "input[type='password']", "text": password},
                         timeout=60)

        time.sleep(1)

        # Find and click Next/Sign in
        print("\nStep 7: Click Next/Sign in...")
        buttons = [n for n in aria if n.get('role') == 'button']
        next_buttons = [b for b in buttons if b.get('name') and
                       any(word in b.get('name').lower() for word in ['next', 'sign in'])]

        if next_buttons:
            btn = next_buttons[0]
            print(f"  Found: {btn.get('name')}")
            selector = f"role=button[name=\"{btn.get('name')}\"]"
            requests.post(f"{API}/click", json={"selector": selector}, timeout=60)
            print(f"  ✅ Clicked!")

        time.sleep(5)  # Wait for OAuth/2FA or inbox

        # Final state
        print("\n" + "="*70)
        print("🔍 FINAL STATE CHECK")
        print("="*70)

        screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
        print(f"\n📸 Final screenshot: {screenshot.get('path')}")

        # Get ARIA to check state
        snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
        aria = snapshot.get('aria', [])

        # Check for OAuth
        oauth_keywords = ['verify', 'code', '2-step', 'phone', 'security', 'recovery']
        oauth_elements = [n for n in aria if n.get('name') and
                         any(kw in n.get('name').lower() for kw in oauth_keywords)]

        # Check for Gmail
        gmail_keywords = ['inbox', 'compose', 'primary', 'starred', 'search mail']
        gmail_elements = [n for n in aria if n.get('name') and
                         any(kw in n.get('name').lower() for kw in gmail_keywords)]

        if gmail_elements:
            print("\n✅ LOGGED IN TO GMAIL!")
            print("\nGmail elements found:")
            for elem in gmail_elements[:10]:
                print(f"  - {elem.get('name')}")

            # Save session
            print("\n💾 Saving session...")
            result = requests.post(f"{API}/save-session", timeout=30).json()
            if result.get('success'):
                print(f"  ✅ Session saved!")

        elif oauth_elements:
            print("\n🔐 OAUTH/2FA PROMPT DETECTED")
            print("\nOAuth elements:")
            for elem in oauth_elements[:10]:
                print(f"  - {elem.get('name')}")

            print("\n" + "="*70)
            print("⏸️  PAUSED FOR USER ACTION")
            print("="*70)
            print("\nPlease check the screenshot and provide:")
            print("1. The verification code (if 2FA)")
            print("2. Or approve on your phone")
            print("\nOnce done, run the continuation script!")

        else:
            print("\n⚠️  UNKNOWN STATE")
            print(f"  Found {len(aria)} ARIA elements")
            print("  Check screenshot to see current page")

else:
    print("\n❌ Could not find email field")

print("\n" + "="*70)
print("✅ LOGIN ATTEMPT COMPLETE")
print("="*70)
