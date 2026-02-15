#!/usr/bin/env python3
"""
Gmail Login - ULTIMATE SOLUTION
Using Phuc Forecast: Trigger ALL validation events properly
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
print("🔐 GMAIL LOGIN - ULTIMATE SOLUTION")
print("="*70)
print("Strategy: Trigger complete validation event chain")
print()

email, password = read_creds()

# Navigate
print("1. Navigate to Gmail...")
requests.post(f"{API}/navigate",
              json={"url": "https://accounts.google.com/ServiceLogin?service=mail"},
              timeout=60)
time.sleep(3)

# Screenshot
requests.get(f"{API}/screenshot", timeout=30)

# ULTIMATE FIX: Trigger complete event chain with JavaScript
print("\n2. Fill email with FULL event chain...")

# JavaScript that triggers ALL validation events
js_fill_and_validate = f"""
async () => {{
    // Find email input
    const input = document.querySelector('input[type="email"]');
    if (!input) throw new Error('Email input not found');

    // Focus the input (triggers focus event)
    input.focus();
    await new Promise(r => setTimeout(r, 100));

    // Clear existing value
    input.value = '';

    // Set the value
    input.value = '{email}';

    // Trigger ALL validation events
    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
    await new Promise(r => setTimeout(r, 50));

    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
    await new Promise(r => setTimeout(r, 50));

    input.dispatchEvent(new KeyboardEvent('keyup', {{ bubbles: true }}));
    await new Promise(r => setTimeout(r, 50));

    // Blur to trigger validation
    input.blur();
    await new Promise(r => setTimeout(r, 200));

    console.log('Email filled and validated');
    return true;
}}
"""

result = requests.post(f"{API}/evaluate",
                      json={"script": js_fill_and_validate},
                      timeout=30)

if result.json().get('success'):
    print("  ✅ Email filled with full validation!")
else:
    print(f"  ❌ Failed: {result.json().get('error')}")
    exit(1)

time.sleep(2)

# Click Next with proper wait
print("\n3. Click Next button (with wait for enabled state)...")

js_click_next = """
async () => {
    // Find Next button
    const buttons = Array.from(document.querySelectorAll('button'));
    const nextBtn = buttons.find(b => b.textContent.toLowerCase().includes('next'));

    if (!nextBtn) throw new Error('Next button not found');

    // Wait for button to be enabled (max 5 seconds)
    for (let i = 0; i < 50; i++) {
        if (!nextBtn.disabled && !nextBtn.hasAttribute('aria-disabled')) {
            break;
        }
        await new Promise(r => setTimeout(r, 100));
    }

    // Scroll into view
    nextBtn.scrollIntoView({ behavior: 'smooth', block: 'center' });
    await new Promise(r => setTimeout(r, 300));

    // Click
    nextBtn.click();

    console.log('Next button clicked');
    return true;
}
"""

result = requests.post(f"{API}/evaluate",
                      json={"script": js_click_next},
                      timeout=30)

if result.json().get('success'):
    print("  ✅ Next clicked!")
else:
    print(f"  ❌ Failed: {result.json().get('error')}")

time.sleep(5)

# Screenshot
screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
print(f"\n📸 Screenshot: {screenshot.get('path')}")

# Check if we're on password page
print("\n4. Checking current page...")
snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
aria = snapshot.get('aria', [])

# Look for password field
password_fields = [n for n in aria if n.get('role') == 'textbox' and
                   'password' in n.get('name', '').lower()]

# Look for blocked message
blocked_keywords = ['couldn\'t sign', 'not secure', 'browser']
is_blocked = any(
    keyword in str(node.get('name', '')).lower()
    for node in aria
    for keyword in blocked_keywords
)

if is_blocked:
    print("\n❌ BLOCKED BY GOOGLE")
    print("Check screenshot for error message")
    exit(1)
elif password_fields:
    print(f"\n✅ SUCCESS! On password page!")
    print(f"   Found password field: {password_fields[0].get('name')}")

    # Fill password with same technique
    print("\n5. Fill password...")

    js_fill_password = f"""
    async () => {{
        const input = document.querySelector('input[type="password"]');
        if (!input) throw new Error('Password input not found');

        input.focus();
        await new Promise(r => setTimeout(r, 100));

        input.value = '{password}';

        input.dispatchEvent(new Event('input', {{ bubbles: true }}));
        await new Promise(r => setTimeout(r, 50));

        input.dispatchEvent(new Event('change', {{ bubbles: true }}));
        await new Promise(r => setTimeout(r, 50));

        input.blur();
        await new Promise(r => setTimeout(r, 200));

        return true;
    }}
    """

    result = requests.post(f"{API}/evaluate",
                          json={"script": js_fill_password},
                          timeout=30)

    if result.json().get('success'):
        print("  ✅ Password filled!")

    time.sleep(1)

    # Click Next/Sign in
    print("\n6. Click Sign in...")

    js_click_signin = """
    async () => {
        const buttons = Array.from(document.querySelectorAll('button'));
        const signinBtn = buttons.find(b => {
            const text = b.textContent.toLowerCase();
            return text.includes('next') || text.includes('sign in');
        });

        if (!signinBtn) throw new Error('Sign in button not found');

        // Wait for enabled
        for (let i = 0; i < 50; i++) {
            if (!signinBtn.disabled) break;
            await new Promise(r => setTimeout(r, 100));
        }

        signinBtn.click();
        return true;
    }
    """

    result = requests.post(f"{API}/evaluate",
                          json={"script": js_click_signin},
                          timeout=30)

    if result.json().get('success'):
        print("  ✅ Sign in clicked!")

    time.sleep(6)

    # Final check
    print("\n7. Final state check...")
    screenshot = requests.get(f"{API}/screenshot", timeout=30).json()
    print(f"📸 Screenshot: {screenshot.get('path')}")

    snapshot = requests.get(f"{API}/snapshot", timeout=30).json()
    aria = snapshot.get('aria', [])

    # Check for Gmail or OAuth
    gmail_keywords = ['inbox', 'compose', 'search mail']
    oauth_keywords = ['verify', 'code', '2-step']

    gmail_elements = [n for n in aria if n.get('name') and
                     any(kw in n.get('name').lower() for kw in gmail_keywords)]
    oauth_elements = [n for n in aria if n.get('name') and
                     any(kw in n.get('name').lower() for kw in oauth_keywords)]

    if gmail_elements:
        print("\n🎉 LOGGED IN TO GMAIL!")

        # Save session
        print("\n💾 Saving session...")
        result = requests.post(f"{API}/save-session", timeout=30).json()
        if result.get('success'):
            print(f"  ✅ Session saved: {result.get('path')}")

    elif oauth_elements:
        print("\n🔐 OAuth/2FA prompt")
        print("Please complete verification, then I'll save the session!")

    else:
        print("\n⚠️  Unknown state - check screenshot")

else:
    print("\n⚠️  Still on email page or unknown state")
    print("Check screenshot")

print("\n" + "="*70)
print("✅ ULTIMATE LOGIN ATTEMPT COMPLETE")
print("="*70)
